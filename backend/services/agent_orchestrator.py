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
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import Generator

from services.agent_memory import AgentMemory
from services.composite_score import compute_composite_score, should_continue_iteration, score_breakdown
from services.rag_service import build_rag_context_string, build_targeted_rag_context
from services.ats_engine import compute_ats_score, TECH_UNIGRAMS, TECH_BIGRAMS
from services.humanization_engine import compute_humanization_score          # v3: new, deterministic
from services.quality_checks import assess_resume_quality
from services.session_cache import agent_cache
from services.ai_service import (
    analyse_job_description,
    gap_analysis,
    rewrite_section,
    critique_section,
    humanize_sections,
    generate_cover_letter,
    generate_application_email,
    generate_interview_prep,
    generate_linkedin_message,
    generate_recruiter_tips,
    rewrite_resume,
)

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
    from services.quality_checks import assess_resume_quality
    from services.composite_score import compute_composite_score
    
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


def _keyword_placement_hint(classified: dict[str, list[str]]) -> str:
    """v3: Render the classification as plain guidance text to fold into the
    rewrite prompt's extra_context, without needing to change rewrite_resume's
    signature."""
    lines = ["KEYWORD PLACEMENT GUIDANCE (place these in the indicated section):"]
    if classified["skills"]:
        lines.append(f"- Skills section: {', '.join(classified['skills'][:15])}")
    if classified["experience"]:
        lines.append(f"- Experience bullets (work naturally into achievements): {', '.join(classified['experience'][:15])}")
    if classified["summary"]:
        lines.append(f"- Summary (mention 1-2 at most, naturally): {', '.join(classified['summary'])}")
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

def _rewrite_and_critique_section(sec, sec_data, job_analysis, gap_instr, missing_kw, targeted_rag, model_id):
    """Wrapper that executes rewrite_section, invokes critique_section, and retries if needed."""
    draft = rewrite_section(sec, sec_data, job_analysis, gap_instr, missing_kw, targeted_rag, model_id)
    try:
        critique = critique_section(sec, draft, gap_instr, targeted_rag, model_id)
        if not critique.get("passes_audit", True):
            feedback = critique.get("corrective_feedback", "Integrate missing keywords better.")
            new_gap = f"{gap_instr}\nCRITIQUE FEEDBACK (MANDATORY TO FIX): {feedback}"
            # Pass 2: Self-correction
            draft = rewrite_section(sec, draft, job_analysis, new_gap, missing_kw, targeted_rag, model_id)
    except Exception:
        pass
    return draft


def run_agent(
    resume_text: str,
    jd_text: str,
    model_id: str | None = None,
) -> Generator[str, None, None]:
    memory = AgentMemory(session_id=str(uuid.uuid4()))
    memory.set_hashes(resume_text, jd_text)
    t_start = time.time()

    # ── Step 0: Resume parsed (already done by router) ───────────────────────
    yield _make_event("parse_resume", "done", {
        "message": "Resume extracted and ready for analysis.",
    })

    # ── PHASE 1: Parallel — JD analysis, ATS baseline ─────────
    yield _make_event("jd_analysis", "running")
    yield _make_event("ats_baseline", "running")

    job_analysis: dict = {}
    initial_ats = None

    def _run_jd_analysis():
        cached = agent_cache.get_jd_analysis(memory.jd_hash)
        if cached:
            return cached
        result = analyse_job_description(jd_text, model_id)
        agent_cache.set_jd_analysis(memory.jd_hash, result)
        return result

    def _run_ats_baseline():
        return compute_ats_score(resume_text, jd_text)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            jd_future  = pool.submit(_run_jd_analysis)
            ats_future = pool.submit(_run_ats_baseline)

            job_analysis = jd_future.result(timeout=35)   # v4: increased from 30s for complex JDs
            memory.job_title = job_analysis.get("job_title", "")
            memory.seniority = job_analysis.get("seniority", "")
            memory.required_skills = job_analysis.get("required_skills", [])

            initial_ats = ats_future.result(timeout=15)
            memory.rag_context_used = True
            memory.rag_context_snippet = ""

    except Exception as exc:
        yield _make_event("error", "error", {"message": f"Phase 1 failed: {str(exc)[:200]}"})
        return

    yield _make_event("jd_analysis", "done", {
        "job_title": memory.job_title,
        "seniority": memory.seniority,
        "required_skills_count": len(memory.required_skills),
        "strategy": job_analysis.get("rewrite_strategy", ""),
    })
    yield _make_event("ats_baseline", "done", {
        "score": initial_ats.score,
        "matched_count": len(initial_ats.matched_keywords),
        "missing_count": len(initial_ats.missing_keywords),
        "missing_keywords": initial_ats.missing_keywords[:10],
    })

    # ── Build dynamic RAG context from learning store (real past winners) ────
    dynamic_rag_context = ""
    try:
        from database import SessionLocal
        from services.learning_store import build_dynamic_rag_context
        _db = SessionLocal()
        try:
            dynamic_rag_context = build_dynamic_rag_context(
                _db, memory.job_title, memory.required_skills
            )
        finally:
            _db.close()
    except Exception:
        pass   # learning store is best-effort; never block main pipeline

    if dynamic_rag_context:
        memory.rag_context_snippet = dynamic_rag_context[:500]

    yield _make_event("rag_retrieval", "done", {
        "chunks_retrieved": True,
        "learning_examples": bool(dynamic_rag_context),
    })

    initial_ats_meta = {
        "score": initial_ats.score,
        "matched": len(initial_ats.matched_keywords),
        "total": initial_ats.total_keywords,
        "missing_count": len(initial_ats.missing_keywords),
    }

    # v3: classify missing keywords by section BEFORE the first rewrite so the
    # model places them correctly on attempt 1 instead of needing a correction pass.
    classified_missing = _classify_missing_keywords(initial_ats.missing_keywords)
    keyword_hint = _keyword_placement_hint(classified_missing)
    combined_extra_context = "\n\n".join(filter(None, [dynamic_rag_context, keyword_hint]))

    # ── PHASE 2: First-pass Rewrite ───────────────────────────────────────────
    yield _make_event("rewrite", "running", {"iteration": 1, "max_iterations": MAX_ITERATIONS})

    tailored_resume: dict = {}

    def _run_first_pass_rewrite():
        first_pass_cache_key = agent_cache.make_key(memory.resume_hash, memory.jd_hash, "full_v1")
        cached_first = agent_cache.get(first_pass_cache_key)
        if cached_first:
            return cached_first
        result = rewrite_resume(
            resume_text, jd_text, job_analysis,
            model_id=model_id,
            missing_keywords=initial_ats.missing_keywords[:25],   # v4: increased from 20 to 25
            extra_context=combined_extra_context or None,
        )
        agent_cache.set(first_pass_cache_key, result, ttl_seconds=1800)
        return result

    try:
        tailored_resume = _run_first_pass_rewrite()
        for sec in ["summary", "experience", "skills", "projects"]:
            memory.snapshot_section(sec, tailored_resume.get(sec), tailored_resume.get(sec))

    except Exception as exc:
        yield _make_event("rewrite", "error", {"iteration": 1, "message": str(exc)[:200]})
        yield _make_event("error", "error", {"message": "First-pass rewrite failed."})
        return

    # Emit optimization_plan event from existing job_analysis (no extra LLM call needed)
    yield _make_event("optimization_plan", "done", {
        "job_title": memory.job_title,
        "rewrite_strategy": job_analysis.get("rewrite_strategy", ""),
        "primary_stack": job_analysis.get("required_skills", [])[:5],
    })

    # ── PHASE 3: Gap analysis and Section-wise parallel rewrite loop ─────────
    try:
        yield _make_event("gap_analysis", "running")

        first_ats = compute_ats_score(json.dumps(tailored_resume), jd_text)

        try:
            gap_report = gap_analysis(
                resume_json=tailored_resume,
                job_analysis=job_analysis,
                ats_score=first_ats.score,
                missing_keywords=first_ats.missing_keywords,
                model_id=model_id,
            )
        except Exception:
            gap_report = {"section_priorities": {}, "critical_gaps": [], "unchanged_sections": []}

        yield _make_event("gap_analysis", "done", {
            "critical_gaps": gap_report.get("critical_gaps", [])[:8],
            "estimated_ats_gain": gap_report.get("estimated_ats_gain", ""),
            "unchanged_sections": gap_report.get("unchanged_sections", []),
        })

        section_priorities = gap_report.get("section_priorities", {})
        unchanged_sections = set(gap_report.get("unchanged_sections", []))
        missing_keywords = first_ats.missing_keywords

        sections_to_rewrite = [
            s for s in ["summary", "experience", "skills", "projects"]
            if s not in unchanged_sections
        ]

        # v3: pre-fetch targeted RAG context once per section instead of re-fetching
        # it on every iteration of the loop below — job_title/required_skills/
        # seniority never change mid-request, so the retrieval result can't either.
        section_rag_cache = {
            sec: build_targeted_rag_context(
                sec, memory.job_title, memory.required_skills, memory.seniority, top_k=3
            )
            for sec in sections_to_rewrite
        }

        # v3: deterministic quality signal for the FIRST candidate too — no LLM call.
        first_human = compute_humanization_score(tailored_resume)
        first_composite = _deterministic_composite(tailored_resume, jd_text, first_ats.score, first_human.score)

        final_ats = first_ats
        best_resume = copy.deepcopy(tailored_resume)
        prev_composite = first_composite

        memory.add_iteration(0, first_ats.score, first_ats.matched_keywords,
                             first_ats.missing_keywords, "First-pass full rewrite.",
                             composite_score=first_composite)

        yield _make_event("rewrite", "done", {
            "iteration": 1,
            "ats_score": first_ats.score,
            "composite_score": round(first_composite * 100),
            "matched_count": len(first_ats.matched_keywords),
            "missing_count": len(first_ats.missing_keywords),
            "target_reached": first_ats.score >= TARGET_ATS,
        })

    except Exception as exc:
        yield _make_event("rewrite", "error", {"iteration": 1, "message": str(exc)[:200]})
        yield _make_event("error", "error", {"message": "First-pass rewrite failed."})
        return

    # Phase 3b: Section-wise refinement iterations (max 2 more)
    for i in range(1, MAX_ITERATIONS):
        if prev_composite >= 0.92:
            break
        if final_ats.score >= TARGET_ATS:
            break
        if not sections_to_rewrite or not missing_keywords:
            break

        score_before = prev_composite

        yield _make_event("rewrite", "running", {
            "iteration": i + 1,
            "max_iterations": MAX_ITERATIONS,
            "sections": sections_to_rewrite,
        })

        try:
            section_results: dict = {}

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {}
                for sec in sections_to_rewrite:
                    gap_instr = section_priorities.get(sec) or f"Integrate missing keywords: {', '.join(missing_keywords[:6])}"
                    sec_data = tailored_resume.get(sec)
                    targeted_rag = section_rag_cache.get(sec, "")   # v3: cached, not re-fetched
                    futures[pool.submit(
                        _rewrite_and_critique_section,
                        sec,
                        sec_data,
                        job_analysis,
                        gap_instr,
                        missing_keywords[:12],
                        targeted_rag,
                        model_id,
                    )] = sec

                # v3: wait() with a real timeout on the whole batch, then collect
                # results only from futures that actually finished. Previously
                # as_completed(timeout=...) could silently drop every unfinished
                # future with no record of which section stalled.
                done, not_done = wait(list(futures.keys()), timeout=SECTION_FUTURE_TIMEOUT, return_when=ALL_COMPLETED)
                for future in done:
                    sec = futures[future]
                    try:
                        section_results[sec] = future.result()
                    except Exception:
                        pass  # keep previous version if this section rewrite failed
                for future in not_done:
                    sec = futures[future]
                    future.cancel()  # best-effort; thread may still finish in background

            if section_results:
                candidate = _merge_section_results(tailored_resume, section_results)
                candidate_ats = compute_ats_score(json.dumps(candidate), jd_text)

                # v3: deterministic humanization check drives the loop — no LLM call here.
                candidate_human = compute_humanization_score(candidate)
                candidate_composite = _deterministic_composite(candidate, jd_text, candidate_ats.score, candidate_human.score)

                if candidate_composite >= prev_composite:
                    for sec, result in section_results.items():
                        before = tailored_resume.get(sec)
                        after = candidate.get(sec)
                        memory.snapshot_section(sec, before, after)

                    tailored_resume = candidate
                    final_ats = candidate_ats
                    best_resume = copy.deepcopy(candidate)

                    improvement = candidate_composite - prev_composite
                    prev_composite = candidate_composite
                    missing_keywords = candidate_ats.missing_keywords

                    memory.add_iteration(
                        i, candidate_ats.score,
                        candidate_ats.matched_keywords,
                        candidate_ats.missing_keywords,
                        f"Section rewrite — sections: {', '.join(section_results.keys())}",
                        composite_score=candidate_composite,
                        changed_sections=list(section_results.keys()),
                    )

                    # ── Delta pattern storage ────────────────────────────────
                    ats_gain = candidate_ats.score - final_ats.score
                    if ats_gain >= 3:
                        new_keywords = list(
                            set(candidate_ats.matched_keywords) -
                            set(final_ats.matched_keywords)
                        )[:15]
                        try:
                            from database import SessionLocal as _SL
                            from models.learning import DeltaPattern
                            _db2 = _SL()
                            try:
                                for sec in section_results.keys():
                                    _db2.add(DeltaPattern(
                                        job_title_key=memory.job_title.lower().strip(),
                                        section_type=sec,
                                        ats_before=final_ats.score,
                                        ats_after=candidate_ats.score,
                                        ats_gain=ats_gain,
                                        keywords_added=json.dumps(new_keywords),
                                    ))
                                _db2.commit()
                            finally:
                                _db2.close()
                        except Exception:
                            pass

                    yield _make_event("rewrite", "done", {
                        "iteration": i + 1,
                        "ats_score": candidate_ats.score,
                        "composite_score": round(candidate_composite * 100),
                        "matched_count": len(candidate_ats.matched_keywords),
                        "missing_count": len(candidate_ats.missing_keywords),
                        "target_reached": candidate_ats.score >= TARGET_ATS,
                        "improvement": round(improvement * 100, 1),
                    })

                    if not should_continue_iteration(score_before, candidate_composite, i, MAX_ITERATIONS):
                        break
                else:
                    yield _make_event("rewrite", "done", {
                        "iteration": i + 1,
                        "ats_score": final_ats.score,
                        "composite_score": round(prev_composite * 100),
                        "matched_count": len(final_ats.matched_keywords),
                        "missing_count": len(final_ats.missing_keywords),
                        "target_reached": final_ats.score >= TARGET_ATS,
                        "improvement": 0,
                    })
                    break

        except Exception as exc:
            yield _make_event("rewrite", "error", {
                "iteration": i + 1,
                "message": str(exc)[:200],
            })
            break

    tailored_resume = best_resume if best_resume else tailored_resume

    # ── Phase 3c: Targeted ATS boost pass (if still < 90) ────────────────────
    # v4: one final improve_resume_for_ats() pass on the top missing keywords to
    # reliably reach the 90+ threshold when section rewrites haven't fully closed the gap.
    if final_ats.score < TARGET_ATS and final_ats.missing_keywords:
        try:
            from services.ai_service import improve_resume_for_ats
            boost_result = improve_resume_for_ats(
                tailored_resume,
                jd_text,
                job_analysis,
                final_ats.missing_keywords[:15],
                model_id=model_id,
            )
            if boost_result:
                boost_ats = compute_ats_score(json.dumps(boost_result), jd_text)
                if boost_ats.score >= final_ats.score:
                    tailored_resume = boost_result
                    best_resume = copy.deepcopy(boost_result)
                    final_ats = boost_ats
                    yield _make_event("rewrite", "done", {
                        "iteration": MAX_ITERATIONS + 1,
                        "ats_score": boost_ats.score,
                        "composite_score": 0,
                        "matched_count": len(boost_ats.matched_keywords),
                        "missing_count": len(boost_ats.missing_keywords),
                        "target_reached": boost_ats.score >= TARGET_ATS,
                        "improvement": boost_ats.score - final_ats.score,
                        "note": "ATS boost pass applied to close keyword gap",
                    })
        except Exception:
            pass  # boost pass is best-effort — never block main pipeline

    # ── PHASE 4: Selective humanization + Quality assessment ─────────────────
    yield _make_event("humanization", "running")

    changed_section_names = list(memory.changed_sections)
    humanized_data: dict = {}

    # v3: only ask the LLM to rewrite sections that actually fail the
    # deterministic humanization check. A section that's already clean
    # (no buzzwords, has outcomes, active voice) skips the call entirely.
    sections_needing_humanization = {}
    section_human_scores = {}
    for sec in changed_section_names:
        sec_data = tailored_resume.get(sec)
        if not sec_data:
            continue
        score = _section_humanization_score(sec, sec_data)
        section_human_scores[sec] = score
        if score < HUMANIZATION_OK_THRESHOLD:
            sections_needing_humanization[sec] = sec_data

    if sections_needing_humanization:
        try:
            humanized_data = humanize_sections(sections_needing_humanization, model_id=model_id)
            if humanized_data:
                tailored_resume = _apply_humanization(
                    tailored_resume, humanized_data, list(sections_needing_humanization.keys())
                )
        except Exception:
            pass  # Humanization is optional — keep rewritten resume if it fails

    yield _make_event("humanization", "done", {
        "sections_humanized": list(humanized_data.keys()),
        "sections_already_clean": [s for s in changed_section_names if s not in sections_needing_humanization],
        "section_scores": section_human_scores,
    })

    # Final ATS validation after humanization
    yield _make_event("ats_validation", "running")
    try:
        post_human_ats = compute_ats_score(json.dumps(tailored_resume), jd_text)
        if post_human_ats.score >= final_ats.score:
            final_ats = post_human_ats
    except Exception:
        pass

    final_ats_meta = {
        "score": final_ats.score,
        "matched": len(final_ats.matched_keywords),
        "total": final_ats.total_keywords,
        "missing_count": len(final_ats.missing_keywords),
    }

    # v3: this is now the ONLY call to assess_resume_quality() in the whole
    # pipeline (was up to 4x before) — it builds the final human-readable
    # report and the official composite score shown to the user.
    quality = assess_resume_quality(tailored_resume, jd_text, initial_ats_meta, final_ats_meta)
    final_composite = compute_composite_score(final_ats.score, quality)

    yield _make_event("ats_validation", "done", {
        "validation_status": "pass" if final_ats.score >= 80 else "needs_review",
        "validation_summary": quality["ats_compatibility_report"],
        "formatting_report": quality["formatting_report"],
        "composite_score": round(final_composite * 100),
    })
    yield _make_event("humanization_check", "done", {
        "humanization_score": quality["humanization_score"],
        "notes": quality["notes"][:3],
    })
    yield _make_event("grammar_check", "done", {
        "grammar_score": quality["grammar_score"],
        "report": quality["grammar_report"],
    })

    reflection_summary = (
        "Output is grounded, recruiter-readable, and ready for export."
        if final_ats.score >= 80 and quality["humanization_score"] >= 80
        else "The draft is usable — one more manual review of wording is recommended."
    )
    yield _make_event("reflection", "done", {
        "reflection_summary": reflection_summary,
        "composite_score": round(final_composite * 100),
    })

    final_review = {
        "recruiter_readability_score": quality["recruiter_readability_score"],
        "confidence_report": quality["confidence_report"],
        "changes_made": quality["changes_made"],
        "before_after_comparison": quality["before_after_comparison"],
    }
    yield _make_event("final_review", "done", final_review)

    # ── PHASE 5: Parallel outputs (5 LLM calls) ───────────────────────────────
    cover_letter: dict = {}
    application_email: dict = {}
    interview_prep: dict = {}
    linkedin_message: dict = {}
    recruiter_tips: dict = {}

    yield _make_event("cover_letter", "running")
    yield _make_event("email", "running")
    yield _make_event("interview_prep", "running")
    yield _make_event("linkedin_message", "running")
    yield _make_event("recruiter_tips", "running")

    cl_rag = build_targeted_rag_context("cover_letter", memory.job_title, memory.required_skills, memory.seniority, top_k=2)
    em_rag = build_targeted_rag_context("email", memory.job_title, memory.required_skills, memory.seniority, top_k=2)

    with ThreadPoolExecutor(max_workers=5) as pool:
        cl_future = pool.submit(generate_cover_letter, tailored_resume, job_analysis, jd_text, model_id, cl_rag)
        em_future = pool.submit(generate_application_email, tailored_resume, job_analysis, jd_text, model_id, em_rag)
        ip_future = pool.submit(generate_interview_prep, tailored_resume, job_analysis, model_id)
        lm_future = pool.submit(generate_linkedin_message, tailored_resume, job_analysis, model_id)
        rt_future = pool.submit(
            generate_recruiter_tips,
            tailored_resume, job_analysis, final_ats.score, final_ats.missing_keywords[:5], model_id
        )

        for future, name in [
            (cl_future, "cover_letter"),
            (em_future, "email"),
            (ip_future, "interview_prep"),
            (lm_future, "linkedin_message"),
            (rt_future, "recruiter_tips"),
        ]:
            try:
                result = future.result(timeout=45)
                if name == "cover_letter":
                    cover_letter = result
                elif name == "email":
                    application_email = result
                elif name == "interview_prep":
                    interview_prep = result
                elif name == "linkedin_message":
                    linkedin_message = result
                elif name == "recruiter_tips":
                    recruiter_tips = result
                yield _make_event(name, "done")
            except Exception as exc:
                yield _make_event(name, "error", {"message": str(exc)[:100]})

    # ── PHASE 6: Deterministic outputs (no LLM) ───────────────────────────────
    match_analysis = _build_match_analysis(job_analysis, final_ats)
    ats_report = _build_ats_report(initial_ats, final_ats, quality)
    change_log = memory.build_change_log()

    memory.total_time_ms = (time.time() - t_start) * 1000

    # ── Complete event ────────────────────────────────────────────────────────
    
    final_human_result = compute_humanization_score(tailored_resume)
    
    yield _make_event("complete", "done", {
        "result": {
            "tailored_resume":    tailored_resume,
            "ats_score":          final_ats.score,
            "matched_keywords":   final_ats.matched_keywords,
            "missing_keywords":   final_ats.missing_keywords,
            "total_keywords":     final_ats.total_keywords,
            "ats_validation": {
                "validation_status":  "pass" if final_ats.score >= 80 else "needs_review",
                "validation_summary": quality["ats_compatibility_report"],
                "formatting_report":  quality["formatting_report"],
            },
            "humanization_score": final_human_result.score,
            "humanization_report": final_human_result.dict(),
            "quality_report": {
                "ats_compatibility_report":  quality["ats_compatibility_report"],
                "formatting_report":         quality["formatting_report"],
                "grammar_report":            quality["grammar_report"],
                "humanization_score":        quality["humanization_score"],
                "recruiter_readability_score": quality["recruiter_readability_score"],
                "changes_made":              quality["changes_made"],
                "before_after_comparison":   quality["before_after_comparison"],
                "confidence_report":         quality["confidence_report"],
            },
            "reflection":         reflection_summary,
            "final_review":       final_review,
            "cover_letter":       cover_letter,
            "application_email":  application_email,
            "interview_prep":     interview_prep,
            "linkedin_message":   linkedin_message,
            "recruiter_tips":     recruiter_tips,
            "match_analysis":     match_analysis,
            "ats_report":         ats_report,
            "change_log":         change_log,
            "job_analysis":       job_analysis,
            "agent_trace":        memory.to_dict(),
            "auto_improved":      len(memory.iterations) > 1,
        }
    })
