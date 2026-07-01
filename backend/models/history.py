from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base


class ResumeHistory(Base):
    __tablename__ = "resume_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = Column(String, nullable=True)
    ats_score = Column(Integer, nullable=True)
    tailored_resume = Column(JSON, nullable=False)
    cover_letter = Column(JSON, nullable=True)
    application_email = Column(JSON, nullable=True)
    job_analysis = Column(JSON, nullable=True)
    quality_report = Column(JSON, nullable=True)
    job_description = Column(Text, nullable=True)
    # Keyword metadata — persisted so history results show accurate keyword counts
    matched_keywords = Column(JSON, nullable=True)   # list[str]
    missing_keywords = Column(JSON, nullable=True)   # list[str]
    total_keywords = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
