from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class MeetingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    participant_email = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    google_event_id = Column(String, nullable=True)
    meet_link = Column(String, nullable=True)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    organizer = relationship("User", back_populates="meetings", foreign_keys=[organizer_id])
