import re

from markupsafe import Markup, escape

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def render_bold_markers(text: str) -> Markup:
    """Convert **term** markers to <strong> for PDF rendering."""
    if not text:
        return Markup("")

    parts = _BOLD_PATTERN.split(str(text))
    rendered: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            rendered.append(str(escape(part)))
        else:
            rendered.append(f"<strong>{escape(part)}</strong>")
    return Markup("".join(rendered))


def bold_list(items: list[str]) -> Markup:
    if not items:
        return Markup("")
    return Markup(", ".join(str(render_bold_markers(item)) for item in items))
