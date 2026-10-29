"""
اختبارات LTI 1.3 — نحاكي منصة LMS حقيقية: نولّد زوج مفاتيح RSA تجريبي، نوقّع
id_token فعلي فيه، ونموّه جلب JWKS المنصة يرجّع مفتاحنا التجريبي. هذا يتحقق
فعليًا إن منطق التحقق من التوقيع يشتغل صح، مو بس شكل الاستجابة.
"""
from unittest.mock import AsyncMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from jose.utils import long_to_base64url

from app.services import lti_service as lti_service_module


def _generate_fake_platform_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk_dict = {
        "kty": "RSA", "use": "sig", "alg": "RS256", "kid": "platform-key-1",
        "n": long_to_base64url(numbers.n).decode(),
        "e": long_to_base64url(numbers.e).decode(),
    }
    return private_key, jwk_dict


def _register_admin(client, email="ltiadmin@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def _register_platform(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/lti/platforms",
        json={
            "name": "Moodle تجريبي", "issuer": "https://moodle.example.com",
            "client_id": "test-client-id", "deployment_id": "deploy-1",
            "auth_login_url": "https://moodle.example.com/auth", "auth_token_url": "https://moodle.example.com/token",
            "jwks_url": "https://moodle.example.com/jwks",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_register_and_list_platforms_requires_admin(client):
    admin_token = _register_admin(client)
    platform = _register_platform(client, admin_token)
    assert platform["issuer"] == "https://moodle.example.com"

    non_admin_token = _register_admin(client, "notadmin@example.com")
    response = client.get(
        "/lti/platforms", headers={"Authorization": f"Bearer {non_admin_token}"}
    )
    assert response.status_code == 403


def test_jwks_endpoint_returns_empty_keys_without_configured_key(client, monkeypatch):
    monkeypatch.setattr(lti_service_module.settings, "LTI_TOOL_PRIVATE_KEY", "")
    response = client.get("/lti/jwks")
    assert response.status_code == 200
    assert response.json() == {"keys": []}


def test_login_rejects_unregistered_platform(client):
    response = client.get(
        "/lti/login",
        params={
            "iss": "https://unknown-platform.example.com",
            "login_hint": "student1",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
        },
    )
    assert response.status_code == 400


def test_login_redirects_to_platform_auth_endpoint(client):
    admin_token = _register_admin(client, "loginflow@example.com")
    platform = _register_platform(client, admin_token)

    response = client.get(
        "/lti/login",
        params={
            "iss": platform["issuer"], "login_hint": "student1",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
            "client_id": platform["client_id"],
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
    assert "moodle.example.com/auth" in response.headers["location"]
    assert "state=" in response.headers["location"]
    assert "nonce=" in response.headers["location"]


def test_full_launch_flow_creates_user_and_issues_tokens(client, monkeypatch):
    admin_token = _register_admin(client, "launchflow@example.com")
    platform_data = _register_platform(client, admin_token)

    # 1) نحاكي خطوة /login عشان نولّد state ونonce صالحين
    login_response = client.get(
        "/lti/login",
        params={
            "iss": platform_data["issuer"], "login_hint": "student42",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
            "client_id": platform_data["client_id"],
        },
        follow_redirects=False,
    )
    from urllib.parse import parse_qs, urlparse
    query = parse_qs(urlparse(login_response.headers["location"]).query)
    state = query["state"][0]
    nonce = query["nonce"][0]

    # 2) نوقّع id_token فعلي كأننا المنصة، ونموّه جلب JWKS المنصة يرجّع مفتاحنا التجريبي
    platform_private_key, platform_jwk = _generate_fake_platform_keypair()
    pem = platform_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    claims = {
        "iss": platform_data["issuer"], "aud": platform_data["client_id"],
        "sub": "moodle-student-42", "nonce": nonce, "name": "طالب تجريبي",
        "email": "student42@moodle.example.com",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": platform_data["deployment_id"],
    }
    id_token = jwt.encode(
        claims, pem, algorithm="RS256", headers={"kid": "platform-key-1"}
    )

    async def fake_fetch_key(jwks_url, kid):
        return platform_jwk

    monkeypatch.setattr(lti_service_module, "fetch_platform_public_key", fake_fetch_key)

    # 3) نستدعي /lti/launch فعليًا — هذا يتحقق من التوقيع الحقيقي
    launch_response = client.post(
        "/lti/launch", data={"id_token": id_token, "state": state}, follow_redirects=False
    )
    assert launch_response.status_code == 302
    location = launch_response.headers["location"]
    assert "/lti-callback" in location
    assert "access_token=" in location
    assert "refresh_token=" in location


def test_launch_rejects_invalid_signature(client, monkeypatch):
    admin_token = _register_admin(client, "badsig@example.com")
    platform_data = _register_platform(client, admin_token)

    login_response = client.get(
        "/lti/login",
        params={
            "iss": platform_data["issuer"], "login_hint": "student1",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
            "client_id": platform_data["client_id"],
        },
        follow_redirects=False,
    )
    from urllib.parse import parse_qs, urlparse
    query = parse_qs(urlparse(login_response.headers["location"]).query)
    state = query["state"][0]

    # نوقّع بمفتاح مختلف تمامًا عن اللي نموّه الفحص يرجّعه — لازم يفشل التحقق
    wrong_key, _ = _generate_fake_platform_keypair()
    _, correct_jwk = _generate_fake_platform_keypair()
    wrong_pem = wrong_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    bad_token = jwt.encode(
        {"iss": platform_data["issuer"], "aud": platform_data["client_id"], "sub": "x", "nonce": "wrong"},
        wrong_pem, algorithm="RS256", headers={"kid": "platform-key-1"},
    )

    async def fake_fetch_key(jwks_url, kid):
        return correct_jwk

    monkeypatch.setattr(lti_service_module, "fetch_platform_public_key", fake_fetch_key)

    response = client.post("/lti/launch", data={"id_token": bad_token, "state": state})
    assert response.status_code == 401


def test_launch_rejects_expired_or_tampered_state(client):
    response = client.post(
        "/lti/launch", data={"id_token": "irrelevant", "state": "not-a-real-state-token"}
    )
    assert response.status_code == 400
