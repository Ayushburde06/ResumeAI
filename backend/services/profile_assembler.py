"""
Assemble a TailoredResume dict from a user career profile, optionally ranked by JD keywords.
"""
from __future__ import annotations

from schemas.profile import CareerProfileSchema, ExperienceSchema, ProjectSchema

from services.ats_engine import _extract_jd_keywords, _sanitize_jd, _stem, _tokenize


def _text_blob(*parts: str) -> str:
    return " ".join(p for p in parts if p).lower()


def _keyword_overlap_score(text: str, jd_keywords: set[str]) -> int:
    if not jd_keywords:
        return 0
    tokens = {_stem(t) for t in _tokenize(text)}
    score = 0
    for kw in jd_keywords:
        if " " in kw:
            if kw in text.lower():
                score += 2
            else:
                parts = kw.split()
                if all(_stem(p) in tokens for p in parts):
                    score += 1
        elif _stem(kw) in tokens or kw in tokens:
            score += 1
    return score


def _project_to_resume_entry(project: ProjectSchema, max_bullets: int = 3) -> dict:
    bullets = [b.strip() for b in project.bullets if b.strip()]
    if not bullets:
        parts = []
        if project.problem.strip():
            parts.append(project.problem.strip())
        if project.solution.strip():
            parts.append(project.solution.strip())
        for m in project.impact_metrics[:2]:
            if m.strip():
                parts.append(m.strip())
        bullets = parts[:max_bullets]
    elif len(bullets) > max_bullets:
        bullets = bullets[:max_bullets]

    desc_parts = [project.problem, project.solution, project.architecture]
    description = " ".join(p.strip() for p in desc_parts if p.strip())[:500]

    return {
        "name": project.name or "Project",
        "description": description or (bullets[0] if bullets else ""),
        "tech_stack": project.tech_stack,
        "link": project.link,
        "live_link": project.live_link,
        "_bullets": bullets,
        "_role": project.role,
    }


def _experience_to_resume_entry(exp: ExperienceSchema, max_bullets: int = 4) -> dict:
    bullets = [b.strip() for b in exp.bullets if b.strip()][:max_bullets]
    return {
        "title": exp.title,
        "company": exp.company,
        "location": exp.location,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "bullets": bullets,
    }


def rank_projects(projects: list[ProjectSchema], jd_text: str) -> list[ProjectSchema]:
    kw_buckets = _extract_jd_keywords(_sanitize_jd(jd_text))
    jd_keywords = kw_buckets["hard_skills"] | kw_buckets["domain_concepts"]
    scored = []
    for p in projects:
        blob = _text_blob(
            p.name, p.role, p.problem, p.solution, p.architecture,
            " ".join(p.tech_stack), " ".join(p.impact_metrics),
            " ".join(p.bullets), p.challenges,
        )
        scored.append((_keyword_overlap_score(blob, jd_keywords), p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def rank_experience(experience: list[ExperienceSchema], jd_text: str) -> list[ExperienceSchema]:
    kw_buckets = _extract_jd_keywords(_sanitize_jd(jd_text))
    jd_keywords = kw_buckets["hard_skills"] | kw_buckets["domain_concepts"]
    scored = []
    for e in experience:
        blob = _text_blob(
            e.title, e.company, " ".join(e.bullets), " ".join(e.tech_stack),
        )
        scored.append((_keyword_overlap_score(blob, jd_keywords), e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored]


def profile_to_tailored_resume(
    profile: CareerProfileSchema,
    jd_text: str = "",
    max_projects: int = 3,
    max_experience: int = 4,
) -> dict:
    """
    Build TailoredResume-compatible dict from profile.
    When jd_text is provided, rank and select top items by keyword overlap.
    """
    pi = profile.personal_info
    projects = rank_projects(profile.projects, jd_text) if jd_text else profile.projects
    experience = rank_experience(profile.experience, jd_text) if jd_text else profile.experience

    projects = projects[:max_projects]
    experience = experience[:max_experience]

    resume_projects = []
    for p in projects:
        entry = _project_to_resume_entry(p)
        resume_projects.append({
            "name": entry["name"],
            "description": entry["description"],
            "tech_stack": entry["tech_stack"],
            "link": entry["link"],
            "live_link": entry["live_link"],
        })

    resume_experience = [_experience_to_resume_entry(e) for e in experience]

    skills = {
        "languages": profile.skills.languages,
        "frameworks": profile.skills.frameworks,
        "databases": profile.skills.databases,
        "tools": profile.skills.tools,
        "concepts": profile.skills.concepts + profile.skills.cloud + profile.skills.devops,
    }

    summary = profile.summary.strip()
    if not summary and pi.headline.strip():
        summary = pi.headline.strip()

    return {
        "personal_info": {
            "name": pi.name,
            "email": pi.email,
            "phone": pi.phone,
            "location": pi.location,
            "linkedin": pi.linkedin,
            "github": pi.github,
            "website": pi.website,
        },
        "summary": summary,
        "experience": resume_experience,
        "education": [
            {
                "degree": e.degree,
                "institution": e.institution,
                "location": e.location,
                "graduation_year": e.graduation_year,
                "gpa": e.gpa,
                "honors": e.honors,
            }
            for e in profile.education
        ],
        "skills": skills,
        "certifications": [
            {"name": c.name, "issuer": c.issuer, "year": c.year}
            for c in profile.certifications
        ],
        "projects": resume_projects,
    }


def profile_to_source_text(profile: CareerProfileSchema) -> str:
    """Flat text from profile for fact-checking and agent input."""
    parts = [profile.summary, profile.personal_info.headline]
    for e in profile.experience:
        parts.extend([e.title, e.company, *e.bullets, *e.tech_stack])
    for p in profile.projects:
        parts.extend([
            p.name, p.role, p.problem, p.solution, p.architecture,
            *p.tech_stack, *p.impact_metrics, *p.bullets, p.challenges,
        ])
    for k, v in profile.skills.model_dump().items():
        if isinstance(v, list):
            parts.extend(v)
    return "\n".join(p for p in parts if p and str(p).strip())
