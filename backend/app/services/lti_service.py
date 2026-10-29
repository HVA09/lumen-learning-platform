"""
منطق LTI 1.3: بناء JWKS والتحقق من id_token وإدارة state ورموز تبادل أحادية الاستخدام.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
import uuid

import httpx
from cryptography.hazmat.primitives import serialization
from jose import jwk, jwt
from jose.utils import long_to_base64url
from sqlalchemy.orm import Session

from app.config import settings
from app.models.lti import LTIAuthCode, LTILoginState

LTI_STATE_TTL_SECONDS = 600
LTI_AUTH_CODE_TTL_SECONDS = 60


def _hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def build_tool_jwks() -> dict:
    """يبني JWKS العام لأداتنا من المفتاح الخاص بالإعدادات."""
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


def create_login_state(
    db: Session, platform_id: int, nonce: str, target_link_uri: str
) -> str:
    """ينشئ state عشوائيًا، ويحفظ بصمته مع nonce ومدة صلاحية قصيرة."""
    now = datetime.now(timezone.utc)
    db.query(LTILoginState).filter(LTILoginState.expires_at < now).delete(
        synchronize_session=False
    )
    state = secrets.token_urlsafe(32)
    db.add(
        LTILoginState(
            state_hash=_hash_secret(state),
            platform_id=platform_id,
            nonce=nonce,
            target_link_uri=target_link_uri,
            expires_at=now + timedelta(seconds=LTI_STATE_TTL_SECONDS),
        )
    )
    db.commit()
    return state


def get_login_state(db: Session, state: str) -> LTILoginState:
    """يعيد state ساريًا وغير مستهلك؛ لا يستهلكه قبل التحقق من id_token."""
    if not state or len(state) > 256:
        raise ValueError("invalid state")
    now = datetime.now(timezone.utc)
    record = (
        db.query(LTILoginState)
        .filter(
            LTILoginState.state_hash == _hash_secret(state),
            LTILoginState.expires_at > now,
            LTILoginState.consumed_at.is_(None),
        )
        .first()
    )
    if record is None:
        raise ValueError("invalid or expired state")
    return record


def consume_login_state(db: Session, state: str) -> bool:
    """يستهلك state ذريًا؛ لا يمكن لطلبين متزامنين استخدامه مرتين."""
    now = datetime.now(timezone.utc)
    updated = (
        db.query(LTILoginState)
        .filter(
            LTILoginState.state_hash == _hash_secret(state),
            LTILoginState.expires_at > now,
            LTILoginState.consumed_at.is_(None),
        )
        .update({LTILoginState.consumed_at: now}, synchronize_session=False)
    )
    if updated != 1:
        return False
    db.commit()
    return True


def create_lti_auth_code(db: Session, user_id: int) -> str:
    """ينشئ رمز تبادل عشوائيًا قصير العمر ويخزن بصمته فقط."""
    now = datetime.now(timezone.utc)
    db.query(LTIAuthCode).filter(LTIAuthCode.expires_at < now).delete(
        synchronize_session=False
    )
    code = secrets.token_urlsafe(32)
    db.add(
        LTIAuthCode(
            code_hash=_hash_secret(code),
            user_id=user_id,
            expires_at=now + timedelta(seconds=LTI_AUTH_CODE_TTL_SECONDS),
        )
    )
    db.commit()
    return code


def consume_lti_auth_code(db: Session, code: str) -> int | None:
    """يحوّل رمزًا صالحًا لمعرّف مستخدم ويستهلكه ذريًا مرة واحدة فقط."""
    if not code or len(code) > 256:
        return None
    now = datetime.now(timezone.utc)
    code_hash = _hash_secret(code)
    record = (
        db.query(LTIAuthCode)
        .filter(
            LTIAuthCode.code_hash == code_hash,
            LTIAuthCode.expires_at > now,
            LTIAuthCode.consumed_at.is_(None),
        )
        .first()
    )
    if record is None:
        return None

    user_id = record.user_id
    updated = (
        db.query(LTIAuthCode)
        .filter(
            LTIAuthCode.code_hash == code_hash,
            LTIAuthCode.expires_at > now,
            LTIAuthCode.consumed_at.is_(None),
        )
        .update({LTIAuthCode.consumed_at: now}, synchronize_session=False)
    )
    if updated != 1:
        return None
    db.commit()
    return user_id


async def fetch_platform_public_key(jwks_url: str, kid: str):
    """يجلب المفتاح العام من JWKS الخاص بالمنصة."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
    keys = response.json().get("keys", [])
    matching_key = next((key for key in keys if key.get("kid") == kid), None)
    if not matching_key:
        raise ValueError("لم يُعثر على مفتاح مطابق في JWKS الخاص بالمنصة")
    return matching_key


async def verify_platform_id_token(
    id_token: str, platform, expected_nonce: str, expected_target_link_uri: str
) -> dict:
    """يتحقق من التوقيع والمصدر والجمهور وnonce وdeployment_id."""
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("id_token لا يحتوي على kid")

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

    required_claims = ("iss", "aud", "sub", "exp", "iat", "nonce")
    if any(name not in claims for name in required_claims):
        raise ValueError("id_token يفتقد claim إلزاميًا")

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
        raise ValueError("مدة صلاحية id_token غير صالحة")

    if not isinstance(claims["sub"], str) or not claims["sub"]:
        raise ValueError("sub غير صالح")
    if claims.get("nonce") != expected_nonce:
        raise ValueError("nonce غير مطابق")
    deployment_claim = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
    if claims.get(deployment_claim) != platform.deployment_id:
        raise ValueError("deployment_id غير مطابق")

    target_link_claim = "https://purl.imsglobal.org/spec/lti/claim/target_link_uri"
    if claims.get(target_link_claim) != expected_target_link_uri:
        raise ValueError("target_link_uri claim لا يطابق عنوان البدء المسجل")
    return claims


def new_nonce() -> str:
    return uuid.uuid4().hex
