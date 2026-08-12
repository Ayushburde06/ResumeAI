"""
fix_planner.py
==============
Translates the vision inspector's verdict into concrete TypographyParams
adjustments. Uses GLM-4.7-Flash via Bedrock for complex multi-issue cases;
falls back to deterministic rules for single-issue verdicts.
"""

import json
import os
from pathlib import Path


def _load_env():
    root = Path(__file__).parent.parent.parent
    env_path = root / "backend" / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)
        except ImportError:
            pass


_load_env()

_BEDROCK_API_KEY  = os.getenv("AWS_BEARER_TOKEN_BEDROCK", "") or os.getenv("GLM_API_KEY", "") or os.getenv("QWEN_API_KEY", "")
_BEDROCK_ENDPOINT = os.getenv("QWEN_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1")
_PLANNER_MODEL    = "zai.glm-4.7-flash"   # fast + cheap for JSON planning

# ── Public API ────────────────────────────────────────────────────────────────

def apply_verdict(params, verdict: dict) -> bool:
    """
    Apply the inspector's verdict to `params` (TypographyParams, mutated in place).
    Returns True if a change was made, False if already at limit or status=pass.
    """
    if verdict.get("status") == "pass":
        return False

    fix = verdict.get("fix", {})
    issues = verdict.get("issues", [])

    if not issues:
        return False

    # For complex multi-issue cases, let GLM plan; for single issues use direct rules
    if len(issues) > 1 and _BEDROCK_API_KEY:
        fix = _glm_plan(params, issues, fix)

    return _apply_fix(params, fix, issues)


# ── Direct rule application ───────────────────────────────────────────────────

def _apply_fix(params, fix: dict, issues: list[str]) -> bool:
    """Apply delta dict to TypographyParams. Returns True if any change made."""

    fs_delta  = float(fix.get("font_size_delta",   0.0))
    lh_delta  = float(fix.get("line_height_delta",  0.0))
    sg_delta  = float(fix.get("section_gap_delta",  0.0))
    eg_delta  = float(fix.get("entry_gap_delta",    0.0))
    bg_delta  = float(fix.get("bullet_gap_delta",   0.0))

    # Guard: clamp to safe ranges to prevent runaway corrections
    fs_delta  = max(-0.5, min(0.5,  fs_delta))
    lh_delta  = max(-0.08, min(0.08, lh_delta))
    sg_delta  = max(-4.0, min(4.0,  sg_delta))
    eg_delta  = max(-2.0, min(2.0,  eg_delta))
    bg_delta  = max(-1.0, min(1.0,  bg_delta))

    changed = False

    # Font size with hard bounds
    new_fs = round(params.font_size + fs_delta, 2)
    if 9.0 <= new_fs <= 12.0 and new_fs != params.font_size:
        params.font_size = new_fs
        changed = True

    # Line height with hard bounds
    new_lh = round(params.line_spacing + lh_delta, 3)
    if 0.95 <= new_lh <= 1.35 and new_lh != params.line_spacing:
        params.line_spacing = new_lh
        changed = True

    # Section gap with hard bounds
    new_sg = round(params.section_before + sg_delta, 1)
    if 2.0 <= new_sg <= 16.0 and new_sg != params.section_before:
        params.section_before = new_sg
        changed = True

    # Entry gap with hard bounds
    new_eg = round(params.entry_before + eg_delta, 1)
    if 0.0 <= new_eg <= 8.0 and new_eg != params.entry_before:
        params.entry_before = new_eg
        changed = True

    # Bullet gap with hard bounds
    new_bg = round(params.bullet_before + bg_delta, 1)
    if 0.0 <= new_bg <= 4.0 and new_bg != params.bullet_before:
        params.bullet_before = new_bg
        changed = True

    return changed


# ── GLM multi-issue planner ───────────────────────────────────────────────────

_PLANNER_SYSTEM = """\
You are a typography fix planner for resume PDF layout.
Given the current typography parameters and a list of layout issues,
output a JSON fix delta that resolves all issues in one step.

Rules:
- font_size_delta: between -0.5 and +0.5
- line_height_delta: between -0.08 and +0.08
- section_gap_delta: between -4 and +4
- entry_gap_delta: between -2 and +2
- bullet_gap_delta: between -1 and +1
- Conflicting issues (e.g. overflow + sparse_bottom): prioritise overflow (shrink)
- Respond ONLY with valid JSON, no markdown fences.
"""


def _glm_plan(params, issues: list[str], vision_fix: dict) -> dict:
    """Ask GLM-4.7-Flash to reconcile complex multi-issue verdicts."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=_BEDROCK_API_KEY, base_url=_BEDROCK_ENDPOINT)

        current = {
            "font_size":      params.font_size,
            "line_spacing":   params.line_spacing,
            "section_before": params.section_before,
            "entry_before":   params.entry_before,
            "bullet_before":  params.bullet_before,
        }

        user_msg = (
            f"Current params: {json.dumps(current)}\n"
            f"Issues: {json.dumps(issues)}\n"
            f"Vision suggested fix: {json.dumps(vision_fix)}\n"
            "Output a single JSON fix delta object with keys: "
            "font_size_delta, line_height_delta, section_gap_delta, "
            "entry_gap_delta, bullet_gap_delta, reasoning."
        )

        resp = client.chat.completions.create(
            model=_PLANNER_MODEL,
            messages=[
                {"role": "system", "content": _PLANNER_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=256,
            temperature=0.0,
        )

        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            raw = raw.removeprefix("json")
            raw = raw.strip()

        return json.loads(raw)

    except Exception:
        # If GLM planner fails, fall back to vision inspector's own fix
        return vision_fix
