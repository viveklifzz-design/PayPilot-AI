from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    merchant_id = Column(String(50), default="m_live_001", nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="INFO", nullable=False, index=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    action_url = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    case = relationship("RecoveryCase", backref="notifications")
