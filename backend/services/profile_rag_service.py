"""
Profile RAG — retrieve relevant evidence chunks from a user's saved career profile.
Complements the global rag_service knowledge base with user-specific facts.

Chunk embeddings are cached per-process so repeated requests don't re-embed
the same profile content (typically 10-20 embedding calls saved per run).
"""
from __future__ import annotations

from schemas.profile import CareerProfileSchema

from services.ai_service import get_embedding
from services.ats_engine import _extract_jd_keywords, _sanitize_jd, _stem, _tokenize
from services.rag_service import RetrievedChunk, cosine_similarity

# ── Embedding cache (process-lifetime, keyed by profile user_id:chunk_id) ────
_embedding_cache: dict[str, list[float]] = {}


def _cached_embed(text: str, cache_key: str) -> list[float] | None:
    """Return cached embedding if available, otherwise compute and cache it."""
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    try:
        vec = get_embedding(text)
        _embedding_cache[cache_key] = vec
        return vec
    except Exception:
        return None


def chunk_profile(career: CareerProfileSchema) -> list[dict]:
    """Split career profile into searchable evidence chunks."""
    chunks: list[dict] = []

    if career.summary.strip():
        chunks.append({
            "id": "summary",
            "text": career.summary.strip(),
            "category": "summary",
            "metadata": {"section": "summary"},
        })

    pi = career.personal_info
    if pi.headline.strip():
        chunks.append({
            "id": "headline",
            "text": pi.headline.strip(),
            "category": "summary",
            "metadata": {"section": "headline"},
        })

    for i, exp in enumerate(career.experience):
        parts = [
            exp.title, exp.company, exp.location,
            " ".join(exp.bullets), " ".join(exp.tech_stack),
        ]
        text = " ".join(p.strip() for p in parts if p and str(p).strip())
        if text:
            chunks.append({
                "id": f"exp_{exp.id or i}",
                "text": text,
                "category": "experience",
                "metadata": {"title": exp.title, "company": exp.company},
            })

    for i, proj in enumerate(career.projects):
        parts = [
            proj.name, proj.role, proj.problem, proj.solution, proj.architecture,
            proj.challenges, " ".join(proj.tech_stack), " ".join(proj.impact_metrics),
            " ".join(proj.bullets),
        ]
        text = " ".join(p.strip() for p in parts if p and str(p).strip())
        if text:
            chunks.append({
                "id": f"proj_{proj.id or i}",
                "text": text,
                "category": "project",
                "metadata": {"name": proj.name, "role": proj.role},
            })

    skill_parts = []
    for key, vals in career.skills.model_dump().items():
        if isinstance(vals, list) and vals:
            skill_parts.extend(vals)
    if skill_parts:
        chunks.append({
            "id": "skills",
            "text": "Skills: " + ", ".join(skill_parts),
            "category": "skills",
            "metadata": {},
        })

    for i, edu in enumerate(career.education):
        text = " ".join(filter(None, [edu.degree, edu.institution, edu.honors]))
        if text:
            chunks.append({
                "id": f"edu_{edu.id or i}",
                "text": text,
                "category": "education",
                "metadata": {},
            })

    return chunks


def _keyword_score(text: str, jd_keywords: set[str]) -> float:
    if not jd_keywords:
        return 0.0
    tokens = {_stem(t) for t in _tokenize(text)}
    text_lower = text.lower()
    hits = 0
    for kw in jd_keywords:
        if " " in kw:
            if kw in text_lower or all(_stem(p) in tokens for p in kw.split()):
                hits += 2
        elif _stem(kw) in tokens or kw in tokens:
            hits += 1
    return hits / max(len(jd_keywords), 1)


def retrieve_profile_chunks(
    career: CareerProfileSchema,
    jd_text: str,
    job_title: str = "",
    required_skills: list[str] | None = None,
    top_k: int = 8,
) -> list[RetrievedChunk]:
    """Retrieve top-k profile chunks relevant to the JD."""
    chunks = chunk_profile(career)
    if not chunks:
        return []

    kw_buckets = _extract_jd_keywords(_sanitize_jd(jd_text))
    jd_keywords = kw_buckets["hard_skills"] | kw_buckets["domain_concepts"]

    query_parts = [jd_text[:500], job_title]
    if required_skills:
        query_parts.extend(required_skills[:10])
    query = " ".join(p for p in query_parts if p)

    query_vector = None
    try:
        query_vector = get_embedding(query)
    except Exception:
        pass

    scored: list[tuple[float, dict]] = []
    for doc in chunks:
        kw_score = _keyword_score(doc["text"], jd_keywords)
        embed_score = 0.0
        if query_vector:
            try:
                cache_key = f"{career.personal_info.email or 'anon'}:{doc['id']}"
                doc_vector = _cached_embed(doc["text"][:800], cache_key)
                if doc_vector:
                    embed_score = cosine_similarity(query_vector, doc_vector)
            except Exception:
                pass
        # Weight embedding + keyword overlap
        combined = embed_score * 0.6 + min(kw_score, 1.0) * 0.4
        if combined > 0:
            scored.append((combined, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, doc in scored[:top_k]:
        results.append(
            RetrievedChunk(
                id=doc["id"],
                text=doc["text"],
                category=doc["category"],
                score=round(score, 4),
                metadata=doc.get("metadata", {}),
            )
        )
    return results


def build_profile_rag_context(
    career: CareerProfileSchema,
    jd_text: str,
    job_analysis: dict | None = None,
    top_k: int = 8,
) -> str:
    """
    Build formatted profile RAG context for LLM prompts.
    Only includes verified user evidence — prevents hallucination.
    """
    ja = job_analysis or {}
    chunks = retrieve_profile_chunks(
        career,
        jd_text,
        job_title=ja.get("job_title", ""),
        required_skills=ja.get("required_skills", []),
        top_k=top_k,
    )
    if not chunks:
        return ""

    lines = [
        "=== USER PROFILE EVIDENCE (use ONLY these verified facts — do NOT invent) ===",
    ]
    for chunk in chunks:
        label = chunk.metadata.get("name") or chunk.metadata.get("title") or chunk.category
        lines.append(f"[{chunk.category.upper()} / {label}] (relevance={chunk.score}) {chunk.text[:600]}")

    lines.append("=== END PROFILE EVIDENCE ===")
    return "\n".join(lines)
