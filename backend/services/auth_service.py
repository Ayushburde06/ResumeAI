import os
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

_raw_secret = os.environ.get("JWT_SECRET", "")
if not _raw_secret or _raw_secret == "CHANGE_THIS_TO_A_RANDOM_64_CHAR_HEX_STRING":
    import sys
    print(
        "\n[FATAL] JWT_SECRET env var is missing or still set to the placeholder value.\n"
        "  Generate one with:  python -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "  Then set it in backend/.env or your deployment environment.\n",
        file=sys.stderr,
    )
    sys.exit(1)
SECRET_KEY = _raw_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed or not plain:
        return False
    try:
        if isinstance(plain, str):
            plain_bytes = plain.encode("utf-8")
        elif isinstance(plain, bytes):
            plain_bytes = plain
        else:
            return False

        if isinstance(hashed, str):
            hashed_bytes = hashed.encode("utf-8")
        elif isinstance(hashed, bytes):
            hashed_bytes = hashed
        else:
            return False

        # Bcrypt hashes require at least 22 characters for salt/header
        if len(hashed_bytes) < 22:
            return False

        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        return False


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
