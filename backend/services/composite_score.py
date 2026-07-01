"""
Composite Score — deterministic quality formula for loop control.

Score = geometric mean of normalized sub-scores.
Represents overall resume quality across 5 axes.
No LLM required — pure computation.
"""
from __future__ import annotations
import math


# ── Sub-score weights ─────────────────────────────────────────────────────────
# These weights reflect which axis matters most for job applications.
_WEIGHTS = {
    "ats": 0.35,          # ATS keyword coverage (highest impact)
    "readability": 0.25,  # Recruiter readability
    "grammar": 0.20,      # Grammar and sentence quality
    "formatting": 0.15,   # Section structure and layout
    "humanization": 0.05, # Avoidance of AI/buzzword language
}


def compute_composite_score(
    ats_score: int,
    quality_report: dict,
) -> float:
    """
    Compute a 0.0–1.0 composite quality score from ATS + quality report.

    Uses a weighted geometric mean so that a zero on any axis
    brings the whole score down (prevents gaming one metric).

    Args:
        ats_score:      0–100 ATS keyword match score
        quality_report: dict from assess_resume_quality()

    Returns:
        float in [0.0, 1.0]
    """
    ats_norm          = max(0, min(100, ats_score)) / 100.0
    readability_norm  = max(0, min(100, quality_report.get("recruiter_readability_score", 70))) / 100.0
    grammar_norm      = max(0, min(100, quality_report.get("grammar_score", 70))) / 100.0
    formatting_norm   = max(0, min(100, quality_report.get("formatting_score", 80))) / 100.0
    humanization_norm = max(0, min(100, quality_report.get("humanization_score", 70))) / 100.0

    scores = {
        "ats":          ats_norm,
        "readability":  readability_norm,
        "grammar":      grammar_norm,
        "formatting":   formatting_norm,
        "humanization": humanization_norm,
    }

    # Weighted geometric mean: exp(Σ w_i * ln(s_i + ε))
    # ε prevents log(0) on any zero score
    epsilon = 0.001
    log_sum = sum(
        _WEIGHTS[k] * math.log(v + epsilon)
        for k, v in scores.items()
    )
    composite = math.exp(log_sum)
    return round(min(1.0, max(0.0, composite)), 4)


def should_continue_iteration(
    previous_score: float,
    current_score: float,
    iteration: int,
    max_iterations: int,
    min_improvement: float = 0.01,
) -> bool:
    """
    Decide whether to run another optimization iteration.

    Stops when:
    - Improvement is below min_improvement (default 1%)
    - Max iterations reached
    - Score is already near-perfect (≥ 0.92)

    Args:
        previous_score:   composite score before this iteration
        current_score:    composite score after this iteration
        iteration:        current iteration index (0-based)
        max_iterations:   hard cap
        min_improvement:  minimum Δ to justify another pass

    Returns:
        True if another iteration should run
    """
    if iteration >= max_iterations - 1:
        return False
    if current_score >= 0.92:
        return False
    improvement = current_score - previous_score
    return improvement >= min_improvement


def score_breakdown(ats_score: int, quality_report: dict) -> dict:
    """
    Return a human-readable breakdown of the composite score components.
    Useful for the ATS report and SSE events.
    """
    composite = compute_composite_score(ats_score, quality_report)
    return {
        "composite": composite,
        "composite_pct": round(composite * 100),
        "ats": ats_score,
        "readability": quality_report.get("recruiter_readability_score", 0),
        "grammar": quality_report.get("grammar_score", 0),
        "formatting": quality_report.get("formatting_score", 0),
        "humanization": quality_report.get("humanization_score", 0),
        "verdict": (
            "Excellent — ready for submission"     if composite >= 0.85 else
            "Good — minor polish remaining"         if composite >= 0.72 else
            "Fair — one more pass recommended"      if composite >= 0.58 else
            "Needs improvement — ATS coverage low"
        ),
    }
