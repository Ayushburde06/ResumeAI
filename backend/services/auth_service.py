import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

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
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
