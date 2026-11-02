"""
إعداد fixtures للاختبارات: قاعدة بيانات PostgreSQL منفصلة للاختبار + FastAPI TestClient.
اضبط TEST_DATABASE_URL في البيئة قبل التشغيل (راجع README.md).
"""
import os

from cryptography.fernet import Fernet

# Test-only key; never reuse this value outside the automated test process.
os.environ["TOTP_ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.content.seeder import seed_all
from app.database import Base, get_db, normalize_database_url
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_backend_test"
)

engine = create_engine(normalize_database_url(TEST_DATABASE_URL))
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def isolate_class_invite_join_limiter(monkeypatch):
    """Keep API tests independent of a local Redis service; limiter has separate unit tests."""
    from app.routers import classes as classes_router

    monkeypatch.setattr(classes_router, "reserve_invite_join_attempt", lambda _user_id: 0)
    monkeypatch.setattr(classes_router, "release_invite_join_attempt", lambda _user_id: None)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    # المنهج وخطط الاشتراك والدروس والأسئلة — نفس اللي تزرعه migrations. الزرع idempotent فما يتعارض
    # لو قاعدة الاختبار متجهّزة مسبقًا بـ alembic upgrade head، ويخلّي الاختبارات تشتغل بدونه.
    with engine.begin() as connection:
        seed_all(connection)
    yield
    # Migration 0015 retains legacy AI tables outside the active ORM metadata.
    # Drop those archived tables first so their preserved foreign keys do not
    # block teardown of the users table in this disposable test database.
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS legacy_ai_messages CASCADE")
        connection.exec_driver_sql("DROP TABLE IF EXISTS legacy_ai_conversations CASCADE")
        connection.exec_driver_sql("DROP TABLE IF EXISTS legacy_ai_usage_logs CASCADE")
        Base.metadata.drop_all(bind=connection)


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
