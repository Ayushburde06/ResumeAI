"""
test_api.py — Integration tests for the FastAPI backend.

Auth model: Supabase Google OAuth only.
  - /api/auth/register and /api/auth/login no longer exist.
  - All protected endpoints require a Supabase-issued JWT Bearer token.
  - Tests generate mock JWTs signed with SUPABASE_JWT_SECRET for testing.
"""
import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ── JWT helpers for test tokens ───────────────────────────────────────────────

_TEST_JWT_SECRET = os.environ.get(
    "SUPABASE_JWT_SECRET",
    "super-secret-jwt-token-with-at-least-32-characters-long",
)


def _make_test_jwt(email: str, name: str = "Test User", expired: bool = False) -> str:
    """
    Generate a signed HS256 JWT that matches the format Supabase produces.
    Requires PyJWT to be installed (it is listed in requirements).
    """
    try:
        import jwt as pyjwt
    except ImportError:
        pytest.skip("PyJWT not installed — skipping JWT-dependent tests")

    now = int(time.time())
    exp = now - 10 if expired else now + 3600
    payload = {
        "sub": str(uuid.uuid4()),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": exp,
        "user_metadata": {"full_name": name},
    }
    return pyjwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


# ── Basic health / security tests ─────────────────────────────────────────────

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


# ── Auth: JWT validation tests ────────────────────────────────────────────────

def test_valid_jwt_allows_me_access():
    """
    A properly signed Supabase JWT should allow the /api/auth/me endpoint to
    return the user's profile (auto-upserted from the JWT payload).
    """
    email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    token = _make_test_jwt(email, name="Test User")

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["name"] == "Test User"
    # Should have quota fields
    assert "analyses_used" in data
    assert "analyses_limit" in data


def test_invalid_jwt_returns_401():
    """
    A completely invalid Bearer token must return 401, never 500.
    This replaces the old malformed-password-hash test: the auth failure path
    for OAuth-only auth is an invalid/missing JWT.
    """
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401


def test_expired_jwt_returns_401():
    """
    An expired Supabase JWT must return 401 (not 500 or 200).
    """
    email = f"expired_{uuid.uuid4().hex[:8]}@example.com"
    token = _make_test_jwt(email, expired=True)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_missing_auth_header_returns_401():
    response = client.get("/api/auth/me")
    assert response.status_code == 401


# ── Profile CRUD flow ─────────────────────────────────────────────────────────

def test_profile_crud_flow():
    """
    Full profile read → write → read flow using a mock Supabase JWT.
    """
    email = f"profile_{uuid.uuid4().hex[:8]}@example.com"
    token = _make_test_jwt(email, name="Profile User")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get empty profile (auto-created)
    get_resp = client.get("/api/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["is_complete"] is False

    # 2. Save a profile
    save_resp = client.put(
        "/api/profile",
        headers=headers,
        json={
            "personal_info": {"name": "Jane Doe", "email": email},
            "summary": "Backend engineer",
            "experience": [{
                "title": "Engineer", "company": "Acme", "location": "",
                "start_date": "2022", "end_date": "Present",
                "bullets": ["Built APIs"], "tech_stack": ["Python"],
            }],
            "projects": [],
            "education": [],
            "skills": {
                "languages": ["Python"], "frameworks": [], "databases": [],
                "tools": [], "concepts": [], "cloud": [], "devops": [],
            },
            "certifications": [],
        },
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["is_complete"] is True


def test_profile_generate_requires_complete_profile():
    """
    Calling /api/profile/generate with an incomplete profile must return 422.
    """
    email = f"gen_{uuid.uuid4().hex[:8]}@example.com"
    token = _make_test_jwt(email, name="Gen User")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/profile/generate",
        headers=headers,
        json={"job_description": "A" * 60, "mode": "script"},
    )
    # Incomplete profile → validation error
    assert resp.status_code == 422
