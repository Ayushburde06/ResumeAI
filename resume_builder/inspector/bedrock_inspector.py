"""
bedrock_inspector.py
====================
Visual layout inspector using Qwen3-VL-235B via AWS Bedrock.

Sends rendered resume page images to the vision model and returns a
structured verdict: pass/fail, specific issues, and a recommended
typography fix delta.

Falls back to the legacy Pillow pixel-analysis if Bedrock is unavailable
(no API key, network error, etc.) so the pipeline never fully breaks.
"""

import base64
import json
import os
import sys
from pathlib import Path

# ── Bedrock credentials (loaded from backend/.env or environment) ────────────
def _load_env():
    """Try to load backend/.env so this script works standalone."""
    root = Path(__file__).parent.parent.parent  # project root
    env_path = root / "backend" / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)
        except ImportError:
            pass  # dotenv not installed; rely on system env


_load_env()

_BEDROCK_API_KEY  = os.getenv("QWEN_API_KEY", "")
_BEDROCK_ENDPOINT = os.getenv("QWEN_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1")
_VISION_MODEL     = "qwen.qwen3-vl-235b-a22b-instruct"

# ── Inspector prompt ──────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a professional resume layout QA engineer.
You will be shown rendered pages of an A4/Letter resume as PNG images.
Your job is to detect layout problems that a recruiter would notice.

Respond ONLY with valid JSON matching this exact schema:
{
  "status": "pass" | "fail",
  "page_count": <integer>,
  "issues": [<string>, ...],
  "fix": {
    "font_size_delta":    <float, e.g. -0.25 or +0.25>,
    "line_height_delta":  <float, e.g. -0.04 or +0.04>,
    "section_gap_delta":  <float, e.g. -2.0 or +2.0>,
    "entry_gap_delta":    <float, e.g. -1.0 or +1.0>,
    "bullet_gap_delta":   <float, e.g. -0.5 or +0.5>,
    "reasoning":          <string>
  }
}

If status is "pass", set all deltas to 0 and issues to [].

Issue codes to use (use exact strings):
- "overflow"           : text bleeds into or past the bottom margin on any page
- "sparse_bottom"      : bottom 30%+ of the last/only page is blank white space
- "second_page_sparse" : a second page exists but contains < 3 lines of content
- "orphan_header"      : a section title appears at the very bottom with no content beneath it
- "crowded"            : text looks cramped, lines too close, hard to read
- "truncated_sentence" : a bullet or line appears cut off mid-sentence

Fix rules:
- If overflow: negative deltas (shrink spacing/font)
- If sparse_bottom: positive deltas (expand spacing/font)
- If second_page_sparse: negative deltas (collapse content to one page)
- If crowded: positive line_height_delta only
- Maximum single-step font_size_delta: ±0.5pt
- Maximum single-step section_gap_delta: ±3.0pt
- If no fix is needed (pass): all deltas = 0
"""

_USER_PROMPT = """\
Inspect the attached resume page image(s) for layout issues.
Return your verdict as JSON only — no markdown, no explanation outside the JSON.
"""


# ── Public API ────────────────────────────────────────────────────────────────

def inspect_pages(image_paths: list[Path], verbose: bool = True) -> dict:
    """
    Send rendered page images to Qwen3-VL and return a structured verdict.

    Returns dict with keys:
        status      : "pass" | "fail"
        page_count  : int
        issues      : list[str]
        fix         : dict with delta fields + reasoning
        source      : "vision" | "pixel_fallback"
    """
    if not _BEDROCK_API_KEY:
        if verbose:
            print("    [inspector] No Bedrock API key — using pixel fallback")
        return _pixel_fallback(image_paths)

    try:
        return _call_vision(image_paths, verbose)
    except Exception as exc:
        if verbose:
            print(f"    [inspector] Vision call failed ({exc}) — using pixel fallback")
        return _pixel_fallback(image_paths)


# ── Vision call ───────────────────────────────────────────────────────────────

def _encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_vision(image_paths: list[Path], verbose: bool) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=_BEDROCK_API_KEY, base_url=_BEDROCK_ENDPOINT)

    # Build content blocks — one image per page (up to 3 pages max for cost)
    content = []
    for path in image_paths[:3]:
        b64 = _encode_image(path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    content.append({"type": "text", "text": _USER_PROMPT})

    if verbose:
        print(f"    [inspector] Sending {len(image_paths[:3])} page(s) to {_VISION_MODEL}...")

    response = client.chat.completions.create(
        model=_VISION_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        max_tokens=512,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if model wraps in ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    verdict = json.loads(raw)
    verdict["source"] = "vision"

    if verbose:
        status = verdict.get("status", "?")
        issues = verdict.get("issues", [])
        reason = verdict.get("fix", {}).get("reasoning", "")
        print(f"    [inspector] status={status}  issues={issues}")
        if reason:
            print(f"    [inspector] reasoning: {reason}")

    return verdict


# ── Pixel fallback (original Pillow heuristics) ───────────────────────────────

def _pixel_fallback(image_paths: list[Path]) -> dict:
    """Reproduce the original pixel-brightness logic as a fallback."""
    try:
        from PIL import Image
    except ImportError:
        return _empty_pass(len(image_paths), source="pixel_fallback")

    def fill_ratio(img, region=None):
        if region:
            img = img.crop(region)
        rgb = img.convert("RGB")
        pixels = list(rgb.getdata())
        non_white = sum(1 for r, g, b in pixels if min(r, g, b) < 230)
        return non_white / len(pixels) if pixels else 0.0

    issues = []
    fix = _zero_fix("pixel heuristic fallback")

    img1 = Image.open(image_paths[0])
    w, h = img1.size

    fill_margin = fill_ratio(img1, (0, int(h * 0.93), w, h))
    fill_bottom = fill_ratio(img1, (0, int(h * 0.65), w, h))

    if fill_margin > 0.04:
        issues.append("overflow")
        fix = _fix(-0.25, -0.04, -2.0, -1.0, -0.5, "overflow detected by pixel analysis")

    if len(image_paths) == 1 and fill_bottom < 0.06:
        issues.append("sparse_bottom")
        fix = _fix(+0.25, +0.04, +2.0, +1.0, +0.5, "sparse bottom detected by pixel analysis")

    if len(image_paths) >= 2:
        last_img = Image.open(image_paths[-1])
        if fill_ratio(last_img) < 0.18:
            issues.append("second_page_sparse")
            fix = _fix(-0.25, -0.04, -2.0, -1.0, -0.5, "sparse second page detected by pixel analysis")

    return {
        "status":     "pass" if not issues else "fail",
        "page_count": len(image_paths),
        "issues":     issues,
        "fix":        fix,
        "source":     "pixel_fallback",
    }


# ── Helper constructors ───────────────────────────────────────────────────────

def _zero_fix(reasoning: str = "") -> dict:
    return {
        "font_size_delta":   0.0,
        "line_height_delta": 0.0,
        "section_gap_delta": 0.0,
        "entry_gap_delta":   0.0,
        "bullet_gap_delta":  0.0,
        "reasoning":         reasoning,
    }


def _fix(fs, lh, sg, eg, bg, reasoning) -> dict:
    return {
        "font_size_delta":   fs,
        "line_height_delta": lh,
        "section_gap_delta": sg,
        "entry_gap_delta":   eg,
        "bullet_gap_delta":  bg,
        "reasoning":         reasoning,
    }


def _empty_pass(page_count: int, source: str) -> dict:
    return {
        "status":     "pass",
        "page_count": page_count,
        "issues":     [],
        "fix":        _zero_fix(),
        "source":     source,
    }
