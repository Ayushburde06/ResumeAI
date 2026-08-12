"""Tests for profile RAG retrieval."""
from schemas.profile import (
    CareerProfileSchema,
    ExperienceSchema,
    PersonalInfoSchema,
    ProjectSchema,
)
from services.profile_rag_service import (
    build_profile_rag_context,
    chunk_profile,
    retrieve_profile_chunks,
)


def _career() -> CareerProfileSchema:
    return CareerProfileSchema(
        personal_info=PersonalInfoSchema(name="Alex Dev"),
        summary="Full-stack engineer",
        experience=[
            ExperienceSchema(
                title="Backend Engineer",
                company="TechCo",
                bullets=["Built FastAPI services", "Deployed on AWS"],
                tech_stack=["Python", "FastAPI", "AWS"],
            )
        ],
        projects=[
            ProjectSchema(
                name="ChatBot",
                problem="Customer support overload",
                solution="Built RAG chatbot with Python and PostgreSQL",
                tech_stack=["Python", "PostgreSQL", "OpenAI"],
                bullets=["Reduced ticket volume 30%"],
            )
        ],
    )


def test_chunk_profile():
    chunks = chunk_profile(_career())
    assert len(chunks) >= 3
    categories = {c["category"] for c in chunks}
    assert "experience" in categories
    assert "project" in categories


def test_retrieve_profile_chunks_ranks_relevant():
    career = _career()
    jd = "Looking for Python FastAPI PostgreSQL backend engineer AWS"
    chunks = retrieve_profile_chunks(career, jd, job_title="Backend Engineer", required_skills=["Python", "FastAPI"])
    assert len(chunks) >= 1
    top_text = chunks[0].text.lower()
    assert "python" in top_text or "fastapi" in top_text


def test_build_profile_rag_context():
    ctx = build_profile_rag_context(_career(), "Python FastAPI backend role", {"job_title": "Backend Engineer", "required_skills": ["Python"]})
    assert "USER PROFILE EVIDENCE" in ctx
    assert "do NOT invent" in ctx.lower() or "NOT invent" in ctx
