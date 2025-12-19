from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.user import RoleEnum, User

# Use SQLite in-memory for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(db: Session) -> str:
    user = User(
        email="admin@test.com",
        hashed_password="hashed_secret",
        full_name="Admin User",
        role=RoleEnum.ADMIN,
    )
    db.add(user)
    db.commit()
    return create_access_token(data={"sub": user.email})


@pytest.fixture
def operator_token(db: Session) -> str:
    user = User(
        email="op@test.com",
        hashed_password="hashed_secret",
        full_name="Operator User",
        role=RoleEnum.OPERATOR,
    )
    db.add(user)
    db.commit()
    return create_access_token(data={"sub": user.email})


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def operator_headers(operator_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {operator_token}"}
