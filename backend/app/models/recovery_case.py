from sqlalchemy import Column, String, Numeric, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_type = Column(String(50), default="PAYMENT_FAILURE", nullable=False, index=True)  # PAYMENT_FAILURE, CHECKOUT_DROPOFF, SUBSCRIPTION_FAILURE
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True, index=True)
    checkout_session_id = Column(String(36), ForeignKey("checkout_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    subscription_attempt_id = Column(String(36), ForeignKey("subscription_payment_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    mandate_id = Column(String(36), ForeignKey("mandates.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    amount = Column(Numeric(12, 2), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    
    priority_score = Column(Numeric(5, 2), nullable=False, default=0.0)
    priority_level = Column(String(20), nullable=False, default="MEDIUM", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors = Column(JSON, nullable=True)

    status = Column(String(50), nullable=False, index=True)  # OPEN, DIAGNOSED, ACTION_PENDING, IN_PROGRESS, RECOVERED, FAILED, ESCALATED, STOPPED
    
    ai_root_cause = Column(String(100), nullable=True)
    ai_recommended_action = Column(String(50), nullable=True)
    ai_confidence = Column(Numeric(5, 2), nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    
    policy_passed = Column(Boolean, default=False, nullable=False)
    policy_failure_reason = Column(Text, nullable=True)
    
    actual_action_taken = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    recovered_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    stop_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="recovery_cases")
    transaction = relationship("Transaction", back_populates="recovery_cases")
    customer = relationship("Customer", back_populates="recovery_cases")
    checkout_session = relationship("CheckoutSession", back_populates="recovery_cases")
    subscription = relationship("Subscription", back_populates="recovery_cases")
    actions = relationship("RecoveryAction", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")
    ai_diagnoses = relationship("AIDiagnosis", back_populates="case", cascade="all, delete-orphan")
