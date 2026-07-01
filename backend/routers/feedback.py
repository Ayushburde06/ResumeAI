"""
Feedback Router — lets users mark a resume result as helpful (👍) or not (👎).

POST /api/feedback
  { "history_id": 42, "rating": "up" | "down" }

This marks the linked learning_examples rows with user_approved=True/False.
Results with user_approved=False are DOWN-weighted in future RAG retrieval.
Results with user_approved=True are UP-weighted (returned first).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models.learning import LearningExample
from models.history import ResumeHistory
from routers.auth import require_user
from models.user import User
from limiter import limiter
from fastapi import Request

router = APIRouter()


class FeedbackRequest(BaseModel):
    history_id: int
    rating: str   # "up" or "down"

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        if v not in ("up", "down"):
            raise ValueError("rating must be 'up' or 'down'")
        return v


@router.post("/feedback")
@limiter.limit("20/minute")
def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Mark learning examples linked to a history row as user-approved or rejected.
    Only the owner of that history row can rate it (IDOR fix).
    """
    # Verify ownership before touching learning data
    history_row = (
        db.query(ResumeHistory)
        .filter(
            ResumeHistory.id == body.history_id,
            ResumeHistory.user_id == current_user.id,
        )
        .first()
    )
    if not history_row:
        raise HTTPException(status_code=404, detail="Resume not found.")

    approved = body.rating == "up"

    rows = (
        db.query(LearningExample)
        .filter(LearningExample.history_id == body.history_id)
        .all()
    )

    if not rows:
        # Graceful: no linked learning examples yet — still OK, just no-op
        return {"status": "ok", "updated": 0}

    for row in rows:
        row.user_approved = approved

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save feedback.")

    return {"status": "ok", "updated": len(rows), "approved": approved}
