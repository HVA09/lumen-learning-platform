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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from cryptography.hazmat.primitives import serialization
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


def _pin_lti_endpoint_url(url: str, resolved_addresses: list[str], *, allow_query: bool = False):
    """Pin a validated endpoint while preserving the original Host and TLS SNI."""
    if allow_query:
        parsed_check = urlsplit(url)
        base = urlunsplit((parsed_check.scheme, parsed_check.netloc, parsed_check.path, "", ""))
        validate_lti_platform_endpoint_url(base)
        if parsed_check.fragment or len(parsed_check.query) > 1000:
            raise ValueError("LTI endpoint query or fragment is invalid")
    else:
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
        (parsed.scheme.lower(), f"{pinned_host}{port_suffix}", parsed.path or "/", parsed.query if allow_query else "", "")
    )
    headers = {"Host": parsed.netloc}
    extensions = {"sni_hostname": hostname} if parsed.scheme.lower() == "https" else {}
    return pinned_url, headers, extensions


async def resolve_lti_platform_endpoint_url(url: str, *, allow_query: bool = False):
    """Resolve DNS once, reject private answers, and return a connection pinned to a safe IP."""
    if allow_query:
        parsed_check = urlsplit(url)
        base = urlunsplit((parsed_check.scheme, parsed_check.netloc, parsed_check.path, "", ""))
        validate_lti_platform_endpoint_url(base)
        if parsed_check.fragment or len(parsed_check.query) > 1000:
            raise ValueError("LTI endpoint query or fragment is invalid")
    else:
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

    return _pin_lti_endpoint_url(url, resolved_addresses, allow_query=allow_query)


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


# LTI Assignment and Grade Services 2.0
AGS_ENDPOINT_CLAIM = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
AGS_RESOURCE_LINK_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
AGS_SCORE_SCOPE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
AGS_MAX_DELIVERY_ATTEMPTS = 8


def validate_lti_ags_lineitem_url(url: str, platform) -> str:
    """Accept only HTTPS lineitems on the registered platform token endpoint origin."""
    if not isinstance(url, str) or not url or len(url) > 2000:
        raise ValueError("LTI AGS lineitem URL is empty or too long")
    parsed = urlsplit(url)
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("LTI AGS lineitem URL is malformed")
    if parsed.fragment or len(parsed.query) > 1000:
        raise ValueError("LTI AGS lineitem query or fragment is invalid")
    base = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    validate_lti_platform_endpoint_url(base)
    token = urlsplit(platform.auth_token_url)
    try:
        line_port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        token_port = token.port or (443 if token.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise ValueError("LTI AGS lineitem URL has an invalid port") from exc
    if (
        parsed.scheme.lower() != "https"
        or token.scheme.lower() != "https"
        or parsed.hostname.lower().rstrip(".") != (token.hostname or "").lower().rstrip(".")
        or line_port != token_port
    ):
        raise ValueError("LTI AGS lineitem must match the registered token endpoint origin")
    return url


def record_lti_ags_launch_context(db, platform, claims: dict) -> bool:
    """Record a resource link without learner identifiers and refresh its approved mapping."""
    from app.models.lti import LTIAssignmentLink, LTIResourceLinkDiscovery

    resource = claims.get(AGS_RESOURCE_LINK_CLAIM)
    resource_id = resource.get("id") if isinstance(resource, dict) else None
    if not isinstance(resource_id, str) or not resource_id or len(resource_id) > 255 or not resource_id.isascii():
        return False

    endpoint = claims.get(AGS_ENDPOINT_CLAIM)
    scopes = endpoint.get("scope") if isinstance(endpoint, dict) else None
    lineitem = endpoint.get("lineitem") if isinstance(endpoint, dict) else None
    safe_lineitem = None
    score_allowed = False
    if isinstance(scopes, list) and AGS_SCORE_SCOPE in scopes and isinstance(lineitem, str):
        try:
            safe_lineitem = validate_lti_ags_lineitem_url(lineitem, platform)
            score_allowed = True
        except ValueError:
            pass

    now = datetime.now(timezone.utc)
    table = LTIResourceLinkDiscovery.__table__
    dialect = db.get_bind().dialect.name
    insert_fn = sqlite_insert if dialect == "sqlite" else pg_insert
    stmt = insert_fn(table).values(
        platform_id=platform.id,
        deployment_id=platform.deployment_id,
        resource_link_id=resource_id,
        lineitem_url=safe_lineitem,
        score_scope_allowed=score_allowed,
        first_seen_at=now,
        last_seen_at=now,
    )
    db.execute(stmt.on_conflict_do_update(
        index_elements=[table.c.platform_id, table.c.deployment_id, table.c.resource_link_id],
        set_={
            "lineitem_url": safe_lineitem,
            "score_scope_allowed": score_allowed,
            "last_seen_at": now,
        },
    ))
    mapping = db.query(LTIAssignmentLink).filter(
        LTIAssignmentLink.platform_id == platform.id,
        LTIAssignmentLink.deployment_id == platform.deployment_id,
        LTIAssignmentLink.resource_link_id == resource_id,
    ).first()
    if mapping is not None:
        mapping.lineitem_url = safe_lineitem
        mapping.score_scope_allowed = score_allowed
    return True


def create_lti_ags_grade_event(db, assignment, submission) -> int | None:
    """Create an outbox event only for the exact mapping bound to this submission."""
    from app.models.lti import LTIAGSGradeEvent, LTIAssignmentLink, LTIUserLink

    mapping_id = submission.lti_assignment_link_id
    if not mapping_id:
        return None
    mapping = db.get(LTIAssignmentLink, mapping_id)
    if mapping is None or mapping.assignment_id != assignment.id:
        return None
    if not mapping.score_scope_allowed or not mapping.lineitem_url:
        return None
    # The external subject is captured from the verified launch session
    # at submission time. Never infer it from local user_id: one local account
    # can legitimately have more than one LMS identity on the same platform.
    lti_subject = submission.lti_subject
    if not lti_subject:
        return None
    identity_link = db.query(LTIUserLink.id).filter(
        LTIUserLink.platform_id == mapping.platform_id,
        LTIUserLink.lti_subject == lti_subject,
        LTIUserLink.user_id == submission.student_user_id,
    ).first()
    if identity_link is None:
        return None
    score_maximum = float(mapping.score_maximum)
    score_given = (float(submission.grade_percentage or 0) / 100.0) * score_maximum
    previous_score_timestamp = (
        db.query(LTIAGSGradeEvent.score_timestamp)
        .filter(
            LTIAGSGradeEvent.assignment_link_id == mapping.id,
            LTIAGSGradeEvent.submission_id == submission.id,
        )
        .order_by(LTIAGSGradeEvent.grade_version.desc())
        .limit(1)
        .scalar()
    )
    score_timestamp = _as_utc(submission.graded_at) or datetime.now(timezone.utc)
    if previous_score_timestamp is not None:
        previous_score_timestamp = _as_utc(previous_score_timestamp)
        score_timestamp = max(
            score_timestamp,
            previous_score_timestamp + timedelta(microseconds=1),
        )
    event = LTIAGSGradeEvent(
        assignment_link_id=mapping.id,
        submission_id=submission.id,
        grade_version=submission.grade_version,
        lti_subject=lti_subject,
        score_given=score_given,
        score_maximum=score_maximum,
        comment=submission.feedback,
        status="pending",
        attempts=0,
        next_attempt_at=datetime.now(timezone.utc),
        score_timestamp=score_timestamp,
    )
    db.add(event)
    db.flush()
    return event.id


def build_ags_client_assertion(platform, now: int | None = None) -> str:
    """Create a short-lived RS256 client assertion for the AGS OAuth grant."""
    if not settings.LTI_TOOL_PRIVATE_KEY.strip():
        raise ValueError("LTI_TOOL_PRIVATE_KEY is not configured")
    try:
        private_key = serialization.load_pem_private_key(
            settings.LTI_TOOL_PRIVATE_KEY.encode("utf-8"), password=None
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("LTI tool private key is invalid") from exc
    from cryptography.hazmat.primitives.asymmetric import rsa
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
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": settings.LTI_TOOL_KID, "typ": "JWT"})


async def _read_ags_response(response, max_bytes: int = 1024 * 1024) -> bytes:
    if 300 <= response.status_code < 400:
        raise ValueError("LTI AGS redirects are not allowed")
    response.raise_for_status()
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise ValueError("LTI AGS response exceeds the configured size limit")
    return bytes(body)


async def request_ags_access_token(platform) -> str:
    """Request an AGS-scoped bearer token using a private-key client assertion."""
    pinned_url, headers, extensions = await resolve_lti_platform_endpoint_url(platform.auth_token_url)
    form = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": build_ags_client_assertion(platform),
        "scope": AGS_SCORE_SCOPE,
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False, trust_env=False) as client:
        async with client.stream("POST", pinned_url, data=form, headers={**headers, "Accept": "application/json"}, extensions=extensions) as response:
            raw = await _read_ags_response(response)
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("LTI AGS token response is not valid JSON") from exc
    token = document.get("access_token") if isinstance(document, dict) else None
    token_type = document.get("token_type") if isinstance(document, dict) else None
    if not isinstance(token, str) or not token or len(token) > 8192 or str(token_type).lower() != "bearer":
        raise ValueError("LTI AGS token response did not contain a valid bearer token")
    return token


async def post_lti_ags_score(platform, lineitem_url: str, payload: dict) -> None:
    """Post one score to the exact verified lineitem endpoint without following redirects."""
    lineitem = validate_lti_ags_lineitem_url(lineitem_url, platform)
    token = await request_ags_access_token(platform)
    parsed = urlsplit(lineitem)
    score_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/scores", parsed.query, ""))
    pinned_url, host_headers, extensions = await resolve_lti_platform_endpoint_url(score_url, allow_query=True)
    headers = {
        **host_headers,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/vnd.ims.lis.v1.score+json",
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False, trust_env=False) as client:
        async with client.stream("POST", pinned_url, json=payload, headers=headers, extensions=extensions) as response:
            await _read_ags_response(response, max_bytes=64 * 1024)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def dispatch_lti_grade_event(db, event_id: int) -> bool:
    """Deliver one pending event with monotonic score timestamps and bounded retries."""
    from app.models.assignment import AssignmentSubmission
    from app.models.lti import LTIAGSGradeEvent, LTIAssignmentLink, LTIPlatform

    event = db.query(LTIAGSGradeEvent).filter(
        LTIAGSGradeEvent.id == event_id
    ).with_for_update().first()
    if event is None or event.status != "pending":
        return False

    now = datetime.now(timezone.utc)
    if _as_utc(event.next_attempt_at) > now:
        return False
    if _as_utc(event.locked_until) and _as_utc(event.locked_until) > now:
        return False

    # Serialize delivery attempts and grading against the same submission row.
    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == event.submission_id
    ).with_for_update().first()
    if submission is None:
        event.status = "dead"
        event.last_error = "ValueError: AGS submission is unavailable"
        event.locked_until = None
        db.commit()
        return False

    # Never retry an older grade after a newer grade version has been recorded.
    newer_event = db.query(LTIAGSGradeEvent.id).filter(
        LTIAGSGradeEvent.assignment_link_id == event.assignment_link_id,
        LTIAGSGradeEvent.submission_id == event.submission_id,
        LTIAGSGradeEvent.grade_version > event.grade_version,
    ).first()
    if newer_event is not None:
        event.status = "superseded"
        event.locked_until = None
        event.last_error = None
        db.commit()
        return False

    # Preserve the grade timestamp on first delivery. Every subsequent
    # attempt (including a manual retry) reserves a new, strictly later AGS time.
    score_timestamp = _as_utc(event.score_timestamp or event.created_at)
    if event.attempts > 0:
        score_timestamp = max(now, score_timestamp + timedelta(microseconds=1))
    event.score_timestamp = score_timestamp
    event.locked_until = now + timedelta(minutes=3)
    event.attempts += 1
    reserved_attempts = event.attempts
    db.commit()

    # Reacquire the event and submission locks after the durable lease commit.
    # The submission lock is held through the LMS request: grading either
    # commits before this check (and makes this event superseded), or waits
    # until this delivery finishes, preserving grade order.
    event = db.query(LTIAGSGradeEvent).filter(
        LTIAGSGradeEvent.id == event_id
    ).with_for_update().first()
    if (
        event is None
        or event.status != "pending"
        or event.attempts != reserved_attempts
    ):
        return False

    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == event.submission_id
    ).with_for_update().first()
    if submission is None:
        event.status = "dead"
        event.locked_until = None
        event.last_error = "ValueError: AGS submission is unavailable"
        db.commit()
        return False

    newer_event = db.query(LTIAGSGradeEvent.id).filter(
        LTIAGSGradeEvent.assignment_link_id == event.assignment_link_id,
        LTIAGSGradeEvent.submission_id == event.submission_id,
        LTIAGSGradeEvent.grade_version > event.grade_version,
    ).first()
    if newer_event is not None:
        event.status = "superseded"
        event.locked_until = None
        event.last_error = None
        db.commit()
        return False

    try:
        mapping = db.get(LTIAssignmentLink, event.assignment_link_id)
        platform = db.get(LTIPlatform, mapping.platform_id) if mapping else None
        if mapping is None or platform is None or not mapping.lineitem_url or not mapping.score_scope_allowed:
            raise ValueError("AGS mapping is not ready")
        timestamp = _as_utc(event.score_timestamp).isoformat(timespec="microseconds").replace("+00:00", "Z")
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
        failed = db.get(LTIAGSGradeEvent, event_id)
        if failed is None:
            return False
        failed.locked_until = None
        failed.last_error = f"{type(exc).__name__}: AGS delivery failed"[:255]
        if failed.attempts >= AGS_MAX_DELIVERY_ATTEMPTS:
            failed.status = "dead"
        else:
            delay = min(60 * (2 ** max(failed.attempts - 1, 0)), 21600)
            failed.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        db.commit()
        return False

    delivered = db.get(LTIAGSGradeEvent, event_id)
    if delivered is None:
        return False
    delivered.status = "sent"
    delivered.delivered_at = datetime.now(timezone.utc)
    delivered.locked_until = None
    delivered.last_error = None
    db.commit()
    return True
