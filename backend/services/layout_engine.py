"""
layout_engine.py — Renderer-Agnostic Adaptive Layout Optimization

This module measures the resume payload and calculates the target
typography, density, and whitespace budgets before handing off
to the specific rendering engine (HTML/WeasyPrint or LaTeX).
"""

def count_resume_words(resume: dict) -> int:
    """
    Count ALL visible text tokens in the resume.
    """
    parts: list[str] = []

    pi = resume.get("personal_info", {}) or {}
    for field in ("name", "phone", "email", "linkedin", "github", "location", "website"):
        val = pi.get(field)
        if isinstance(val, str):
            parts.append(val)

    summary = resume.get("summary")
    if isinstance(summary, str) and summary.strip():
        parts.append("Summary")
        parts.append(summary)

    exps = resume.get("experience", [])
    if exps:
        parts.append("Experience Work Experience")
        for exp in exps:
            if not isinstance(exp, dict): continue
            for field in ("company", "title", "location", "start_date", "end_date"):
                val = exp.get(field)
                if isinstance(val, str): parts.append(val)
            for b in exp.get("bullets", []):
                if isinstance(b, str): parts.append(b)

    projs = resume.get("projects", [])
    if projs:
        parts.append("Projects")
        for proj in projs:
            if not isinstance(proj, dict): continue
            if isinstance(proj.get("name"), str): parts.append(proj["name"])
            ts = proj.get("tech_stack", [])
            if isinstance(ts, list): parts.extend(str(t) for t in ts if t)
            desc = proj.get("description", "")
            if isinstance(desc, str): parts.append(desc)
            elif isinstance(desc, list): parts.extend(d for d in desc if isinstance(d, str))

    skills = resume.get("skills", {})
    if isinstance(skills, dict) and any(skills.values()):
        parts.append("Skills Technical Skills")
        for k, v in skills.items():
            if isinstance(v, list) and v:
                parts.extend(str(s) for s in v if s)

    certs = resume.get("certifications", [])
    if certs:
        parts.append("Certifications Extracurricular")
        for cert in certs:
            if not isinstance(cert, dict): continue
            for field in ("name", "issuer", "year", "date"):
                val = cert.get(field)
                if isinstance(val, str): parts.append(str(val))

    edus = resume.get("education", [])
    if edus:
        parts.append("Education")
        for edu in edus:
            if not isinstance(edu, dict): continue
            for field in ("institution", "degree", "gpa", "location", "graduation_year", "honors"):
                val = edu.get(field)
                if isinstance(val, str): parts.append(val)

    return len(" ".join(parts).split())


def choose_typography(word_count: int) -> dict:
    """
    Map resume word count to a full typography spec.
    """
    table = [
        (120,  12.0, 1.80, 24, 18, 24, 12.0, 15, 18, 14),
        (160,  11.0, 1.65, 18, 14, 22, 11.0, 13, 14, 11),
        (210,   9.8, 1.44, 12,  8, 20,  9.8, 10, 10,  8),
        (270,   9.4, 1.40, 10,  7, 19,  9.4,  9,  8,  7),
        (340,   9.0, 1.35,  9,  6, 18,  9.0,  9,  7,  6),
        (420,   8.6, 1.30,  8,  5, 18,  8.6,  8,  6,  5),
        (510,   8.2, 1.26,  7,  4, 17,  8.4,  8,  5,  5),
        (600,   7.8, 1.22,  6,  3, 16,  8.2,  7,  4,  4),
        (700,   7.5, 1.20,  5,  3, 15,  8.0,  7,  3,  4),
        (820,   7.2, 1.18,  4,  2, 14,  7.6,  7,  2,  3),
        (960,   7.0, 1.16,  4,  2, 14,  7.4,  6,  1,  3),
        (9999,  6.8, 1.14,  3,  1, 13,  7.2,  6,  1,  2),
    ]
    for (max_w, fs, lh, smb, emb, ns, ss, bp, cmb, hmb) in table:
        if word_count <= max_w:
            return dict(
                font_size=fs,
                line_height=lh,
                section_mb=smb,
                entry_mb=emb,
                name_size=ns,
                subtitle_size=ss,
                body_padding=bp,
                contact_mb=cmb,
                header_mb=hmb,
            )
    return dict(
        font_size=6.8, line_height=1.14, section_mb=2, entry_mb=1,
        name_size=12, subtitle_size=7.2, body_padding=6, contact_mb=0, header_mb=2,
    )

def optimize_layout(resume: dict) -> dict:
    """
    Returns an optimized layout payload, including typography constraints.
    """
    word_count = count_resume_words(resume)
    return {
        "word_count": word_count,
        "typography": choose_typography(word_count)
    }
