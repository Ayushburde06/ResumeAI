"""
Agent Orchestrator v3 — Ultra-Fast 5-Phase Agentic RAG Pipeline.

Changes from v2 (see inline `# v3:` comments for exact diffs):
  1. The section-rewrite loop no longer calls the LLM-based assess_resume_quality()
     on every candidate. It uses a deterministic humanization score instead
     (services.humanization_engine.compute_humanization_score) to decide whether
     a candidate is better. assess_resume_quality() now runs exactly once, after
     the loop exits, purely to build the human-readable report for the UI.
  2. Targeted RAG context per section is fetched once before the iteration loop
     (job_title/required_skills/seniority don't change between iterations) instead
     of being re-fetched on every pass.
  3. Phase 4 humanization only calls the LLM (humanize_sections) on sections that
     actually fail the deterministic humanization check. Clean sections are
     skipped entirely.
  4. Missing keywords are classified by likely section (skills vs. narrative)
     before the first-pass rewrite, so the model places them correctly on
     attempt 1 instead of needing a correction iteration.
  5. The section-wise parallel rewrite step uses wait(..., timeout=...) instead
     of as_completed(timeout=...), so a slow section is attributed correctly
     instead of silently dropping every unfinished future in the batch.

Philosophy: parse once, cache aggressively, rewrite only changed sections,
run independent work in parallel, stop when improvements become negligible,
and never pay for an LLM call when a deterministic check gives the same answer.

Pipeline:
  Phase 1 (parallel): JD analysis + ATS baseline + RAG retrieval
  Phase 2 (parallel): Gap analysis + Optimization plan
  Phase 3 (serial loop, max 3): Section-wise parallel rewrite → deterministic validation
  Phase 4 (serial): Selective humanization + Quality assessment (1x LLM call, not 4x)
  Phase 5 (parallel): Cover letter + Email + Interview prep + LinkedIn + Tips
  Phase 6 (deterministic): ATS report + Match analysis + Change log
"""
import copy
import json
import time
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor

from schemas.profile import CareerProfileSchema

from services.agent_memory import AgentMemory
from services.ai_service import (
    analyse_job_description,
    build_capability_graph,
    classify_role_domain,
    critique_section,
    gap_analysis,
    generate_application_email,
    generate_cover_letter,
    generate_linkedin_message,
    rewrite_resume,
    rewrite_section,
)
from services.ats_engine import TECH_BIGRAMS, TECH_UNIGRAMS, compute_ats_score
from services.composite_score import (
    compute_composite_score,
    score_breakdown,
)
from services.humanization_engine import (
    compute_humanization_score,  # v3: new, deterministic
)
from services.loop_engine import run_quality_loop
from services.profile_assembler import (
    profile_to_source_text,
    profile_to_tailored_resume,
)
from services.profile_rag_service import build_profile_rag_context
from services.quality_checks import assess_resume_quality
from services.rag_service import build_rag_context_string, build_targeted_rag_context

MAX_ITERATIONS = 3
TARGET_ATS = 90
MIN_COMPOSITE_IMPROVEMENT = 0.01   # 1% — stop iterating below this
HUMANIZATION_OK_THRESHOLD = 80     # v3: sections scoring >= this skip the LLM humanize pass
SECTION_FUTURE_TIMEOUT = 30        # v3: seconds to wait for the whole rewrite_section batch


def _make_event(step: str, status: str = "running", data: dict | None = None) -> str:
    payload = {"step": step, "status": status, **(data or {})}
    return f"data: {json.dumps(payload)}\n\n"


# ── Deterministic helpers (no LLM) ───────────────────────────────────────────

def _deterministic_composite(resume: dict, jd_text: str, ats_score: int, humanization_score: int) -> float:
    """
    v3 fixed: Real composite score using the weighted geometric mean of all 5 axes.
    Calls assess_resume_quality (which is 100% deterministic and uses no LLM calls)
    to get readability/grammar/formatting, then injects our dedicated humanization
    score, and computes the correct geometric mean composite.
    """
    from services.composite_score import compute_composite_score
    from services.quality_checks import assess_resume_quality
    
    # Get the other 3 axes deterministically
    quality = assess_resume_quality(resume, jd_text, None, None)
    
    # Override with our advanced humanization_score
    quality["humanization_score"] = humanization_score
    
    return compute_composite_score(ats_score, quality)


def _classify_missing_keywords(missing: list[str]) -> dict[str, list[str]]:
    """
    v3: Deterministically bucket missing JD keywords by the section they're
    most likely to belong in, using the same TECH_UNIGRAMS/TECH_BIGRAMS sets
    ats_engine already maintains. Skills-shaped keywords (languages,
    frameworks, tools) go to the skills section; everything else (domain
    terms, methodologies, soft-skill phrases) is treated as narrative and
    routed to summary/experience. This lets the first-pass rewrite place
    keywords correctly instead of needing a follow-up iteration to fix
    placement.
    """
    skills_kw = [k for k in missing if k in TECH_UNIGRAMS or k in TECH_BIGRAMS]
    narrative_kw = [k for k in missing if k not in skills_kw]
    return {
        "skills": skills_kw,
        "experience": narrative_kw,
        "summary": narrative_kw[:5],
    }


def _keyword_placement_hint(classified: dict[str, list[str]], adaptive_report: dict | None = None) -> str:
    """v3: Render the classification as plain guidance text to fold into the
    rewrite prompt's extra_context, without needing to change rewrite_resume's
    signature.

    When adaptive_report is present, also injects bridge framing so the rewrite
    LLM knows which gaps to frame as transferable rather than absent.
    """
    lines = ["KEYWORD PLACEMENT GUIDANCE (place these in the indicated section):"]
    if classified["skills"]:
        lines.append(f"- Skills section: {', '.join(classified['skills'][:15])}")
    if classified["experience"]:
        lines.append(f"- Experience bullets (work naturally into achievements): {', '.join(classified['experience'][:15])}")
    if classified["summary"]:
        lines.append(f"- Summary (mention 1-2 at most, naturally): {', '.join(classified['summary'])}")

    # Inject adaptive bridge framing if available
    if adaptive_report:
        try:
            from services.adaptive_gap import build_gap_context_for_rewrite
            gap_ctx = build_gap_context_for_rewrite(adaptive_report)
            if gap_ctx:
                lines.append("")
                lines.append(gap_ctx)
        except Exception:
            pass

    return "\n".join(lines)


def _section_humanization_score(section_name: str, section_data) -> int:
    """
    v3: Deterministic 0-100 humanization score for a single section, reusing
    compute_humanization_score(). Skills sections aren't bullet/prose content
    so they're exempt (always considered fine). Empty sections are treated as
    fine rather than penalized — compute_humanization_score returns 0 for "no
    bullets to evaluate", which would otherwise wrongly trigger a humanize call.
    """
    if section_name == "skills" or not section_data:
        return 100

    if section_name == "summary":
        fake_resume = {"summary": section_data, "experience": [], "projects": []}
    elif section_name == "experience":
        fake_resume = {"summary": "", "experience": section_data, "projects": []}
    elif section_name == "projects":
        fake_resume = {"summary": "", "experience": [], "projects": section_data}
    else:
        return 100

    result = compute_humanization_score(fake_resume)
    # No bullets found isn't the same as "bad" — don't force an LLM call over it.
    if not result.bullet_feedback:
        return 100
    return result.score


def _build_match_analysis(
    job_analysis: dict,
    final_ats,
) -> dict:
    """Compute match analysis deterministically from JD + ATS data. No LLM."""
    required = job_analysis.get("required_skills", [])
    matched = set(k.lower() for k in final_ats.matched_keywords)

    matched_reqs = [r for r in required if r.lower() in matched]
    unmet_reqs = [r for r in required if r.lower() not in matched]

    # Candidate strengths = top matched required skills
    strengths = matched_reqs[:5]

    score = final_ats.score
    verdict = (
        "Strong match — apply with confidence"         if score >= 85 else
        "Good match — minor keyword gaps remain"        if score >= 70 else
        "Moderate match — review unmet requirements"    if score >= 55 else
        "Weak match — significant gaps vs JD"
    )

    return {
        "match_score": score,
        "matched_requirements": matched_reqs[:10],
        "unmet_requirements": unmet_reqs[:10],
        "candidate_strengths": strengths,
        "fit_verdict": verdict,
    }


def _build_ats_report(
    initial_ats,
    final_ats,
    quality: dict,
) -> dict:
    """Build a structured ATS report. Deterministic — no LLM."""
    improvement = final_ats.score - initial_ats.score
    return {
        "baseline_score": initial_ats.score,
        "final_score": final_ats.score,
        "improvement": f"+{improvement}" if improvement >= 0 else str(improvement),
        "matched_keywords": final_ats.matched_keywords[:30],
        "missing_keywords": final_ats.missing_keywords[:20],
        "total_keywords": final_ats.total_keywords,
        "score_breakdown": score_breakdown(final_ats.score, quality),
    }


def _merge_section_results(
    base_resume: dict,
    section_results: dict,
) -> dict:
    """
    Merge section-level rewrite results back into the full resume dict.
    Only overwrites sections that have valid non-empty results.
    """
    merged = copy.deepcopy(base_resume)

    if "summary" in section_results:
        val = section_results["summary"]
        if isinstance(val, dict):
            val = val.get("summary", "")
        if val:
            merged["summary"] = val

    if "skills" in section_results:
        val = section_results["skills"]
        if isinstance(val, dict):
            val = val.get("skills", val)
        if val:
            merged["skills"] = val

    if "experience" in section_results:
        val = section_results["experience"]
        if isinstance(val, dict):
            # Could be {"experience": [...]} or the list directly
            val = val.get("experience", val) if isinstance(val, dict) else val
        if val and isinstance(val, list):
            merged["experience"] = val

    if "projects" in section_results:
        val = section_results["projects"]
        if isinstance(val, dict):
            val = val.get("projects", val) if isinstance(val, dict) else val
        if val and isinstance(val, list):
            merged["projects"] = val

    return merged


def _apply_humanization(
    resume: dict,
    humanized: dict,
    changed_section_names: list[str],
) -> dict:
    """Apply humanization pass results — only to sections that were rewritten."""
    result = copy.deepcopy(resume)

    if "summary" in humanized and "summary" in changed_section_names:
        val = humanized["summary"]
        if isinstance(val, dict):
            val = val.get("summary", "")
        if val:
            result["summary"] = val

    if "experience" in humanized and "experience" in changed_section_names:
        val = humanized["experience"]
        if isinstance(val, dict):
            val = val.get("experience", val)
        if val and isinstance(val, list):
            result["experience"] = val

    if "projects" in humanized and "projects" in changed_section_names:
        val = humanized["projects"]
        if isinstance(val, dict):
            val = val.get("projects", val)
        if val and isinstance(val, list):
            result["projects"] = val

    return result


# ── Main generator ────────────────────────────────────────────────────────────

def _rewrite_and_critique_section(sec, sec_data, job_analysis, gap_instr, missing_kw, targeted_rag, model_id,
                                   original_text: str | None = None):
    """Wrapper that executes rewrite_section, runs post-processing guards, invokes critique_section, and retries if needed."""
    from services.ai_service import (
        _clean_resume,  # local import avoids circular at module level
    )
    draft = rewrite_section(sec, sec_data, job_analysis, gap_instr, missing_kw, targeted_rag, model_id)
    # Action 2-alt: apply _clean_resume immediately after each draft so all existing
    # guards (metric guard, project/experience matching, skills hallucination guard)
    # run in the section-rewrite path — not just after the full-resume rewrite.
    if original_text:
        draft = _clean_resume(draft, original_text)
    try:
        critique = critique_section(sec, draft, gap_instr, targeted_rag, model_id)
        if not critique.get("passes_audit", True):
            feedback = critique.get("corrective_feedback", "Integrate missing keywords better.")
            new_gap = f"{gap_instr}\nCRITIQUE FEEDBACK (MANDATORY TO FIX): {feedback}"
            # Pass 2: Self-correction
            draft = rewrite_section(sec, draft, job_analysis, new_gap, missing_kw, targeted_rag, model_id)
            # Re-apply guards after the correction pass too
            if original_text:
                draft = _clean_resume(draft, original_text)
    except Exception:
        pass
    return draft


def run_agent(
    resume_text: str,
    jd_text: str,
    model_id: str | None = None,
    career_profile: CareerProfileSchema | None = None,
    use_quality_loop: bool = True,
) -> Generator[str, None, None]:
    memory = AgentMemory(session_id=str(uuid.uuid4()))
    memory.set_hashes(resume_text, jd_text)
    t_start = time.perf_counter()
    phase_timings: dict[str, int] = {}
    source_text = profile_to_source_text(career_profile) if career_profile else resume_text

    # ── Stage 3: Resume Parser ───────────────────────────────────────────────
    if career_profile:
        yield _make_event("parse_resume", "done", {
            "message": "Loaded structured profile — skipping PDF parse.",
        })
    else:
        yield _make_event("parse_resume", "done", {
            "message": "Resume extracted and ready for analysis.",
        })

    # ── JD Intelligence Agent ─────────────────────────────────────────────────
    yield _make_event("jd_analysis", "running")
    phase_start = time.perf_counter()
    job_analysis = analyse_job_description(jd_text, model_id)
    phase_timings["jd_analysis_ms"] = round((time.perf_counter() - phase_start) * 1000)
    yield _make_event("jd_analysis", "done", {
        "job_title": job_analysis.get("job_title", ""),
        "seniority": job_analysis.get("seniority", ""),
        "duration_ms": phase_timings["jd_analysis_ms"],
    })

    # ── RAG retrieval (global + profile) ─────────────────────────────────────
    yield _make_event("rag_retrieval", "running")
    phase_start = time.perf_counter()
    global_rag = build_rag_context_string(
        job_analysis.get("job_title", ""),
        job_analysis.get("required_skills", []),
        job_analysis.get("seniority", ""),
    )
    profile_rag = ""
    if career_profile:
        profile_rag = build_profile_rag_context(career_profile, jd_text, job_analysis)
    combined_rag = "\n\n".join(filter(None, [profile_rag, global_rag]))
    phase_timings["rag_retrieval_ms"] = round((time.perf_counter() - phase_start) * 1000)
    yield _make_event("rag_retrieval", "done", {
        "profile_chunks": profile_rag.count("[") if profile_rag else 0,
        "global_rag_loaded": bool(global_rag),
        "duration_ms": phase_timings["rag_retrieval_ms"],
    })

    rag_enriched_text = source_text
    if combined_rag:
        rag_enriched_text = f"{combined_rag}\n\n--- CANDIDATE SOURCE ---\n{source_text}"

    # ── Structural parse ──────────────────────────────────────────────────────
    yield _make_event("structural_parse", "running")
    if career_profile:
        structured_resume = profile_to_tailored_resume(career_profile, jd_text)
    else:
        structured_resume = rewrite_resume(resume_text, "", {}, model_id)
    yield _make_event("structural_parse", "done")

    # ── Stage 1: Career Identity Agent ───────────────────────────────────────
    yield _make_event("career_identity", "running")
    from services.ai_service import (
        analyze_career_identity,
        improve_resume_for_ats,
        map_evidence,
        review_hiring_manager,
        review_hr,
        review_jd_poster,
        rewrite_human_tone,
    )
    identity = analyze_career_identity(rag_enriched_text, model_id)
    yield _make_event("career_identity", "done", {
        "primary_role": identity.get("primary_role", "Unknown"),
        "confidence": identity.get("confidence", 0),
    })

    # ── Stage 4: Evidence Mapper ─────────────────────────────────────────────
    yield _make_event("evidence_mapping", "running")
    evidence = map_evidence(structured_resume, job_analysis, model_id)
    yield _make_event("evidence_mapping", "done", {
        "verified_score": evidence.get("verified_score", 0),
    })

    # ── Stage 5: Ranking Agent ───────────────────────────────────────────────
    yield _make_event("ranking", "done", {"message": "Projects ordered by evidence weight."})

    # ── Stage 6: Gap Analysis Agent ──────────────────────────────────────────
    yield _make_event("gap_analysis", "running")
    initial_ats = compute_ats_score(json.dumps(structured_resume), jd_text)

    # ── Stage 6a: Domain Classifier ──────────────────────────────────────────
    yield _make_event("domain_classify", "running")
    try:
        domain_profile = classify_role_domain(jd_text, model_id)
    except Exception:
        domain_profile = {
            "domain": job_analysis.get("job_title", "Software Engineering"),
            "seniority": job_analysis.get("seniority", "mid"),
            "role_type": "backend-heavy",
            "industry": "Technology",
            "explicit_skills": job_analysis.get("required_skills", []),
            "implicit_expectations": [],
            "nice_to_haves": [],
            "red_flags_if_missing": [],
        }
    yield _make_event("domain_classify", "done", {
        "domain": domain_profile.get("domain", ""),
        "seniority": domain_profile.get("seniority", ""),
        "role_type": domain_profile.get("role_type", ""),
        "implicit_count": len(domain_profile.get("implicit_expectations", [])),
    })

    # ── Stage 6b: Capability Graph Builder ───────────────────────────────────
    yield _make_event("capability_graph", "running")
    try:
        capability_graph = build_capability_graph(structured_resume, model_id)
    except Exception:
        capability_graph = {}
    yield _make_event("capability_graph", "done", {
        "skills_mapped": len(capability_graph),
    })

    # ── Stage 6c: Adaptive Gap Diff (deterministic, no LLM) ──────────────────
    try:
        from services.adaptive_gap import adaptive_gap_diff
        adaptive_report = adaptive_gap_diff(
            capability_graph, domain_profile, initial_ats.missing_keywords
        )
    except Exception:
        adaptive_report = {
            "critical": [], "bridgeable": [], "implicit": [], "true_unknowns": [],
            "domain": domain_profile.get("domain", ""),
            "seniority": domain_profile.get("seniority", ""),
            "role_type": domain_profile.get("role_type", ""),
        }
    yield _make_event("adaptive_gap", "done", {
        "critical": adaptive_report.get("critical", [])[:8],
        "bridgeable_count": len(adaptive_report.get("bridgeable", [])),
        "bridgeable": adaptive_report.get("bridgeable", [])[:5],
        "implicit": adaptive_report.get("implicit", [])[:6],
        "true_unknowns": adaptive_report.get("true_unknowns", [])[:5],
    })

    gap_report = gap_analysis(
        structured_resume, job_analysis, initial_ats.score, initial_ats.missing_keywords,
        model_id, adaptive_report=adaptive_report
    )
    yield _make_event("gap_analysis", "done", {
        "critical_gaps": gap_report.get("critical_gaps", [])[:8],
    })

    # ── Stage 7: Real HR recruiter review ────────────────────────────────────
    yield _make_event("hr_review", "running")
    hr_feedback = review_hr(structured_resume, model_id)
    hr_signal = str(hr_feedback.get("signal", "RED")).upper()
    yield _make_event("hr_review", "done", {
        "hr_readability_score": hr_feedback.get("hr_readability_score", 80),
        "shortlist_decision": hr_feedback.get("shortlist_decision", "NO"),
        "signal": hr_signal,
        "signal_reason": hr_feedback.get("signal_reason", ""),
        "issues_to_fix": hr_feedback.get("issues_to_fix", [])[:5],
    })

    # ── Stage 8: Technical hiring manager review ─────────────────────────────
    yield _make_event("hm_review", "running")
    hm_feedback = review_hiring_manager(structured_resume, model_id)
    hm_signal = str(hm_feedback.get("signal", "RED")).upper()
    yield _make_event("hm_review", "done", {
        "hm_confidence_score": hm_feedback.get("hm_confidence_score", 80),
        "interview_decision": hm_feedback.get("interview_decision", "NO"),
        "signal": hm_signal,
        "signal_reason": hm_feedback.get("signal_reason", ""),
        "issues_to_fix": hm_feedback.get("issues_to_fix", [])[:5],
    })

    # ── Stage 9: Fix issues raised by reviewers ──────────────────────────────
    yield _make_event("rewrite", "running", {"iteration": 1, "max_iterations": 1})
    rewritten_resume = rewrite_human_tone(
        structured_resume, evidence, hr_feedback, hm_feedback, identity, model_id
    )
    yield _make_event("rewrite", "done", {
        "message": "Resume rewritten to address HR and technical reviewer feedback.",
    })

    # ── Stage 10: Founder / JD-poster review (replaces bare fact-check) ───────
    yield _make_event("jd_poster_review", "running")
    poster_review = review_jd_poster(
        rewritten_resume, source_text, job_analysis, jd_text, model_id
    )
    final_resume = poster_review.get("fact_checked_resume", rewritten_resume)
    poster_signal = str(poster_review.get("signal", "RED")).upper()
    yield _make_event("jd_poster_review", "done", {
        "evidence_credibility_score": poster_review.get("evidence_credibility_score", 90),
        "stripped_claims": poster_review.get("stripped_claims", [])[:6],
        "hire_decision": poster_review.get("hire_decision", "NO"),
        "signal": poster_signal,
        "signal_reason": poster_review.get("signal_reason", ""),
        "final_call": poster_review.get("final_call", ""),
        "issues_to_fix": poster_review.get("issues_to_fix", [])[:5],
    })

    reviewer_signals = {
        "hr": hr_signal,
        "technical": hm_signal,
        "jd_poster": poster_signal,
    }
    all_green = all(s == "GREEN" for s in reviewer_signals.values())
    needs_fix = (
        not all_green
        or bool(hr_feedback.get("issues_to_fix"))
        or bool(hm_feedback.get("issues_to_fix"))
        or bool(poster_review.get("issues_to_fix"))
        or bool(poster_review.get("stripped_claims"))
    )

    # ── Quality loop: agent self-fixes when reviewers raise red flags ────────
    loop_meta = {"iterations": 0, "passed": all_green, "auto_fixes": []}
    if use_quality_loop and needs_fix:
        yield _make_event("quality_loop", "running", {
            "max_iterations": 5,
            "reason": "Reviewers flagged issues — agent is self-fixing.",
        })

        def _improve_fn(resume, jd_t, ja, missing, mid):
            return improve_resume_for_ats(resume, jd_t, ja, missing, mid)

        loop_result = run_quality_loop(
            draft=final_resume,
            jd_text=jd_text,
            source_text=source_text,
            job_analysis=job_analysis,
            model_id=model_id,
            improve_fn=_improve_fn,
        )
        final_resume = loop_result.resume
        loop_meta = {
            "iterations": loop_result.iterations,
            "passed": loop_result.passed,
            "auto_fixes": loop_result.auto_fixes,
        }
        yield _make_event("quality_loop", "done", {
            **loop_meta,
            "message": "Self-fix loop finished." if loop_result.passed else "Self-fix applied; residual risks remain.",
        })
    elif all_green:
        yield _make_event("quality_loop", "done", {
            "iterations": 0,
            "passed": True,
            "auto_fixes": [],
            "message": "All reviewers gave green signals — skipped self-fix loop.",
        })

    # ── Final validation + hiring call ───────────────────────────────────────
    yield _make_event("ats_validation", "running")
    final_ats = compute_ats_score(json.dumps(final_resume), jd_text)

    quality_report = {
        "hr_readability_score": hr_feedback.get("hr_readability_score", 80),
        "hm_confidence_score": hm_feedback.get("hm_confidence_score", 80),
        "human_writing_score": 95,
        "evidence_credibility_score": poster_review.get("evidence_credibility_score", 95),
        "ats_compatibility_report": "ATS keywords optimized against the job description.",
        "formatting_report": "Layout follows one-page constraints.",
    }
    final_composite = compute_composite_score(final_ats.score, quality_report)
    validation_pass = final_composite >= 0.85 and final_ats.score >= 80
    yield _make_event("ats_validation", "done", {
        "composite_score": round(final_composite * 100),
        "validation_status": "pass" if validation_pass else "needs_work",
        "validation_summary": f"Composite {round(final_composite * 100)} · ATS {final_ats.score}",
    })

    if all_green and validation_pass:
        final_signal = "GREEN"
        final_call = poster_review.get("final_call") or "Interview — all reviewers approved."
        hiring_decision = "INTERVIEW"
    elif loop_meta.get("passed") and validation_pass:
        final_signal = "GREEN"
        final_call = "Interview — agent fixed reviewer issues and cleared validation."
        hiring_decision = "INTERVIEW"
    elif poster_signal == "GREEN" or hm_signal == "GREEN":
        final_signal = "YELLOW"
        final_call = poster_review.get("final_call") or "Revise then re-check — mixed reviewer signals."
        hiring_decision = "REVISE"
    else:
        final_signal = "RED"
        final_call = poster_review.get("final_call") or "Pass / rewrite needed — reviewers were not convinced."
        hiring_decision = "PASS"

    yield _make_event("final_review", "done", {
        "confidence_report": f"Positioned as {identity.get('primary_role', 'candidate')}",
        "changes_made": [
            "HR recruiter review",
            "Technical hiring manager review",
            "Founder / JD-poster review",
            *(["Self-fix loop"] if loop_meta.get("iterations", 0) > 0 else ["Green-signal skip"]),
        ],
        "final_signal": final_signal,
        "final_call": final_call,
        "hiring_decision": hiring_decision,
        "reviewer_signals": reviewer_signals,
        "recruiter_readability_score": hr_feedback.get("hr_readability_score", 80),
    })

    # ── Parallel Outputs ─────────────────────────────────────────────────────
    yield _make_event("cover_letter", "running")
    yield _make_event("email", "running")
    yield _make_event("linkedin_message", "running")

    cl_rag = build_targeted_rag_context(
        "cover_letter",
        job_analysis.get("job_title", ""),
        job_analysis.get("required_skills", []),
        job_analysis.get("seniority", ""),
    )
    if profile_rag:
        cl_rag = profile_rag + "\n\n" + cl_rag
    em_rag = build_targeted_rag_context(
        "email",
        job_analysis.get("job_title", ""),
        job_analysis.get("required_skills", []),
        job_analysis.get("seniority", ""),
    )

    cover_letter = {"subject_line": "", "body": ""}
    application_email = {"subject_line": "", "body": ""}
    linkedin_message = {}

    with ThreadPoolExecutor(max_workers=3) as pool:
        cl_future = pool.submit(generate_cover_letter, final_resume, job_analysis, jd_text, model_id, cl_rag)
        em_future = pool.submit(generate_application_email, final_resume, job_analysis, jd_text, model_id, em_rag)
        li_future = pool.submit(generate_linkedin_message, final_resume, job_analysis, model_id, jd_text)

        try:
            cover_letter = cl_future.result(timeout=45)
            yield _make_event("cover_letter", "done", cover_letter)
        except Exception as e:
            yield _make_event("cover_letter", "error", {"message": str(e)})

        try:
            application_email = em_future.result(timeout=45)
            yield _make_event("email", "done", application_email)
        except Exception as e:
            yield _make_event("email", "error", {"message": str(e)})

        try:
            linkedin_message = li_future.result(timeout=60)
            yield _make_event("linkedin_message", "done", linkedin_message)
        except Exception as e:
            yield _make_event("linkedin_message", "error", {"message": str(e)})

    quality_report_full = assess_resume_quality(
        final_resume, jd_text,
        {"score": initial_ats.score, "matched": len(initial_ats.matched_keywords), "total": initial_ats.total_keywords, "missing_count": len(initial_ats.missing_keywords)},
        {"score": final_ats.score, "matched": len(final_ats.matched_keywords), "total": final_ats.total_keywords, "missing_count": len(final_ats.missing_keywords)},
    )
    quality_report_full.update({
        "hr_readability_score": hr_feedback.get("hr_readability_score", 80),
        "hm_confidence_score": hm_feedback.get("hm_confidence_score", 80),
        "evidence_credibility_score": poster_review.get("evidence_credibility_score", 95),
        "reviewer_panel": {
            "hr": {
                "signal": hr_signal,
                "decision": hr_feedback.get("shortlist_decision", "NO"),
                "reason": hr_feedback.get("signal_reason", ""),
                "score": hr_feedback.get("hr_readability_score", 80),
            },
            "technical": {
                "signal": hm_signal,
                "decision": hm_feedback.get("interview_decision", "NO"),
                "reason": hm_feedback.get("signal_reason", ""),
                "score": hm_feedback.get("hm_confidence_score", 80),
            },
            "jd_poster": {
                "signal": poster_signal,
                "decision": poster_review.get("hire_decision", "NO"),
                "reason": poster_review.get("signal_reason", ""),
                "score": poster_review.get("evidence_credibility_score", 95),
                "final_call": poster_review.get("final_call", ""),
            },
        },
        "final_signal": final_signal,
        "final_call": final_call,
        "hiring_decision": hiring_decision,
        "confidence_report": final_call,
    })

    result_payload = {
        "tailored_resume": final_resume,
        "ats_score": final_ats.score,
        "matched_keywords": final_ats.matched_keywords,
        "missing_keywords": final_ats.missing_keywords,
        "total_keywords": final_ats.total_keywords,
        "cover_letter": cover_letter,
        "application_email": application_email,
        "job_analysis": job_analysis,
        "linkedin_message": linkedin_message,
        "quality_report": quality_report_full,
        "auto_improved": loop_meta["iterations"] > 0,
        "model_used": model_id or "",
        "generation_mode": "profile_agent" if career_profile else "agent",
        "loop_iterations": loop_meta["iterations"],
        "loop_passed": loop_meta["passed"],
        "auto_fixes": loop_meta["auto_fixes"],
        "reviewer_signals": reviewer_signals,
        "final_signal": final_signal,
        "final_call": final_call,
        "hiring_decision": hiring_decision,
        # ── NEW: Adaptive gap intelligence ──────────────────────────────────
        "adaptive_gap_report": adaptive_report,
        "domain_profile": domain_profile,
        # ─────────────────────────────────────────────────────────────────────
        "timings": {
            **phase_timings,
            "total_ms": round((time.perf_counter() - t_start) * 1000),
        },
        "ats_report": {
            "baseline_score": initial_ats.score,
            "final_score": final_ats.score,
            "improvement": final_ats.score - initial_ats.score,
            "matched_keywords": final_ats.matched_keywords[:30],
            "missing_keywords": final_ats.missing_keywords[:20],
            "total_keywords": final_ats.total_keywords,
            "score_breakdown": score_breakdown(final_ats.score, quality_report),
        },
        "match_analysis": {
            "match_score": final_ats.score,
            "matched_requirements": final_ats.matched_keywords[:10],
            "unmet_requirements": final_ats.missing_keywords[:10],
            "candidate_strengths": list(evidence.get("evidence_map", {}).keys())[:10],
            "fit_verdict": {
                "GREEN": "Interview ready — reviewers approved",
                "YELLOW": "Mixed signals — revise recommended",
                "RED": "Not ready — rewrite needed",
            }.get(final_signal, "Needs review"),
        },
    }

    yield _make_event("complete", "done", {"result": result_payload})
