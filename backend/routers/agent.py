"""
Agent Router — SSE streaming endpoint for Agentic AI + RAG analysis.
POST /api/agent-analyze  →  streams Server-Sent Events.
"""

from database import get_db
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from limiter import limiter
from models.user import User
from quota import check_user_quota
from services.agent_sse import stream_agent_sse
from services.parser import parse_resume
from services.rag_service import get_store_stats
from sqlalchemy.orm import Session

from routers.analyze import _validate_model_id
from routers.auth import ADMIN_EMAILS, require_user

router = APIRouter()

@router.post("/agent-analyze")
@limiter.limit("1/minute")   # burst limit — agent is 5-10x more expensive
async def agent_analyze(
    request: Request,
    resume_file: UploadFile = File(..., description="Resume file — PDF or DOCX"),
    job_description: str = Form(..., description="Full text of the job description"),
    model: str = Form(default="", description="Model ID (e.g. nvidia, gemini, glm, kimi, qwen, deepseek)"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Agentic resume analysis with RAG + self-improving rewrite loop.
    Streams Server-Sent Events (SSE) showing each agent step in real-time.
    """
    if not resume_file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # ── Daily quota check (rolling 24h) ────────────────────────────────────────
    stats, _ = check_user_quota(db, current_user, operation="agent")

    # ── File validation ──────────────────────────────────────────────────────
    file_bytes = await resume_file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    if len(job_description.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short.")
    if len(job_description) > 20_000:
        raise HTTPException(status_code=400, detail="Job description is too long (max 20,000 chars).")

    # ── Parse resume ─────────────────────────────────────────────────────────
    try:
        resume_text = parse_resume(resume_file.filename, file_bytes, resume_file.content_type)
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

    # ── Stream SSE response ──────────────────────────────────────────────────
    return StreamingResponse(
        stream_agent_sse(request, resume_text, job_description, model_id, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering for SSE
            "Connection": "keep-alive",
        },
    )


@router.get("/agent/rag-stats")
async def rag_stats(_user: User = Depends(require_user)):
    """Return statistics about the loaded RAG knowledge store."""
    return get_store_stats()
