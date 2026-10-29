"""Create the initial Lumen administrator through a trusted local CLI.

Run from the backend directory after migrations:
    python -m app.create_admin
This is intentionally not an HTTP endpoint.
"""
from getpass import getpass

from sqlalchemy import func
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole


def create_admin_user(db: Session, email: str, password: str) -> User:
    try:
        normalized_email = str(TypeAdapter(EmailStr).validate_python(email.strip())).lower()
    except ValidationError as exc:
        raise ValueError("Enter a valid email address.") from exc
    if len(password) < 8:
        raise ValueError("The password must contain at least 8 characters.")
    if db.query(func.count(User.id)).filter(User.role == UserRole.admin).scalar():
        raise ValueError("An administrator already exists; refusing to bootstrap another.")
    existing = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if existing:
        raise ValueError("An account with this email already exists.")
    user = User(
        email=normalized_email,
        hashed_password=hash_password(password),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    email = input("Administrator email: ").strip().lower()
    password = getpass("Administrator password (minimum 8 characters): ")
    confirmation = getpass("Repeat administrator password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    db = SessionLocal()
    try:
        user = create_admin_user(db, email, password)
    except ValueError as exc:
        db.rollback()
        raise SystemExit(str(exc)) from exc
    finally:
        db.close()
    print(f"Created administrator account for {user.email} (id={user.id}).")


if __name__ == "__main__":
    main()
