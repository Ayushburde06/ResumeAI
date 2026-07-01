"""
Admin Router — endpoints only accessible by admin users.

GET  /api/admin/learning          list recent learning examples (paginated)
GET  /api/admin/learning/export   download as JSON
GET  /api/admin/learning/stats    aggregate stats by job_title + section
DELETE /api/admin/learning/{id}   remove a bad example
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.learning import LearningExample, DeltaPattern
from models.user import User
from routers.auth import require_user, ADMIN_EMAILS

router = APIRouter()


def _require_admin(current_user: User = Depends(require_user)) -> User:
    if current_user.email.lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


@router.get("/admin/learning")
def list_learning_examples(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    job_title: Optional[str] = Query(None),
    section_type: Optional[str] = Query(None),
    min_score: int = Query(0),
    approved_only: bool = Query(False),
    _admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """List learning examples with optional filters."""
    q = db.query(LearningExample)
    if job_title:
        q = q.filter(LearningExample.job_title_key.ilike(f"%{job_title.lower()}%"))
    if section_type:
        q = q.filter(LearningExample.section_type == section_type)
    if min_score > 0:
        q = q.filter(LearningExample.ats_score >= min_score)
    if approved_only:
        q = q.filter(LearningExample.user_approved == True)  # noqa: E712

    total = q.count()
    rows = (
        q.order_by(LearningExample.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": r.id,
                "job_title_key": r.job_title_key,
                "seniority": r.seniority,
                "section_type": r.section_type,
                "ats_score": r.ats_score,
                "model_used": r.model_used,
                "user_approved": r.user_approved,
                "history_id": r.history_id,
                "content_preview": r.content[:200],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/admin/learning/export")
def export_learning_examples(
    min_score: int = Query(88),
    _admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Export all high-quality learning examples as JSON."""
    rows = (
        db.query(LearningExample)
        .filter(
            LearningExample.ats_score >= min_score,
            LearningExample.user_approved != False,  # noqa: E712
        )
        .order_by(LearningExample.ats_score.desc())
        .all()
    )
    data = [
        {
            "id": r.id,
            "job_title_key": r.job_title_key,
            "seniority": r.seniority,
            "skills_key": r.skills_key,
            "section_type": r.section_type,
            "ats_score": r.ats_score,
            "model_used": r.model_used,
            "user_approved": r.user_approved,
            "content": r.content,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return JSONResponse(
        content={"count": len(data), "examples": data},
        headers={"Content-Disposition": "attachment; filename=learning_examples.json"},
    )


@router.get("/admin/learning/stats")
def learning_stats(
    _admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Aggregate stats: count + avg ATS by job title and section."""
    by_title = (
        db.query(
            LearningExample.job_title_key,
            func.count(LearningExample.id).label("count"),
            func.avg(LearningExample.ats_score).label("avg_ats"),
        )
        .group_by(LearningExample.job_title_key)
        .order_by(func.count(LearningExample.id).desc())
        .limit(20)
        .all()
    )
    by_section = (
        db.query(
            LearningExample.section_type,
            func.count(LearningExample.id).label("count"),
            func.avg(LearningExample.ats_score).label("avg_ats"),
        )
        .group_by(LearningExample.section_type)
        .all()
    )
    delta_top = (
        db.query(DeltaPattern)
        .order_by(DeltaPattern.ats_gain.desc())
        .limit(10)
        .all()
    )
    total = db.query(func.count(LearningExample.id)).scalar()
    approved = db.query(func.count(LearningExample.id)).filter(LearningExample.user_approved == True).scalar()  # noqa: E712
    rejected = db.query(func.count(LearningExample.id)).filter(LearningExample.user_approved == False).scalar()  # noqa: E712

    return {
        "total_examples": total,
        "user_approved": approved,
        "user_rejected": rejected,
        "by_job_title": [
            {"job_title": r.job_title_key, "count": r.count, "avg_ats": round(float(r.avg_ats or 0), 1)}
            for r in by_title
        ],
        "by_section": [
            {"section": r.section_type, "count": r.count, "avg_ats": round(float(r.avg_ats or 0), 1)}
            for r in by_section
        ],
        "top_delta_patterns": [
            {
                "job_title_key": d.job_title_key,
                "section_type": d.section_type,
                "ats_before": d.ats_before,
                "ats_after": d.ats_after,
                "ats_gain": d.ats_gain,
                "keywords_added": json.loads(d.keywords_added) if d.keywords_added else [],
            }
            for d in delta_top
        ],
    }


@router.delete("/admin/learning/{example_id}")
def delete_learning_example(
    example_id: int,
    _admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Remove a bad / incorrect learning example."""
    row = db.query(LearningExample).filter(LearningExample.id == example_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Example not found.")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": example_id}
