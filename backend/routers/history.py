
from database import DATABASE_URL, get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from limiter import limiter
from models.history import ResumeHistory
from models.user import User
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from routers.auth import require_user

router = APIRouter(prefix="/history", tags=["history"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SaveHistoryRequest(BaseModel):
    tailored_resume: dict
    cover_letter: dict | None = None
    application_email: dict | None = None
    job_analysis: dict | None = None
    quality_report: dict | None = None
    job_description: str | None = None
    ats_score: int | None = None
    matched_keywords: list | None = None
    missing_keywords: list | None = None
    total_keywords: int | None = None


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
    # Avoid loading heavy JSON blobs (cover letter, full JD, etc.) for the list view.
    if DATABASE_URL.startswith("sqlite"):
        name_col = func.json_extract(ResumeHistory.tailored_resume, "$.personal_info.name")
    else:
        # PostgreSQL / JSON-capable dialects
        name_col = ResumeHistory.tailored_resume["personal_info"]["name"].as_string()

    rows = (
        db.query(
            ResumeHistory.id,
            ResumeHistory.job_title,
            ResumeHistory.ats_score,
            ResumeHistory.created_at,
            name_col.label("candidate_name"),
        )
        .filter(ResumeHistory.user_id == user.id)
        .order_by(ResumeHistory.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": row.id,
            "job_title": row.job_title or "Untitled Role",
            "candidate_name": row.candidate_name or "",
            "ats_score": row.ats_score,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
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
