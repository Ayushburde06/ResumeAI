"""
User usage tracking — lifetime quota for free users, daily quota for premium.

FREE_DAILY_LIMIT = max AI operations per non-premium user (lifetime, NOT per day).
PREMIUM_DAILY_LIMIT = max AI operations per premium user per rolling 24 hours.

analysis_count is the lifetime counter used for free-user enforcement.
DailyUsage table tracks per-operation logs for premium rolling-window enforcement.
"""
from datetime import datetime, timedelta

from database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

FREE_DAILY_LIMIT = 3       # lifetime — 3 resumes total per free account
PREMIUM_DAILY_LIMIT = 100  # per rolling 24h for premium


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    analysis_count = Column(Integer, default=0, nullable=False)   # lifetime count
    is_premium = Column(Boolean, default=False, nullable=False)
    last_reset_at = Column(DateTime(timezone=True), nullable=True)


class DailyUsage(Base):
    """One row per AI operation — enables rolling 24-hour window queries for premium."""
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("ix_daily_usage_user_created", "user_id", "created_at"),
    )


def get_today_usage(db: Session, user_id: int, operation: str) -> int:
    """Count operations in the last rolling 24 hours for one operation bucket."""
    since = datetime.utcnow() - timedelta(hours=24)
    return (
        db.query(DailyUsage)
        .filter(
            DailyUsage.user_id == user_id,
            DailyUsage.operation == operation,
            DailyUsage.created_at >= since,
        )
        .count()
    )


def get_rolling_usage(db: Session, user_id: int) -> int:
    """Total AI operations across ALL buckets in the last rolling 24 hours."""
    since = datetime.utcnow() - timedelta(hours=24)
    return (
        db.query(DailyUsage)
        .filter(
            DailyUsage.user_id == user_id,
            DailyUsage.created_at >= since,
        )
        .count()
    )


def check_quota(db: Session, user_id: int, operation: str = "analyze") -> UserStats:
    """
    Centralised quota enforcement.

    Free users: lifetime limit (FREE_DAILY_LIMIT = 3 total, NOT per day).
    Premium users: rolling 24h limit (PREMIUM_DAILY_LIMIT = 100/day).

    Returns UserStats on success, raises HTTPException(429) if limit exceeded.
    """
    from fastapi import HTTPException

    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id, analysis_count=0, is_premium=False)
        db.add(stats)
        db.commit()
        db.refresh(stats)

    if stats.is_premium:
        # Premium: rolling 24h window
        limit = PREMIUM_DAILY_LIMIT
        used = get_rolling_usage(db, user_id)
    else:
        # Free: lifetime count — 3 resumes total, ever
        limit = FREE_DAILY_LIMIT
        used = stats.analysis_count

    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "used": used,
                "limit": limit,
                "premium": stats.is_premium,
                "message": (
                    f"You've used all {limit} free resume generations. "
                    "Upgrade to Premium for 100/day."
                ) if not stats.is_premium else (
                    f"You've used {used}/{limit} AI operations today. "
                ),
            },
        )

    return stats


def log_operation(db: Session, user_id: int, operation: str) -> None:
    """Record an AI operation for quota tracking."""
    entry = DailyUsage(user_id=user_id, operation=operation)
    db.add(entry)
    # Also bump the lifetime counter (used for free-user enforcement)
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if stats:
        stats.analysis_count += 1
    db.commit()