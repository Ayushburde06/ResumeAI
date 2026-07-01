"""
Agent Memory — per-request session context store.
Tracks iteration history, ATS score progression, critique notes,
section-level snapshots, and composite score history for early stopping.
"""
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IterationRecord:
    iteration: int
    ats_score: int
    composite_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    critique: str
    changed_sections: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentMemory:
    """
    Lightweight in-memory context object for a single agent run.
    Created fresh per request — no persistence needed.
    Tracks section versions for delta editing and change log generation.
    """
    session_id: str = ""
    job_title: str = ""
    seniority: str = ""
    required_skills: list[str] = field(default_factory=list)
    iterations: list[IterationRecord] = field(default_factory=list)
    best_ats_score: int = 0
    best_composite_score: float = 0.0
    total_time_ms: float = 0.0
    rag_context_used: bool = False
    rag_context_snippet: str = ""

    # v2: section-level tracking
    resume_hash: str = ""           # SHA-256[:16] of raw resume text
    jd_hash: str = ""               # SHA-256[:16] of JD text
    section_versions: dict = field(default_factory=dict)   # {section: {before: dict, after: dict}}
    changed_sections: set = field(default_factory=set)     # which sections were actually rewritten
    composite_scores: list = field(default_factory=list)   # composite score per iteration

    def set_hashes(self, resume_text: str, jd_text: str) -> None:
        """Compute and store hash keys for cache lookup."""
        self.resume_hash = hashlib.sha256(resume_text.encode("utf-8", errors="replace")).hexdigest()[:16]
        self.jd_hash = hashlib.sha256(jd_text.encode("utf-8", errors="replace")).hexdigest()[:16]

    def snapshot_section(self, section: str, before: Any, after: Any) -> None:
        """Record before/after state of a section for change log generation."""
        self.section_versions[section] = {"before": before, "after": after}
        if before != after:
            self.changed_sections.add(section)

    def build_change_log(self) -> list[dict]:
        """
        Generate a human-readable change log from section snapshots.
        Returns list of {section, change} dicts.
        """
        log = []
        section_labels = {
            "summary": "Summary",
            "experience": "Experience",
            "skills": "Skills",
            "projects": "Projects",
        }
        for section, versions in self.section_versions.items():
            label = section_labels.get(section, section.title())
            before = versions.get("before")
            after = versions.get("after")
            if before == after:
                continue
            if section == "summary":
                log.append({"section": label, "change": "Rewritten for stronger ATS alignment and natural tone"})
            elif section == "skills":
                log.append({"section": label, "change": "Reorganized into 5 clean categories; added missing JD keywords"})
            elif section == "experience":
                log.append({"section": label, "change": "Strengthened action verbs and integrated targeted keywords into bullets"})
            elif section == "projects":
                log.append({"section": label, "change": "Improved technical clarity, architecture language, and ATS keyword coverage"})
            else:
                log.append({"section": label, "change": "Optimized for ATS and recruiter readability"})
        return log

    def add_iteration(
        self,
        iteration: int,
        ats_score: int,
        matched_keywords: list[str],
        missing_keywords: list[str],
        critique: str,
        composite_score: float = 0.0,
        changed_sections: list[str] | None = None,
    ) -> None:
        record = IterationRecord(
            iteration=iteration,
            ats_score=ats_score,
            composite_score=composite_score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            critique=critique,
            changed_sections=changed_sections or [],
        )
        self.iterations.append(record)
        self.composite_scores.append(composite_score)
        if ats_score > self.best_ats_score:
            self.best_ats_score = ats_score
        if composite_score > self.best_composite_score:
            self.best_composite_score = composite_score

    def get_critique_summary(self) -> str:
        """
        Return a formatted summary of all past iteration critiques
        to inject into the next rewrite prompt.
        """
        if not self.iterations:
            return ""
        lines = ["PREVIOUS ATTEMPTS AND CRITIQUES:"]
        for rec in self.iterations:
            lines.append(
                f"Attempt {rec.iteration + 1}: ATS={rec.ats_score}% | "
                f"Missing: {', '.join(rec.missing_keywords[:8])} | "
                f"Critique: {rec.critique}"
            )
        lines.append(
            "ACTION REQUIRED: Integrate every missing keyword listed above "
            "into the resume naturally. Do not repeat the same mistakes."
        )
        return "\n".join(lines)

    def get_score_progression(self) -> list[int]:
        """Return list of ATS scores across iterations."""
        return [rec.ats_score for rec in self.iterations]

    def to_dict(self) -> dict[str, Any]:
        """Serialize memory for SSE/API response."""
        return {
            "iterations_run": len(self.iterations),
            "ats_progression": self.get_score_progression(),
            "composite_progression": [round(s, 3) for s in self.composite_scores],
            "best_ats_score": self.best_ats_score,
            "best_composite_score": round(self.best_composite_score, 3),
            "rag_context_used": self.rag_context_used,
            "total_time_ms": round(self.total_time_ms, 1),
            "sections_changed": list(self.changed_sections),
        }
