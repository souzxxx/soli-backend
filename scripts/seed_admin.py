import os

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.user import RoleEnum, User


def main() -> None:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    full_name = os.getenv("ADMIN_FULL_NAME", "Admin")

    if not email or not password:
        raise SystemExit("ADMIN_EMAIL and ADMIN_PASSWORD must be set")

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print("Admin already exists")
            return

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=RoleEnum.ADMIN,
        )
        db.add(user)
        db.commit()
        print("Admin created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
