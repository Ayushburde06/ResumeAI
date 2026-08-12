"""User career profile CRUD and profile-based resume generation."""

from database import get_db
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from limiter import limiter
from models.stats import UserStats
from models.user import User
from quota import check_user_quota, log_user_operation
from schemas.profile import (
    CareerProfileSchema,
    GenerateFromProfileRequest,
    ProfileResponse,
)
from services.agent_sse import stream_agent_sse
from services.ai_service import (
    analyse_job_description,
    rewrite_resume,
)
from services.parser import parse_resume
from services.profile_assembler import profile_to_source_text
from services.profile_service import (
    ensure_item_ids,
    get_or_create_profile,
    load_career_data,
    profile_is_complete,
    save_career_data,
)
from sqlalchemy.orm import Session

from routers.analyze import _validate_model_id
from routers.auth import ADMIN_EMAILS, require_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db, current_user.id)
    data = load_career_data(profile)
    updated = profile.updated_at.isoformat() if profile.updated_at else None
    return ProfileResponse(
        career_data=data,
        updated_at=updated,
        is_complete=profile_is_complete(data),
    )


@router.put("", response_model=ProfileResponse)
@limiter.limit("30/minute")
async def save_profile(
    request: Request,
    body: CareerProfileSchema,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    data = ensure_item_ids(body)
    profile = save_career_data(db, current_user.id, data)
    updated = profile.updated_at.isoformat() if profile.updated_at else None
    return ProfileResponse(
        career_data=data,
        updated_at=updated,
        is_complete=profile_is_complete(data),
    )


@router.post("/import-resume", response_model=ProfileResponse)
@limiter.limit("5/minute")
async def import_resume_to_profile(
    request: Request,
    resume_file: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """One-time PDF/DOCX import to bootstrap profile via AI structural parse."""
    if not resume_file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    file_bytes = await resume_file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    try:
        resume_text = parse_resume(resume_file.filename, file_bytes, resume_file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse the resume file.")

    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from the resume.")

    is_admin = current_user.email.lower() in ADMIN_EMAILS
    check_user_quota(db, current_user, operation="profile_generate")
    try:
        structured = rewrite_resume(resume_text, "", {}, model_id=None)
    except Exception:
        raise HTTPException(status_code=502, detail="AI service unavailable for import.")
    log_user_operation(db, current_user, operation="profile_generate")

    # Map TailoredResume dict → CareerProfileSchema
    pi = structured.get("personal_info", {})
    skills_raw = structured.get("skills", {})
    imported = CareerProfileSchema(
        personal_info={
            "name": pi.get("name", ""),
            "email": pi.get("email", ""),
            "phone": pi.get("phone", ""),
            "location": pi.get("location", ""),
            "linkedin": pi.get("linkedin", ""),
            "github": pi.get("github", ""),
            "website": pi.get("website", ""),
            "headline": structured.get("summary", "")[:120],
        },
        summary=structured.get("summary", ""),
        experience=[
            {
                "title": e.get("title", ""),
                "company": e.get("company", ""),
                "location": e.get("location", ""),
                "start_date": e.get("start_date", ""),
                "end_date": e.get("end_date", ""),
                "bullets": e.get("bullets", []),
                "tech_stack": [],
            }
            for e in structured.get("experience", [])
        ],
        projects=[
            {
                "name": p.get("name", ""),
                "problem": p.get("description", ""),
                "solution": "",
                "tech_stack": p.get("tech_stack", []),
                "link": p.get("link", ""),
                "live_link": p.get("live_link", ""),
                "bullets": [],
            }
            for p in structured.get("projects", [])
        ],
        education=[
            {
                "degree": e.get("degree", ""),
                "institution": e.get("institution", ""),
                "location": e.get("location", ""),
                "graduation_year": e.get("graduation_year", ""),
                "gpa": e.get("gpa", ""),
                "honors": e.get("honors", ""),
            }
            for e in structured.get("education", [])
        ],
        skills={
            "languages": skills_raw.get("languages", skills_raw.get("Languages", [])),
            "frameworks": skills_raw.get("frameworks", skills_raw.get("Frameworks", [])),
            "databases": skills_raw.get("databases", skills_raw.get("Databases", [])),
            "tools": skills_raw.get("tools", skills_raw.get("Tools", [])),
            "concepts": skills_raw.get("concepts", skills_raw.get("Concepts", [])),
        },
        certifications=[
            {
                "name": c.get("name", ""),
                "issuer": c.get("issuer", ""),
                "year": c.get("year", ""),
            }
            for c in structured.get("certifications", [])
        ],
    )
    imported = ensure_item_ids(imported)
    profile = save_career_data(db, current_user.id, imported)
    updated = profile.updated_at.isoformat() if profile.updated_at else None
    return ProfileResponse(
        career_data=imported,
        updated_at=updated,
        is_complete=profile_is_complete(imported),
    )


def _check_usage(db: Session, user: User, operation: str = "profile_generate") -> tuple[UserStats, int]:
    stats, used = check_user_quota(db, user, operation)
    return stats, used


@router.post("/agent-generate")
@limiter.limit("3/minute")
async def profile_agent_generate(
    request: Request,
    body: GenerateFromProfileRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Full agent pipeline with profile RAG + quality loop, streamed via SSE.
    Use instead of sync /generate when mode=agent for live progress.
    """
    jd = body.job_description.strip()
    if len(jd) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short.")
    if len(jd) > 20_000:
        raise HTTPException(status_code=400, detail="Job description is too long.")

    profile_row = get_or_create_profile(db, current_user.id)
    career = load_career_data(profile_row)
    if not profile_is_complete(career):
        raise HTTPException(
            status_code=422,
            detail="Profile incomplete. Add your name and at least one experience or project.",
        )

    stats, _ = _check_usage(db, current_user)
    is_admin = current_user.email.lower() in ADMIN_EMAILS
    model_id = _validate_model_id(body.model, is_admin=is_admin)
    source_text = profile_to_source_text(career)

    return StreamingResponse(
        stream_agent_sse(
            request,
            source_text,
            jd,
            model_id,
            current_user,
            career_profile=career,
            operation="profile_generate",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
