import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from limiter import limiter          # shared instance registered on app.state
from models.user import User
from models.stats import UserStats, FREE_LIMIT
from services.auth_service import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Admin emails get unlimited premium access automatically.
# Set ADMIN_EMAILS=you@example.com,other@example.com in .env
_raw_admin = os.environ.get("ADMIN_EMAILS", "")
ADMIN_EMAILS: set[str] = {e.strip().lower() for e in _raw_admin.split(",") if e.strip()}


def _is_admin(email: str) -> bool:
    return email.lower().strip() in ADMIN_EMAILS


def _ensure_premium(user_id: int, db: Session) -> UserStats:
    """Create or update UserStats to is_premium=True for admin accounts."""
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id, analysis_count=0, is_premium=True)
        db.add(stats)
    elif not stats.is_premium:
        stats.is_premium = True
    db.commit()
    db.refresh(stats)
    return stats

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    analyses_used: int = 0
    analyses_limit: int = FREE_LIMIT
    is_premium: bool = False


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ── Dependency: current user (optional) ──────────────────────────────────────

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    return user


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
@limiter.limit("10/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Full name is required.")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Name must be 100 characters or fewer.")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Strip any HTML tags from name to prevent stored XSS via non-React renderers
    name = re.sub(r'<[^>]+>', '', name).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name contains invalid characters.")

    email_lower = body.email.lower().strip()
    user = User(
        name=name,
        email=email_lower,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Grant unlimited premium to admin accounts on registration
    is_admin = _is_admin(email_lower)
    if is_admin:
        _ensure_premium(user.id, db)

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user=UserOut(
            id=user.id, name=user.name, email=user.email,
            analyses_used=0,
            analyses_limit=FREE_LIMIT,
            is_premium=is_admin,
        ),
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Always fetch live stats so the frontend gets the real usage count on login
    # Admin accounts are auto-upgraded to premium on every login (idempotent)
    if _is_admin(user.email):
        stats = _ensure_premium(user.id, db)
    else:
        stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()

    analysis_count = stats.analysis_count if stats else 0
    is_premium = stats.is_premium if stats else False

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user=UserOut(
            id=user.id, name=user.name, email=user.email,
            analyses_used=analysis_count,
            analyses_limit=FREE_LIMIT,
            is_premium=is_premium,
        ),
    )


@router.get("/me")
def me(user: User = Depends(require_user), db: Session = Depends(get_db)):
    if _is_admin(user.email):
        stats = _ensure_premium(user.id, db)
    else:
        stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()
    analysis_count = stats.analysis_count if stats else 0
    is_premium = stats.is_premium if stats else False
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "analyses_used": analysis_count,
        "analyses_limit": FREE_LIMIT,
        "is_premium": is_premium,
    }
