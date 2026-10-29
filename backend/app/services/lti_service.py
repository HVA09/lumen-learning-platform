"""
منطق LTI 1.3: بناء JWKS الخاص بأداتنا، تشفير/فك حالة OIDC المؤقتة (state)،
والتحقق من id_token اللي ترسله منصة LMS (Moodle/Canvas) بعد المصادقة.

ملاحظة صادقة: هذا تطبيق متوافق مع مواصفة LTI 1.3 حسب توثيقها الرسمي (IMS Global)،
لكن ما قدرت أختبره فعليًا مقابل منصة Moodle/Canvas حقيقية — لازم تختبره بحساب
تجريبي (Moodle sandbox) قبل الاعتماد عليه بالإنتاج، ومن المتوقع تحتاج تعديلات
طفيفة حسب تفاصيل المنصة اللي تربطها.
"""
import time
import uuid

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from jose.utils import long_to_base64url

from app.config import settings

LTI_STATE_TTL_SECONDS = 600  # 10 دقايق كافية لإكمال تدفق OIDC


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


def encode_login_state(platform_id: int, nonce: str, target_link_uri: str) -> str:
    """حالة OIDC موقّعة بمفتاحنا الداخلي — بديل عن جلسة سيرفر، وتُتحقق وقت /lti/launch"""
    payload = {
        "platform_id": platform_id,
        "nonce": nonce,
        "target_link_uri": target_link_uri,
        "exp": int(time.time()) + LTI_STATE_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_login_state(state: str) -> dict:
    return jwt.decode(state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


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


async def verify_platform_id_token(id_token: str, platform, expected_nonce: str) -> dict:
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

    deployment_claim = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
    if claims.get(deployment_claim) != platform.deployment_id:
        raise ValueError("deployment_id غير مطابق للمنصة المسجّلة")

    return claims


def new_nonce() -> str:
    return uuid.uuid4().hex
