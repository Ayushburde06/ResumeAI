import re


def to_href(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if re.match(r"^(mailto:|tel:|https?://)", value, re.I):
        return value
    return f"https://{value.lstrip('/')}"


def link_label(raw: str, kind: str | None = None) -> str:
    if kind == "github":
        return "GitHub"
    if kind == "linkedin":
        return "LinkedIn"
    if kind == "website":
        return "Website"

    lower = (raw or "").lower()
    if "github.com" in lower:
        return "GitHub"
    if "linkedin.com" in lower:
        return "LinkedIn"
    if "gitlab.com" in lower:
        return "GitLab"
    return "Link"
