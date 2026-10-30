"""
منطق LTI 1.3: بناء JWKS الخاص بأداتنا، إدارة حالة OIDC أحادية الاستخدام،
والتحقق من id_token اللي ترسله منصة LMS (Moodle/Canvas) بعد المصادقة.

ملاحظة صادقة: هذا تطبيق متوافق مع مواصفة LTI 1.3 حسب توثيقها الرسمي (IMS Global)،
لكن ما قدرت أختبره فعليًا مقابل منصة Moodle/Canvas حقيقية — لازم تختبره بحساب
تجريبي (Moodle sandbox) قبل الاعتماد عليه بالإنتاج، ومن المتوقع تحتاج تعديلات
طفيفة حسب تفاصيل المنصة اللي تربطها.
"""
import base64
import hashlib
import ipaddress
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.config import settings

LTI_STATE_TTL_SECONDS = 600  # 10 دقايق كافية لإكمال تدفق OIDC
LTI_AUTH_CODE_TTL_SECONDS = 60  # رمز تبادل الدخول صالح لدقيقة واحدة


def validate_lti_platform_endpoint_url(url: str) -> str:
    """Allow HTTPS LMS endpoints; allow HTTP loopback only outside production."""
    if not isinstance(url, str) or not url or len(url) > 2000:
        raise ValueError("LTI platform endpoint URL is empty or too long")
    parsed = urlsplit(url)
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("LTI platform endpoint URL is malformed")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("LTI platform endpoint URL has an invalid port") from exc

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower().rstrip(".")
    local_http_allowed = (
        settings.ENVIRONMENT.strip().lower() in {"development", "test", "testing"}
        and hostname in {"localhost", "127.0.0.1", "::1"}
    )
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    # Do not let an admin-configured endpoint target private, loopback, link-local,
    # multicast, or reserved IP literals. HTTP loopback remains available for local tests.
    local_hostname = (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    )
    if local_hostname and not local_http_allowed:
        raise ValueError("LTI platform endpoints cannot target local hostnames")

    if address is not None and not address.is_global:
        if not (scheme == "http" and local_http_allowed and address.is_loopback):
            raise ValueError("LTI platform endpoints cannot target non-public IP addresses")

    if scheme != "https" and not (scheme == "http" and local_http_allowed):
        raise ValueError("LTI platform endpoints must use HTTPS outside local development")
    return url


def long_to_base64url(value: int) -> bytes:
    """Encode an unsigned integer as unpadded base64url for a JSON Web Key."""
    if value < 0:
        raise ValueError("JWK integer values must be non-negative")
    length = max(1, (value.bit_length() + 7) // 8)
    raw = value.to_bytes(length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def hash_opaque_token(token: str) -> str:
    """يُخزَّن hash الرموز العشوائية بدل قيمتها الخام في قاعدة البيانات."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_tool_jwks() -> dict:
    """يبني JWKS العام لأداتنا من المفتاح الخاص بالإعدادات — تعرضه منصات LMS
    وقت التحقق من client assertions نرسلها لهم (تصحيح الدرجات مثلًا)"""
    if not settings.LTI_TOOL_PRIVATE_KEY:
        return {"keys": []}

    private_key = serialization.load_pem_private_key(
        settings.LTI_TOOL_PRIVATE_KEY.encode(), password=None
    )
    public_numbers = private_key.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": settings.LTI_TOOL_KID,
                "n": long_to_base64url(public_numbers.n).decode(),
                "e": long_to_base64url(public_numbers.e).decode(),
            }
        ]
    }


async def fetch_platform_public_key(jwks_url: str, kid: str):
    """يجيب مفتاح المنصة العام من jwks_url بتاعها، مطابق للـ kid المذكور بالـ id_token"""
    validate_lti_platform_endpoint_url(jwks_url)
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
    keys = response.json().get("keys", [])
    matching_key = next((k for k in keys if k.get("kid") == kid), None)
    if not matching_key:
        raise ValueError("ما لقينا مفتاح مطابق بـ JWKS الخاص بالمنصة")
    return matching_key


async def verify_platform_id_token(
    id_token: str, platform, expected_nonce: str, expected_target_link_uri: str
) -> dict:
    """Verify signature, OIDC claims, and the required LTI Resource Link message claims."""
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("id_token is missing kid")

    platform_jwk = await fetch_platform_public_key(platform.jwks_url, kid)
    public_key = jwk.construct(platform_jwk, algorithm="RS256")
    claims = jwt.decode(
        id_token,
        public_key.to_dict(),
        algorithms=["RS256"],
        audience=platform.client_id,
        issuer=platform.issuer,
        options={"verify_at_hash": False},
    )

    message_type_claim = "https://purl.imsglobal.org/spec/lti/claim/message_type"
    version_claim = "https://purl.imsglobal.org/spec/lti/claim/version"
    target_link_claim = "https://purl.imsglobal.org/spec/lti/claim/target_link_uri"
    resource_link_claim = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
    required_claims = (
        "iss",
        "aud",
        "sub",
        "exp",
        "iat",
        "nonce",
        message_type_claim,
        version_claim,
        target_link_claim,
        resource_link_claim,
    )
    if any(name not in claims for name in required_claims):
        raise ValueError("id_token is missing a required LTI claim")

    # OIDC requires azp to be checked for multi-audience ID tokens.
    authorized_party = claims.get("azp")
    audience = claims["aud"]
    if authorized_party is not None and authorized_party != platform.client_id:
        raise ValueError("azp does not match the registered client_id")
    if isinstance(audience, list) and len(audience) > 1 and authorized_party != platform.client_id:
        raise ValueError("multi-valued aud requires azp to match the registered client_id")

    if claims.get(message_type_claim) != "LtiResourceLinkRequest":
        raise ValueError("unsupported LTI message type")
    if claims.get(version_claim) != "1.3.0":
        raise ValueError("unsupported LTI version")

    resource_link = claims.get(resource_link_claim)
    if not isinstance(resource_link, dict):
        raise ValueError("resource_link claim must be an object")
    resource_link_id = resource_link.get("id")
    if (
        not isinstance(resource_link_id, str)
        or not resource_link_id
        or len(resource_link_id) > 255
        or not resource_link_id.isascii()
    ):
        raise ValueError("resource_link.id is invalid")

    now = datetime.now(timezone.utc).timestamp()
    issued_at = claims["iat"]
    expires_at = claims["exp"]
    if (
        isinstance(issued_at, bool)
        or not isinstance(issued_at, (int, float))
        or isinstance(expires_at, bool)
        or not isinstance(expires_at, (int, float))
        or expires_at <= now
        or issued_at > now + 60
        or expires_at <= issued_at
    ):
        raise ValueError("id_token time claims are invalid")

    if not isinstance(claims["sub"], str) or not claims["sub"] or len(claims["sub"]) > 255:
        raise ValueError("sub is invalid")
    if claims.get("nonce") != expected_nonce:
        raise ValueError("nonce does not match the stored OIDC state")
    if claims.get(target_link_claim) != expected_target_link_uri:
        raise ValueError("target_link_uri does not match the stored OIDC state")

    deployment_claim = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
    if claims.get(deployment_claim) != platform.deployment_id:
        raise ValueError("deployment_id does not match the registered platform")

    return claims

def new_nonce() -> str:
    return uuid.uuid4().hex
