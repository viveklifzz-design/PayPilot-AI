from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class AIDiagnosis(Base):
    __tablename__ = "ai_diagnoses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="gemini")  # gemini, fallback
    model = Column(String(50), nullable=False, default="gemini-2.5-flash")
    prompt_version = Column(String(20), nullable=False, default="v1.0.0")
    
    risk_level = Column(String(20), nullable=False)
    recoverability_score = Column(Numeric(5, 2), nullable=False)
    failure_category = Column(String(50), nullable=False)
    root_cause = Column(String(100), nullable=False)
    recommended_action = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 2), nullable=False)
    reason = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    raw_response = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    case = relationship("RecoveryCase", back_populates="ai_diagnoses")
