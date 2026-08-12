"""
Loop Engineer — autonomous verify → fix → re-verify until pass or max iterations.
No user prompts during the loop.
"""
from __future__ import annotations

import copy
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from services.ats_engine import compute_ats_score
from services.composite_score import compute_composite_score, should_continue_iteration
from services.humanization_engine import compute_humanization_score
from services.quality_checks import assess_resume_quality
from services.script_generator import trim_resume_for_one_page

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 5
ATS_PASS_THRESHOLD = 90
COMPOSITE_PASS_THRESHOLD = 0.85


@dataclass
class VerifierResult:
    name: str
    passed: bool
    score: float | int | None = None
    details: dict = field(default_factory=dict)


@dataclass
class LoopResult:
    resume: dict
    iterations: int
    verifiers: list[VerifierResult]
    ats_score: int
    composite_score: float
    auto_fixes: list[str]
    passed: bool


def _run_verifiers(
    resume: dict,
    jd_text: str,
    source_text: str,
    original_ats: dict | None = None,
) -> tuple[list[VerifierResult], dict]:
    """Run all verifiers; return results + quality_report."""
    resume_json = json.dumps(resume)
    ats = compute_ats_score(resume_json, jd_text)
    human = compute_humanization_score(resume)
    orig = original_ats or {"score": 0, "matched": 0, "total": 0, "missing_count": 0}
    quality = assess_resume_quality(
        resume,
        jd_text,
        orig,
        {"score": ats.score, "matched": len(ats.matched_keywords), "total": ats.total_keywords, "missing_count": len(ats.missing_keywords)},
    )
    quality_report = {
        "hr_readability_score": quality.get("hr_readability_score", 70),
        "hm_confidence_score": quality.get("hm_confidence_score", 70),
        "human_writing_score": human.score,
        "evidence_credibility_score": quality.get("evidence_credibility_score", 85),
    }
    composite = compute_composite_score(ats.score, quality_report)

    word_count = len(resume_json.split())
    layout_ok = word_count < 4500

    results = [
        VerifierResult("ats", ats.score >= ATS_PASS_THRESHOLD, ats.score, {
            "matched": ats.matched_keywords,
            "missing": ats.missing_keywords,
            "total": ats.total_keywords,
        }),
        VerifierResult("composite", composite >= COMPOSITE_PASS_THRESHOLD, composite, quality_report),
        VerifierResult("humanization", human.score >= 65, human.score, human.dict()),
        VerifierResult("layout", layout_ok, word_count, {"word_count": word_count}),
    ]
    return results, {"ats": ats, "quality_report": quality_report, "composite": composite, "human": human}


def _apply_ats_fix(
    resume: dict,
    missing_keywords: list[str],
    jd_text: str,
    job_analysis: dict,
    model_id: str | None,
    improve_fn: Callable | None,
) -> tuple[dict, str]:
    """Inject missing keywords via AI improve or deterministic summary append."""
    if improve_fn and missing_keywords:
        try:
            improved = improve_fn(resume, jd_text, job_analysis, missing_keywords[:12], model_id)
            return improved, "ats_improve_ai"
        except Exception as e:
            logger.warning("ATS AI fix failed: %s", e)

    # Deterministic fallback: append top missing skills to summary
    if missing_keywords:
        patched = copy.deepcopy(resume)
        summary = patched.get("summary", "")
        to_add = missing_keywords[:5]
        extra = ", ".join(to_add)
        if extra.lower() not in summary.lower():
            patched["summary"] = f"{summary.rstrip('.')}. Proficient in {extra}.".strip()
        return patched, "ats_improve_summary"
    return resume, "none"


def _apply_humanization_fix(
    resume: dict,
    source_text: str,
    model_id: str | None,
    rewrite_fn: Callable | None,
) -> tuple[dict, str]:
    if rewrite_fn:
        try:
            from services.ai_service import rewrite_human_tone
            identity = {"primary_role": "Professional", "confidence": 80}
            evidence = {"verified_score": 85}
            hr = {"hr_readability_score": 80}
            hm = {"hm_confidence_score": 80}
            improved = rewrite_human_tone(resume, evidence, hr, hm, identity, model_id)
            return improved, "humanize_rewrite"
        except Exception as e:
            logger.warning("Humanization fix failed: %s", e)
    return resume, "none"


def _apply_fact_fix(
    resume: dict,
    source_text: str,
    model_id: str | None,
) -> tuple[dict, str]:
    try:
        from services.ai_service import fact_check
        result = fact_check(resume, source_text, model_id)
        fixed = result.get("fact_checked_resume", resume)
        stripped = result.get("stripped_claims", [])
        if stripped:
            return fixed, f"fact_check_stripped_{len(stripped)}"
    except Exception as e:
        logger.warning("Fact check failed: %s", e)
    return resume, "none"


def run_quality_loop(
    draft: dict,
    jd_text: str,
    source_text: str,
    job_analysis: dict | None = None,
    model_id: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    improve_fn: Callable | None = None,
) -> LoopResult:
    """
    Autonomous verify-fix loop. Returns best resume after pass or max iterations.
    """
    job_analysis = job_analysis or {}
    current = copy.deepcopy(draft)
    auto_fixes: list[str] = []
    previous_composite = 0.0
    final_verifiers: list[VerifierResult] = []
    final_ats_score = 0
    final_composite = 0.0

    for iteration in range(max_iterations):
        verifiers, meta = _run_verifiers(current, jd_text, source_text)
        final_verifiers = verifiers
        final_ats_score = meta["ats"].score
        final_composite = meta["composite"]
        all_pass = all(v.passed for v in verifiers)

        if all_pass:
            return LoopResult(
                resume=current,
                iterations=iteration + 1,
                verifiers=verifiers,
                ats_score=final_ats_score,
                composite_score=final_composite,
                auto_fixes=auto_fixes,
                passed=True,
            )

        if iteration >= max_iterations - 1:
            break

        if not should_continue_iteration(previous_composite, final_composite, iteration, max_iterations):
            break
        previous_composite = final_composite

        # Apply fixes in priority order
        fixed = False
        for v in verifiers:
            if v.passed:
                continue
            if v.name == "ats" and v.details.get("missing"):
                current, fix = _apply_ats_fix(
                    current, v.details["missing"], jd_text, job_analysis, model_id, improve_fn,
                )
                if fix != "none":
                    auto_fixes.append(f"iter{iteration+1}:{fix}")
                    fixed = True
                    break
            elif v.name == "layout":
                current = trim_resume_for_one_page(current)
                auto_fixes.append(f"iter{iteration+1}:layout_trim")
                fixed = True
                break
            elif v.name == "humanization":
                current, fix = _apply_humanization_fix(current, source_text, model_id, None)
                if fix != "none":
                    auto_fixes.append(f"iter{iteration+1}:{fix}")
                    fixed = True
                    break

        if not fixed:
            # Try fact check as general cleanup
            current, fix = _apply_fact_fix(current, source_text, model_id)
            if fix != "none":
                auto_fixes.append(f"iter{iteration+1}:{fix}")
            else:
                break

    return LoopResult(
        resume=current,
        iterations=max_iterations,
        verifiers=final_verifiers,
        ats_score=final_ats_score,
        composite_score=final_composite,
        auto_fixes=auto_fixes,
        passed=False,
    )
