from sqlalchemy import Column, Integer, Boolean, ForeignKey
from database import Base

FREE_LIMIT = 3


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    analysis_count = Column(Integer, default=0, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
