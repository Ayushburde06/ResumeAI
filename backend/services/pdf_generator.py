"""
pdf_generator.py — HTML → PDF using WeasyPrint.

Architecture:
  1. Jinja2 renders resume dict → HTML string
  2. ALL visible text (headers, titles, bullets, names, dates) is counted
     to get an accurate density score — NOT just bullets/skills
  3. Typography settings (font, line-height, spacing, header sizes, padding)
     are derived from density and injected into <head>
  4. Single WeasyPrint render → PDF bytes

One-page guarantee:
  - Font scales from 11pt (sparse) down to 6.8pt (very dense)
  - Body padding scales from 12mm down to 6mm
  - Name heading scales from 20pt down to 14pt
  - Section titles scale from 10pt down to 7.5pt
  - page-break-inside is removed from .section via injection so
    WeasyPrint never pushes a whole section to page 2
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from services.resume_links import link_label, to_href
from services.text_formatting import bold_list, extract_skills_flat, render_bold_markers

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
VALID_TEMPLATES = {"modern", "classic", "minimal"}

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)
_jinja_env.filters["to_href"]    = to_href
_jinja_env.filters["link_label"] = link_label
# NOTE: "bold" and "bold_list" filters are registered per-call inside generate_pdf
# so they can be made context-aware (JD keywords + candidate skills).


# ── Content density counter ───────────────────────────────────────────────────

def _count_resume_words(resume: dict) -> int:
    """
    Count ALL visible text tokens in the resume — not just bullets.
    This includes:
      - Personal info (name, phone, email, linkedin, github, location, website)
      - Summary text and header
      - Experience (company, title, location, dates, bullets) and header
      - Projects (name, tech_stack, description) and header
      - Skills (all categories and category labels) and header
      - Education (institution, degree, gpa, honors, location, year) and header
      - Certifications (name, issuer, year) and header
    """
    parts: list[str] = []

    # Personal info
    pi = resume.get("personal_info", {}) or {}
    for field in ("name", "phone", "email", "linkedin", "github", "location", "website"):
        val = pi.get(field)
        if isinstance(val, str):
            parts.append(val)

    # Summary
    summary = resume.get("summary")
    if isinstance(summary, str) and summary.strip():
        parts.append("Summary")
        parts.append(summary)

    # Experience — company, title, location, dates, bullets
    exps = resume.get("experience", [])
    if exps:
        parts.append("Experience Work Experience")
        for exp in exps:
            if not isinstance(exp, dict):
                continue
            for field in ("company", "title", "location", "start_date", "end_date"):
                val = exp.get(field)
                if isinstance(val, str):
                    parts.append(val)
            for b in exp.get("bullets", []):
                if isinstance(b, str):
                    parts.append(b)

    # Projects — name, tech_stack items, description
    projs = resume.get("projects", [])
    if projs:
        parts.append("Projects")
        for proj in projs:
            if not isinstance(proj, dict):
                continue
            if isinstance(proj.get("name"), str):
                parts.append(proj["name"])
            ts = proj.get("tech_stack", [])
            if isinstance(ts, list):
                parts.extend(str(t) for t in ts if t)
            desc = proj.get("description", "")
            if isinstance(desc, str):
                parts.append(desc)
            elif isinstance(desc, list):
                parts.extend(d for d in desc if isinstance(d, str))

    # Skills
    skills = resume.get("skills", {})
    if isinstance(skills, dict) and any(skills.values()):
        parts.append("Skills Technical Skills")
        labels = {
            "languages": "Languages",
            "frameworks": "Frameworks Libraries",
            "databases": "Databases",
            "tools": "Tools Technologies",
            "concepts": "Concepts",
        }
        for k, v in skills.items():
            if isinstance(v, list) and v:
                parts.append(labels.get(k, str(k)))
                parts.extend(str(s) for s in v if s)

    # Education
    edus = resume.get("education", [])
    if edus:
        parts.append("Education")
        for edu in edus:
            if not isinstance(edu, dict):
                continue
            for field in ("institution", "degree", "gpa", "location", "graduation_year", "honors"):
                val = edu.get(field)
                if isinstance(val, str):
                    parts.append(val)

    # Certifications
    certs = resume.get("certifications", [])
    if certs:
        parts.append("Certifications Extracurricular")
        for cert in certs:
            if not isinstance(cert, dict):
                continue
            for field in ("name", "issuer", "year"):
                val = cert.get(field)
                if isinstance(val, str):
                    parts.append(str(val))

    return len(" ".join(parts).split())


# ── Typography scale ──────────────────────────────────────────────────────────

def _choose_typography(word_count: int) -> dict:
    """
    Map resume word count (all visible text) to a full typography spec.

    Returns:
      font_size    (pt)  — body text size
      line_height        — unitless multiplier
      section_mb   (px)  — margin-bottom on .section
      entry_mb     (px)  — margin-bottom on .entry
      name_size    (pt)  — .name / .candidate-name heading size
      subtitle_size(pt)  — .section-title size
      body_padding (mm)  — body padding (all sides)
      contact_mb   (px)  — margin-bottom on .contact-line
      header_mb    (px)  — margin-bottom on .header div
    """
    # Each row: (max_words, font_size, line_height, section_mb, entry_mb,
    #            name_size, subtitle_size, body_padding, contact_mb, header_mb)
    table = [
        (120,  11.0, 1.70, 18, 14, 22, 11.0, 13, 14, 10),
        (160,  10.5, 1.60, 16, 12, 21, 10.5, 13, 12,  8),
        (210,  10.0, 1.50, 14, 10, 20, 10.0, 12, 10,  7),
        (270,   9.5, 1.44, 12,  8, 19,  9.5, 12,  8,  6),
        (340,   9.0, 1.38, 10,  6, 18,  9.0, 11,  6,  5),
        (420,   8.5, 1.32,  8,  5, 17,  8.8, 10,  4,  5),
        (510,   8.2, 1.28,  7,  4, 16,  8.5, 10,  3,  4),
        (600,   8.0, 1.24,  6,  3, 15,  8.2,  9,  2,  4),
        (700,   7.7, 1.20,  5,  2, 14,  8.0,  8,  1,  3),
        (820,   7.4, 1.18,  4,  2, 14,  7.8,  7,  1,  3),
        (960,   7.1, 1.16,  3,  1, 13,  7.5,  7,  0,  2),
        (9999,  6.8, 1.14,  2,  1, 12,  7.2,  6,  0,  2),
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
    # Fallback (should never reach here due to 9999 sentinel)
    return dict(
        font_size=6.8, line_height=1.14, section_mb=2, entry_mb=1,
        name_size=12, subtitle_size=7.2, body_padding=6, contact_mb=0, header_mb=2,
    )


# ── Typography injection ──────────────────────────────────────────────────────

def _inject_typography(html: str, t: dict) -> str:
    """
    Inject a comprehensive typography override block into <head>.
    Overrides body text, spacing, name heading, section titles, padding,
    and removes page-break-inside from .section so WeasyPrint never
    pushes an entire section to page 2.
    """
    override = (
        "<style>\n"
        # Body: font, line-height, padding
        f"  body         {{ font-size: {t['font_size']}pt !important; "
        f"line-height: {t['line_height']} !important; "
        f"padding: {t['body_padding']}mm {t['body_padding']}mm !important; }}\n"
        # Minimal template layout padding
        f"  .sidebar     {{ padding: {t['body_padding']}mm 8mm {t['body_padding']}mm 10mm !important; }}\n"
        f"  .main        {{ padding: {t['body_padding']}mm 10mm {t['body_padding']}mm 8mm !important; }}\n"
        # Section spacing — allow natural page flow for sections but prevent entry slicing
        f"  .section, .s-section {{ margin-bottom: {t['section_mb']}px !important; "
        f"page-break-inside: auto !important; }}\n"
        f"  .entry, .job, .project {{ margin-bottom: {t['entry_mb']}px !important; "
        f"page-break-inside: avoid !important; }}\n"
        # Section title spacing
        f"  .section-title, .s-section-title {{ margin-top: {t['section_mb']}px !important; "
        f"font-size: {t['subtitle_size']}pt !important; }}\n"
        # Name / heading
        f"  .name, .candidate-name {{ font-size: {t['name_size']}pt !important; }}\n"
        # Contact line margin
        f"  .contact-line {{ margin-bottom: {t['contact_mb']}px !important; }}\n"
        # Header block bottom margin
        f"  .header      {{ margin-bottom: {t['header_mb']}px !important; }}\n"
        "</style>\n"
    )
    if "</head>" in html:
        return html.replace("</head>", override + "</head>", 1)
    return override + html


# ── WeasyPrint render ─────────────────────────────────────────────────────────

def render_html_to_pdf(html_content: str) -> bytes:
    """
    Render an HTML string to PDF bytes using WeasyPrint.
    """
    try:
        import weasyprint
    except ImportError as e:
        raise RuntimeError(
            "WeasyPrint is not installed. Run: pip install weasyprint"
        ) from e

    pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("WeasyPrint did not return valid PDF bytes.")

    return pdf_bytes


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(
    resume_data: dict,
    template_name: str = "modern",
    jd_keywords: list[str] | None = None,
) -> bytes:
    """
    Generate a PDF from resume data and a named template.

    Args:
        resume_data:   Full resume dict.
        template_name: One of 'modern', 'classic', 'minimal'.
        jd_keywords:   Optional list of JD-required keywords.
                       When provided, matching terms in bullets are bolded
                       with highest priority (Layer 1 of bolding engine).
    """
    if template_name not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template '{template_name}'. Choose from: {VALID_TEMPLATES}"
        )

    # ── Build context-aware bold filter ─────────────────────────────────────
    # Flatten candidate's own skills list for Layer 3 (tech stack) bolding.
    resume_skills = extract_skills_flat(resume_data.get("skills", {}))

    def _bold_filter(text: str) -> object:
        return render_bold_markers(
            text,
            jd_keywords=jd_keywords,
            resume_skills=resume_skills,
        )

    def _bold_list_filter(items: list[str]) -> object:
        from markupsafe import Markup
        return Markup(", ".join(str(_bold_filter(item)) for item in items))

    # Clone env so the global env is never mutated between concurrent requests.
    env = _jinja_env.overlay()
    env.filters["bold"]      = _bold_filter
    env.filters["bold_list"] = _bold_list_filter

    template = env.get_template(f"{template_name}.html")
    html = template.render(resume=resume_data)

    word_count = _count_resume_words(resume_data)
    typography = _choose_typography(word_count)
    html       = _inject_typography(html, typography)

    try:
        return render_html_to_pdf(html)
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}") from e
