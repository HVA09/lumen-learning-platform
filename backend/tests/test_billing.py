"""
اختبارات المرحلة الثامنة: الاشتراكات والدفع (مزوّد الدفع مموّه دائمًا — بدون اتصال حقيقي)
"""
from unittest.mock import AsyncMock, MagicMock

from app.routers import billing as billing_router_module
from app.models.processed_webhook_event import ProcessedWebhookEvent
from app.routers.billing import _claim_webhook_event
from app.services.payment_providers.base import CheckoutResult, WebhookEvent


def _register_and_login(client, email="billing@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_list_plans_is_public_and_seeded(client):
    response = client.get("/billing/plans")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Free" in names
    assert "Pro" in names


def test_get_subscription_returns_null_when_none(client):
    token = _register_and_login(client)
    response = client.get("/billing/subscription", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() is None


def test_checkout_returns_url_from_provider(client, monkeypatch):
    mock_provider = MagicMock()
    mock_provider.create_checkout_session = AsyncMock(
        return_value=CheckoutResult(checkout_url="https://checkout.example.com/session123")
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    monkeypatch.setattr(
        billing_router_module.app_settings, "FRONTEND_URL", "https://trusted.example.com"
    )
    token = _register_and_login(client)
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    response = client.post(
        "/billing/checkout",
        json={"plan_id": pro_plan["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.example.com/session123"
    mock_provider.create_checkout_session.assert_awaited_once()
    checkout_args = mock_provider.create_checkout_session.await_args.kwargs
    assert checkout_args["success_url"] == "https://trusted.example.com/billing/success"
    assert checkout_args["cancel_url"] == "https://trusted.example.com/billing/cancel"


def test_checkout_rejects_client_supplied_redirect_urls(client, monkeypatch):
    mock_provider = MagicMock()
    mock_provider.create_checkout_session = AsyncMock(
        return_value=CheckoutResult(checkout_url="https://checkout.example.com/session123")
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    token = _register_and_login(client, "redirects@example.com")
    plan = next(p for p in client.get("/billing/plans").json() if p["name"] == "Pro")

    response = client.post(
        "/billing/checkout",
        json={
            "plan_id": plan["id"],
            "success_url": "https://attacker.example/collect",
            "cancel_url": "https://attacker.example/leave",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    mock_provider.create_checkout_session.assert_not_awaited()


def test_checkout_rejects_unknown_plan(client, monkeypatch):
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: MagicMock())
    token = _register_and_login(client)

    response = client.post(
        "/billing/checkout",
        json={"plan_id": 999999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_webhook_checkout_completed_creates_active_subscription(client, monkeypatch):
    token = _register_and_login(client, "webhookuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers).json()
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(
        return_value=WebhookEvent(
            event_type="checkout_completed",
            provider_subscription_id="sub_123",
            provider_customer_id="cus_123",
            status="active",
            client_reference_id=str(me["id"]),
            plan_id=str(pro_plan["id"]),
            event_id="evt_checkout_completed_001",
        )
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    response = client.post("/billing/webhook/stripe", json={"type": "fake"})
    assert response.status_code == 200

    sub_response = client.get("/billing/subscription", headers=headers)
    assert sub_response.json()["status"] == "active"
    assert sub_response.json()["plan"]["name"] == "Pro"


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(side_effect=ValueError("bad signature"))
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    response = client.post("/billing/webhook/stripe", json={"type": "fake"})
    assert response.status_code == 400


def test_cancel_subscription(client, monkeypatch):
    token = _register_and_login(client, "canceluser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers).json()
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(
        return_value=WebhookEvent(
            event_type="checkout_completed",
            provider_subscription_id="sub_789",
            provider_customer_id="cus_789",
            status="active",
            client_reference_id=str(me["id"]),
            plan_id=str(pro_plan["id"]),
            event_id="evt_checkout_cancel_test_001",
        )
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)
    client.post("/billing/webhook/stripe", json={"type": "fake"})

    mock_provider.cancel_subscription = AsyncMock(return_value=None)
    response = client.post("/billing/cancel", headers=headers)
    assert response.status_code == 200

    sub_response = client.get("/billing/subscription", headers=headers)
    assert sub_response.json()["status"] == "canceled"


def test_billing_requires_authentication(client):
    assert client.get("/billing/subscription").status_code == 401
    assert client.post("/billing/cancel").status_code == 401



def test_repeated_checkout_webhook_is_processed_once(client, monkeypatch, db_session):
    token = _register_and_login(client, "webhook-duplicate@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user = client.get("/users/me", headers=headers).json()
    plan = next(p for p in client.get("/billing/plans").json() if p["name"] == "Pro")

    event = WebhookEvent(
        event_type="checkout_completed",
        provider_subscription_id="sub_duplicate_001",
        provider_customer_id="cus_duplicate_001",
        status="active",
        client_reference_id=str(user["id"]),
        plan_id=str(plan["id"]),
        event_id="evt_duplicate_checkout_001",
    )
    provider = MagicMock()
    provider.verify_webhook.return_value = event
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: provider)

    activation_email = MagicMock()
    realtime_notification = AsyncMock()
    monkeypatch.setattr(
        billing_router_module, "send_subscription_activated_email", activation_email
    )
    monkeypatch.setattr(
        billing_router_module, "notify_realtime", realtime_notification
    )

    first = client.post("/billing/webhook/stripe", json={"type": "signed"})
    second = client.post("/billing/webhook/stripe", json={"type": "signed"})

    assert first.status_code == 200
    assert first.json() == {"received": True, "duplicate": False}
    assert second.status_code == 200
    assert second.json() == {"received": True, "duplicate": True}
    activation_email.assert_called_once_with(user["email"], "Pro")
    realtime_notification.assert_awaited_once()
    assert (
        db_session.query(ProcessedWebhookEvent)
        .filter_by(provider="stripe", provider_event_id="evt_duplicate_checkout_001")
        .count()
        == 1
    )


def test_webhook_event_ids_are_scoped_to_each_provider(db_session):
    event = WebhookEvent(
        event_type="ignored",
        provider_subscription_id=None,
        provider_customer_id=None,
        status=None,
        client_reference_id=None,
        event_id="shared-event-id",
    )

    assert _claim_webhook_event(event, "stripe", db_session) is True
    db_session.commit()
    assert _claim_webhook_event(event, "stripe", db_session) is False
    assert _claim_webhook_event(event, "paypal", db_session) is True
    db_session.commit()

    assert db_session.query(ProcessedWebhookEvent).count() == 2


def test_webhook_without_provider_event_id_is_rejected(client, monkeypatch, db_session):
    provider = MagicMock()
    provider.verify_webhook.return_value = WebhookEvent(
        event_type="ignored",
        provider_subscription_id=None,
        provider_customer_id=None,
        status=None,
        client_reference_id=None,
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: provider)

    response = client.post("/billing/webhook/stripe", json={"type": "signed"})

    assert response.status_code == 400
    assert db_session.query(ProcessedWebhookEvent).count() == 0


def test_unmatched_subscription_update_is_retryable_and_not_recorded(
    client, monkeypatch, db_session
):
    provider = MagicMock()
    provider.verify_webhook.return_value = WebhookEvent(
        event_type="subscription_updated",
        provider_subscription_id="sub_not_created_yet",
        provider_customer_id="cus_future",
        status="past_due",
        client_reference_id=None,
        event_id="evt_subscription_before_checkout",
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: provider)

    response = client.post("/billing/webhook/stripe", json={"type": "signed"})

    assert response.status_code == 503
    assert (
        db_session.query(ProcessedWebhookEvent)
        .filter_by(provider_event_id="evt_subscription_before_checkout")
        .count()
        == 0
    )


def test_unknown_signed_provider_event_is_recorded_and_deduplicated(
    client, monkeypatch, db_session
):
    provider = MagicMock()
    provider.verify_webhook.return_value = WebhookEvent(
        event_type="ignored",
        provider_subscription_id=None,
        provider_customer_id=None,
        status=None,
        client_reference_id=None,
        event_id="evt_unknown_001",
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: provider)

    first = client.post("/billing/webhook/stripe", json={"type": "signed"})
    second = client.post("/billing/webhook/stripe", json={"type": "signed"})

    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert db_session.query(ProcessedWebhookEvent).count() == 1
