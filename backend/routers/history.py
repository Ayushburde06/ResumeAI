from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.history import ResumeHistory
from models.user import User
from routers.auth import require_user
from limiter import limiter

router = APIRouter(prefix="/history", tags=["history"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SaveHistoryRequest(BaseModel):
    tailored_resume: dict
    cover_letter: Optional[dict] = None
    application_email: Optional[dict] = None
    job_analysis: Optional[dict] = None
    quality_report: Optional[dict] = None
    job_description: Optional[str] = None
    ats_score: Optional[int] = None
    matched_keywords: Optional[list] = None
    missing_keywords: Optional[list] = None
    total_keywords: Optional[int] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/save")
@limiter.limit("30/minute")
def save_history(
    request: Request,
    body: SaveHistoryRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    job_title = ""
    if body.job_analysis:
        job_title = body.job_analysis.get("job_title", "")

    entry = ResumeHistory(
        user_id=user.id,
        job_title=job_title,
        ats_score=body.ats_score,
        tailored_resume=body.tailored_resume,
        cover_letter=body.cover_letter,
        application_email=body.application_email,
        job_analysis=body.job_analysis,
        quality_report=body.quality_report,
        job_description=body.job_description,
        matched_keywords=body.matched_keywords,
        missing_keywords=body.missing_keywords,
        total_keywords=body.total_keywords,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "message": "Saved to history."}


@router.get("")
@limiter.limit("60/minute")
def list_history(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(ResumeHistory)
        .filter(ResumeHistory.user_id == user.id)
        .order_by(ResumeHistory.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": e.id,
            "job_title": e.job_title or "Untitled Role",
            "candidate_name": (
                e.tailored_resume.get("personal_info", {}).get("name", "")
                if e.tailored_resume else ""
            ),
            "ats_score": e.ats_score,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.get("/{entry_id}")
@limiter.limit("60/minute")
def get_history(
    request: Request,
    entry_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(ResumeHistory)
        .filter(ResumeHistory.id == entry_id, ResumeHistory.user_id == user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {
        "id": entry.id,
        "job_title": entry.job_title or "Untitled Role",
        "ats_score": entry.ats_score,
        "tailored_resume": entry.tailored_resume,
        "cover_letter": entry.cover_letter,
        "application_email": entry.application_email,
        "job_analysis": entry.job_analysis,
        "quality_report": entry.quality_report,
        "job_description": entry.job_description,
        "matched_keywords": entry.matched_keywords or [],
        "missing_keywords": entry.missing_keywords or [],
        "total_keywords": entry.total_keywords or 0,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.delete("/{entry_id}")
@limiter.limit("30/minute")
def delete_history(
    request: Request,
    entry_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(ResumeHistory)
        .filter(ResumeHistory.id == entry_id, ResumeHistory.user_id == user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Resume not found.")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted."}
