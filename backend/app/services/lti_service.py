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
import uuid

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.config import settings

LTI_STATE_TTL_SECONDS = 600  # 10 دقايق كافية لإكمال تدفق OIDC
LTI_AUTH_CODE_TTL_SECONDS = 60  # رمز تبادل الدخول صالح لدقيقة واحدة


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
    """يتحقق من توقيع id_token القادم من منصة LMS، والمُصدر، والجمهور، والـ nonce.
    يرجّع المطالبات (claims) بعد التحقق، أو يرمي استثناء لو أي فحص فشل."""
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("id_token بدون kid — ما نقدر نحدد مفتاح التحقق")

    platform_jwk = await fetch_platform_public_key(platform.jwks_url, kid)
    public_key = jwk.construct(platform_jwk, algorithm="RS256")

    claims = jwt.decode(
        id_token, public_key.to_dict(), algorithms=["RS256"],
        audience=platform.client_id, issuer=platform.issuer,
        options={"verify_at_hash": False},
    )

    if claims.get("nonce") != expected_nonce:
        raise ValueError("nonce غير مطابق — احتمال إعادة تشغيل الطلب (replay)")

    target_link_claim = "https://purl.imsglobal.org/spec/lti/claim/target_link_uri"
    if claims.get(target_link_claim) != expected_target_link_uri:
        raise ValueError("target_link_uri غير مطابق لحالة OIDC المحفوظة")

    deployment_claim = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
    if claims.get(deployment_claim) != platform.deployment_id:
        raise ValueError("deployment_id غير مطابق للمنصة المسجّلة")

    return claims


def new_nonce() -> str:
    return uuid.uuid4().hex
