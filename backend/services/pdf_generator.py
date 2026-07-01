"""
pdf_generator.py — HTML → PDF using Playwright (pure Python, no GTK/Cairo needed).

Architecture:
  1. Jinja2 renders resume dict → HTML string
  2. Content word count determines base font size (one-time, no re-render loop)
  3. Font-size override injected into <head>
  4. Playwright runs in a ThreadPoolExecutor thread (required because FastAPI is
     async and Playwright sync API cannot be called inside an asyncio event loop)
  5. Single Chromium render → PDF bytes

No Node subprocess. No persistent server. No GTK runtime. No re-render loop.
"""

import concurrent.futures
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from services.resume_links import link_label, to_href
from services.text_formatting import bold_list, render_bold_markers

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
VALID_TEMPLATES = {"modern", "classic", "minimal"}

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)
_jinja_env.filters["to_href"]    = to_href
_jinja_env.filters["link_label"] = link_label
_jinja_env.filters["bold"]       = render_bold_markers
_jinja_env.filters["bold_list"]  = bold_list


# ── Content density → font size ───────────────────────────────────────────────

def _count_resume_words(resume: dict) -> int:
    parts: list[str] = []
    if isinstance(resume.get("summary"), str):
        parts.append(resume["summary"])
    for exp in resume.get("experience", []):
        if isinstance(exp, dict):
            for b in exp.get("bullets", []):
                if isinstance(b, str):
                    parts.append(b)
    for proj in resume.get("projects", []):
        if isinstance(proj, dict):
            desc = proj.get("description", "")
            if isinstance(desc, str):
                parts.append(desc)
            elif isinstance(desc, list):
                parts.extend(d for d in desc if isinstance(d, str))
    skills = resume.get("skills", {})
    if isinstance(skills, dict):
        for v in skills.values():
            if isinstance(v, list):
                parts.extend(str(s) for s in v)
    return len(" ".join(parts).split())


def _choose_typography(word_count: int) -> dict:
    """
    Map resume word count to typography settings.
    Two directions:
      - Short resume  (< 300 words): expand font + spacing to fill the page
      - Normal/dense  (>= 300 words): keep compact so everything fits on one page

    Returns a dict with: font_size (pt), line_height, section_mb (px), entry_mb (px)
    """
    if word_count < 100:
        return {"font_size": 11.0, "line_height": 1.70, "section_mb": 18, "entry_mb": 14}
    if word_count < 150:
        return {"font_size": 10.5, "line_height": 1.60, "section_mb": 16, "entry_mb": 12}
    if word_count < 200:
        return {"font_size": 10.0, "line_height": 1.50, "section_mb": 14, "entry_mb": 10}
    if word_count < 260:
        return {"font_size": 9.5,  "line_height": 1.45, "section_mb": 12, "entry_mb": 8}
    if word_count < 320:
        return {"font_size": 9.0,  "line_height": 1.38, "section_mb": 10, "entry_mb": 6}
    if word_count < 400:
        return {"font_size": 8.5,  "line_height": 1.32, "section_mb": 8,  "entry_mb": 5}
    if word_count < 480:
        return {"font_size": 8.2,  "line_height": 1.28, "section_mb": 7,  "entry_mb": 4}
    if word_count < 560:
        return {"font_size": 8.0,  "line_height": 1.25, "section_mb": 6,  "entry_mb": 3}
    return     {"font_size": 7.8,  "line_height": 1.22, "section_mb": 5,  "entry_mb": 2}


def _inject_typography(html: str, t: dict) -> str:
    """Inject a single typography override block into <head>."""
    override = (
        "<style>\n"
        f"  body        {{ font-size: {t['font_size']}pt !important; "
        f"line-height: {t['line_height']} !important; }}\n"
        f"  .section    {{ margin-bottom: {t['section_mb']}px !important; }}\n"
        f"  .entry      {{ margin-bottom: {t['entry_mb']}px !important; }}\n"
        f"  .section-title {{ margin-top: {t['section_mb']}px !important; }}\n"
        "</style>\n"
    )
    if "</head>" in html:
        return html.replace("</head>", override + "</head>", 1)
    return override + html


# ── Playwright render ─────────────────────────────────────────────────────────

async def _async_render(html_content: str) -> bytes:
    """Async Playwright render — called via asyncio.run() in a clean thread."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="domcontentloaded")
            await page.evaluate("() => document.fonts.ready")
            return await page.pdf(
                format="A4",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                print_background=True,
                prefer_css_page_size=True,
            )
        finally:
            await browser.close()


def _run_in_clean_thread(html_content: str) -> bytes:
    """
    Entry point for the ThreadPoolExecutor worker.
    Creates a ProactorEventLoop explicitly — required on Windows because
    SelectorEventLoop does NOT support subprocess creation (NotImplementedError).
    ProactorEventLoop is the only loop that handles subprocesses on Windows.
    """
    import asyncio
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_render(html_content))
    finally:
        loop.close()


def render_html_to_pdf(html_content: str) -> bytes:
    """
    Render an HTML string to PDF bytes using Playwright + Chromium.
    Runs in a dedicated thread with a fresh event loop — required because
    FastAPI's asyncio loop cannot host Playwright's subprocess on Windows.
    """
    try:
        import playwright  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        ) from e

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run_in_clean_thread, html_content)
        pdf_bytes = future.result(timeout=60)

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("Playwright did not return valid PDF bytes.")

    return pdf_bytes


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(resume_data: dict, template_name: str = "modern") -> bytes:
    """
    Generate a PDF from resume data and a named template.
    Signature unchanged — analyze.py calls this directly.
    """
    if template_name not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template '{template_name}'. Choose from: {VALID_TEMPLATES}"
        )

    template = _jinja_env.get_template(f"{template_name}.html")
    html = template.render(resume=resume_data)

    word_count = _count_resume_words(resume_data)
    typography = _choose_typography(word_count)
    html       = _inject_typography(html, typography)

    try:
        return render_html_to_pdf(html)
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}") from e
