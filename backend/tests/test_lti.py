"""
اختبارات LTI 1.3: تتحقق من التوقيع، state أحادي الاستخدام، وعدم كشف JWT في URL.
"""
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose.utils import long_to_base64url

from app.models.user import User, UserRole
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


def _register_admin(client, db_session, email="ltiadmin@example.com", password="StrongPass123"):
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    user = db_session.query(User).filter(User.email == email).one()
    # Public registration must never create an admin; tests promote explicitly.
    user.role = UserRole.admin
    db_session.commit()
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
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


def test_register_and_list_platforms_requires_admin(client, db_session):
    admin_token = _register_admin(client, db_session)
    platform = _register_platform(client, admin_token)
    assert platform["issuer"] == "https://moodle.example.com"

    non_admin_token = client.post(
        "/auth/login",
        json={"email": "ltiadmin@example.com", "password": "StrongPass123"},
    ).json()["access_token"]
    # The test user is deliberately promoted to admin above, so use a separate regular user.
    client.post("/auth/register", json={"email": "notadmin@example.com", "password": "StrongPass123"})
    non_admin_token = client.post(
        "/auth/login", json={"email": "notadmin@example.com", "password": "StrongPass123"}
    ).json()["access_token"]
    response = client.get("/lti/platforms", headers={"Authorization": f"Bearer {non_admin_token}"})
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


def test_login_redirects_to_platform_auth_endpoint(client, db_session):
    admin_token = _register_admin(client, db_session, "loginflow@example.com")
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
    assert response.headers["cache-control"] == "no-store"


def test_full_launch_flow_issues_single_use_exchange_code(client, db_session, monkeypatch):
    admin_token = _register_admin(client, db_session, "launchflow@example.com")
    platform_data = _register_platform(client, admin_token)

    login_response = client.get(
        "/lti/login",
        params={
            "iss": platform_data["issuer"], "login_hint": "student42",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
            "client_id": platform_data["client_id"],
        },
        follow_redirects=False,
    )
    query = parse_qs(urlparse(login_response.headers["location"]).query)
    state = query["state"][0]
    nonce = query["nonce"][0]

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
    id_token = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "platform-key-1"})

    async def fake_fetch_key(jwks_url, kid):
        return platform_jwk

    monkeypatch.setattr(lti_service_module, "fetch_platform_public_key", fake_fetch_key)

    launch_response = client.post(
        "/lti/launch", data={"id_token": id_token, "state": state}, follow_redirects=False
    )
    assert launch_response.status_code == 302
    location = launch_response.headers["location"]
    assert "/lti-callback#code=" in location
    assert "access_token=" not in location
    assert "refresh_token=" not in location
    assert launch_response.headers["cache-control"] == "no-store"

    code = parse_qs(urlparse(location).fragment).get("code", [None])[0]
    assert code
    exchange_response = client.post("/lti/exchange", json={"code": code})
    assert exchange_response.status_code == 200
    tokens = exchange_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    replay_response = client.post("/lti/exchange", json={"code": code})
    assert replay_response.status_code == 401
    state_replay = client.post(
        "/lti/launch", data={"id_token": id_token, "state": state}, follow_redirects=False
    )
    assert state_replay.status_code == 400


def test_launch_rejects_invalid_signature(client, db_session, monkeypatch):
    admin_token = _register_admin(client, db_session, "badsig@example.com")
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
    state = parse_qs(urlparse(login_response.headers["location"]).query)["state"][0]

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


def test_login_rejects_insecure_non_local_target_uri(client, db_session):
    admin_token = _register_admin(client, db_session, "insecuretarget@example.com")
    platform = _register_platform(client, admin_token)
    response = client.get(
        "/lti/login",
        params={
            "iss": platform["issuer"], "login_hint": "student1",
            "target_link_uri": "http://attacker.example/lti/launch",
            "client_id": platform["client_id"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
