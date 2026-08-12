"""
latex_generator.py  – LaTeX Resume Generator Engine

This module uses Jinja2 to render LaTeX templates (.tex.jinja) and provides
custom LaTeX-specific escaping and formatting filters.
"""

import asyncio
import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader


def _dict_to_namespace(obj):
    """Recursively convert dicts to SimpleNamespace so Jinja2 dot-access works."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _dict_to_namespace(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_dict_to_namespace(v) for v in obj]
    return obj

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# ─────────────────────────────────────────────────────────────────────────────
#  Character-level LaTeX escaping
# ─────────────────────────────────────────────────────────────────────────────

_ESCAPE_MAP: dict[str, str] = {
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
    "<":  r"\textless{}",
    ">":  r"\textgreater{}",
    "\u2013": "--",             # en-dash
    "\u2014": "---",            # em-dash
    "\u2022": r"\textbullet{}",
    "\u2018": "`",              # left single quote
    "\u2019": "'",              # right single quote
    "\u201c": "``",             # left double quote
    "\u201d": "''",             # right double quote
    "\u00a0": "~",              # non-breaking space
    "\u2026": r"\ldots{}",      # ellipsis
    "\u00b7": r"\textperiodcentered{}",
    "\u00e9": r"\'{e}",
    "\u00e8": r"\`{e}",
    "\u00e0": r"\`{a}",
    "\u00fc": r'\"{u}',
    "\u00f6": r'\"{o}',
    "\u00e4": r'\"{a}',
}

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)

def tex_escape(text: object) -> str:
    """Escape arbitrary text for safe LaTeX body inclusion."""
    if text is None:
        return ""
    out: list[str] = []
    for ch in str(text):
        out.append(_ESCAPE_MAP.get(ch, ch))
    return "".join(out)

def _e_url(url: str) -> str:
    r"""Escape a URL for use inside \href{}. Underscores must NOT be escaped."""
    return (url or "").replace("%", r"\%")

def tex_bold(text: object) -> str:
    """Convert **phrase** → \textbf{phrase}, escaping all other chars."""
    if text is None:
        return ""
    parts = _BOLD_RE.split(str(text))
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(tex_escape(part))
        else:
            out.append(r"\textbf{" + tex_escape(part) + "}")
    return "".join(out)

def tex_bold_list(items: list[str]) -> str:
    if not items:
        return ""
    return ", ".join(tex_bold(item) for item in items if item)

def tex_myuline_href(url: str, label: str) -> str:
    r"""Produce \href{url}{\myuline{label}}"""
    return rf"\href{{{_e_url(url)}}}{{\myuline{{{tex_escape(label)}}}}}"

def tex_shorten(url: str, maxlen: int = 32) -> str:
    """Human-readable URL label."""
    if not url: return ""
    label = (url
             .replace("https://", "")
             .replace("http://", "")
             .replace("www.", "")
             .rstrip("/"))
    return label[:maxlen] + ("…" if len(label) > maxlen else "")

def tex_split_sentences(text: str) -> list[str]:
    """Split a description paragraph into bullet lines."""
    if not text or not text.strip(): return []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) <= 1 and ". " in text:
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return lines

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False, # LaTeX doesn't use HTML escaping
    trim_blocks=True,
    lstrip_blocks=True,
    block_start_string='<BLOCK>',
    block_end_string='</BLOCK>',
    variable_start_string='<<',
    variable_end_string='>>',
    comment_start_string='<#',
    comment_end_string='#>',
)

_jinja_env.filters["tex_escape"] = tex_escape
_jinja_env.filters["tex_bold"] = tex_bold
_jinja_env.filters["tex_bold_list"] = tex_bold_list
_jinja_env.filters["tex_myuline_href"] = tex_myuline_href
_jinja_env.filters["tex_shorten"] = tex_shorten
_jinja_env.filters["tex_split_sentences"] = tex_split_sentences


def generate_latex(resume_data: dict, template_name: str = "harshibar") -> str:
    """
    Generate LaTeX source code from a .tex.jinja template.
    """
    template = _jinja_env.get_template(f"{template_name}.tex.jinja")
    # LaTeX template expects data in `resume` variable
    return template.render(resume=_dict_to_namespace(resume_data))

async def generate_pdf_from_latex(resume_data: dict, template_name: str = "harshibar") -> bytes:
    """
    Compile LaTeX to PDF using pdflatex. Requires pdflatex to be installed on the server.
    """
    tex_source = generate_latex(resume_data, template_name)
    
    # Create a temporary directory to compile the latex file
    with tempfile.TemporaryDirectory() as temp_dir:
        tex_path = os.path.join(temp_dir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_source)
            
        try:
            def _run_latexmk():
                return subprocess.run(
                    ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            process = await asyncio.to_thread(_run_latexmk)
            
            if process.returncode != 0:
                import logging
                logging.error(f"latexmk compilation failed:\n{process.stdout.decode(errors='ignore')}")
                raise RuntimeError("latexmk compilation failed. Check logs for details.")
                
            pdf_path = os.path.join(temp_dir, "resume.pdf")
            with open(pdf_path, "rb") as f:
                return f.read()
                
        except FileNotFoundError:
            raise RuntimeError("latex_runtime_missing")
