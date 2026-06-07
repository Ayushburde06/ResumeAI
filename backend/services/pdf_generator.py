import shutil
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from services.resume_links import link_label, to_href
from services.text_formatting import bold_list, render_bold_markers

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
PUPPETEER_RENDERER = Path(__file__).with_name("render_pdf.cjs")

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)
_jinja_env.filters["to_href"] = to_href
_jinja_env.filters["link_label"] = link_label
_jinja_env.filters["bold"] = render_bold_markers
_jinja_env.filters["bold_list"] = bold_list

VALID_TEMPLATES = {"modern", "classic", "minimal"}


def _render_with_puppeteer(html_content: str) -> bytes:
    node_path = shutil.which("node")
    if not node_path:
        raise RuntimeError("Node.js is required for Puppeteer PDF generation.")

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
        raise RuntimeError("Puppeteer PDF generation timed out.") from e

    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "Puppeteer PDF generation failed.")

    if not result.stdout.startswith(b"%PDF"):
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "Puppeteer did not return a valid PDF.")

    return result.stdout




def generate_pdf(resume_data: dict, template_name: str = "modern") -> bytes:
    if template_name not in VALID_TEMPLATES:
        raise ValueError(f"Unknown template '{template_name}'. Choose from: {VALID_TEMPLATES}")

    template = _jinja_env.get_template(f"{template_name}.html")
    html_content = template.render(resume=resume_data)

    try:
        return _render_with_puppeteer(html_content)
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}")
