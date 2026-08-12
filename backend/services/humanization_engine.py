"""
humanization_engine.py

Companion scorer to ats_engine.py. Where compute_ats_score() measures
*keyword coverage* against a JD, compute_humanization_score() measures
whether the resume actually *reads like a human wrote it* — concrete
outcomes, plain phrasing, reasonable sentence length, active voice.

Intended usage in the app:
    ats_result = compute_ats_score(resume, jd_text)
    human_result = compute_humanization_score(resume)
    # surface both to the user separately — don't blend them into one number.
"""

import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Buzzword / filler list — words that read as "AI-generated resume speak"
# rather than something a person would say describing their own work.
# Kept separate from STOP_WORDS in ats_engine.py because these are NOT
# stripped for keyword matching — they're actively penalized here.
# ---------------------------------------------------------------------------
BUZZWORDS = {
    "leverage", "leveraged", "leveraging",
    "spearhead", "spearheaded", "spearheading",
    "orchestrate", "orchestrated", "orchestrating",
    "synergy", "synergize", "synergized",
    "utilize", "utilized", "utilizing",
    "robust", "dynamic", "passionate", "results-driven", "results driven",
    "cutting-edge", "cutting edge", "seamless", "seamlessly",
    "game-changing", "game changing", "innovative", "innovatively",
    "world-class", "best-in-class", "next-generation",
    "holistic", "paradigm", "streamline", "streamlined", "streamlining",
    "empower", "empowered", "empowering",
    "unlock", "unlocked", "unlocking",
    "harness", "harnessed", "harnessing",
    "elevate", "elevated", "elevating",
    "transformative", "transformational",
    "proactively", "strategically", "meticulously",
    "unparalleled", "exceptional", "outstanding", "top-notch",
    "thought leader", "thought leadership",
    "value-add", "value add", "circle back", "deep dive", "low-hanging fruit",
}

# Phrase-level patterns that are near-universal LLM tics.
FILLER_PHRASE_PATTERNS = [
    r"\bnot only\b.{0,40}\bbut also\b",
    r"\bin today's fast-paced\b",
    r"\bplayed a (key|pivotal|critical) role\b",
    r"\bresponsible for\b",
    r"\bin order to\b",
    r"\ba wide range of\b",
    r"\bit is (important|worth noting)\b",
    r"\bin an effort to\b",
    r"\bas a result of\b",
    r"\bfurther enhancing\b",
    r"\bdeveloped and (implemented|deployed|integrated)\b",
    r"\bbuilt and (deployed|integrated|launched)\b",
    r"\bplays a (key|pivotal|critical|vital) role\b",
    r"\bensured (the|that)\b",
    r"\bcontributed to (the|a)\b",
]
_FILLER_RE = re.compile("|".join(FILLER_PHRASE_PATTERNS), re.IGNORECASE)

# Signals that a bullet describes an outcome, not just a task.
OUTCOME_SIGNAL_WORDS = {
    "reduced", "increased", "decreased", "decreasing", "cut", "improved", "eliminated", "prevented",
    "resolved", "fixed", "solved", "saved", "grew", "boosted", "doubled",
    "halved", "accelerated", "shortened", "lowered", "raised", "generated",
    "recovered", "unblocked", "scaled", "slashed", "before", "after", "from", "to",
}

# Weak passive-voice openers ("was responsible for", "were tasked with", etc.)
_PASSIVE_RE = re.compile(
    r"\b(was|were|is|are|been|being)\s+\w+ed\b", re.IGNORECASE
)

_NUMBER_RE = re.compile(r"\d")


class BulletFeedback(NamedTuple):
    text: str
    has_number: bool
    has_outcome_word: bool
    is_passive: bool
    has_buzzword: bool
    has_filler_phrase: bool
    word_count: int
    flags: list[str]


class HumanizationResult(NamedTuple):
    score: int                       # 0-100
    bullet_feedback: list[BulletFeedback]
    buzzwords_found: list[str]
    filler_phrases_found: list[str]
    pct_bullets_with_outcome: float
    pct_bullets_passive: float
    avg_bullet_length: float
    summary_notes: list[str]
    
    def dict(self):
        return {
            "score": self.score,
            "bullet_feedback": [f._asdict() for f in self.bullet_feedback],
            "buzzwords_found": self.buzzwords_found,
            "filler_phrases_found": self.filler_phrases_found,
            "pct_bullets_with_outcome": self.pct_bullets_with_outcome,
            "pct_bullets_passive": self.pct_bullets_passive,
            "avg_bullet_length": self.avg_bullet_length,
            "summary_notes": self.summary_notes,
        }


def _split_sentences_or_bullets(text: str) -> list[str]:
    """Split resume bullet/summary text into individual lines to evaluate."""
    lines = [l.strip("•*- \t") for l in text.splitlines()]
    return [l for l in lines if l.strip()]


def _extract_bullets(resume: dict) -> list[str]:
    """Pull every experience/project bullet out of a parsed resume dict."""
    bullets: list[str] = []
    for exp in resume.get("experience", []) or []:
        if isinstance(exp, dict):
            for b in exp.get("bullets", []) or []:
                if isinstance(b, str) and b.strip():
                    bullets.append(b.strip())
    for proj in resume.get("projects", []) or []:
        if isinstance(proj, dict):
            desc = proj.get("description", "")
            if isinstance(desc, str) and desc.strip():
                bullets.extend(_split_sentences_or_bullets(desc))
    return bullets


def _find_buzzwords(text: str) -> list[str]:
    lower = text.lower()
    return sorted({b for b in BUZZWORDS if b in lower})


def _find_filler_phrases(text: str) -> list[str]:
    return sorted({m.group(0).lower() for m in _FILLER_RE.finditer(text)})


def evaluate_bullet(bullet: str) -> BulletFeedback:
    lower = bullet.lower()
    has_number = bool(_NUMBER_RE.search(bullet))
    has_outcome_word = any(w in lower for w in OUTCOME_SIGNAL_WORDS)
    is_passive = bool(_PASSIVE_RE.search(bullet)) or lower.startswith("responsible for")
    buzzwords = _find_buzzwords(bullet)
    fillers = _find_filler_phrases(bullet)
    word_count = len(bullet.split())

    flags = []
    if not (has_number or has_outcome_word):
        flags.append("No visible outcome — describes a task, not a result. "
                      "Add what changed (a number, a before/after, a concrete effect).")
    if is_passive:
        flags.append("Passive/vague phrasing ('responsible for...'). Rewrite starting with the action verb.")
    if buzzwords:
        flags.append(f"Buzzwords: {', '.join(buzzwords)} — replace with a plain description of what you did.")
    if fillers:
        flags.append(f"Generic filler phrasing: {', '.join(fillers)}")
    if word_count > 28:
        flags.append("Bullet is long — split into two ideas or trim to under ~25 words.")

    return BulletFeedback(
        text=bullet,
        has_number=has_number,
        has_outcome_word=has_outcome_word,
        is_passive=is_passive,
        has_buzzword=bool(buzzwords),
        has_filler_phrase=bool(fillers),
        word_count=word_count,
        flags=flags,
    )


def compute_humanization_score(resume: dict) -> HumanizationResult:
    """
    Scores how 'human and HR-readable' a resume's bullets/summary are,
    independent of ATS keyword coverage. Meant to be shown alongside
    compute_ats_score(), not merged into it.
    """
    bullets = _extract_bullets(resume)
    summary_text = resume.get("summary", "") if isinstance(resume, dict) else ""

    all_text_blocks = bullets + ([summary_text] if summary_text else [])

    if not bullets:
        return HumanizationResult(
            score=0,
            bullet_feedback=[],
            buzzwords_found=[],
            filler_phrases_found=[],
            pct_bullets_with_outcome=0.0,
            pct_bullets_passive=0.0,
            avg_bullet_length=0.0,
            summary_notes=["No experience/project bullets found to evaluate."],
        )

    feedback = [evaluate_bullet(b) for b in bullets]

    n = len(feedback)
    outcome_count = sum(1 for f in feedback if f.has_number or f.has_outcome_word)
    passive_count = sum(1 for f in feedback if f.is_passive)
    buzzword_count = sum(1 for f in feedback if f.has_buzzword)
    avg_len = sum(f.word_count for f in feedback) / n

    pct_outcome = outcome_count / n * 100
    pct_passive = passive_count / n * 100
    pct_buzzword = buzzword_count / n * 100

    all_buzzwords = sorted({w for block in all_text_blocks for w in _find_buzzwords(block)})
    all_fillers = sorted({p for block in all_text_blocks for p in _find_filler_phrases(block)})

    # Start at 100, deduct for the things HR readers actually notice.
    score = 100.0
    score -= (100 - pct_outcome) * 0.4      # missing outcomes hurts
    score -= pct_passive * 0.25
    score -= pct_buzzword * 0.35            # penalize bullets with buzzwords
    score -= min(25, len(all_buzzwords) * 5) # distinct buzzword count penalty across whole resume
    score -= min(20, len(all_fillers) * 6)  # filler phrase penalty
    if avg_len > 26:
        score -= min(15, (avg_len - 26) * 1.5)
    score = max(0, min(100, round(score)))

    notes = []
    if pct_outcome < 50:
        notes.append(f"Only {pct_outcome:.0f}% of bullets show a concrete outcome — "
                      "aim for most bullets to include a number or clear result.")
    if pct_passive > 20:
        notes.append(f"{pct_passive:.0f}% of bullets use passive/vague phrasing — "
                      "lead with a strong action verb instead.")
    if all_buzzwords:
        notes.append(f"Buzzwords found across the resume: {', '.join(all_buzzwords)}.")
    if avg_len > 26:
        notes.append(f"Average bullet length is {avg_len:.0f} words — tighten to under ~25.")
    if not notes:
        notes.append("Reads clean — concrete outcomes, active voice, no filler detected.")

    return HumanizationResult(
        score=int(score),
        bullet_feedback=feedback,
        buzzwords_found=all_buzzwords,
        filler_phrases_found=all_fillers,
        pct_bullets_with_outcome=round(pct_outcome, 1),
        pct_bullets_passive=round(pct_passive, 1),
        avg_bullet_length=round(avg_len, 1),
        summary_notes=notes,
    )
