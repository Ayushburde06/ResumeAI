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
    job_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
