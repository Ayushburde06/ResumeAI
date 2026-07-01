"""
Learning Store — saves and retrieves winning resume sections from the DB.

HOW IT WORKS:
  1. After every successful analysis where ATS >= LEARN_THRESHOLD (88%),
     extract the key resume sections and store them with the job context.
  2. On future analyses for similar roles, retrieve these real examples
     and inject them into the RAG context alongside the static JSONL files.
  3. The more users run analyses, the better the RAG context becomes.

This creates a compounding improvement loop with zero extra AI calls.
"""
import json
import re
from sqlalchemy.orm import Session
from models.learning import LearningExample

LEARN_THRESHOLD = 88   # minimum ATS score to save as a winning example
MAX_EXAMPLES_PER_QUERY = 3


def _normalize_job_title(title: str) -> str:
    """Normalize job titles so similar roles share examples."""
    t = title.lower().strip()
    # Map common synonyms to canonical forms
    _SYNONYMS = {
        "swe": "software engineer",
        "software developer": "software engineer",
        "software development engineer": "software engineer",
        "backend dev": "backend developer",
        "backend engineer": "backend developer",
        "frontend dev": "frontend developer",
        "frontend engineer": "frontend developer",
        "full stack": "fullstack developer",
        "full-stack developer": "fullstack developer",
        "full stack developer": "fullstack developer",
        "mern developer": "fullstack developer",
        "mean developer": "fullstack developer",
        "ml engineer": "machine learning engineer",
        "ai engineer": "machine learning engineer",
        "data engineer": "data engineer",
        "devops engineer": "devops engineer",
        "site reliability engineer": "devops engineer",
        "sre": "devops engineer",
    }
    for pattern, canonical in _SYNONYMS.items():
        if pattern in t:
            return canonical
    # Strip generic suffixes
    for suffix in [" intern", " trainee", " fresher", " associate"]:
        if t.endswith(suffix):
            t = t[: -len(suffix)].strip()
    return t


def _make_skills_key(skills: list[str]) -> str:
    """Create a sorted, normalized key from top skills for fuzzy matching."""
    normalized = sorted({s.lower().strip() for s in skills if s.strip()}[:8])
    return ",".join(normalized)


def _skills_overlap(key_a: str, key_b: str) -> int:
    """Count overlapping skills between two skill keys."""
    set_a = set(key_a.split(","))
    set_b = set(key_b.split(","))
    return len(set_a & set_b)


def save_winning_example(
    db: Session,
    job_title: str,
    seniority: str,
    required_skills: list[str],
    resume: dict,
    ats_score: int,
    model_used: str = "",
    history_id: int | None = None,
) -> None:
    """
    Save key resume sections as winning examples when ATS score >= threshold.
    Called automatically in analyze.py after a successful high-scoring run.
    """
    if ats_score < LEARN_THRESHOLD:
        return

    job_title_key = _normalize_job_title(job_title)
    skills_key = _make_skills_key(required_skills)

    sections_to_save = {}

    # Summary
    if resume.get("summary"):
        sections_to_save["summary"] = resume["summary"]

    # Experience bullets (first role only — most relevant)
    experience = resume.get("experience", [])
    if experience and isinstance(experience[0], dict):
        bullets = experience[0].get("bullets", [])
        if bullets:
            sections_to_save["experience"] = json.dumps(bullets[:3])

    # Projects (first project description)
    projects = resume.get("projects", [])
    if projects and isinstance(projects[0], dict):
        desc = projects[0].get("description", "")
        if desc:
            sections_to_save["projects"] = desc

    for section_type, content in sections_to_save.items():
        try:
            example = LearningExample(
                job_title_key=job_title_key,
                seniority=seniority or "",
                skills_key=skills_key,
                section_type=section_type,
                content=content,
                ats_score=ats_score,
                model_used=model_used,
                history_id=history_id,
            )
            db.add(example)
        except Exception:
            pass  # never block the main response

    try:
        db.commit()
    except Exception:
        db.rollback()


def retrieve_winning_examples(
    db: Session,
    job_title: str,
    required_skills: list[str],
    section_type: str = "",
    top_k: int = MAX_EXAMPLES_PER_QUERY,
) -> list[dict]:
    """
    Retrieve winning examples for a similar role + skill set.
    Returns list of {section_type, content, ats_score} dicts.
    """
    job_title_key = _normalize_job_title(job_title)
    skills_key = _make_skills_key(required_skills)

    query = db.query(LearningExample).filter(
        LearningExample.job_title_key == job_title_key,
        LearningExample.ats_score >= LEARN_THRESHOLD,
    )
    if section_type:
        query = query.filter(LearningExample.section_type == section_type)

    candidates = query.order_by(LearningExample.ats_score.desc()).limit(20).all()

    # Score by skills overlap — prefer examples with more matching skills
    scored = []
    for ex in candidates:
        overlap = _skills_overlap(skills_key, ex.skills_key)
        scored.append((overlap, ex.ats_score, ex))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    return [
        {
            "section_type": ex.section_type,
            "content": ex.content,
            "ats_score": ex.ats_score,
            "job_title": ex.job_title_key,
        }
        for _, _, ex in scored[:top_k]
    ]


def build_dynamic_rag_context(
    db: Session,
    job_title: str,
    required_skills: list[str],
) -> str:
    """
    Build a RAG context string from real past winning examples.
    Injected into AI prompts alongside static JSONL knowledge.
    """
    examples = retrieve_winning_examples(db, job_title, required_skills)
    if not examples:
        return ""

    lines = ["=== REAL WINNING EXAMPLES (from past high-scoring analyses for this role) ==="]
    lines.append("These were from resumes that scored 88%+ ATS. Use them as style and phrasing reference.")
    lines.append("")

    for ex in examples:
        label = f"[{ex['section_type'].upper()} / ATS {ex['ats_score']}%]"
        content = ex["content"]
        # Parse JSON bullets if needed
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                content = "\n".join(f"• {b}" for b in parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        lines.append(f"{label} {content[:400]}")

    return "\n".join(lines)
