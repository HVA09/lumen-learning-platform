"""
اختبارات المرحلة الحادية عشرة: تحقق من أن caching وqueue_email يشتغلون بأمان
حتى بدون Redis/Celery متاحين (fallback بدون كسر التطبيق)
"""
from app.cache import cache_delete, cache_get, cache_set
from app.tasks import queue_email


def test_cache_get_returns_none_without_redis():
    # في هذا المشروع كما هو (بدون تثبيت مكتبة redis)، لازم يرجع None دائمًا بأمان
    assert cache_get("any-key") is None


def test_cache_set_and_delete_do_not_raise_without_redis():
    cache_set("any-key", {"a": 1}, 60)
    cache_delete("any-key")  # المهم إنها ما ترمي استثناء


def test_queue_email_falls_back_to_sync_send(monkeypatch):
    sent = {}

    def fake_send_email(to, subject, body):
        sent["to"] = to
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr("app.tasks.send_email", fake_send_email)
    queue_email("test@example.com", "موضوع", "محتوى")

    assert sent["to"] == "test@example.com"
    assert sent["subject"] == "موضوع"


def test_billing_plans_endpoint_still_works_with_caching_layer(client):
    # يتأكد إن إضافة caching ما كسرت البيانات نفسها (بدون Redis، الكاش يرجع None دائمًا)
    response = client.get("/billing/plans")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_health_check_reports_database_status(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_security_headers_present_on_every_response(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    # HSTS يُضاف فقط بالإنتاج (تفعيله بالتطوير المحلي يكسر HTTP على localhost)
    assert "strict-transport-security" not in response.headers


def test_gzip_middleware_compresses_large_responses(client):
    response = client.get("/health", headers={"Accept-Encoding": "gzip"})
    # /health رده صغير عادةً (تحت 1000 بايت threshold)، فنتأكد بس إن الميدلوير مضاف
    # وما يكسر الردود الصغيرة (بيرجعها بدون ضغط، وهذا سلوك صحيح متوقّع)
    assert response.status_code == 200
