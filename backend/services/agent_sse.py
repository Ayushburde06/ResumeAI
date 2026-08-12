"""Shared SSE streaming for agent pipeline (PDF upload or profile-based)."""
from __future__ import annotations

import asyncio
import json

from database import SessionLocal
from fastapi import Request
from models.history import ResumeHistory
from models.stats import UserStats
from models.user import User
from quota import log_user_operation
from schemas.profile import CareerProfileSchema

from services.agent_orchestrator import run_agent


async def stream_agent_sse(
    request: Request,
    resume_text: str,
    jd_text: str,
    model_id: str | None,
    user: User,
    career_profile: CareerProfileSchema | None = None,
    operation: str = "agent",
):
    """
    Async generator: runs agent in thread pool, yields SSE bytes,
    saves history on completion.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    final_result: dict | None = None

    def _producer():
        try:
            for event_str in run_agent(
                resume_text,
                jd_text,
                model_id,
                career_profile=career_profile,
            ):
                loop.call_soon_threadsafe(queue.put_nowait, event_str)
        except Exception:
            import traceback
            traceback.print_exc()
            err_evt = f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': 'Agent analysis failed. Please try again.'})}\n\n"
            loop.call_soon_threadsafe(queue.put_nowait, err_evt)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    executor_future = loop.run_in_executor(None, _producer)

    final_result: dict | None = None
    stream_started = False
    try:
        while True:
            if await request.is_disconnected():
                break
            event_str = await queue.get()
            if event_str is None:
                break
            stream_started = True

            # ── Intercept "complete" to save history before the client sees it ──
            is_complete = '"step": "complete"' in event_str and '"result"' in event_str
            if is_complete:
                try:
                    data = json.loads(event_str.replace("data: ", "").strip())
                    final_result = data.get("result")
                except Exception:
                    pass

                # Save history + yield history_saved BEFORE the complete event
                if final_result and user:
                    db_sess = SessionLocal()
                    try:
                        history_id = None
                        try:
                            ja = final_result.get("job_analysis", {})
                            ats_score = final_result.get("ats_score", 0)
                            entry = ResumeHistory(
                                user_id=user.id,
                                job_title=ja.get("job_title", ""),
                                ats_score=ats_score,
                                tailored_resume=final_result.get("tailored_resume", {}),
                                cover_letter=final_result.get("cover_letter", {}),
                                application_email=final_result.get("application_email", {}),
                                job_analysis=ja,
                                quality_report=final_result.get("quality_report", {}),
                                job_description=jd_text,
                                matched_keywords=final_result.get("matched_keywords", []),
                                missing_keywords=final_result.get("missing_keywords", []),
                                total_keywords=final_result.get("total_keywords", 0),
                            )
                            db_sess.add(entry)
                            db_sess.commit()
                            db_sess.refresh(entry)
                            history_id = entry.id
                            history_event = f"data: {json.dumps({'step': 'history_saved', 'history_id': history_id})}\n\n"
                            yield history_event.encode("utf-8")
                        except Exception:
                            pass

                        try:
                            from services.learning_store import save_winning_example
                            if ats_score >= 88:
                                save_winning_example(
                                    db=db_sess,
                                    job_title=ja.get("job_title", ""),
                                    seniority=ja.get("seniority", ""),
                                    required_skills=ja.get("required_skills", []),
                                    resume=final_result.get("tailored_resume", {}),
                                    ats_score=ats_score,
                                    model_used=model_id or "",
                                    history_id=history_id,
                                )
                        except Exception:
                            pass
                    finally:
                        db_sess.close()

            yield event_str.encode("utf-8")

    finally:
        await executor_future

    # Charge quota once the agent actually started consuming AI, even if the
    # client disconnected before completion (executor keeps running regardless).
    if (final_result or stream_started) and user:
        db_sess = SessionLocal()
        try:
            user_stats = db_sess.query(UserStats).filter(UserStats.user_id == user.id).first()
            if user_stats:
                log_user_operation(db_sess, user, operation=operation)

        finally:
            db_sess.close()
