from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)  # RETRY, RECOVERY_LINK, REMINDER, ESCALATE, STOP
    status = Column(String(50), nullable=False, index=True)  # INITIATED, SUCCESS, FAILED, EXPIRED
    razorpay_payment_link_id = Column(String(255), nullable=True, index=True)
    short_url = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)
    executed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case = relationship("RecoveryCase", back_populates="actions")
