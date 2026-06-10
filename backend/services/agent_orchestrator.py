"""
Agent Orchestrator — Self-Improving Resume Rewrite Loop
Uses only GLM/Qwen via existing ai_service._get_client().
Runs up to MAX_ITERATIONS rewrites, self-critiques after each,
and stops when ATS >= TARGET_ATS or iterations are exhausted.
Emits progress events via an async generator for SSE streaming.
"""
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from services.agent_memory import AgentMemory
from services.rag_service import build_rag_context_string
from services.ats_engine import compute_ats_score
from services.ai_service import (
    plan_analysis,
    analyse_job_description,
    rewrite_resume,
    improve_resume_for_ats,
    critique_resume,
    generate_cover_letter,
    generate_application_email,
    generate_interview_prep,
)

MAX_ITERATIONS = 2        # reduced from 3 — 2 attempts cover 95%+ of cases, saves ~20s worst-case
TARGET_ATS = 85        # lowered from 90 — stops loop sooner, saving 1+ rewrite cycles


def _make_event(step: str, status: str = "running", data: dict | None = None) -> str:
    """Format a Server-Sent Event string."""
    payload = {"step": step, "status": status, **(data or {})}
    return f"data: {json.dumps(payload)}\n\n"


# Max RAG context chars injected into rewrite prompts — keeps input tokens lean
_RAG_CONTEXT_MAX_CHARS = 800


def _enrich_rewrite_with_rag(
    resume_text: str,
    jd_text: str,
    job_analysis: dict,
    rag_context: str,
    memory: AgentMemory,
    model_id: str | None,
) -> dict:
    """
    Rewrite the resume with RAG context injected into the prompt.
    If memory has prior iterations, include critique summary so the
    agent knows what it already tried and what went wrong.
    RAG context is trimmed to _RAG_CONTEXT_MAX_CHARS to keep input tokens lean.
    """
    critique_block = memory.get_critique_summary()

    # Trim RAG context to avoid inflating input token count on every call
    rag_trimmed = rag_context[:_RAG_CONTEXT_MAX_CHARS] if rag_context else ""

    enriched_resume_text = resume_text
    if rag_trimmed or critique_block:
        prefix_parts = []
        if rag_trimmed:
            prefix_parts.append(f"[RETRIEVED INDUSTRY CONTEXT — use as writing style reference]\n{rag_trimmed}")
        if critique_block:
            prefix_parts.append(f"[AGENT SELF-CRITIQUE FROM PREVIOUS ATTEMPTS]\n{critique_block}")
        enriched_resume_text = "\n\n".join(prefix_parts) + "\n\n[CANDIDATE RESUME]\n" + resume_text

    return rewrite_resume(enriched_resume_text, jd_text, job_analysis, model_id=model_id)


def run_agent(
    resume_text: str,
    jd_text: str,
    model_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Synchronous generator that yields SSE event strings.
    The FastAPI router wraps this in an async generator via
    asyncio.to_thread / ThreadPoolExecutor.

    Yields SSE events:
      {"step": "planning",       "status": "running|done|error", ...}
      {"step": "rag_retrieval",  "status": "running|done", ...}
      {"step": "jd_analysis",    "status": "running|done", ...}
      {"step": "rewrite",        "status": "running|done", "iteration": N, "ats": X}
      {"step": "critique",       "status": "running|done", "iteration": N}
      {"step": "cover_letter",   "status": "running|done"}
      {"step": "email",          "status": "running|done"}
      {"step": "interview_prep", "status": "running|done"}
      {"step": "complete",       "status": "done", "result": {...}}
      {"step": "error",          "status": "error", "message": "..."}
    """
    memory = AgentMemory(session_id=str(uuid.uuid4()))
    t_start = time.time()

    # ── Steps 1 + 3 in parallel: Planning & JD Analysis ─────────────────────
    # plan_analysis and analyse_job_description are independent — run concurrently
    # to save ~10–20s of sequential LLM wait time.
    yield _make_event("planning", "running")
    yield _make_event("jd_analysis", "running")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            plan_future = pool.submit(plan_analysis, resume_text, jd_text, model_id)
            jd_future   = pool.submit(analyse_job_description, jd_text, model_id)
            plan         = plan_future.result()
            job_analysis = jd_future.result()

        memory.job_title       = plan.get("job_title", "") or job_analysis.get("job_title", "")
        memory.seniority       = plan.get("seniority", "") or job_analysis.get("seniority", "")
        memory.required_skills = plan.get("primary_stack", []) or job_analysis.get("required_skills", [])

        yield _make_event("planning", "done", {
            "job_title": memory.job_title,
            "seniority": memory.seniority,
            "strategy": plan.get("rewrite_strategy", ""),
        })
        yield _make_event("jd_analysis", "done", {
            "job_title": job_analysis.get("job_title", ""),
            "required_skills_count": len(job_analysis.get("required_skills", [])),
        })
    except Exception as exc:
        # If JD analysis fails the pipeline cannot continue
        yield _make_event("planning", "error", {"message": str(exc)[:200]})
        yield _make_event("error", "error", {"message": f"Startup analysis failed: {str(exc)[:200]}"})
        return

    # ── Step 2: RAG Retrieval (fast — pure Python TF-IDF, no LLM) ───────────
    yield _make_event("rag_retrieval", "running")
    try:
        rag_context = build_rag_context_string(
            job_title=memory.job_title,
            required_skills=memory.required_skills,
            seniority=memory.seniority,
        )
        memory.rag_context_used = bool(rag_context)
        memory.rag_context_snippet = rag_context[:150] if rag_context else ""
        yield _make_event("rag_retrieval", "done", {
            "chunks_retrieved": bool(rag_context),
            "context_preview": memory.rag_context_snippet,
        })
    except Exception:
        rag_context = ""
        yield _make_event("rag_retrieval", "done", {"chunks_retrieved": False})

    # ── Steps 4–6: Self-improving rewrite loop ──────────────────────────────
    tailored_resume: dict = {}
    final_ats = None

    for i in range(MAX_ITERATIONS):
        yield _make_event("rewrite", "running", {"iteration": i + 1, "max_iterations": MAX_ITERATIONS})
        try:
            if i == 0:
                # First attempt: full rewrite enriched with RAG context
                tailored_resume = _enrich_rewrite_with_rag(
                    resume_text, jd_text, job_analysis, rag_context, memory, model_id
                )
            else:
                # Subsequent attempts: targeted ATS improvement with critique guidance
                critique_context = memory.get_critique_summary()
                enriched_jd = jd_text
                if critique_context:
                    enriched_jd = f"[PREVIOUS ATTEMPT CRITIQUE]\n{critique_context}\n\n[JOB DESCRIPTION]\n{jd_text}"

                tailored_resume = improve_resume_for_ats(
                    tailored_resume,
                    enriched_jd,
                    job_analysis,
                    memory.iterations[-1].missing_keywords if memory.iterations else [],
                    model_id=model_id,
                )

            ats = compute_ats_score(json.dumps(tailored_resume), jd_text)
            final_ats = ats

            yield _make_event("rewrite", "done", {
                "iteration": i + 1,
                "ats_score": ats.score,
                "matched_count": len(ats.matched_keywords),
                "missing_count": len(ats.missing_keywords),
                "target_reached": ats.score >= TARGET_ATS,
            })

            if ats.score >= TARGET_ATS:
                # Target reached — no need for critique or more iterations
                memory.add_iteration(i, ats.score, ats.matched_keywords, ats.missing_keywords, "Target ATS reached.")
                break

            # ── Critique ──────────────────────────────────────────────────
            if i < MAX_ITERATIONS - 1 and ats.missing_keywords:
                yield _make_event("critique", "running", {"iteration": i + 1})
                try:
                    critique_result = critique_resume(
                        tailored_resume,
                        ats.missing_keywords,
                        jd_text,
                        model_id=model_id,
                    )
                    diagnosis = critique_result.get("overall_diagnosis", "")
                    # Build a concise critique string for memory
                    critique_str = diagnosis
                    priority = critique_result.get("priority_order", [])
                    if priority:
                        critique_str += f" Priority fixes: {', '.join(priority[:5])}"

                    memory.add_iteration(
                        i, ats.score, ats.matched_keywords, ats.missing_keywords, critique_str
                    )
                    yield _make_event("critique", "done", {
                        "iteration": i + 1,
                        "diagnosis": diagnosis[:150],
                        "priority_fixes": critique_result.get("priority_order", [])[:5],
                    })
                except Exception:
                    # Critique failed — still record iteration, continue loop
                    memory.add_iteration(
                        i, ats.score, ats.matched_keywords, ats.missing_keywords, "Critique unavailable."
                    )
                    yield _make_event("critique", "done", {"iteration": i + 1})
            else:
                memory.add_iteration(
                    i, ats.score, ats.matched_keywords, ats.missing_keywords, "Final iteration."
                )

        except Exception as exc:
            yield _make_event("rewrite", "error", {"iteration": i + 1, "message": str(exc)[:200]})
            if not tailored_resume:
                yield _make_event("error", "error", {"message": "Resume rewrite failed. Cannot continue."})
                return
            break  # Use whatever resume we have

    if not tailored_resume:
        yield _make_event("error", "error", {"message": "No resume was produced."})
        return

    # Ensure final ATS is computed
    if final_ats is None:
        final_ats = compute_ats_score(json.dumps(tailored_resume), jd_text)

    # ── Step 7: Parallel generation — cover letter, email, interview prep ───
    cover_letter: dict = {}
    application_email: dict = {}
    interview_prep: dict = {}

    yield _make_event("cover_letter", "running")
    yield _make_event("email", "running")
    yield _make_event("interview_prep", "running")

    with ThreadPoolExecutor(max_workers=3) as pool:
        cl_future = pool.submit(
            generate_cover_letter,
            tailored_resume, job_analysis, jd_text, model_id,
        )
        em_future = pool.submit(
            generate_application_email,
            tailored_resume, job_analysis, jd_text, model_id,
        )
        ip_future = pool.submit(
            generate_interview_prep,
            tailored_resume, job_analysis, model_id,
        )

        # Collect results individually so one failure doesn't hide the others
        try:
            cover_letter = cl_future.result()
            yield _make_event("cover_letter", "done")
        except Exception as exc:
            yield _make_event("cover_letter", "error", {"message": str(exc)[:100]})

        try:
            application_email = em_future.result()
            yield _make_event("email", "done")
        except Exception as exc:
            yield _make_event("email", "error", {"message": str(exc)[:100]})

        try:
            interview_prep = ip_future.result()
            yield _make_event("interview_prep", "done")
        except Exception as exc:
            yield _make_event("interview_prep", "error", {"message": str(exc)[:100]})

    # ── Final result ─────────────────────────────────────────────────────────
    memory.total_time_ms = (time.time() - t_start) * 1000

    yield _make_event("complete", "done", {
        "result": {
            "tailored_resume": tailored_resume,
            "ats_score": final_ats.score,
            "matched_keywords": final_ats.matched_keywords,
            "missing_keywords": final_ats.missing_keywords,
            "total_keywords": final_ats.total_keywords,
            "cover_letter": cover_letter,
            "application_email": application_email,
            "interview_prep": interview_prep,
            "job_analysis": job_analysis,
            "agent_trace": memory.to_dict(),
            "auto_improved": len(memory.iterations) > 1,
        }
    })
