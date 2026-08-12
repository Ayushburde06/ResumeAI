"""
Deterministic resume generation from profile — minimal LLM, JD-aware selection.
"""
from __future__ import annotations

from schemas.profile import CareerProfileSchema

from services.profile_assembler import (
    profile_to_tailored_resume,
)


def generate_from_profile_script(
    profile: CareerProfileSchema,
    jd_text: str,
    max_projects: int = 3,
    max_experience: int = 4,
) -> dict:
    """
    Script mode: assemble TailoredResume from profile using keyword-ranked selection.
    No LLM calls — fast and deterministic.
    """
    return profile_to_tailored_resume(
        profile,
        jd_text=jd_text,
        max_projects=max_projects,
        max_experience=max_experience,
    )


def trim_resume_for_one_page(resume: dict) -> dict:
    """Deterministic trim when layout verifier fails."""
    import copy
    trimmed = copy.deepcopy(resume)

    exp = trimmed.get("experience", [])
    if len(exp) > 3:
        trimmed["experience"] = exp[:3]
        for item in trimmed["experience"]:
            bullets = item.get("bullets", [])
            if len(bullets) > 3:
                item["bullets"] = bullets[:3]

    projects = trimmed.get("projects", [])
    if len(projects) > 2:
        trimmed["projects"] = projects[:2]

    summary = trimmed.get("summary", "")
    if len(summary) > 400:
        trimmed["summary"] = summary[:397] + "..."

    return trimmed
