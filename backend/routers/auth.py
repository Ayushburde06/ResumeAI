"""Auth router — email/password register + login with bot/spam detection."""
import logging
import os
import re
import hashlib
import json
from pathlib import Path

logger = logging.getLogger(__name__)

import httpx
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from limiter import limiter
from models.stats import FREE_DAILY_LIMIT, UserStats
from models.user import User
from quota import get_user_quota_summary
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter(prefix="/auth", tags=["auth"])

# Admin emails get unlimited premium access automatically.
_raw_admin = os.environ.get("ADMIN_EMAILS", "")
ADMIN_EMAILS: set[str] = {e.strip().lower() for e in _raw_admin.split(",") if e.strip()}


def _is_admin(email: str) -> bool:
    return email.lower().strip() in ADMIN_EMAILS


def _ensure_premium(user_id: int, db: Session) -> UserStats:
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id, analysis_count=0, is_premium=True)
        db.add(stats)
    elif not stats.is_premium:
        stats.is_premium = True
    db.commit()
    db.refresh(stats)
    return stats


# ── Bot / spam email detection ────────────────────────────────────────────────

# Known disposable email domains (updated regularly)
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "yopmail.com", "throwaway.email", "sharklasers.com", "trashmail.com",
    "temp-mail.org", "fakeinbox.com", "emailondeck.com", "moakt.com",
    "dispostable.com", "maildrop.cc", "harakirimail.com", "spamgourmet.com",
    "wegwerfemail.de", "temporary-mail.net", "guerrillamail.info",
    "guerrillamail.biz", "guerrillamail.org", "guerrillamail.net",
    "guerrillamail.de", "guerrillamailblock.com", "pokemail.net",
    "spam4.me", "spamdecoy.net", "discardmail.com", "discard.email",
    "mailcatch.com", "tyldd.com", "getnada.com", "inboxkitten.com",
    "mailsac.com", "anonaddy.me", "simplelogin.com", "simplelogin.co",
    "aleeas.com", "8alias.com", "dralias.com", "slmail.me",
    "silomails.com", "erine.email",
}

# Suspicious email patterns (bots often use these)
_BOT_PATTERNS = [
    re.compile(r"test\d+@", re.IGNORECASE),
    re.compile(r"bot\d+@", re.IGNORECASE),
    re.compile(r"spam\d+@", re.IGNORECASE),
    re.compile(r"^[a-z]{1,2}\d{5,}@", re.IGNORECASE),  # e.g. ab12345@gmail.com
    re.compile(r"^[a-f0-9]{20,}@", re.IGNORECASE),       # hex hash as email
]

# Maximum registration rate per IP (via limiter)
_MAX_PASSWORD_LENGTH = 128
_MIN_PASSWORD_LENGTH = 8


def _is_bot_email(email: str) -> str | None:
    """Returns a reason string if the email looks like a bot, else None."""
    domain = email.split("@")[-1].lower()
    if domain in DISPOSABLE_DOMAINS:
        return "Disposable email addresses are not allowed."
    for pattern in _BOT_PATTERNS:
        if pattern.search(email):
            return "This email looks suspicious."
    return None


def _validate_password(password: str) -> str | None:
    """Returns error string if password is too weak, else None."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f"Password must be at least {_MIN_PASSWORD_LENGTH} characters."
    if len(password) > _MAX_PASSWORD_LENGTH:
        return f"Password must be less than {_MAX_PASSWORD_LENGTH} characters."
    return None


# ── Request / Response models ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("Name must be between 1 and 100 characters.")
        return v

    @field_validator("password")
    @classmethod
    def password_ok(cls, v: str) -> str:
        err = _validate_password(v)
        if err:
            raise ValueError(err)
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    name: str
    analyses_used: int
    analyses_limit: int
    is_premium: bool


# ── JWT dependency ────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        from services.auth_service import decode_token
        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")  # prevent registration spam
async def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    name = body.name.strip()

    # Bot/spam check
    bot_reason = _is_bot_email(email)
    if bot_reason:
        raise HTTPException(status_code=400, detail=bot_reason)

    # Check if email already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    from services.auth_service import hash_password, create_access_token
    hashed = hash_password(body.password)

    user = User(name=name, email=email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)

    if _is_admin(email):
        _ensure_premium(user.id, db)

    token = create_access_token(user.id, email)
    
    # Create UserStats row for quota tracking
    existing_stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()
    if not existing_stats:
        stats = UserStats(user_id=user.id, analysis_count=0, is_premium=_is_admin(email))
        db.add(stats)
        db.commit()

    used, is_premium = get_user_quota_summary(db, user)

    return AuthResponse(
        token=token,
        email=email,
        name=name,
        analyses_used=used,
        analyses_limit=FREE_DAILY_LIMIT,
        is_premium=is_premium,
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    from services.auth_service import verify_password, create_access_token
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id, email)
    used, is_premium = get_user_quota_summary(db, user)

    return AuthResponse(
        token=token,
        email=user.email,
        name=user.name,
        analyses_used=used,
        analyses_limit=FREE_DAILY_LIMIT,
        is_premium=is_premium,
    )


@router.get("/me")
@limiter.limit("60/minute")
def me(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        if _is_admin(user.email):
            _ensure_premium(user.id, db)
        used, is_premium = get_user_quota_summary(db, user)
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "analyses_used": used,
            "analyses_limit": FREE_DAILY_LIMIT,
            "is_premium": is_premium,
        }
    except Exception as e:
        logger.error(f"Error in /me: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching user data.")