from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    actor = Column(String(50), nullable=False, index=True)  # SYSTEM, AI_AGENT, POLICY_ENGINE, HUMAN_OPERATOR, RAZORPAY_WEBHOOK
    event_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case = relationship("RecoveryCase", back_populates="audit_logs")
