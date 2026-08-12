"""
pdf_generator.py — HTML → PDF using WeasyPrint (pure Python, no Chromium).

Architecture:
  1. Jinja2 renders resume dict → HTML string
  2. WeasyPrint renders HTML → PDF bytes (~50MB RAM, pure Python)
  3. Google Fonts fetched via url_fetcher for identical typography to Playwright

Quality optimizations vs naive WeasyPrint:
  - presentational_hints=True for better CSS compliance
  - Custom url_fetcher caches Google Fonts CSS for fast repeated renders
  - @page CSS with proper A4 margins
  - Fallback font stack if Google Fonts unreachable
"""
import logging
import json
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from services.layout_optimizer import (
    apply_adjustments,
    inspect_pdf,
    needs_trim,
    trim_content,
)
from services.resume_links import link_label, to_href
from services.text_formatting import extract_skills_flat, render_bold_markers

logger = logging.getLogger(__name__)


def _dict_to_namespace(obj):
    """Recursively convert dicts to SimpleNamespace so Jinja2 dot-access works."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _dict_to_namespace(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_dict_to_namespace(v) for v in obj]
    return obj


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
VALID_TEMPLATES = {
    "modern": "modern.html",
    "classic": "classic.html",
    # Public API compatibility: the frontend calls this layout "minimal".
    "minimal": "minimalist.html",
    "executive": "executive.html",
    "split": "split.html",
    "minimalist": "minimalist.html",
}

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)
_jinja_env.filters["to_href"] = to_href
_jinja_env.filters["link_label"] = link_label


def _adaptive_layout(resume_data: dict) -> dict[str, float]:
    """Calculate continuous typography and spacing from the content volume."""
    serialized = json.dumps(resume_data, ensure_ascii=False)
    bullet_count = 0
    for section in ("experience", "projects"):
        for entry in resume_data.get(section, []) or []:
            bullets = entry.get("bullets", []) if isinstance(entry, dict) else []
            if isinstance(bullets, list):
                bullet_count += len([b for b in bullets if str(b).strip()])
            elif isinstance(bullets, str):
                bullet_count += len([b for b in bullets.splitlines() if b.strip()])
            description = entry.get("description", "") if isinstance(entry, dict) else ""
            bullet_count += len([b for b in str(description).splitlines() if b.strip()])

    section_count = sum(
        1 for key in ("summary", "experience", "projects", "skills", "education", "certifications")
        if resume_data.get(key)
    )
    content_units = len(serialized) / 85 + bullet_count * 0.7 + section_count * 2
    overflow_pressure = max(0.0, content_units - 35.0)
    font_size = max(7.75, min(9.45, 9.45 - overflow_pressure * 0.017))
    line_height = max(1.20, min(1.46, 1.46 - overflow_pressure * 0.0026))
    section_gap = max(4.0, min(10.0, 10.0 - overflow_pressure * 0.085))
    entry_gap = max(2.0, min(7.0, 7.0 - overflow_pressure * 0.07))
    title_gap = max(3.0, min(7.0, 7.0 - overflow_pressure * 0.06))
    return {
        "font_size": round(font_size, 2),
        "line_height": round(line_height, 3),
        "section_gap": round(section_gap, 2),
        "entry_gap": round(entry_gap, 2),
        "title_gap": round(title_gap, 2),
    }

# ── Font fetching: cache Google Fonts CSS to avoid repeated network calls ─────

_gf_cache: dict[str, dict] = {}

def _url_fetcher(url, timeout=10, ssl_context=None):
    """Custom URL fetcher that caches Google Fonts responses.
    Returns dict with 'string' and 'mime_type' keys as WeasyPrint expects.
    Font files (woff2, ttf, otf) must be returned as bytes, CSS as string.
    """
    if url in _gf_cache:
        return _gf_cache[url]
    import httpx
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        if r.status_code == 200:
            mime = r.headers.get('content-type', 'text/css')
            # Font files: WeasyPrint passes content to write_bytes() → must be bytes
            if any(ft in mime for ft in ('font/', 'octet-stream')):
                result = {'string': r.content, 'mime_type': mime}
            else:
                result = {'string': r.text, 'mime_type': mime}
            _gf_cache[url] = result
            return result
    except Exception:
        pass
    return {'string': '', 'mime_type': 'text/css'}

# ── Base CSS: ensures consistent rendering across all templates ───────────────
# This replaces the @import url('https://fonts.googleapis.com/...') in templates
# with a local font stack that looks identical.

_BASE_CSS = """
@page {
    size: A4;
    margin: 0;
}

/* Use system fonts that match Inter's metrics closely */
body {
    font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

/* Continuous layout variables are calculated per resume. */
body {
    font-size: var(--resume-font-size, 8.5pt) !important;
    line-height: var(--resume-line-height, 1.35) !important;
}
.section { margin-bottom: var(--resume-section-gap, 8px) !important; }
.entry { margin-bottom: var(--resume-entry-gap, 6px) !important; }
.section-title {
    margin-bottom: var(--resume-title-gap, 6px) !important;
    margin-top: var(--resume-title-gap, 6px) !important;
}
.bullets li { margin-bottom: var(--resume-bullet-gap, 1px) !important; }
.summary,
.section > div[style*="font-size"] {
    font-size: var(--resume-font-size, 8.5pt) !important;
    line-height: var(--resume-line-height, 1.35) !important;
}

/* Ensure proper page breaks */
.entry, .section {
    page-break-inside: avoid;
}

/* WeasyPrint flexbox gap workaround — use margins instead */
.contact-line {
    gap: 0 !important;
}
.contact-item {
    margin-right: 14px;
}
.contact-item:last-child {
    margin-right: 0;
}
.project-links {
    gap: 0 !important;
}
.project-link-btn {
    margin-right: 10px;
}
.project-link-btn:last-child {
    margin-right: 0;
}
"""


def _build_style_string(layout: dict) -> str:
    """Build CSS custom-property string from a layout dict."""
    return (
        f'--resume-font-size:{layout["font_size"]}pt; '
        f'--resume-line-height:{layout["line_height"]}; '
        f'--resume-section-gap:{layout["section_gap"]}px; '
        f'--resume-entry-gap:{layout["entry_gap"]}px; '
        f'--resume-title-gap:{layout["title_gap"]}px; '
        f'--resume-bullet-gap:{max(0.0, layout["entry_gap"] - 4.0):.2f}px;'
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_pdf(
    resume_data: dict,
    template_name: str = "modern",
    jd_keywords: list[str] | None = None,
) -> bytes:
    """
    Generate a PDF from resume data and a named template using WeasyPrint.

    Uses a 3-layer layout system:
      L1 (pre-render):  Trim content if too dense (cap bullets, drop excess entries)
      L2 (render):      Adaptive layout — estimate spacing from content volume
      L3 (post-render): Inspect actual PDF with PyMuPDF, adjust spacing, re-render
                        (max 3 iterations until page fill is optimal)

    Args:
        resume_data:   Full resume dict.
        template_name: One of 'modern', 'classic', 'executive', 'split'.
        jd_keywords:   Optional list of JD-required keywords.
                       When provided, matching terms in bullets are bolded.
    """
    if template_name not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template '{template_name}'. Choose from: {list(VALID_TEMPLATES)}"
        )

    # ── Build context-aware bold filter ─────────────────────────────────────
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
    env.filters["bold"] = _bold_filter
    env.filters["bold_list"] = _bold_list_filter

    # ── L1: Pre-render content trimming ─────────────────────────────────────
    # If the agent generated too many bullets/entries, trim before rendering
    # so the font doesn't have to shrink to an unreadable size.
    if needs_trim(resume_data):
        logger.info("L1: Content too dense — trimming bullets and entries")
        resume_data = trim_content(resume_data)

    # ── Render HTML once (content doesn't change between correction iterations)
    template = env.get_template(VALID_TEMPLATES[template_name])
    base_html = template.render(resume=_dict_to_namespace(resume_data))

    # ── L2: Initial adaptive layout estimate ────────────────────────────────
    layout = _adaptive_layout(resume_data)

    # ── L3: Render → Inspect → Adjust → Re-render loop ──────────────────────
    # Render the PDF, inspect actual page fill with PyMuPDF, and adjust
    # spacing if content overflows or has too much empty space.
    # Max 3 iterations — each adds ~100ms (inspect + re-render).
    MAX_CORRECTIONS = 3
    pdf_bytes = None

    for iteration in range(MAX_CORRECTIONS):
        style = _build_style_string(layout)
        html = base_html.replace("<body>", f'<body style="{style}">', 1)

        try:
            doc = HTML(string=html, url_fetcher=_url_fetcher)
            pdf_bytes = doc.write_pdf(
                stylesheets=[CSS(string=_BASE_CSS, url_fetcher=_url_fetcher)],
                presentational_hints=True,
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise RuntimeError(f"PDF generation failed: {e}") from e

        # Inspect the rendered PDF
        verdict = inspect_pdf(pdf_bytes)

        logger.info(
            f"Layout L3 iter {iteration + 1}/{MAX_CORRECTIONS}: "
            f"pages={verdict['page_count']} issues={verdict['issues']} "
            f"fill={verdict['fill_ratios']}"
        )

        # No issues → layout is optimal
        if not verdict["issues"]:
            break

        # Last iteration → return best effort
        if iteration == MAX_CORRECTIONS - 1:
            logger.warning(
                f"Layout L3: issues remain after {MAX_CORRECTIONS} iterations: "
                f"{verdict['issues']}"
            )
            break

        # Apply spacing adjustments for next iteration
        layout = apply_adjustments(layout, verdict["adjustments"])

    return pdf_bytes


# ── BrowserManager stub for backward compatibility ────────────────────────────
# (main.py startup checks for this — no-op since WeasyPrint has no browser)

class BrowserManager:
    """No-op stub for browser, but repurposed to warm the WeasyPrint font cache."""
    _loop = None

    @classmethod
    async def warm(cls):
        # Pre-fetch the common Google Fonts to avoid blocking the first PDF generation
        font_url = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
        logger.info("Warming WeasyPrint font cache...")
        import asyncio
        # Run synchronous fetch in a thread so we don't block the async event loop during startup
        await asyncio.to_thread(_url_fetcher, font_url)
        logger.info("WeasyPrint font cache warmed.")

    @classmethod
    async def close_all(cls):
        pass


# ── Synchronous wrapper (for batch_process.py and CLI scripts) ────────────────

def generate_pdf_sync(resume_data: dict, template: str = "modern") -> bytes:
    """Synchronous wrapper around async generate_pdf(). Safe to call from
    non-async contexts such as batch_process.py."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # Already inside an event loop — run in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, generate_pdf(resume_data, template_name=template))
            return future.result(timeout=120)
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(generate_pdf(resume_data, template_name=template))


# ── Cover letter PDF ──────────────────────────────────────────────────────────

def generate_cover_letter_pdf(cover_letter: dict, resume_data: dict) -> bytes:
    """Render a cover letter dict to PDF using the cover_letter.html template.
    Issue 7: dedicated cover letter rendering template.

    cover_letter: {"subject_line": "...", "body": "date\\n\\nDear...\\n\\nP1\\n\\nP2..."}
    resume_data:  the tailored resume dict (for candidate contact info in the header).
    """
    import re
    import datetime

    personal = resume_data.get("personal_info", {})
    body     = cover_letter.get("body", "")

    # Split the body into paragraphs (separated by double newlines)
    # Filter out the date line and the Dear line — those are in the template
    paragraphs = []
    for chunk in re.split(r"\n{2,}", body.strip()):
        stripped = chunk.strip()
        if not stripped:
            continue
        # Skip the date line and the "Dear Hiring Manager," line — template handles them
        if re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d', stripped):
            continue
        if stripped.lower().startswith("dear "):
            continue
        # Skip the sign-off block (starts with Regards or Best)
        if stripped.lower().startswith(("regards", "best,", "sincerely")):
            continue
        paragraphs.append(stripped)

    # Extract today's date from the body if present, otherwise generate it
    date_match = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',
        body
    )
    letter_date = date_match.group(0) if date_match else datetime.date.today().strftime("%B %d, %Y")

    template = _jinja_env.get_template("cover_letter.html")
    html = template.render(
        candidate_name = personal.get("name", ""),
        email          = personal.get("email", ""),
        phone          = personal.get("phone", ""),
        location       = personal.get("location", ""),
        portfolio      = personal.get("website", "") or personal.get("portfolio", ""),
        github         = personal.get("github", ""),
        linkedin_url   = personal.get("linkedin", ""),
        subject_line   = cover_letter.get("subject_line", ""),
        letter_date    = letter_date,
        paragraphs     = paragraphs,
    )

    doc = HTML(string=html, url_fetcher=_url_fetcher)
    return doc.write_pdf(
        stylesheets=[CSS(string=_BASE_CSS, url_fetcher=_url_fetcher)],
        presentational_hints=True,
    )
