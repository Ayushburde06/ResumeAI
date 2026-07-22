import re
from markupsafe import Markup, escape

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")

# ── Action verbs — NEVER bold these ──────────────────────────────────────────
# Bolding action verbs reduces their visual weight and clutters the bullet.
_ACTION_VERBS = frozenset({
    "built", "designed", "developed", "created", "implemented", "optimized",
    "integrated", "automated", "reduced", "improved", "delivered", "engineered",
    "refactored", "deployed", "led", "managed", "wrote", "configured",
    "architected", "migrated", "containerized", "maintained", "debugged",
    "tested", "reviewed", "launched", "shipped", "published",
})

# ── Quantifiable impact metrics ────────────────────────────────────────────────
# Matches values like: 45%, $500K, 10M+, 2.5x, 99.9% uptime, 200ms latency
_METRIC_PATTERN = re.compile(
    r"\b(\$?\d+(?:\.\d+)?(?:%|k|M|B|x|\+)?"
    r"(?:\s*(?:users|events|requests|ms|seconds|minutes|hours|days|percent"
    r"|latency\s+reduction|uptime|downloads|revenue|queries|rps|QPS"
    r"|API\s+calls?|page\s+views?|transactions?|deployments?|LOC|lines?))?)\b",
    re.IGNORECASE,
)

# ── Static core tech keywords (fallback when no JD/skills provided) ───────────
_CORE_TECH_PATTERN = re.compile(
    r"\b(Python|FastAPI|React|Next\.js|Node\.js|TypeScript|JavaScript|"
    r"PostgreSQL|Redis|Docker|Kubernetes|AWS|GCP|Azure|Microservices|"
    r"RESTful\s+APIs?|REST\s+APIs?|GraphQL|CI/CD|Django|Flask|Spring\s+Boot|"
    r"Java|Go|Golang|Rust|C\+\+|PyTorch|TensorFlow|MongoDB|Kafka|"
    r"Elasticsearch|TailwindCSS|Redux|SQL|NoSQL|gRPC|Celery|Nginx|"
    r"Terraform|Ansible|Prometheus|Grafana|OpenAI|LangChain|Pinecone|"
    r"Supabase|Firebase|Vercel|HuggingFace|scikit-learn|Pandas|NumPy)\b",
    re.IGNORECASE,
)

# ── Max bold clamp ────────────────────────────────────────────────────────────
_MAX_BOLDS_PER_BULLET = 3


def _count_bold_groups(text: str) -> int:
    """Count how many **...** groups already exist in text."""
    return len(_BOLD_PATTERN.findall(text))


def _is_action_verb(token: str) -> bool:
    return token.strip().lower().rstrip(".,;:") in _ACTION_VERBS


def _safe_sub(pattern: re.Pattern, text: str, current_count: int) -> tuple[str, int]:
    """
    Apply regex bold substitution but stop once _MAX_BOLDS_PER_BULLET is reached.
    Returns (new_text, updated_count).
    """
    result_parts = []
    last = 0
    for m in pattern.finditer(text):
        if current_count >= _MAX_BOLDS_PER_BULLET:
            break
        term = m.group(0)
        # Skip if already inside bold markers
        before = text[:m.start()]
        if before.count("**") % 2 == 1:
            continue
        # Skip action verbs
        if _is_action_verb(term):
            continue
        result_parts.append(text[last:m.start()])
        result_parts.append(f"**{term}**")
        last = m.end()
        current_count += 1
    result_parts.append(text[last:])
    return "".join(result_parts), current_count


def _build_jd_pattern(jd_keywords: list[str]) -> re.Pattern | None:
    """Build a regex pattern from job description keywords, sorted longest-first to avoid partial matches."""
    if not jd_keywords:
        return None
    escaped = sorted(
        [re.escape(k.strip()) for k in jd_keywords if k.strip()],
        key=len,
        reverse=True,
    )
    if not escaped:
        return None
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def _build_skills_pattern(resume_skills: list[str]) -> re.Pattern | None:
    """Build a regex pattern from the candidate's own tech skill list."""
    if not resume_skills:
        return None
    escaped = sorted(
        [re.escape(s.strip()) for s in resume_skills if s.strip() and len(s.strip()) > 1],
        key=len,
        reverse=True,
    )
    if not escaped:
        return None
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def auto_bold_high_impact_keywords(
    text: str,
    jd_keywords: list[str] | None = None,
    resume_skills: list[str] | None = None,
) -> str:
    """
    Intelligently bold high-impact keywords inside a resume bullet.

    Priority order (per AGENTS.md Bullet Keyword Bolding Standard):
      1. JD-required keywords  (if jd_keywords provided)
      2. Quantifiable metrics  (%, $, M+, x, uptime, etc.)
      3. Core tech stack       (jd resume_skills > static core tech list)

    Hard limits:
      - Max 3 bold groups per bullet.
      - Never bold action verbs.
      - Preserve existing **markers** — text already containing ** is returned unchanged.
    """
    if not text:
        return text

    # If the AI already placed explicit bold markers, respect them entirely.
    if "**" in text:
        return text

    bold_count = 0

    # ── Layer 1: JD-required keywords (highest priority) ──────────────────────
    if jd_keywords:
        jd_pattern = _build_jd_pattern(jd_keywords)
        if jd_pattern:
            text, bold_count = _safe_sub(jd_pattern, text, bold_count)

    if bold_count >= _MAX_BOLDS_PER_BULLET:
        return text

    # ── Layer 2: Quantifiable metrics ─────────────────────────────────────────
    def _bold_metric(m: re.Match) -> str:
        nonlocal bold_count
        val = m.group(1)
        # Skip standalone small numbers or 4-digit years
        if val.isdigit() and (len(val) == 4 or int(val) < 10):
            return val
        if bold_count >= _MAX_BOLDS_PER_BULLET:
            return val
        bold_count += 1
        return f"**{val}**"

    # Only apply to non-already-bolded segments
    segments = _BOLD_PATTERN.split(text)
    rebuilt = []
    for i, seg in enumerate(segments):
        if i % 2 == 0:
            rebuilt.append(_METRIC_PATTERN.sub(_bold_metric, seg))
        else:
            rebuilt.append(f"**{seg}**")
    text = "".join(rebuilt)

    if bold_count >= _MAX_BOLDS_PER_BULLET:
        return text

    # ── Layer 3: Core tech stack ───────────────────────────────────────────────
    # Prefer candidate's own skill list over static keyword list
    tech_pattern = (
        _build_skills_pattern(resume_skills) if resume_skills else _CORE_TECH_PATTERN
    )
    if tech_pattern:
        text, bold_count = _safe_sub(tech_pattern, text, bold_count)

    return text


def render_bold_markers(
    text: str,
    jd_keywords: list[str] | None = None,
    resume_skills: list[str] | None = None,
) -> Markup:
    """
    Convert **term** markers to <strong> for PDF/HTML rendering.
    Runs auto_bold_high_impact_keywords first if no existing markers found.
    """
    if not text:
        return Markup("")

    processed = auto_bold_high_impact_keywords(
        str(text),
        jd_keywords=jd_keywords,
        resume_skills=resume_skills,
    )

    parts = _BOLD_PATTERN.split(processed)
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


def extract_skills_flat(skills_dict: dict) -> list[str]:
    """
    Flatten the nested skills dict (e.g. {Languages: [...], Frontend: [...]})
    into a single list of skill strings for use as resume_skills in bolding.
    """
    if not skills_dict or not isinstance(skills_dict, dict):
        return []
    flat: list[str] = []
    for category_items in skills_dict.values():
        if isinstance(category_items, list):
            flat.extend(str(s) for s in category_items if s)
    return flat
