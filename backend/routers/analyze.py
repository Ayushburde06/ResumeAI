import io
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.history import ResumeHistory
from models.stats import UserStats, FREE_LIMIT
from models.user import User
from routers.auth import require_user, get_current_user, ADMIN_EMAILS
from services.parser import parse_resume
from services.ai_service import (
    analyse_job_description,
    rewrite_resume,
    generate_cover_letter,
    generate_application_email,
    improve_resume_for_ats,
    get_available_models,
    suggest_job_search_params,
)
from services.ats_engine import compute_ats_score
from services.pdf_generator import generate_pdf
from services.latex_generator import generate_latex

router = APIRouter()


class AnalyzeResponse(BaseModel):
    tailored_resume: dict
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    total_keywords: int
    cover_letter: dict
    application_email: dict
    job_analysis: dict
    auto_improved: bool = False
    model_used: str = ""
    # Usage info (only populated for logged-in users)
    analyses_used: int = 0
    analyses_limit: int = FREE_LIMIT
    is_premium: bool = False

class SuggestJobSearchResponse(BaseModel):
    search_term: str
    location: str

class ExportRequest(BaseModel):
    resume: dict
    template: str = "modern"


class ImproveATSRequest(BaseModel):
    tailored_resume: dict
    job_description: str
    job_analysis: dict
    missing_keywords: list[str]
    model: str | None = None


class ImproveATSResponse(BaseModel):
    tailored_resume: dict
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    total_keywords: int


class RescoreATSRequest(BaseModel):
    tailored_resume: dict
    job_description: str


class RescoreATSResponse(BaseModel):
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    total_keywords: int


class ModelInfo(BaseModel):
    id: str
    display_name: str
    is_default: bool


def _safe_pdf_filename(resume: dict, template: str) -> str:
    candidate_name = resume.get("personal_info", {}).get("name", "resume")
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in candidate_name).strip()
    return f"{safe_name}_{template}.pdf"


@router.get("/models", response_model=list[ModelInfo])
async def list_models(current_user: Optional[User] = Depends(get_current_user)):
    """Return available AI models. Admin users also see admin-only models."""
    is_admin = bool(current_user and current_user.email.lower() in ADMIN_EMAILS)
    return get_available_models(is_admin=is_admin)


def _validate_model_id(model_id: Optional[str], is_admin: bool = False) -> Optional[str]:
    """Return model_id only if it is a known (and permitted) model; else None (use default)."""
    if not model_id:
        return None
    allowed = {m["id"] for m in get_available_models(is_admin=is_admin)}
    return model_id if model_id in allowed else None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    resume_file: UploadFile = File(..., description="Resume file — PDF or DOCX"),
    job_description: str = Form(..., description="Full text of the job description"),
    model: str = Form(default="", description="Model ID to use (e.g. qwen, glm, deepseek)"),
    current_user: User = Depends(require_user),   # login required
    db: Session = Depends(get_db),
):
    if not resume_file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # ── Usage limit check ───────────────────────────────────────────────────
    stats: Optional[UserStats] = db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    if not stats:
        stats = UserStats(user_id=current_user.id, analysis_count=0, is_premium=False)
        db.add(stats)
        db.commit()
        db.refresh(stats)

    if not stats.is_premium and stats.analysis_count >= FREE_LIMIT:
        raise HTTPException(
            status_code=402,
            detail=f"You've used all {FREE_LIMIT} free resume tailorings. Upgrade to Premium for unlimited access.",
        )

    file_bytes = await resume_file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    if len(job_description.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short. Please paste the full JD.")
    if len(job_description) > 20_000:
        raise HTTPException(status_code=400, detail="Job description is too long (max 20,000 characters).")

    try:
        resume_text = parse_resume(resume_file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse the resume file.")

    if not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the resume. Ensure it is not scanned/image-only.",
        )

    is_admin = current_user.email.lower() in ADMIN_EMAILS
    model_id = _validate_model_id(model.strip() or None, is_admin=is_admin)

    # ── Step 1: Sequential AI calls (each depends on the previous) ─────────────
    try:
        job_analysis = analyse_job_description(job_description, model_id=model_id)
        tailored_resume = rewrite_resume(resume_text, job_description, job_analysis, model_id=model_id)
    except Exception:
        raise HTTPException(status_code=502, detail="AI service is temporarily unavailable. Please try again.")

    tailored_text = json.dumps(tailored_resume)
    ats = compute_ats_score(tailored_text, job_description)

    # ── Step 2: Parallel AI calls — cover letter + email + optional ATS boost ────────
    auto_improved = False
    try:
        needs_improve = ats.score < 88 and bool(ats.missing_keywords)

        if needs_improve:
            with ThreadPoolExecutor(max_workers=3) as pool:
                cover_future = pool.submit(
                    generate_cover_letter,
                    tailored_resume, job_analysis, job_description, model_id,
                )
                email_future = pool.submit(
                    generate_application_email,
                    tailored_resume, job_analysis, job_description, model_id,
                )
                improve_future = pool.submit(
                    improve_resume_for_ats,
                    tailored_resume, job_description,
                    job_analysis, ats.missing_keywords, model_id,
                )
                cover_letter = cover_future.result()
                application_email = email_future.result()
                tailored_resume = improve_future.result()
            tailored_text = json.dumps(tailored_resume)
            ats = compute_ats_score(tailored_text, job_description)
            auto_improved = True
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                cover_future = pool.submit(
                    generate_cover_letter,
                    tailored_resume, job_analysis,
                    jd_text=job_description, model_id=model_id,
                )
                email_future = pool.submit(
                    generate_application_email,
                    tailored_resume, job_analysis,
                    jd_text=job_description, model_id=model_id,
                )
                cover_letter = cover_future.result()
                application_email = email_future.result()
    except Exception:
        raise HTTPException(status_code=502, detail="AI service is temporarily unavailable. Please try again.")

    # ── Post-analysis: increment count + auto-save history ──────────────────
    analyses_used = 0
    is_premium = False
    if stats:
        stats.analysis_count += 1
        db.commit()
        db.refresh(stats)
        analyses_used = stats.analysis_count
        is_premium = stats.is_premium

        # Auto-save to history
        try:
            job_title = job_analysis.get("job_title", "") if job_analysis else ""
            entry = ResumeHistory(
                user_id=current_user.id,
                job_title=job_title,
                ats_score=ats.score,
                tailored_resume=tailored_resume,
                cover_letter=cover_letter,
                application_email=application_email,
                job_analysis=job_analysis,
                job_description=job_description,
            )
            db.add(entry)
            db.commit()
        except Exception:
            pass  # Never block the response due to a save failure

    return AnalyzeResponse(
        tailored_resume=tailored_resume,
        ats_score=ats.score,
        matched_keywords=ats.matched_keywords,
        missing_keywords=ats.missing_keywords,
        total_keywords=ats.total_keywords,
        cover_letter=cover_letter,
        application_email=application_email,
        job_analysis=job_analysis,
        auto_improved=auto_improved,
        model_used=model_id or "",
        analyses_used=analyses_used,
        analyses_limit=FREE_LIMIT,
        is_premium=is_premium,
    )


@router.post("/suggest-job-search", response_model=SuggestJobSearchResponse)
async def suggest_job_search(
    resume_file: UploadFile = File(..., description="Resume file — PDF or DOCX"),
    model: str = Form(default="", description="Model ID to use (e.g. qwen, glm, deepseek)"),
    _user: User = Depends(require_user),
):
    if not resume_file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    file_bytes = await resume_file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    try:
        resume_text = parse_resume(resume_file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse the resume file.")

    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from the resume.")

    model_id = _validate_model_id(model.strip() or None)

    try:
        suggestion = suggest_job_search_params(resume_text, model_id=model_id)
        return SuggestJobSearchResponse(
            search_term=suggestion.get("search_term", ""),
            location=suggestion.get("location", "")
        )
    except Exception:
        raise HTTPException(status_code=502, detail="AI service is temporarily unavailable.")


@router.post("/export-pdf")
async def export_pdf(
    body: ExportRequest,
    _user: User = Depends(require_user),
):
    try:
        pdf_bytes = generate_pdf(body.resume, body.template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = _safe_pdf_filename(body.resume, body.template)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export-latex")
async def export_latex(
    body: ExportRequest,
    _user: User = Depends(require_user),
):
    """Return a professionally formatted LaTeX (.tex) resume file."""
    try:
        tex_content = generate_latex(body.resume)
    except Exception:
        raise HTTPException(status_code=500, detail="LaTeX generation failed. Please try again.")

    candidate_name = body.resume.get("personal_info", {}).get("name", "resume")
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in candidate_name).strip()
    filename = f"{safe_name}_resume.tex"

    return StreamingResponse(
        io.BytesIO(tex_content.encode("utf-8")),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/improve-ats", response_model=ImproveATSResponse)
async def improve_ats(
    body: ImproveATSRequest,
    _user: User = Depends(require_user),
):
    if len(body.job_description.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short.")

    model_id = _validate_model_id(body.model.strip() if body.model else None)

    try:
        tailored_resume = improve_resume_for_ats(
            body.tailored_resume,
            body.job_description,
            body.job_analysis,
            body.missing_keywords,
            model_id=model_id,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="AI service is temporarily unavailable.")

    tailored_text = json.dumps(tailored_resume)
    ats = compute_ats_score(tailored_text, body.job_description)

    return ImproveATSResponse(
        tailored_resume=tailored_resume,
        ats_score=ats.score,
        matched_keywords=ats.matched_keywords,
        missing_keywords=ats.missing_keywords,
        total_keywords=ats.total_keywords,
    )


@router.post("/rescore-ats", response_model=RescoreATSResponse)
async def rescore_ats(
    body: RescoreATSRequest,
    _user: User = Depends(require_user),
):
    if len(body.job_description.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short.")

    tailored_text = json.dumps(body.tailored_resume)
    ats = compute_ats_score(tailored_text, body.job_description)

    return RescoreATSResponse(
        ats_score=ats.score,
        matched_keywords=ats.matched_keywords,
        missing_keywords=ats.missing_keywords,
        total_keywords=ats.total_keywords,
    )
