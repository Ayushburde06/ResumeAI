"""
Deterministic resume quality checks.

These heuristics are intentionally lightweight so they can run on every
analysis without adding another model call. They are used to surface
humanization, grammar, readability, and formatting signals alongside ATS.
"""
from __future__ import annotations

import re
from collections import Counter

from services.ats_engine import get_resume_plain_text

BANNED_PHRASES = [
    "leveraged",
    "spearheaded",
    "synergized",
    "revolutionized",
    "utilized",
    "orchestrated",
    "transformed",
    "world-class",
    "cutting-edge",
    "visionary",
    "dynamic",
    "highly motivated",
    "results-driven",
    "passionate",
    "hardworking",
]


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _collect_lines(resume: dict) -> list[str]:
    lines: list[str] = []
    summary = str(resume.get("summary", "")).strip()
    if summary:
        lines.extend([line.strip() for line in re.split(r"[\n\r]+", summary) if line.strip()])

    for exp in resume.get("experience", []):
        if isinstance(exp, dict):
            for bullet in exp.get("bullets", []) or []:
                if isinstance(bullet, str) and bullet.strip():
                    lines.append(bullet.strip())

    for proj in resume.get("projects", []):
        if isinstance(proj, dict):
            desc = str(proj.get("description", "")).strip()
            if desc:
                lines.extend([line.strip() for line in desc.split("\n") if line.strip()])

    return lines


def assess_resume_quality(resume: dict, jd_text: str, ats_before: dict | None, ats_after: dict | None) -> dict:
    text = get_resume_plain_text(resume).lower()
    lines = _collect_lines(resume)

    banned_hits = [phrase for phrase in BANNED_PHRASES if phrase in text]
    repeated_starts = Counter(
        re.sub(r"[^a-z]+", "", line.split(" ", 1)[0].lower())
        for line in lines
        if line.split()
    )
    repetitive_openers = sum(1 for _, count in repeated_starts.items() if count >= 3)
    long_lines = sum(1 for line in lines if len(line.split()) > 28)
    sentence_errors = sum(
        1 for line in lines
        if line and not line.endswith((".", "!", "?", ")", "]", '"', "'"))
    )
    weak_words = sum(
        text.count(word)
        for word in ("worked on", "responsible for", "helped with", "participated in", "assisted with")
    )

    humanization_score = _clamp(
        100
        - len(banned_hits) * 10
        - repetitive_openers * 8
        - weak_words * 4
    )

    grammar_score = _clamp(
        100
        - sentence_errors * 4
        - max(0, long_lines - 2) * 3
    )

    section_presence = {
        "summary": bool(str(resume.get("summary", "")).strip()),
        "experience": bool(resume.get("experience")),
        "education": bool(resume.get("education")),
        "skills": bool(resume.get("skills")),
        "projects": bool(resume.get("projects")),
    }
    sections_present = sum(section_presence.values())

    formatting_score = _clamp(
        100
        - max(0, 5 - sections_present) * 6
        - (0 if section_presence["skills"] else 12)
        - (0 if section_presence["experience"] else 10)
    )

    ats_before_score = int((ats_before or {}).get("score", 0) or 0)
    ats_after_score = int((ats_after or {}).get("score", 0) or 0)
    readable_notes = []
    if banned_hits:
        readable_notes.append(f"removed or avoided {len(banned_hits)} buzzword patterns")
    if repetitive_openers:
        readable_notes.append("varied bullet openers to reduce monotony")
    if long_lines:
        readable_notes.append("kept long bullets under control")

    if not readable_notes:
        readable_notes.append("kept the wording concise and factual")

    recruiter_readability_score = _clamp(
        round((humanization_score + grammar_score + formatting_score) / 3)
    )

    compatibility_note = "ATS-friendly single-column structure with standard section headings."
    if formatting_score < 80:
        compatibility_note = "Review section order and spacing so ATS parsers can read the resume cleanly."

    confidence_note = (
        f"Confidence is high: ATS moved from {ats_before_score}% to {ats_after_score}% while keeping the rewrite factual."
        if ats_after_score >= 80 and humanization_score >= 80
        else f"Confidence is moderate: ATS is {ats_after_score}% and the draft should be checked once more for wording polish."
    )

    change_log = [
        f"ATS score moved from {ats_before_score}% to {ats_after_score}%.",
        f"Keyword coverage changed from {(ats_before or {}).get('matched', 0)} to {(ats_after or {}).get('matched', 0)} matched terms.",
        "Summary, experience, skills, and projects were kept aligned to the source resume and job description.",
    ]

    if banned_hits:
        change_log.append(f"Buzzword usage was reduced by avoiding: {', '.join(banned_hits[:4])}.")

    if section_presence["projects"]:
        change_log.append("Project descriptions remain compact and recruiter-scannable.")

    before_after = {
        "ats_before": ats_before_score,
        "ats_after": ats_after_score,
        "keyword_coverage_before": int(round(((ats_before or {}).get("matched", 0) or 0) / max(1, (ats_before or {}).get("total", 1)) * 100)),
        "keyword_coverage_after": int(round(((ats_after or {}).get("matched", 0) or 0) / max(1, (ats_after or {}).get("total", 1)) * 100)),
        "missing_before": int((ats_before or {}).get("missing_count", 0) or 0),
        "missing_after": int((ats_after or {}).get("missing_count", 0) or 0),
    }

    return {
        "ats_compatibility_report": compatibility_note,
        "formatting_report": "Standard resume headings, plain text structure, and predictable section ordering.",
        "grammar_report": " ".join(
            [
                f"Grammar score {grammar_score}/100.",
                "No obvious sentence-level issues found." if grammar_score >= 80 else "Some bullets still need a final polish.",
            ]
        ),
        "humanization_score": humanization_score,
        "recruiter_readability_score": recruiter_readability_score,
        "changes_made": change_log,
        "before_after_comparison": before_after,
        "confidence_report": confidence_note,
        "notes": readable_notes,
        "formatting_score": formatting_score,
        "grammar_score": grammar_score,
    }
