"""
RAG Service — Lightweight Retrieval-Augmented Generation
Uses keyword/TF-IDF scoring (pure Python + numpy via pandas dependency).
No heavy dependencies: no ChromaDB, no sentence-transformers.
All LLM calls route through existing GLM/Qwen via ai_service._get_client().
"""
import json
import math
import re
from pathlib import Path
from typing import NamedTuple

# ── Knowledge base path ──────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data" / "rag_knowledge"

# ── In-memory knowledge store ────────────────────────────────────────────────
_knowledge_store: list[dict] = []
_idf_cache: dict[str, float] = {}
_store_loaded = False


class RetrievedChunk(NamedTuple):
    id: str
    text: str
    category: str
    score: float
    metadata: dict


def _load_knowledge_store() -> None:
    """Load all JSONL knowledge files into memory on first use."""
    global _knowledge_store, _store_loaded
    if _store_loaded:
        return

    _knowledge_store = []
    files = [
        "resume_templates.jsonl",
        "ats_rules.jsonl",
        "job_market_signals.jsonl",
        "cover_letter_patterns.jsonl",   # v2: targeted cover letter RAG
        "hr_communication.jsonl",         # v2: LinkedIn, email, referral RAG
    ]

    for fname in files:
        path = _DATA_DIR / fname
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    # Normalise: ensure a unified 'text' field for scoring
                    if "text" not in doc:
                        # For job_market_signals: combine keywords into text
                        parts = []
                        if "category" in doc:
                            parts.append(doc["category"])
                        if "subcategory" in doc:
                            parts.append(doc["subcategory"])
                        if "top_keywords" in doc:
                            parts.extend(doc["top_keywords"])
                        if "rule" in doc:
                            parts.append(doc["rule"])
                        doc["text"] = " ".join(str(p) for p in parts)
                    # Add source file tag
                    doc["_source"] = fname.replace(".jsonl", "")
                    _knowledge_store.append(doc)
                except json.JSONDecodeError:
                    continue

    _build_idf()
    _store_loaded = True


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercase."""
    return re.findall(r"[a-z][a-z0-9+#\-.]{1,}", text.lower())


def _build_idf() -> None:
    """Compute IDF weights across the knowledge store."""
    global _idf_cache
    N = len(_knowledge_store)
    if N == 0:
        return

    df: dict[str, int] = {}
    for doc in _knowledge_store:
        tokens = set(_tokenize(doc.get("text", "") + " " + " ".join(doc.get("tags", []))))
        for t in tokens:
            df[t] = df.get(t, 0) + 1

    _idf_cache = {
        t: math.log((N + 1) / (freq + 1)) + 1.0
        for t, freq in df.items()
    }


def _score_document(doc: dict, query_tokens: set[str], query_text: str) -> float:
    """TF-IDF-style score for a document given query tokens."""
    doc_text = doc.get("text", "") + " " + " ".join(doc.get("tags", []))
    doc_tokens = _tokenize(doc_text)

    if not doc_tokens:
        return 0.0

    # TF for doc
    tf: dict[str, float] = {}
    for t in doc_tokens:
        tf[t] = tf.get(t, 0) + 1
    doc_len = len(doc_tokens)
    for t in tf:
        tf[t] = tf[t] / doc_len

    # TF-IDF dot product with query
    score = 0.0
    for qt in query_tokens:
        if qt in tf:
            idf = _idf_cache.get(qt, 1.0)
            score += tf[qt] * idf

    # Bonus: exact phrase substring match (e.g., job title in text)
    doc_text_lower = doc_text.lower()
    query_lower = query_text.lower()
    for phrase in [query_lower[:20], query_lower[: len(query_lower) // 2]]:
        if len(phrase) > 5 and phrase in doc_text_lower:
            score *= 1.4
            break

    return score


def retrieve(
    query: str,
    job_title: str = "",
    required_skills: list[str] | None = None,
    top_k: int = 6,
    source_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve the top-k most relevant knowledge chunks for a query.

    Args:
        query: Free-text query (job title + key skills merged).
        job_title: Parsed job title from JD analysis.
        required_skills: List of required skills from JD analysis.
        top_k: Number of chunks to return.
        source_filter: If set, only return chunks from this source file
                       ('resume_templates', 'ats_rules', 'job_market_signals').
    """
    _load_knowledge_store()

    if not _knowledge_store:
        return []

    # Build unified query text
    parts = [query]
    if job_title:
        parts.append(job_title)
    if required_skills:
        parts.extend(required_skills[:10])
    full_query = " ".join(parts)
    query_tokens = set(_tokenize(full_query))

    scored: list[tuple[float, dict]] = []
    for doc in _knowledge_store:
        if source_filter and doc.get("_source") != source_filter:
            continue
        score = _score_document(doc, query_tokens, full_query)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in scored[:top_k]:
        results.append(
            RetrievedChunk(
                id=doc.get("id", ""),
                text=doc.get("text", ""),
                category=doc.get("category", doc.get("_source", "")),
                score=round(score, 4),
                metadata={
                    "source": doc.get("_source", ""),
                    "role": doc.get("role", ""),
                    "seniority": doc.get("seniority", ""),
                    "tags": doc.get("tags", []),
                    "priority": doc.get("priority", ""),
                    "system": doc.get("system", ""),
                    "priority_keywords": doc.get("priority_keywords", []),
                },
            )
        )
    return results


def build_rag_context_string(
    job_title: str,
    required_skills: list[str],
    seniority: str = "",
) -> str:
    """
    Build a formatted RAG context string to inject into LLM prompts.
    Retrieves relevant templates, ATS rules, and market signals.
    Returns a concise block ready to paste into a system/user prompt.
    """
    _load_knowledge_store()

    query = f"{job_title} {seniority} {' '.join(required_skills[:8])}"

    # Get chunks from all three sources
    templates = retrieve(query, job_title, required_skills, top_k=3, source_filter="resume_templates")
    ats_rules = retrieve(query, job_title, required_skills, top_k=4, source_filter="ats_rules")
    market    = retrieve(query, job_title, required_skills, top_k=2, source_filter="job_market_signals")

    lines = []

    if templates:
        lines.append("=== INDUSTRY RESUME EXAMPLES (use as writing style reference) ===")
        for chunk in templates:
            meta = chunk.metadata
            label = f"[{meta.get('role', '')} / {meta.get('seniority', '')}]"
            lines.append(f"{label} {chunk.text}")
        lines.append("")

    if ats_rules:
        lines.append("=== ATS FORMATTING RULES (apply these to avoid parser failures) ===")
        for chunk in ats_rules:
            priority = chunk.metadata.get("priority", "")
            system   = chunk.metadata.get("system", "general")
            lines.append(f"[{system.upper()} / {priority.upper()}] {chunk.text}")
        lines.append("")

    if market:
        lines.append("=== JOB MARKET SIGNALS (top keywords for this role category) ===")
        for chunk in market:
            pk = chunk.metadata.get("priority_keywords", [])
            if pk:
                lines.append(f"Priority keywords for {chunk.category}: {', '.join(pk)}")
            lines.append(f"Full keyword set: {chunk.text[:300]}")
        lines.append("")

    return "\n".join(lines) if lines else ""


def get_store_stats() -> dict:
    """Return statistics about the loaded knowledge store."""
    _load_knowledge_store()
    sources: dict[str, int] = {}
    for doc in _knowledge_store:
        src = doc.get("_source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    return {"total_documents": len(_knowledge_store), "by_source": sources}


# ── v2: Targeted retrieval per output type ────────────────────────────────────

_SECTION_SOURCE_MAP = {
    # Resume sections → resume writing guidance
    "summary":      ["resume_templates", "ats_rules"],
    "experience":   ["resume_templates", "ats_rules", "job_market_signals"],
    "skills":       ["ats_rules", "job_market_signals"],
    "projects":     ["resume_templates", "ats_rules"],
    # Document types → communication templates
    "cover_letter": ["cover_letter_patterns"],
    "email":        ["hr_communication"],
    "linkedin":     ["hr_communication"],
    "referral":     ["hr_communication"],
}


def build_targeted_rag_context(
    section_type: str,
    job_title: str = "",
    required_skills: list[str] | None = None,
    seniority: str = "",
    top_k: int = 3,
) -> str:
    """
    Retrieve RAG context for a SPECIFIC section or output type.
    Only retrieves from relevant knowledge sources — avoids contaminating
    cover letter prompts with resume template docs, and vice versa.

    Args:
        section_type: One of 'summary','experience','skills','projects',
                      'cover_letter','email','linkedin','referral'
        job_title:    Parsed job title for scoring
        required_skills: JD required skills for scoring
        seniority:    Seniority level for scoring
        top_k:        Max chunks per source

    Returns:
        Compact context string ready to inject into an LLM prompt.
    """
    _load_knowledge_store()
    allowed_sources = _SECTION_SOURCE_MAP.get(section_type, ["resume_templates", "ats_rules"])

    query = f"{job_title} {seniority} {section_type} {' '.join((required_skills or [])[:6])}"

    lines = []
    for source in allowed_sources:
        chunks = retrieve(
            query=query,
            job_title=job_title,
            required_skills=required_skills,
            top_k=top_k,
            source_filter=source,
        )
        for chunk in chunks:
            if chunk.text.strip():
                lines.append(f"[{chunk.category.upper()}] {chunk.text}")

    return "\n".join(lines) if lines else ""

