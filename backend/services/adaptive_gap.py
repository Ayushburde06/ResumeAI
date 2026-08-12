"""
Adaptive Gap Detection Service — v1

Replaces flat keyword matching with a 3-phase domain-aware gap analysis:

Phase 1 (LLM): classify_role_domain   → DomainProfile (explicit/implicit/nice-to-have/red-flags)
Phase 2 (LLM): build_capability_graph → CapabilityGraph (skill → implied capabilities)
Phase 3 (det): adaptive_gap_diff      → AdaptiveGapReport (critical/bridgeable/implicit/unknowns)

The deterministic diff in Phase 3 uses `capability_bridge_map.json` — a versioned,
human-reviewable lookup table — to detect bridgeable gaps without an LLM call.

Architecture invariants (per AGENTS.md):
- Both LLM calls route to the cheap/flash model (jd_analysis task routing).
- Phase 3 is 100% deterministic: no LLM, no randomness, unit-testable.
- No RAG re-fetch. Domain context is fetched once, passed to the rewrite stage.
- All outputs are plain dicts — no dataclasses — for simple JSON serialisation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Load bridge map once at import time ──────────────────────────────────────

_BRIDGE_MAP_PATH = Path(__file__).parent / "capability_bridge_map.json"

def _load_bridge_map() -> dict[str, list[str]]:
    try:
        with open(_BRIDGE_MAP_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        # Strip metadata keys (_version, _description) and lower-case everything
        return {
            k.lower(): [c.lower() for c in v]
            for k, v in raw.items()
            if not k.startswith("_")
        }
    except Exception as e:
        logger.warning("Could not load capability_bridge_map.json: %s", e)
        return {}

_BRIDGE_MAP: dict[str, list[str]] = _load_bridge_map()


# ── Prompt Templates ─────────────────────────────────────────────────────────

DOMAIN_CLASSIFIER_SYSTEM = """You are a senior technical recruiter specialising in role classification.
Given a job description, infer the full context of what this role requires — including things
hiring managers ASSUME but don't always write down.

Return ONLY valid JSON. Be concise but complete. Think beyond the literal words."""

DOMAIN_CLASSIFIER_PROMPT = """Analyse this job description and classify the role domain.

JOB DESCRIPTION:
{jd_text}

Return JSON with EXACTLY this shape:
{{
  "domain": "specific domain name, e.g. 'Atlassian Platform Engineer', 'ML Infrastructure', 'Frontend SaaS'",
  "seniority": "intern/junior/junior-mid/mid/senior/lead/staff",
  "role_type": "backend-heavy/frontend-heavy/full-stack/data-engineering/ml-engineering/devops/mobile/platform/other",
  "industry": "e.g. 'Enterprise SaaS', 'FinTech', 'EdTech', 'E-commerce', 'AI startup'",
  "explicit_skills": ["every hard skill directly named in the JD"],
  "implicit_expectations": [
    "skills every HM in this domain ASSUMES even if not written, e.g. Git for any SWE role,",
    "Linux for any backend role, REST API design for any backend, Agile/Scrum for any team role"
  ],
  "nice_to_haves": ["skills mentioned as optional/preferred"],
  "red_flags_if_missing": [
    "skills that would cause most HMs in this domain to pass on the candidate"
  ]
}}"""


CAPABILITY_GRAPH_SYSTEM = """You are a senior software architect mapping what a resume IMPLIES.
Given a structured resume, build a capability map: for each skill or technology listed,
infer what broader capabilities it implies the candidate has.

Focus on transferable technical implications — not soft skills.
Return ONLY valid JSON."""

CAPABILITY_GRAPH_PROMPT = """Build a capability map for this resume.

RESUME SKILLS AND EXPERIENCE (condensed):
{resume_summary}

For EACH technology/skill listed, output what capabilities it implies.
Examples:
  "FastAPI" → ["REST API design", "async patterns", "OpenAPI", "Python backend", "backend"]
  "Docker" → ["containerization", "deployment", "environment isolation", "devops"]
  "TypeScript" → ["OOP patterns", "type safety", "frontend", "JavaScript", "Node.js-adjacent"]

Return JSON where keys are the exact skills from the resume and values are capability arrays:
{{
  "SkillName": ["capability 1", "capability 2", "..."],
  ...
}}

Rules:
- Include ALL skills, frameworks, tools, and languages mentioned
- Keep capability strings short (2-4 words max each)
- Focus on technical domain implications, not personality traits
- 3–6 capabilities per skill"""


# ── LLM Functions ─────────────────────────────────────────────────────────────

def classify_role_domain(jd_text: str, model_id: str | None = None) -> dict:
    """
    LLM Call #1 — classify the role domain and infer implicit expectations.
    Routes to cheap/flash model. Returns a DomainProfile dict.
    """
    from services.ai_service import (
        _create_chat_completion,
        _extract_content,
        _parse_json_response,
        get_client_for_task,
    )

    if not jd_text or not jd_text.strip():
        return {
            "domain": "Software Engineering",
            "seniority": "mid",
            "role_type": "backend-heavy",
            "industry": "Technology",
            "explicit_skills": [],
            "implicit_expectations": [],
            "nice_to_haves": [],
            "red_flags_if_missing": [],
        }

    client, model = get_client_for_task("jd_analysis")

    try:
        response = _create_chat_completion(
            client,
            model_id,
            model=model,
            messages=[
                {"role": "system", "content": DOMAIN_CLASSIFIER_SYSTEM},
                {"role": "user", "content": DOMAIN_CLASSIFIER_PROMPT.format(
                    jd_text=jd_text[:6000]  # cap to avoid token blowout
                )},
            ],
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        result = _parse_json_response(_extract_content(response))
        # Ensure all expected keys exist with sane defaults
        result.setdefault("domain", "Software Engineering")
        result.setdefault("seniority", "mid")
        result.setdefault("role_type", "backend-heavy")
        result.setdefault("industry", "Technology")
        result.setdefault("explicit_skills", [])
        result.setdefault("implicit_expectations", [])
        result.setdefault("nice_to_haves", [])
        result.setdefault("red_flags_if_missing", [])
        return result
    except Exception as e:
        logger.warning("classify_role_domain failed: %s", e)
        return {
            "domain": "Software Engineering",
            "seniority": "mid",
            "role_type": "backend-heavy",
            "industry": "Technology",
            "explicit_skills": [],
            "implicit_expectations": [],
            "nice_to_haves": [],
            "red_flags_if_missing": [],
        }


def build_capability_graph(resume_json: dict, model_id: str | None = None) -> dict[str, list[str]]:
    """
    LLM Call #2 — build a capability map from the resume.
    Maps skill → [implied capabilities]. Routes to cheap/flash model.
    """
    from services.ai_service import (
        _create_chat_completion,
        _extract_content,
        _parse_json_response,
        get_client_for_task,
    )

    client, model = get_client_for_task("jd_analysis")

    # Build a condensed resume summary — skills + tech stacks only
    skills_flat = []
    skills_dict = resume_json.get("skills", {})
    if isinstance(skills_dict, dict):
        for category, items in skills_dict.items():
            if isinstance(items, list):
                skills_flat.extend(items)

    tech_stacks = []
    for proj in resume_json.get("projects", [])[:4]:
        tech_stacks.extend(proj.get("tech_stack", []))
    for exp in resume_json.get("experience", [])[:3]:
        tech_stacks.extend(exp.get("tech_stack", []))

    all_skills = list(dict.fromkeys(skills_flat + tech_stacks))  # deduped, order-preserved

    # Also include bullets keywords via simple extraction
    bullet_texts = []
    for exp in resume_json.get("experience", [])[:2]:
        bullet_texts.extend(exp.get("bullets", [])[:2])
    for proj in resume_json.get("projects", [])[:2]:
        bullet_texts.extend(proj.get("bullets", [])[:2])

    resume_summary = (
        f"SKILLS: {', '.join(all_skills[:40])}\n"
        f"TECH STACKS (from projects/experience): {', '.join(set(tech_stacks[:25]))}\n"
        f"SAMPLE BULLETS:\n" + "\n".join(bullet_texts[:6])
    )

    try:
        response = _create_chat_completion(
            client,
            model_id,
            model=model,
            messages=[
                {"role": "system", "content": CAPABILITY_GRAPH_SYSTEM},
                {"role": "user", "content": CAPABILITY_GRAPH_PROMPT.format(
                    resume_summary=resume_summary[:4000]
                )},
            ],
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        result = _parse_json_response(_extract_content(response))
        # Validate: every value must be a list
        return {
            k: v if isinstance(v, list) else []
            for k, v in result.items()
            if isinstance(k, str)
        }
    except Exception as e:
        logger.warning("build_capability_graph failed: %s", e)
        # Fallback: build a basic graph from known skills
        return {skill: [] for skill in all_skills[:30]}


# ── Deterministic Gap Diff ────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def _candidate_capabilities(capability_graph: dict[str, list[str]]) -> set[str]:
    """Flatten all implied capabilities from the candidate's graph into one set."""
    caps: set[str] = set()
    for skill, implied in capability_graph.items():
        caps.add(_normalise(skill))
        for cap in implied:
            caps.add(_normalise(cap))
    return caps


def _is_bridgeable(
    missing_skill: str,
    candidate_caps: set[str],
    capability_graph: dict[str, list[str]],
) -> tuple[bool, list[str], str]:
    """
    Check if a missing skill can be bridged by the candidate's capabilities.

    Returns (is_bridgeable, matching_candidate_skills, bridge_framing_text).

    Logic:
    1. Check if any candidate capability directly matches the missing skill
    2. Look up the bridge map for the missing skill → get required bridging capabilities
    3. If any required bridging capability exists in candidate's capabilities → bridgeable
    """
    norm_missing = _normalise(missing_skill)

    # Direct match — candidate already has it somewhere implied
    if norm_missing in candidate_caps:
        return True, [], ""

    # Bridge map lookup
    bridge_caps = _BRIDGE_MAP.get(norm_missing, [])
    if not bridge_caps:
        # Try partial match — e.g. "spring boot" against "spring"
        for key in _BRIDGE_MAP:
            if key in norm_missing or norm_missing in key:
                bridge_caps = _BRIDGE_MAP[key]
                break

    matching = [cap for cap in bridge_caps if cap in candidate_caps]
    if matching:
        candidate_skills = [
            skill for skill, implied_caps in capability_graph.items()
            if any(_normalise(c) in candidate_caps for c in implied_caps)
            and any(m in [_normalise(i) for i in implied_caps] or m == _normalise(skill) for m in matching)
        ][:3]
        framing = _generate_bridge_framing(missing_skill, candidate_skills or matching[:2])
        return True, candidate_skills or matching[:2], framing

    return False, [], ""


def _generate_bridge_framing(missing_skill: str, bridging_items: list[str]) -> str:
    """Generate the bridge framing sentence for a rewriter prompt."""
    if not bridging_items:
        return f"Adjacent knowledge of {missing_skill} domain"
    items_str = "/".join(str(b) for b in bridging_items[:3])
    return f"Strong foundation via {items_str}; {missing_skill} is a syntax/tooling gap, not a domain gap"


def adaptive_gap_diff(
    capability_graph: dict[str, list[str]],
    domain_profile: dict,
    ats_missing_keywords: list[str],
) -> dict:
    """
    Deterministic Phase 3 — no LLM.

    Classifies each missing keyword (from ATS scan + domain implicit expectations) into:
      - critical:    required + missing + no bridge possible
      - bridgeable:  missing but candidate has adjacent/transferable skills
      - implicit:    domain expects it but it wasn't in the JD either
      - true_unknowns: truly unknown — surface as questions

    Returns an AdaptiveGapReport dict.
    """
    candidate_caps = _candidate_capabilities(capability_graph)
    red_flags = {_normalise(r) for r in domain_profile.get("red_flags_if_missing", [])}
    implicit_expectations = domain_profile.get("implicit_expectations", [])

    critical: list[str] = []
    bridgeable: list[dict] = []
    implicit_gaps: list[str] = []
    true_unknowns: list[str] = []

    # ── Process ATS missing keywords ──────────────────────────────────────────
    for kw in ats_missing_keywords:
        norm_kw = _normalise(kw)

        # Skip if the candidate already implies this capability
        if norm_kw in candidate_caps:
            continue

        is_bridge, bridging_skills, framing = _is_bridgeable(kw, candidate_caps, capability_graph)

        if is_bridge:
            bridgeable.append({
                "jd_needs": kw,
                "candidate_has": bridging_skills,
                "bridge_framing": framing,
                "bridge_reason": f"Candidate has adjacent skills: {', '.join(str(s) for s in bridging_skills[:3])}",
            })
        elif norm_kw in red_flags:
            # Truly critical: required, missing, no bridge, red flag
            critical.append(kw)
        else:
            # Not bridgeable, not a red flag — borderline, surface as unknown if domain-specific
            true_unknowns.append(kw)

    # ── Process implicit domain expectations ──────────────────────────────────
    ats_missing_norm = {_normalise(k) for k in ats_missing_keywords}
    for expectation in implicit_expectations:
        norm_exp = _normalise(expectation)

        # Already covered in ATS scan
        if norm_exp in ats_missing_norm:
            continue
        # Already in candidate capabilities
        if norm_exp in candidate_caps:
            continue
        # Implicit gap — domain assumes this but it's not even in the JD
        implicit_gaps.append(expectation)

    # ── Deduplicate and cap lists ─────────────────────────────────────────────
    def _dedup(lst: list) -> list:
        seen: set = set()
        out = []
        for item in lst:
            key = item if isinstance(item, str) else str(item)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    return {
        "critical": _dedup(critical)[:15],
        "bridgeable": _dedup(bridgeable)[:10],
        "implicit": _dedup(implicit_gaps)[:10],
        "true_unknowns": _dedup(true_unknowns)[:8],
        "domain": domain_profile.get("domain", ""),
        "seniority": domain_profile.get("seniority", ""),
        "role_type": domain_profile.get("role_type", ""),
    }


def build_gap_context_for_rewrite(adaptive_report: dict) -> str:
    """
    Render the adaptive gap report as plain text to inject into rewrite prompts.
    This gives the LLM rewriter the bridge framing context without needing to
    understand the full report structure.
    """
    lines: list[str] = []

    bridgeable = adaptive_report.get("bridgeable", [])
    if bridgeable:
        lines.append("BRIDGEABLE GAPS — use these framing statements naturally in bullets or summary:")
        for gap in bridgeable:
            jd_needs = gap.get("jd_needs", "")
            framing = gap.get("bridge_framing", "")
            if jd_needs and framing:
                lines.append(f"  • {jd_needs}: \"{framing}\"")

    implicit = adaptive_report.get("implicit", [])
    if implicit:
        lines.append("\nIMPLICIT DOMAIN EXPECTATIONS — weave into bullets ONLY if there is real evidence:")
        for exp in implicit:
            lines.append(f"  • {exp}")

    critical = adaptive_report.get("critical", [])
    if critical:
        lines.append("\nCRITICAL GAPS — these are truly missing. Do NOT fabricate experience.")
        lines.append("  Acknowledge adjacent skills instead: e.g. 'Experience with [similar tech]'")
        for gap in critical:
            lines.append(f"  • {gap}")

    if not lines:
        return ""

    header = (
        f"ADAPTIVE GAP CONTEXT (Domain: {adaptive_report.get('domain', 'N/A')}, "
        f"Seniority: {adaptive_report.get('seniority', 'N/A')}):"
    )
    return header + "\n" + "\n".join(lines)
