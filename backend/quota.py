"""
Shared quota helpers — call these at the top of every AI-costed endpoint.

Import path:  from quota import check_user_quota, log_user_operation
"""
from models.stats import UserStats, check_quota, get_rolling_usage, log_operation
from models.user import User
from sqlalchemy.orm import Session


def check_user_quota(db: Session, user: User, operation: str = "analyze") -> tuple[UserStats, int]:
    """Check daily quota. Returns (stats, rolling_usage_across_all_buckets).
    Raises HTTPException(429) for free users over limit."""
    stats = check_quota(db, user.id, operation)
    used = get_rolling_usage(db, user.id)
    return stats, used


def log_user_operation(db: Session, user: User, operation: str = "analyze") -> None:
    """Record an AI operation against the user's daily quota."""
    log_operation(db, user.id, operation)


def get_user_quota_summary(db: Session, user: User) -> tuple[int, bool]:
    """Return (rolling_usage, is_premium) for display purposes (no enforcement)."""
    from models.stats import UserStats
    stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()
    is_premium = stats.is_premium if stats else False
    used = get_rolling_usage(db, user.id)
    return used, is_premium