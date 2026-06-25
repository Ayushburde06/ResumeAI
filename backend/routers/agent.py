"""
Agent Router — SSE streaming endpoint for Agentic AI + RAG analysis.
POST /api/agent-analyze  →  streams Server-Sent Events.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.history import ResumeHistory
from models.stats import UserStats, FREE_LIMIT
from models.user import User
from routers.auth import require_user, ADMIN_EMAILS
from services.parser import parse_resume
from services.agent_orchestrator import run_agent
from services.rag_service import get_store_stats
from services.ai_service import get_available_models
from routers.analyze import _validate_model_id

router = APIRouter()


async def _sse_generator(
    request: Request,
    resume_text: str,
    jd_text: str,
    model_id: str | None,
    db: Session,
    user: User,
    stats: UserStats,
):
    """
    Async generator that runs the agent in a thread pool and yields
    SSE-formatted bytes. Saves to history on completion.
    """
    import json

    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    final_result: dict | None = None

    def _producer():
        try:
            for event_str in run_agent(resume_text, jd_text, model_id):
                loop.call_soon_threadsafe(queue.put_nowait, event_str)
        except Exception as e:
            err_evt = f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': str(e)})}\n\n"
            loop.call_soon_threadsafe(queue.put_nowait, err_evt)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    # Run in thread pool to avoid blocking
    executor_future = loop.run_in_executor(None, _producer)

    try:
        while True:
            if await request.is_disconnected():
                break

            event_str = await queue.get()
            if event_str is None:
                break
            yield event_str.encode("utf-8")

            # Extract final result for history saving
            if '"step": "complete"' in event_str:
                try:
                    data = json.loads(event_str.replace("data: ", "").strip())
                    final_result = data.get("result")
                except Exception:
                    pass
    finally:
        await executor_future

    # ── Post-analysis: save history + update usage count ─────────────────
    if final_result and stats:
        try:
            stats.analysis_count += 1
            db.commit()
        except Exception:
            pass

        try:
            ja = final_result.get("job_analysis", {})
            entry = ResumeHistory(
                user_id=user.id,
                job_title=ja.get("job_title", ""),
                ats_score=final_result.get("ats_score", 0),
                tailored_resume=final_result.get("tailored_resume", {}),
                cover_letter=final_result.get("cover_letter", {}),
                application_email=final_result.get("application_email", {}),
                job_analysis=ja,
                quality_report=final_result.get("quality_report", {}),
                job_description=jd_text,
            )
            db.add(entry)
            db.commit()
        except Exception:
            pass  # Never block the stream due to save failure


@router.post("/agent-analyze")
async def agent_analyze(
    request: Request,
    resume_file: UploadFile = File(..., description="Resume file — PDF or DOCX"),
    job_description: str = Form(..., description="Full text of the job description"),
    model: str = Form(default="", description="Model ID (e.g. glm, qwen)"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Agentic resume analysis with RAG + self-improving rewrite loop.
    Streams Server-Sent Events (SSE) showing each agent step in real-time.
    """
    if not resume_file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # ── Usage limit check ────────────────────────────────────────────────────
    stats: Optional[UserStats] = (
        db.query(UserStats).filter(UserStats.user_id == current_user.id).first()
    )
    if not stats:
        stats = UserStats(user_id=current_user.id, analysis_count=0, is_premium=False)
        db.add(stats)
        db.commit()
        db.refresh(stats)

    if not stats.is_premium and stats.analysis_count >= FREE_LIMIT:
        raise HTTPException(
            status_code=402,
            detail=f"You've used all {FREE_LIMIT} free tailorings. Upgrade to Premium for unlimited access.",
        )

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

    # ── Stream SSE response ──────────────────────────────────────────────────
    return StreamingResponse(
        _sse_generator(request, resume_text, job_description, model_id, db, current_user, stats),
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
