from services.auth_service import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_access_token_lifecycle():
    user_id = 42
    email = "testuser@example.com"

    token = create_access_token(user_id=user_id, email=email)
    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_token(token)
    assert payload is not None
    assert payload.get("sub") == "42"
    assert payload.get("email") == email
    assert "exp" in payload


def test_decode_invalid_token():
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
    assert decode_token(invalid_token) is None
    assert decode_token("completely_random_garbage") is None


def test_verify_password_resilience():
    # Null / Empty
    assert verify_password("", "hashed_pw") is False
    assert verify_password("plain_pw", "") is False
    assert verify_password("", "") is False
    assert verify_password(None, "hashed_pw") is False
    assert verify_password("plain_pw", None) is False

    # Malformed / Legacy / Corrupted hashes
    assert verify_password("password123", "not_a_valid_bcrypt_hash") is False
    assert verify_password("password123", "1234567890") is False
    assert verify_password("password123", "$2a$12$invalid_short_hash") is False
    assert verify_password("password123", "md5:5f4dcc3b5aa765d61d8327deb882cf99") is False

    # Non-string types
    assert verify_password("password123", 12345) is False
    assert verify_password("password123", ["hash"]) is False

