"""Provider adapters must preserve verified webhook event IDs."""

import asyncio
import json
import sys
from types import SimpleNamespace

from app.services.payment_providers.paypal_provider import PayPalProvider
from app.services.payment_providers.stripe_provider import StripeProvider


def test_stripe_adapter_preserves_subscription_deletion_event_id(monkeypatch):
    payload_event = {
        "id": "evt_stripe_subscription_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "status": "canceled",
            }
        },
    }
    fake_stripe = SimpleNamespace(
        api_key=None,
        Webhook=SimpleNamespace(construct_event=lambda *_args: payload_event),
    )
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)

    provider = StripeProvider("sk_test_fake", "whsec_fake")
    event = provider.verify_webhook(b"{}", {"stripe-signature": "signed"})

    assert event.event_id == "evt_stripe_subscription_deleted"
    assert event.event_type == "subscription_canceled"
    assert event.provider_subscription_id == "sub_123"


def test_paypal_adapter_preserves_verified_event_id(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeAsyncClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **_kwargs):
            if url.endswith("/v1/oauth2/token"):
                return FakeResponse({"access_token": "test-access-token"})
            return FakeResponse({"verification_status": "SUCCESS"})

    monkeypatch.setattr(
        "app.services.payment_providers.paypal_provider.httpx.AsyncClient",
        FakeAsyncClient,
    )
    provider = PayPalProvider(
        client_id="client-id",
        client_secret="client-secret",
        webhook_id="webhook-id",
        api_base="https://api-m.sandbox.paypal.com",
    )
    payload = {
        "id": "WH-7X12345678901234-1234567890123456",
        "event_type": "BILLING.SUBSCRIPTION.UPDATED",
        "resource": {
            "id": "I-SUBSCRIPTION",
            "custom_id": "12:34",
            "status": "ACTIVE",
        },
    }

    event = asyncio.run(
        provider.verify_webhook_async(
            json.dumps(payload).encode("utf-8"),
            {
                "paypal-auth-algo": "SHA256withRSA",
                "paypal-cert-url": "https://api.paypal.com/cert",
                "paypal-transmission-id": "transmission-id",
                "paypal-transmission-sig": "signature",
                "paypal-transmission-time": "2026-10-31T00:00:00Z",
            },
        )
    )

    assert event.event_id == payload["id"]
    assert event.event_type == "subscription_updated"
    assert event.provider_subscription_id == "I-SUBSCRIPTION"
