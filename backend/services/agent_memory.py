"""
Agent Memory — per-request session context store.
Tracks iteration history, ATS score progression, and critique notes
so the agent knows what it already tried and why it failed.
"""
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IterationRecord:
    iteration: int
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    critique: str          # LLM-generated critique of why keywords were missed
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentMemory:
    """
    Lightweight in-memory context object for a single agent run.
    Created fresh per request — no persistence needed.
    """
    session_id: str = ""
    job_title: str = ""
    seniority: str = ""
    required_skills: list[str] = field(default_factory=list)
    iterations: list[IterationRecord] = field(default_factory=list)
    best_ats_score: int = 0
    total_time_ms: float = 0.0
    rag_context_used: bool = False
    rag_context_snippet: str = ""   # short preview of what was retrieved

    def add_iteration(
        self,
        iteration: int,
        ats_score: int,
        matched_keywords: list[str],
        missing_keywords: list[str],
        critique: str,
    ) -> None:
        record = IterationRecord(
            iteration=iteration,
            ats_score=ats_score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            critique=critique,
        )
        self.iterations.append(record)
        if ats_score > self.best_ats_score:
            self.best_ats_score = ats_score

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
            "best_ats_score": self.best_ats_score,
            "rag_context_used": self.rag_context_used,
            "total_time_ms": round(self.total_time_ms, 1),
        }
