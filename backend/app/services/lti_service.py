"""
منطق LTI 1.3: بناء JWKS الخاص بأداتنا، إدارة حالة OIDC أحادية الاستخدام،
والتحقق من id_token اللي ترسله منصة LMS (Moodle/Canvas) بعد المصادقة.

ملاحظة صادقة: هذا تطبيق متوافق مع مواصفة LTI 1.3 حسب توثيقها الرسمي (IMS Global)،
لكن ما قدرت أختبره فعليًا مقابل منصة Moodle/Canvas حقيقية — لازم تختبره بحساب
تجريبي (Moodle sandbox) قبل الاعتماد عليه بالإنتاج، ومن المتوقع تحتاج تعديلات
طفيفة حسب تفاصيل المنصة اللي تربطها.
"""
import asyncio
import base64
import hashlib
import ipaddress
import json
import socket
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.config import settings

LTI_STATE_TTL_SECONDS = 600  # 10 دقايق كافية لإكمال تدفق OIDC
LTI_AUTH_CODE_TTL_SECONDS = 60  # رمز تبادل الدخول صالح لدقيقة واحدة


def validate_lti_platform_endpoint_url(url: str) -> str:
    """Validate an LMS endpoint's URL syntax and reject unsafe literal/local hosts."""
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
        and scheme == "http"
        and hostname in {"localhost", "127.0.0.1", "::1"}
    )
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    local_hostname = (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    )
    if local_hostname and not local_http_allowed:
        raise ValueError("LTI platform endpoints cannot target local hostnames")

    if address is not None and not address.is_global:
        if not (local_http_allowed and address.is_loopback):
            raise ValueError("LTI platform endpoints cannot target non-public IP addresses")

    if scheme != "https" and not local_http_allowed:
        raise ValueError("LTI platform endpoints must use HTTPS outside local development")
    return url


def _validate_lti_resolved_addresses(addresses: list[str], *, allow_loopback: bool = False):
    """Fail closed unless every DNS result is public (or explicit local test loopback)."""
    if not addresses:
        raise ValueError("LTI platform hostname resolved to no addresses")

    validated = []
    for candidate in addresses:
        try:
            address = ipaddress.ip_address(candidate.split("%", 1)[0])
        except ValueError as exc:
            raise ValueError("LTI platform hostname resolved to an invalid IP address") from exc

        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped

        if not address.is_global and not (allow_loopback and address.is_loopback):
            raise ValueError("LTI platform hostname resolves to a non-public IP address")
        validated.append(address)

    return validated


def _pin_lti_endpoint_url(url: str, resolved_addresses: list[str]):
    """Pin the HTTP connection to a checked IP while retaining the original Host and TLS SNI."""
    validate_lti_platform_endpoint_url(url)
    parsed = urlsplit(url)
    hostname = parsed.hostname.lower().rstrip(".")
    environment = settings.ENVIRONMENT.strip().lower()
    allow_loopback = (
        parsed.scheme.lower() == "http"
        and environment in {"development", "test", "testing"}
        and hostname in {"localhost", "127.0.0.1", "::1"}
    )
    addresses = _validate_lti_resolved_addresses(
        resolved_addresses, allow_loopback=allow_loopback
    )
    selected = addresses[0]
    pinned_host = f"[{selected.compressed}]" if isinstance(selected, ipaddress.IPv6Address) else selected.compressed
    port_suffix = f":{parsed.port}" if parsed.port is not None else ""
    pinned_url = urlunsplit(
        (parsed.scheme.lower(), f"{pinned_host}{port_suffix}", parsed.path or "/", "", "")
    )
    headers = {"Host": parsed.netloc}
    extensions = {"sni_hostname": hostname} if parsed.scheme.lower() == "https" else {}
    return pinned_url, headers, extensions


async def resolve_lti_platform_endpoint_url(url: str):
    """Resolve DNS once, validate every answer, and return a connection pinned to a safe IP."""
    validate_lti_platform_endpoint_url(url)
    parsed = urlsplit(url)
    hostname = parsed.hostname.lower().rstrip(".")
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None

    if literal is not None:
        resolved_addresses = [literal.compressed]
    else:
        try:
            records = await asyncio.get_running_loop().getaddrinfo(
                hostname, port, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            raise ValueError("Unable to resolve LTI platform hostname safely") from exc
        resolved_addresses = list(dict.fromkeys(record[4][0] for record in records))

    return _pin_lti_endpoint_url(url, resolved_addresses)


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
    """Fetch a bounded JWKS response over a DNS-pinned, public-IP-only connection."""
    pinned_url, headers, extensions = await resolve_lti_platform_endpoint_url(jwks_url)
    content = bytearray()
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        async with client.stream(
            "GET", pinned_url, headers=headers, extensions=extensions
        ) as response:
            if 300 <= response.status_code < 400:
                raise ValueError("LTI JWKS endpoint redirects are not allowed")
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > 1024 * 1024:
                    raise ValueError("LTI JWKS response exceeds the 1 MiB limit")

    try:
        document = json.loads(bytes(content))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("LTI JWKS response is not valid JSON") from exc

    keys = document.get("keys") if isinstance(document, dict) else None
    if not isinstance(keys, list):
        raise ValueError("LTI JWKS response does not contain a keys array")
    matching_key = next((key for key in keys if isinstance(key, dict) and key.get("kid") == kid), None)
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


# LTI Assignment and Grade Services (AGS) 2.0
AGS_ENDPOINT_CLAIM = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
AGS_RESOURCE_LINK_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
AGS_SCORE_SCOPE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
AGS_MAX_RESPONSE_BYTES = 1024 * 1024
AGS_MAX_DELIVERY_ATTEMPTS = 8


def validate_lti_ags_lineitem_url(url: str, platform) -> str:
    """Accept only a safe HTTPS lineitem endpoint on the registered token-server origin."""
    clean_url = validate_lti_platform_endpoint_url(url)
    parsed = urlsplit(clean_url)
    token_endpoint = urlsplit(platform.auth_token_url)

    def effective_port(parts):
        return parts.port or (443 if parts.scheme.lower() == "https" else 80)

    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname is None
        or token_endpoint.hostname is None
        or parsed.hostname.lower().rstrip(".") != token_endpoint.hostname.lower().rstrip(".")
        or effective_port(parsed) != effective_port(token_endpoint)
    ):
        raise ValueError("LTI AGS lineitem must use the registered platform token endpoint origin")
    return clean_url


def record_lti_ags_launch_context(db, platform, claims: dict) -> bool:
    """Record score permission only for a pre-registered resource link and trusted LMS origin."""
    from app.models.lti import LTIAssignmentLink

    resource = claims.get(AGS_RESOURCE_LINK_CLAIM)
    resource_link_id = resource.get("id") if isinstance(resource, dict) else None
    if not isinstance(resource_link_id, str):
        return False

    mapping = (
        db.query(LTIAssignmentLink)
        .filter(
            LTIAssignmentLink.platform_id == platform.id,
            LTIAssignmentLink.deployment_id == platform.deployment_id,
            LTIAssignmentLink.resource_link_id == resource_link_id,
        )
        .first()
    )
    if mapping is None:
        return False

    endpoint = claims.get(AGS_ENDPOINT_CLAIM)
    scopes = endpoint.get("scope") if isinstance(endpoint, dict) else None
    lineitem = endpoint.get("lineitem") if isinstance(endpoint, dict) else None
    if not isinstance(scopes, list) or AGS_SCORE_SCOPE not in scopes or not isinstance(lineitem, str):
        mapping.lineitem_url = None
        mapping.score_scope_allowed = False
        return True

    try:
        mapping.lineitem_url = validate_lti_ags_lineitem_url(lineitem, platform)
    except ValueError:
        mapping.lineitem_url = None
        mapping.score_scope_allowed = False
    else:
        mapping.score_scope_allowed = True
    return True


def create_lti_ags_grade_events(db, assignment, submission) -> list[int]:
    """Create durable outbox entries for every mapped LMS resource linked to this student."""
    from app.models.lti import LTIUserLink, LTIAssignmentLink, LTIAGSGradeEvent

    links = (
        db.query(LTIAssignmentLink)
        .filter(
            LTIAssignmentLink.assignment_id == assignment.id,
            LTIAssignmentLink.score_scope_allowed.is_(True),
            LTIAssignmentLink.lineitem_url.is_not(None),
        )
        .all()
    )
    event_ids = []
    for mapping in links:
        user_link = (
            db.query(LTIUserLink)
            .filter(
                LTIUserLink.platform_id == mapping.platform_id,
                LTIUserLink.user_id == submission.student_user_id,
            )
            .first()
        )
        if user_link is None:
            continue
        event = LTIAGSGradeEvent(
            assignment_link_id=mapping.id,
            submission_id=submission.id,
            grade_version=submission.grade_version,
            lti_subject=user_link.lti_subject,
            score_given=(float(submission.grade_percentage) / 100.0) * mapping.score_maximum,
            score_maximum=mapping.score_maximum,
            comment=submission.feedback,
            status="pending",
            attempts=0,
            next_attempt_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()
        event_ids.append(event.id)
    return event_ids


def build_ags_client_assertion(platform, now: int | None = None) -> str:
    """Create a short-lived RS256 client assertion for the LTI AGS OAuth client-credentials grant."""
    if not settings.LTI_TOOL_PRIVATE_KEY.strip():
        raise ValueError("LTI_TOOL_PRIVATE_KEY is not configured")
    try:
        private_key = serialization.load_pem_private_key(
            settings.LTI_TOOL_PRIVATE_KEY.encode("utf-8"), password=None
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("LTI tool private key is invalid") from exc
    if not isinstance(private_key, rsa.RSAPrivateKey) or private_key.key_size < 2048:
        raise ValueError("LTI AGS requires an RSA private key of at least 2048 bits")

    issued_at = int(now if now is not None else datetime.now(timezone.utc).timestamp())
    claims = {
        "iss": platform.client_id,
        "sub": platform.client_id,
        "aud": platform.auth_token_url,
        "iat": issued_at,
        "exp": issued_at + 300,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": settings.LTI_TOOL_KID, "typ": "JWT"},
    )


async def _read_ags_response(response, max_bytes: int = AGS_MAX_RESPONSE_BYTES) -> bytes:
    if 300 <= response.status_code < 400:
        raise ValueError("LTI AGS redirects are not allowed")
    response.raise_for_status()
    content = bytearray()
    async for chunk in response.aiter_bytes():
        content.extend(chunk)
        if len(content) > max_bytes:
            raise ValueError("LTI AGS response exceeds the configured size limit")
    return bytes(content)


async def request_ags_access_token(platform) -> str:
    """Exchange a signed client assertion for a scoped AGS access token."""
    pinned_url, host_headers, extensions = await resolve_lti_platform_endpoint_url(
        platform.auth_token_url
    )
    assertion = build_ags_client_assertion(platform)
    form = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": assertion,
        "scope": AGS_SCORE_SCOPE,
    }
    async with httpx.AsyncClient(
        timeout=15.0, follow_redirects=False, trust_env=False
    ) as client:
        async with client.stream(
            "POST",
            pinned_url,
            data=form,
            headers={**host_headers, "Accept": "application/json"},
            extensions=extensions,
        ) as response:
            content = await _read_ags_response(response)
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("LTI AGS token response is not valid JSON") from exc
    token = document.get("access_token") if isinstance(document, dict) else None
    token_type = document.get("token_type") if isinstance(document, dict) else None
    if not isinstance(token, str) or not token or len(token) > 8192:
        raise ValueError("LTI AGS token response did not contain a valid access token")
    if not isinstance(token_type, str) or token_type.lower() != "bearer":
        raise ValueError("LTI AGS token response did not provide a Bearer token")
    return token


async def post_lti_ags_score(platform, lineitem_url: str, payload: dict) -> None:
    """Post one score to the pinned, registered platform lineitem endpoint."""
    safe_lineitem = validate_lti_ags_lineitem_url(lineitem_url, platform)
    token = await request_ags_access_token(platform)
    parsed = urlsplit(safe_lineitem)
    score_url = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/scores", "", "")
    )
    pinned_url, host_headers, extensions = await resolve_lti_platform_endpoint_url(score_url)
    headers = {
        **host_headers,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/vnd.ims.lis.v1.score+json",
    }
    async with httpx.AsyncClient(
        timeout=15.0, follow_redirects=False, trust_env=False
    ) as client:
        async with client.stream(
            "POST",
            pinned_url,
            json=payload,
            headers=headers,
            extensions=extensions,
        ) as response:
            await _read_ags_response(response, max_bytes=64 * 1024)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def dispatch_lti_grade_event(db, event_id: int) -> bool:
    """Deliver one persisted outbox event with a lease, bounded retries, and safe error state."""
    from app.models.lti import LTIAGSGradeEvent, LTIAssignmentLink, LTIPlatform

    event = (
        db.query(LTIAGSGradeEvent)
        .filter(LTIAGSGradeEvent.id == event_id)
        .with_for_update()
        .first()
    )
    if event is None or event.status != "pending":
        return False

    now = datetime.now(timezone.utc)
    if _as_utc(event.next_attempt_at) > now:
        return False
    locked_until = _as_utc(event.locked_until)
    if locked_until is not None and locked_until > now:
        return False

    event.locked_until = now + timedelta(minutes=3)
    event.attempts += 1
    db.commit()

    mapping = db.get(LTIAssignmentLink, event.assignment_link_id)
    platform = db.get(LTIPlatform, mapping.platform_id) if mapping else None
    try:
        if mapping is None or platform is None:
            raise ValueError("LTI assignment mapping is unavailable")
        if not mapping.score_scope_allowed or not mapping.lineitem_url:
            raise ValueError("LTI AGS score permission is not available")
        timestamp = _as_utc(event.created_at).isoformat().replace("+00:00", "Z")
        score = {
            "userId": event.lti_subject,
            "scoreGiven": event.score_given,
            "scoreMaximum": event.score_maximum,
            "activityProgress": "Completed",
            "gradingProgress": "FullyGraded",
            "timestamp": timestamp,
        }
        if event.comment:
            score["comment"] = event.comment[:5000]
        await post_lti_ags_score(platform, mapping.lineitem_url, score)
    except Exception as exc:
        db.rollback()
        failed_event = db.get(LTIAGSGradeEvent, event_id)
        if failed_event is None:
            return False
        failed_event.locked_until = None
        failed_event.last_error = f"{type(exc).__name__}: AGS delivery failed"[:255]
        if failed_event.attempts >= AGS_MAX_DELIVERY_ATTEMPTS:
            failed_event.status = "dead"
        else:
            delay_seconds = min(60 * (2 ** (failed_event.attempts - 1)), 21600)
            failed_event.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay_seconds
            )
        db.commit()
        return False

    delivered_event = db.get(LTIAGSGradeEvent, event_id)
    if delivered_event is None:
        return False
    delivered_event.status = "sent"
    delivered_event.delivered_at = datetime.now(timezone.utc)
    delivered_event.locked_until = None
    delivered_event.last_error = None
    db.commit()
    return True
