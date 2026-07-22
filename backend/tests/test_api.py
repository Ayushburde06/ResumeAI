import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_present():
    response = client.get("/health")
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "strict-origin" in headers.get("referrer-policy", "").lower()


def test_unauthenticated_history_returns_401():
    response = client.get("/api/history")
    assert response.status_code == 401


def test_auth_register_and_login_flow():
    import uuid
    unique_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # 1. Register new user
    reg_response = client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": unique_email, "password": password},
    )
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert "token" in reg_data
    assert reg_data["user"]["email"] == unique_email

    token = reg_data["token"]

    # 2. Get profile /me with Bearer token
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == unique_email
    assert me_data["name"] == "Test User"

    # 3. Login with credentials
    login_response = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_response.status_code == 200
    assert "token" in login_response.json()
