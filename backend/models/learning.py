"""
LearningExample — stores winning resume sections from past successful analyses.
When ATS score >= 88%, individual sections (summary, experience bullets, project
descriptions) are saved here, keyed by normalized job title + top skills.

These are retrieved by the RAG service and injected as real examples into future
prompts — creating a compounding improvement loop.

DeltaPattern — stores what changed between iterations when ATS improved significantly.
Used to understand WHICH edits reliably improve ATS score.
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class LearningExample(Base):
    __tablename__ = "learning_examples"

    id              = Column(Integer, primary_key=True, index=True)
    job_title_key   = Column(String, index=True, nullable=False)
    seniority       = Column(String, default="")
    skills_key      = Column(String, index=True, default="")
    section_type    = Column(String, nullable=False)               # summary|experience|projects|skills
    content         = Column(Text, nullable=False)
    ats_score       = Column(Integer, default=0)
    model_used      = Column(String, default="")
    user_approved   = Column(Boolean, default=None, nullable=True) # None=auto, True=👍, False=👎
    history_id      = Column(Integer, nullable=True)               # link back to ResumeHistory row
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class DeltaPattern(Base):
    """Records what keywords/phrases were added between iterations that raised ATS score."""
    __tablename__ = "delta_patterns"

    id              = Column(Integer, primary_key=True, index=True)
    job_title_key   = Column(String, index=True, nullable=False)
    section_type    = Column(String, nullable=False)               # summary|experience|projects|skills
    ats_before      = Column(Integer, nullable=False)
    ats_after       = Column(Integer, nullable=False)
    ats_gain        = Column(Integer, nullable=False)              # ats_after - ats_before
    keywords_added  = Column(Text, default="")                    # JSON list of keywords added
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
