"""
اختبارات المرحلة العاشرة: الإشعارات (REST + WebSocket الفوري)
"""
from unittest.mock import MagicMock

from app.config import settings
from app.routers import billing as billing_router_module
from app.services.payment_providers.base import WebhookEvent


def _register_and_login(client, email="notify@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.cookies.get("lumen_access")


def test_welcome_notification_created_on_register(client):
    token = _register_and_login(client, "welcome@example.com")
    response = client.get(
        "/notifications", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    types = [n["notification_type"] for n in response.json()]
    assert "welcome" in types


def test_mark_notification_read(client):
    token = _register_and_login(client, "readtest@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    notifications = client.get("/notifications", headers=headers).json()
    target = notifications[0]
    assert target["is_read"] is False

    response = client.post(f"/notifications/{target['id']}/read", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_mark_all_read(client):
    token = _register_and_login(client, "readall@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/notifications/read-all", headers=headers)
    notifications = client.get("/notifications", headers=headers).json()
    assert all(n["is_read"] for n in notifications)


def test_cannot_read_other_users_notification(client):
    token_a = _register_and_login(client, "notifyowner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    target = client.get("/notifications", headers=headers_a).json()[0]

    token_b = _register_and_login(client, "notifyintruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.post(f"/notifications/{target['id']}/read", headers=headers_b)
    assert response.status_code == 404


def test_notifications_require_authentication(client):
    assert client.get("/notifications").status_code == 401


def test_websocket_rejects_invalid_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/notifications?token=not-a-real-token", headers={"origin": settings.CORS_ORIGINS[0]}) as websocket:
            websocket.receive_json()


def test_websocket_broadcasts_realtime_notification_to_multiple_user_sessions(
    client, monkeypatch
):
    # The mocked Stripe webhook is test-only; production payments remain disabled by default.
    monkeypatch.setattr(billing_router_module.app_settings, "PAYMENT_PROVIDER", "stripe")
    email = "wsuser@example.com"
    password = "StrongPass123"
    token = _register_and_login(client, email, password)
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers).json()
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    origin_headers = {"origin": settings.CORS_ORIGINS[0]}
    with client.websocket_connect(
        "/ws/notifications", headers=origin_headers
    ) as first_session:
        # A second login creates a distinct server-side session for the same user.
        second_login = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert second_login.status_code == 200
        second_token = second_login.cookies.get("lumen_access")
        assert second_token and second_token != token

        with client.websocket_connect(
            "/ws/notifications", headers=origin_headers
        ) as second_session:
            mock_provider = MagicMock()
            mock_provider.verify_webhook = MagicMock(
                return_value=WebhookEvent(
                    event_id="evt_ws_subscription_activated_multi_session_001",
                    event_type="checkout_completed",
                    provider_subscription_id="sub_ws_multi_session",
                    provider_customer_id="cus_ws_multi_session",
                    status="active",
                    client_reference_id=str(me["id"]),
                    plan_id=str(pro_plan["id"]),
                )
            )
            monkeypatch.setattr(
                billing_router_module, "get_payment_provider", lambda: mock_provider
            )
            webhook_response = client.post(
                "/billing/webhook/stripe", json={"type": "fake"}
            )
            assert webhook_response.status_code == 200

            first_data = first_session.receive_json()
            second_data = second_session.receive_json()
            assert first_data["id"] == second_data["id"]
            assert first_data["title"] == "تم تفعيل اشتراكك"
            assert first_data["notification_type"] == "billing"
            assert second_data == first_data

    saved_notifications = client.get("/notifications", headers=headers)
    assert saved_notifications.status_code == 200
    assert any(
        item["id"] == first_data["id"] and item["title"] == "تم تفعيل اشتراكك"
        for item in saved_notifications.json()
    )


def test_websocket_rejects_untrusted_origin_even_with_session_cookie(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    _register_and_login(client, "ws-origin@example.com")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws/notifications",
            headers={"origin": "https://attacker.invalid"},
        ) as websocket:
            websocket.receive_json()



def test_notification_limit_is_bounded(client):
    token = _register_and_login(client, "notify-limit@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/notifications?limit=0", headers=headers).status_code == 422
    assert client.get("/notifications?limit=101", headers=headers).status_code == 422
