"""
اتصال قاعدة البيانات عبر SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings


def normalize_database_url(url: str) -> str:
    """Use the psycopg2 driver provided by requirements for common PostgreSQL URL forms."""
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


engine = create_engine(
    normalize_database_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency تعطي جلسة DB لكل طلب، وتغلقها تلقائيًا بعد الانتهاء."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
