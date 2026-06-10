"""
pdf_generator.py — HTML → PDF using a persistent Puppeteer HTTP server.

Architecture:
  FastAPI start-up launches pdf_server.cjs (Node.js) as a background process.
  That process keeps ONE Chromium browser warm for the lifetime of the app.
  Each PDF request is a simple HTTP POST to 127.0.0.1:9009, returning PDF bytes.

Benefits over the old one-shot subprocess approach:
  - No 3–8s browser cold-start per request
  - No subprocess spawn overhead per call
  - If the server isn't available, falls back to the old one-shot subprocess
"""

import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from services.resume_links import link_label, to_href
from services.text_formatting import bold_list, render_bold_markers

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
PUPPETEER_RENDERER  = Path(__file__).with_name("render_pdf.cjs")   # legacy fallback
PUPPETEER_SERVER    = Path(__file__).with_name("pdf_server.cjs")    # persistent server

PDF_SERVER_PORT = int(__import__("os").environ.get("PDF_SERVER_PORT", "9009"))
PDF_SERVER_URL  = f"http://127.0.0.1:{PDF_SERVER_PORT}/"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)
_jinja_env.filters["to_href"]   = to_href
_jinja_env.filters["link_label"] = link_label
_jinja_env.filters["bold"]       = render_bold_markers
_jinja_env.filters["bold_list"]  = bold_list

VALID_TEMPLATES = {"modern", "classic", "minimal"}


# ── Primary path: call the persistent HTTP server ────────────────────────────

def _render_via_server(html_content: str) -> bytes:
    """
    POST the HTML to the warm Puppeteer HTTP server.
    Fast path — no process spawn, browser already warm.
    Raises urllib.error.URLError if the server is unreachable.
    """
    data = html_content.encode("utf-8")
    req  = urllib.request.Request(
        PDF_SERVER_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    # Per-request timeout: 30s is more than enough when browser is already warm
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"PDF server returned HTTP {resp.status}")
        pdf = resp.read()

    if not pdf.startswith(b"%PDF"):
        raise RuntimeError("PDF server did not return valid PDF bytes")

    return pdf


# ── Fallback path: legacy one-shot subprocess ─────────────────────────────────

def _render_via_subprocess(html_content: str) -> bytes:
    """
    Fallback: spawn a fresh Node/Puppeteer process per request.
    Slower (3-8s cold-start) but works even if the server is down.
    """
    node_path = shutil.which("node")
    if not node_path:
        raise RuntimeError("Node.js is required for PDF generation.")

    try:
        result = subprocess.run(
            [node_path, str(PUPPETEER_RENDERER)],
            input=html_content.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Puppeteer PDF generation timed out (fallback subprocess).") from e

    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "Puppeteer PDF generation failed.")

    if not result.stdout.startswith(b"%PDF"):
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "Puppeteer did not return a valid PDF.")

    return result.stdout


# ── Public API ────────────────────────────────────────────────────────────────

def render_html_to_pdf(html_content: str) -> bytes:
    """
    Render HTML to PDF bytes.
    Tries the persistent server first; falls back to subprocess if unavailable.
    """
    try:
        return _render_via_server(html_content)
    except (urllib.error.URLError, ConnectionRefusedError, OSError):
        # Server not running (e.g. local dev without the server started)
        return _render_via_subprocess(html_content)


def generate_pdf(resume_data: dict, template_name: str = "modern") -> bytes:
    if template_name not in VALID_TEMPLATES:
        raise ValueError(
            f"Unknown template '{template_name}'. Choose from: {VALID_TEMPLATES}"
        )

    template     = _jinja_env.get_template(f"{template_name}.html")
    html_content = template.render(resume=resume_data)

    try:
        return render_html_to_pdf(html_content)
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}") from e
