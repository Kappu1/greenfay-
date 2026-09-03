import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date

from app.database import Base, get_db
from app.main import app, seed_data
from app.auth import pw_hash
from app.models import User

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    return eng

@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionTesting = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    db = SessionTesting()

    # Seed admin user if not present
    if not db.query(User).filter(User.email == 'admin@greenfay.local').first():
        db.add(User(email='admin@greenfay.local', name='Admin', role='admin', password_hash=pw_hash('admin123'), active=True))
        db.commit()

    yield db

    db.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def auth_client(client):
    res = client.post("/api/login", json={"email": "admin@greenfay.local", "password": "admin123"})
    assert res.status_code == 200
    return client

