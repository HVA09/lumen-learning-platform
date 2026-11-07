"""
اختبارات LTI 1.3 — نحاكي منصة LMS حقيقية: نولّد زوج مفاتيح RSA تجريبي، نوقّع
id_token فعلي فيه، ونموّه جلب JWKS المنصة يرجّع مفتاحنا التجريبي. هذا يتحقق
فعليًا إن منطق التحقق من التوقيع يشتغل صح، مو بس شكل الاستجابة.
"""
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.models.user import UserRole
from tests.quiz_helpers import set_role
from app.services import lti_service as lti_service_module
from app.services.lti_service import long_to_base64url


def _generate_fake_platform_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk_dict = {
        "kty": "RSA", "use": "sig", "alg": "RS256", "kid": "platform-key-1",
        "n": long_to_base64url(numbers.n).decode(),
        "e": long_to_base64url(numbers.e).decode(),
    }
    return private_key, jwk_dict


def _register_admin(
    client, db_session, email="ltiadmin@example.com", password="StrongPass123", make_admin=True
):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    if make_admin:
        set_role(db_session, email, UserRole.admin)
    return login_response.cookies.get("lumen_access")


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

    non_admin_token = _register_admin(client, db_session, "notadmin@example.com", make_admin=False)
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
    assert response.headers["referrer-policy"] == "no-referrer"


def test_full_launch_flow_creates_user_and_issues_tokens(client, db_session, monkeypatch):
    admin_token = _register_admin(client, db_session, "launchflow@example.com")
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

    now = int(time.time())
    claims = {
        "iss": platform_data["issuer"], "aud": platform_data["client_id"],
        "sub": "moodle-student-42", "nonce": nonce, "iat": now, "exp": now + 300,
        "name": "طالب تجريبي",
        "email": "student42@moodle.example.com",
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": platform_data["deployment_id"],
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/resource_link": {"id": "resource-42"},
        "https://purl.imsglobal.org/spec/lti/claim/target_link_uri": "https://mylumen.example.com/lti/launch",
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
    assert "code=" in location
    assert "access_token=" not in location
    assert "refresh_token=" not in location

    from urllib.parse import parse_qs, urlparse
    exchange_code = parse_qs(urlparse(location).fragment)["code"][0]
    exchange = client.post("/lti/exchange-code", json={"code": exchange_code})
    assert exchange.status_code == 200
    assert exchange.json()["authenticated"] is True
    assert "access_token" not in exchange.json()
    assert "refresh_token" not in exchange.json()
    assert exchange.cookies.get("lumen_access")
    assert exchange.cookies.get("lumen_refresh")
    assert "httponly" in exchange.headers.get("set-cookie", "").lower()

    # رمز التبادل أحادي الاستخدام؛ إعادة إرساله يجب أن تفشل.
    replay = client.post("/lti/exchange-code", json={"code": exchange_code})
    assert replay.status_code == 401

    # وحالة OIDC نفسها لا يمكن استعمالها مجددًا.
    replay_state = client.post(
        "/lti/launch", data={"id_token": id_token, "state": state}, follow_redirects=False
    )
    assert replay_state.status_code == 400


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


def test_lti_exchange_code_is_invalidated_after_password_change(client, db_session):
    from datetime import datetime, timedelta, timezone
    import secrets

    from app.models.lti import LTIAuthCode
    from app.models.user import User
    from app.services.lti_service import hash_opaque_token

    email = "lti-code-version@example.com"
    response = client.post(
        "/auth/register", json={"email": email, "password": "StrongPass123"}
    )
    assert response.status_code == 201
    user = db_session.query(User).filter(User.email == email).one()

    code = secrets.token_urlsafe(32)
    db_session.add(
        LTIAuthCode(
            code_hash=hash_opaque_token(code),
            user_id=user.id,
            token_version=user.token_version,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=60),
        )
    )
    user.token_version += 1
    db_session.commit()

    exchanged = client.post("/lti/exchange-code", json={"code": code})
    assert exchanged.status_code == 401


def test_launch_rejects_signed_target_link_uri_mismatch(client, db_session, monkeypatch):
    admin_token = _register_admin(client, db_session, "targetmismatch@example.com")
    platform_data = _register_platform(client, admin_token)
    expected_target = "https://mylumen.example.com/lti/launch"

    login_response = client.get(
        "/lti/login",
        params={
            "iss": platform_data["issuer"],
            "login_hint": "student42",
            "target_link_uri": expected_target,
            "client_id": platform_data["client_id"],
        },
        follow_redirects=False,
    )
    from urllib.parse import parse_qs, urlparse
    query = parse_qs(urlparse(login_response.headers["location"]).query)
    state = query["state"][0]
    nonce = query["nonce"][0]

    platform_private_key, platform_jwk = _generate_fake_platform_keypair()
    pem = platform_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = int(time.time())
    claims = {
        "iss": platform_data["issuer"],
        "aud": platform_data["client_id"],
        "sub": "target-mismatch-student",
        "nonce": nonce,
        "iat": now,
        "exp": now + 300,
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": platform_data["deployment_id"],
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/resource_link": {"id": "resource-43"},
        "https://purl.imsglobal.org/spec/lti/claim/target_link_uri": "https://attacker.example/other-launch",
    }
    id_token = jwt.encode(
        claims, pem, algorithm="RS256", headers={"kid": "platform-key-1"}
    )

    async def fake_fetch_key(jwks_url, kid):
        return platform_jwk

    monkeypatch.setattr(lti_service_module, "fetch_platform_public_key", fake_fetch_key)
    response = client.post("/lti/launch", data={"id_token": id_token, "state": state})
    assert response.status_code == 401


def test_launch_rejects_unsupported_lti_message_and_missing_azp(client, db_session, monkeypatch):
    admin_token = _register_admin(client, db_session, "invalidclaims@example.com")
    platform_data = _register_platform(client, admin_token)
    expected_target = "https://mylumen.example.com/lti/launch"

    login_response = client.get(
        "/lti/login",
        params={
            "iss": platform_data["issuer"],
            "login_hint": "student42",
            "target_link_uri": expected_target,
            "client_id": platform_data["client_id"],
        },
        follow_redirects=False,
    )
    from urllib.parse import parse_qs, urlparse
    query = parse_qs(urlparse(login_response.headers["location"]).query)
    state = query["state"][0]
    nonce = query["nonce"][0]

    platform_private_key, platform_jwk = _generate_fake_platform_keypair()
    pem = platform_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = int(time.time())
    valid_claims = {
        "iss": platform_data["issuer"],
        "aud": platform_data["client_id"],
        "sub": "invalid-claims-student",
        "nonce": nonce,
        "iat": now,
        "exp": now + 300,
        "https://purl.imsglobal.org/spec/lti/claim/deployment_id": platform_data["deployment_id"],
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiResourceLinkRequest",
        "https://purl.imsglobal.org/spec/lti/claim/version": "1.3.0",
        "https://purl.imsglobal.org/spec/lti/claim/resource_link": {"id": "resource-44"},
        "https://purl.imsglobal.org/spec/lti/claim/target_link_uri": expected_target,
    }

    async def fake_fetch_key(jwks_url, kid):
        return platform_jwk

    monkeypatch.setattr(lti_service_module, "fetch_platform_public_key", fake_fetch_key)

    wrong_type = {
        **valid_claims,
        "https://purl.imsglobal.org/spec/lti/claim/message_type": "LtiDeepLinkingRequest",
    }
    wrong_type_token = jwt.encode(
        wrong_type, pem, algorithm="RS256", headers={"kid": "platform-key-1"}
    )
    assert client.post(
        "/lti/launch", data={"id_token": wrong_type_token, "state": state}
    ).status_code == 401

    multiple_audiences = {
        **valid_claims,
        "aud": [platform_data["client_id"], "unexpected-audience"],
    }
    multiple_audience_token = jwt.encode(
        multiple_audiences, pem, algorithm="RS256", headers={"kid": "platform-key-1"}
    )
    assert client.post(
        "/lti/launch", data={"id_token": multiple_audience_token, "state": state}
    ).status_code == 401

    missing_resource_id = {
        **valid_claims,
        "https://purl.imsglobal.org/spec/lti/claim/resource_link": {},
    }
    missing_resource_token = jwt.encode(
        missing_resource_id, pem, algorithm="RS256", headers={"kid": "platform-key-1"}
    )
    assert client.post(
        "/lti/launch", data={"id_token": missing_resource_token, "state": state}
    ).status_code == 401

    # The same OIDC state remains available after rejected tokens and accepts
    # only a correctly signed, complete LTI Resource Link Request.
    valid_token = jwt.encode(
        valid_claims, pem, algorithm="RS256", headers={"kid": "platform-key-1"}
    )
    accepted = client.post(
        "/lti/launch", data={"id_token": valid_token, "state": state}, follow_redirects=False
    )
    assert accepted.status_code == 302


def test_login_post_accepts_form_and_preserves_platform_hints(client, db_session):
    admin_token = _register_admin(client, db_session, "loginpost@example.com")
    platform = _register_platform(client, admin_token)
    message_hint = "opaque-platform-hint:/path?x=1&keep=unchanged"

    response = client.post(
        "/lti/login",
        data={
            "iss": platform["issuer"],
            "login_hint": "student-post",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
            "client_id": platform["client_id"],
            "lti_message_hint": message_hint,
            "lti_deployment_id": platform["deployment_id"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    from urllib.parse import parse_qs, urlparse
    params = parse_qs(urlparse(response.headers["location"]).query)
    assert params["lti_message_hint"] == [message_hint]

    invalid_deployment = client.get(
        "/lti/login",
        params={
            "iss": platform["issuer"],
            "login_hint": "student-get",
            "target_link_uri": "https://mylumen.example.com/lti/launch",
            "client_id": platform["client_id"],
            "lti_deployment_id": "wrong-deployment",
        },
        follow_redirects=False,
    )
    assert invalid_deployment.status_code == 400


def test_register_rejects_non_https_remote_platform_endpoints(client, db_session):
    admin_token = _register_admin(client, db_session, "insecure-platform@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}
    valid = {
        "name": "Moodle Security Test",
        "issuer": "https://moodle.example.com",
        "client_id": "https-client",
        "deployment_id": "deploy-https",
        "auth_login_url": "https://moodle.example.com/auth",
        "auth_token_url": "https://moodle.example.com/token",
        "jwks_url": "https://moodle.example.com/jwks",
    }

    for field in ("issuer", "auth_login_url", "auth_token_url", "jwks_url"):
        payload = {**valid, "client_id": f"http-{field}"}
        payload[field] = "http://attacker.example/lti-endpoint"
        response = client.post("/lti/platforms", json=payload, headers=headers)
        assert response.status_code == 422, field


def test_register_allows_local_http_lti_endpoints_outside_production(client, db_session):
    admin_token = _register_admin(client, db_session, "local-platform@example.com")
    response = client.post(
        "/lti/platforms",
        json={
            "name": "Local Moodle",
            "issuer": "http://localhost:8080",
            "client_id": "local-client",
            "deployment_id": "local-deploy",
            "auth_login_url": "http://localhost:8080/auth",
            "auth_token_url": "http://localhost:8080/token",
            "jwks_url": "http://localhost:8080/jwks",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201

def test_register_rejects_non_public_ip_literal_endpoints(client, db_session):
    admin_token = _register_admin(client, db_session, "private-endpoint-admin@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}
    valid = {
        "name": "LTI endpoint security test",
        "issuer": "https://moodle.example.com",
        "client_id": "private-endpoint-client",
        "deployment_id": "private-endpoint-deploy",
        "auth_login_url": "https://moodle.example.com/auth",
        "auth_token_url": "https://moodle.example.com/token",
        "jwks_url": "https://moodle.example.com/jwks",
    }

    for field in ("issuer", "auth_login_url", "auth_token_url", "jwks_url"):
        payload = {**valid, "client_id": f"private-{field}"}
        payload[field] = "https://169.254.169.254/latest/meta-data"
        response = client.post("/lti/platforms", json=payload, headers=headers)
        assert response.status_code == 422, field

def test_lti_endpoint_validator_blocks_local_hostnames_in_production(monkeypatch):
    monkeypatch.setattr(lti_service_module.settings, "ENVIRONMENT", "production")

    for url in (
        "https://localhost/jwks",
        "https://service.localhost/jwks",
        "https://127.0.0.1/jwks",
        "https://[::1]/jwks",
    ):
        with pytest.raises(ValueError):
            lti_service_module.validate_lti_platform_endpoint_url(url)



def test_lti_dns_validation_rejects_any_non_public_answer():
    with pytest.raises(ValueError):
        lti_service_module._validate_lti_resolved_addresses(
            ["8.8.8.8", "10.20.30.40"]
        )

    with pytest.raises(ValueError):
        lti_service_module._validate_lti_resolved_addresses(
            ["2606:4700:4700::1111", "fe80::1"]
        )


def test_lti_endpoint_pin_preserves_original_host_and_tls_sni(monkeypatch):
    monkeypatch.setattr(lti_service_module.settings, "ENVIRONMENT", "production")

    pinned_url, headers, extensions = lti_service_module._pin_lti_endpoint_url(
        "https://moodle.example.com:8443/jwks",
        ["8.8.8.8", "1.1.1.1"],
    )

    assert pinned_url == "https://8.8.8.8:8443/jwks"
    assert headers == {"Host": "moodle.example.com:8443"}
    assert extensions == {"sni_hostname": "moodle.example.com"}


def test_lti_endpoint_pin_rejects_private_address_even_when_public_ip_is_first(monkeypatch):
    monkeypatch.setattr(lti_service_module.settings, "ENVIRONMENT", "production")

    with pytest.raises(ValueError):
        lti_service_module._pin_lti_endpoint_url(
            "https://moodle.example.com/jwks",
            ["8.8.8.8", "192.168.1.10"],
        )

def test_browser_lti_exchange_requires_trusted_origin_and_csrf(client, db_session):
    from datetime import datetime, timedelta, timezone
    import secrets

    from app.config import settings
    from app.models.lti import LTIAuthCode
    from app.models.user import User
    from app.services.lti_service import hash_opaque_token

    email = "lti-cookie-csrf@example.com"
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    user = db_session.query(User).filter(User.email == email).one()
    code = secrets.token_urlsafe(32)
    db_session.add(
        LTIAuthCode(
            code_hash=hash_opaque_token(code),
            user_id=user.id,
            token_version=user.token_version,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=60),
        )
    )
    db_session.commit()

    csrf = client.get("/auth/csrf").json()["csrf_token"]
    rejected_origin = client.post(
        "/lti/exchange-code",
        json={"code": code},
        headers={
            "origin": "https://attacker.invalid",
            "X-CSRF-Token": csrf,
        },
    )
    assert rejected_origin.status_code == 403

    missing_csrf = client.post(
        "/lti/exchange-code",
        json={"code": code},
        headers={"origin": settings.CORS_ORIGINS[0]},
    )
    assert missing_csrf.status_code == 403

    accepted = client.post(
        "/lti/exchange-code",
        json={"code": code},
        headers={
            "origin": settings.CORS_ORIGINS[0],
            "X-CSRF-Token": csrf,
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["authenticated"] is True
    assert "access_token" not in accepted.json()



def test_lti_key_generator_outputs_dotenv_compatible_multiline_pem(tmp_path):
    import subprocess
    import sys

    from dotenv import dotenv_values

    output = subprocess.run(
        [sys.executable, "scripts/generate_lti_key.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    env_file = tmp_path / ".env"
    env_file.write_text(output, encoding="utf-8")
    values = dotenv_values(env_file)

    private_key_pem = values["LTI_TOOL_PRIVATE_KEY"]
    assert private_key_pem.startswith("-----BEGIN PRIVATE KEY-----\\n") is False
    assert private_key_pem.startswith("-----BEGIN PRIVATE KEY-----\\n") or private_key_pem.startswith("-----BEGIN PRIVATE KEY-----\n")
    assert private_key_pem.endswith("-----END PRIVATE KEY-----\\n") is False
    assert values["LTI_TOOL_KID"].startswith("lumen-")
    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    assert private_key.key_size >= 2048


def test_ags_lineitem_url_must_match_registered_https_origin(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(lti_service_module.settings, "ENVIRONMENT", "production")
    platform = SimpleNamespace(auth_token_url="https://moodle.example.com/token")

    assert lti_service_module.validate_lti_ags_lineitem_url(
        "https://moodle.example.com/lineitems/42", platform
    ) == "https://moodle.example.com/lineitems/42"

    for unsafe in (
        "http://moodle.example.com/lineitems/42",
        "https://attacker.example/lineitems/42",
        "https://moodle.example.com.evil.invalid/lineitems/42",
        "https://user@moodle.example.com/lineitems/42",
        "https://moodle.example.com/lineitems/42#fragment",
    ):
        with pytest.raises(ValueError):
            lti_service_module.validate_lti_ags_lineitem_url(unsafe, platform)


def test_lti_profile_uses_only_verified_valid_email():
    from app.routers.lti import _build_lti_profile

    fallback, full_name, verified = _build_lti_profile(
        {"email": "student@example.com", "email_verified": False, "name": " Student "},
        7,
        "external-subject-7",
    )
    assert fallback.endswith("@lti.local")
    assert full_name == "Student"
    assert verified is False

    email, _, verified = _build_lti_profile(
        {"email": " STUDENT@example.com ", "email_verified": True},
        7,
        "external-subject-7",
    )
    assert email == "student@example.com"
    assert verified is True


def test_record_ags_launch_context_discovers_only_safe_lineitems(db_session, monkeypatch):
    from app.models.lti import LTIPlatform, LTIResourceLinkDiscovery

    monkeypatch.setattr(lti_service_module.settings, "ENVIRONMENT", "production")
    platform = LTIPlatform(
        name="AGS test",
        issuer="https://moodle.example.com",
        client_id="ags-client",
        deployment_id="ags-deployment",
        auth_login_url="https://moodle.example.com/auth",
        auth_token_url="https://moodle.example.com/token",
        jwks_url="https://moodle.example.com/jwks",
    )
    db_session.add(platform)
    db_session.flush()

    resource_claim = "https://purl.imsglobal.org/spec/lti/claim/resource_link"
    endpoint_claim = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
    claims = {
        resource_claim: {"id": "resource-safe-1"},
        endpoint_claim: {
            "scope": ["https://purl.imsglobal.org/spec/lti-ags/scope/score"],
            "lineitem": "https://moodle.example.com/lineitems/42",
        },
    }
    assert lti_service_module.record_lti_ags_launch_context(db_session, platform, claims)
    db_session.flush()
    discovered = db_session.query(LTIResourceLinkDiscovery).filter_by(
        platform_id=platform.id, resource_link_id="resource-safe-1"
    ).one()
    assert discovered.lineitem_url == "https://moodle.example.com/lineitems/42"
    assert discovered.score_scope_allowed is True

    claims[resource_claim] = {"id": "resource-unsafe-2"}
    claims[endpoint_claim]["lineitem"] = "https://attacker.example/lineitems/99"
    assert lti_service_module.record_lti_ags_launch_context(db_session, platform, claims)
    db_session.flush()
    unsafe = db_session.query(LTIResourceLinkDiscovery).filter_by(
        platform_id=platform.id, resource_link_id="resource-unsafe-2"
    ).one()
    assert unsafe.lineitem_url is None
    assert unsafe.score_scope_allowed is False
