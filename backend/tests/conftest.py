"""
إعداد fixtures للاختبارات: قاعدة بيانات PostgreSQL منفصلة للاختبار + FastAPI TestClient.
اضبط TEST_DATABASE_URL في البيئة قبل التشغيل (راجع README.md).
"""
import os

# Tests explicitly use a non-production mode; the application default is fail-closed.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.content.seeder import seed_all
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def disable_external_email_queue(monkeypatch):
    """Unit tests must not wait for a real Redis/Celery broker or send emails."""
    from app import tasks

    monkeypatch.setattr(tasks, "queue_email", lambda *args, **kwargs: None)


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_backend_test"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    # المنهج وخطط الاشتراك والدروس والأسئلة — نفس اللي تزرعه migrations. الزرع idempotent فما يتعارض
    # لو قاعدة الاختبار متجهّزة مسبقًا بـ alembic upgrade head، ويخلّي الاختبارات تشتغل بدونه.
    with engine.begin() as connection:
        seed_all(connection)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    """كل اختبار يشتغل داخل transaction يُلغى (rollback) بعد انتهائه — عزل كامل بين الاختبارات"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
