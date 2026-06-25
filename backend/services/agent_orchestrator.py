"""
Agent Orchestrator - self-improving resume rewrite loop.

This module keeps the multi-agent flow lightweight but explicit:
parse -> plan -> analyze JD -> retrieve RAG context -> gap analysis -> rewrite
-> critique -> ATS validation -> reflection -> final assets.
"""
import json
import copy
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from services.agent_memory import AgentMemory
from services.rag_service import build_rag_context_string
from services.ats_engine import compute_ats_score
from services.quality_checks import assess_resume_quality
from services.ai_service import (
    analyse_job_description,
    rewrite_resume,
    improve_resume_for_ats,
    critique_resume,
    generate_cover_letter,
    generate_application_email,
    generate_interview_prep,
)

MAX_ITERATIONS = 3
TARGET_ATS = 90


def _make_event(step: str, status: str = "running", data: dict | None = None) -> str:
    payload = {"step": step, "status": status, **(data or {})}
    return f"data: {json.dumps(payload)}\n\n"


_RAG_CONTEXT_MAX_CHARS = 800


def _enrich_rewrite_with_rag(
    resume_text: str,
    jd_text: str,
    job_analysis: dict,
    rag_context: str,
    memory: AgentMemory,
    model_id: str | None,
    missing_keywords: list[str] | None = None,
) -> dict:
    critique_block = memory.get_critique_summary()
    rag_trimmed = rag_context[:_RAG_CONTEXT_MAX_CHARS] if rag_context else ""

    enriched_resume_text = resume_text
    if rag_trimmed or critique_block:
        prefix_parts = []
        if rag_trimmed:
            prefix_parts.append(
                "[RETRIEVED INDUSTRY CONTEXT - use as writing style reference]\n"
                f"{rag_trimmed}"
            )
        if critique_block:
            prefix_parts.append(f"[AGENT SELF-CRITIQUE FROM PREVIOUS ATTEMPTS]\n{critique_block}")
        enriched_resume_text = "\n\n".join(prefix_parts) + "\n\n[CANDIDATE RESUME]\n" + resume_text

    return rewrite_resume(
        enriched_resume_text,
        jd_text,
        job_analysis,
        model_id=model_id,
        missing_keywords=missing_keywords,
    )


def run_agent(
    resume_text: str,
    jd_text: str,
    model_id: str | None = None,
) -> AsyncGenerator[str, None]:
    memory = AgentMemory(session_id=str(uuid.uuid4()))
    t_start = time.time()

    yield _make_event("parse_resume", "running")
    yield _make_event("parse_resume", "done", {
        "message": "Resume text extracted and ready for structured analysis.",
    })

    yield _make_event("planning", "running")
    yield _make_event("jd_analysis", "running")
    try:
        job_analysis = analyse_job_description(jd_text, model_id)

        memory.job_title = job_analysis.get("job_title", "")
        memory.seniority = job_analysis.get("seniority", "")
        memory.required_skills = job_analysis.get("required_skills", [])

        original_ats = compute_ats_score(resume_text, jd_text)
        initial_missing = original_ats.missing_keywords

        yield _make_event("planning", "done", {
            "job_title": memory.job_title,
            "seniority": memory.seniority,
            "strategy": job_analysis.get(
                "rewrite_strategy",
                "Targeting job description keywords and structure.",
            ),
        })
        yield _make_event("jd_analysis", "done", {
            "job_title": job_analysis.get("job_title", ""),
            "required_skills_count": len(job_analysis.get("required_skills", [])),
        })
        yield _make_event("gap_analysis", "done", {
            "job_title": memory.job_title,
            "missing_keywords": initial_missing[:12],
            "missing_count": len(initial_missing),
            "priority": "Address missing keywords in summary, experience, skills, and projects.",
        })
    except Exception as exc:
        yield _make_event("planning", "error", {"message": str(exc)[:200]})
        yield _make_event("error", "error", {"message": f"Startup analysis failed: {str(exc)[:200]}"})
        return

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

    tailored_resume: dict = {}
    best_resume: dict = {}
    final_ats = None
    initial_ats_meta = {
        "score": original_ats.score,
        "matched": len(original_ats.matched_keywords),
        "total": original_ats.total_keywords,
        "missing_count": len(original_ats.missing_keywords),
    }

    for i in range(MAX_ITERATIONS):
        yield _make_event("rewrite", "running", {"iteration": i + 1, "max_iterations": MAX_ITERATIONS})
        try:
            if i == 0:
                tailored_resume = _enrich_rewrite_with_rag(
                    resume_text, jd_text, job_analysis, rag_context, memory, model_id, initial_missing
                )
            else:
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
            proposed_ats = compute_ats_score(json.dumps(tailored_resume), jd_text)
            if final_ats is None or proposed_ats.score >= final_ats.score:
                ats = proposed_ats
                final_ats = ats
                best_resume = copy.deepcopy(tailored_resume)
            else:
                ats = final_ats
                tailored_resume = copy.deepcopy(best_resume)

            yield _make_event("rewrite", "done", {
                "iteration": i + 1,
                "ats_score": ats.score,
                "matched_count": len(ats.matched_keywords),
                "missing_count": len(ats.missing_keywords),
                "target_reached": ats.score >= TARGET_ATS,
            })

            if ats.score >= TARGET_ATS:
                memory.add_iteration(i, ats.score, ats.matched_keywords, ats.missing_keywords, "Target ATS reached.")
                break

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
                    memory.add_iteration(
                        i, ats.score, ats.matched_keywords, ats.missing_keywords, "Critique unavailable."
                    )
                    yield _make_event("critique", "done", {"iteration": i + 1})
            else:
                memory.add_iteration(i, ats.score, ats.matched_keywords, ats.missing_keywords, "Final iteration.")

        except Exception as exc:
            yield _make_event("rewrite", "error", {"iteration": i + 1, "message": str(exc)[:200]})
            if not tailored_resume:
                yield _make_event("error", "error", {"message": "Resume rewrite failed. Cannot continue."})
                return
            break

    if not tailored_resume:
        yield _make_event("error", "error", {"message": "No resume was produced."})
        return

    if final_ats is None:
        final_ats = compute_ats_score(json.dumps(tailored_resume), jd_text)

    final_ats_meta = {
        "score": final_ats.score,
        "matched": len(final_ats.matched_keywords),
        "total": final_ats.total_keywords,
        "missing_count": len(final_ats.missing_keywords),
    }

    quality = assess_resume_quality(tailored_resume, jd_text, initial_ats_meta, final_ats_meta)
    yield _make_event("humanization_check", "done", {
        "humanization_score": quality["humanization_score"],
        "notes": quality["notes"][:3],
    })
    yield _make_event("grammar_check", "done", {
        "grammar_score": quality["grammar_score"],
        "report": quality["grammar_report"],
    })
    yield _make_event("ats_validation", "done", {
        "validation_status": "pass" if final_ats.score >= 80 else "needs_review",
        "validation_summary": quality["ats_compatibility_report"],
        "formatting_report": quality["formatting_report"],
    })

    reflection_summary = (
        "Output is grounded, recruiter-readable, and ready for export."
        if final_ats.score >= 80 and quality["humanization_score"] >= 80 and quality["grammar_score"] >= 80
        else "The draft is usable, but another pass could improve wording or keyword balance."
    )
    yield _make_event("reflection", "done", {
        "reflection_summary": reflection_summary,
        "needs_another_pass": bool((final_ats.missing_keywords or quality["humanization_score"] < 80 or quality["grammar_score"] < 80) and len(memory.iterations) < MAX_ITERATIONS),
    })

    final_review = {
        "recruiter_readability_score": quality["recruiter_readability_score"],
        "confidence_report": quality["confidence_report"],
        "changes_made": quality["changes_made"],
        "before_after_comparison": quality["before_after_comparison"],
    }
    yield _make_event("final_review", "done", final_review)

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

    memory.total_time_ms = (time.time() - t_start) * 1000

    yield _make_event("complete", "done", {
        "result": {
            "tailored_resume": tailored_resume,
            "ats_score": final_ats.score,
            "matched_keywords": final_ats.matched_keywords,
            "missing_keywords": final_ats.missing_keywords,
            "total_keywords": final_ats.total_keywords,
            "ats_validation": {
                "validation_status": "pass" if final_ats.score >= 80 else "needs_review",
                "validation_summary": quality["ats_compatibility_report"],
                "formatting_report": quality["formatting_report"],
            },
            "quality_report": {
                "ats_compatibility_report": quality["ats_compatibility_report"],
                "formatting_report": quality["formatting_report"],
                "grammar_report": quality["grammar_report"],
                "humanization_score": quality["humanization_score"],
                "recruiter_readability_score": quality["recruiter_readability_score"],
                "changes_made": quality["changes_made"],
                "before_after_comparison": quality["before_after_comparison"],
                "confidence_report": quality["confidence_report"],
            },
            "reflection": reflection_summary,
            "final_review": final_review,
            "cover_letter": cover_letter,
            "application_email": application_email,
            "interview_prep": interview_prep,
            "job_analysis": job_analysis,
            "agent_trace": memory.to_dict(),
            "auto_improved": len(memory.iterations) > 1,
        }
    })
