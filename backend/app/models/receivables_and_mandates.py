from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_number = Column(String(100), nullable=False, unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="DUE", nullable=False, index=True)  # DUE, OVERDUE, REMINDER, FOLLOW_UP, PROMISE_TO_PAY, PAID, ESCALATED
    days_overdue = Column(Integer, default=0, nullable=False)
    promise_date = Column(DateTime(timezone=True), nullable=True)
    reminder_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    merchant = relationship("Merchant")
    customer = relationship("Customer")

class Mandate(Base):
    __tablename__ = "mandates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    mandate_number = Column(String(100), nullable=False, unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    billing_interval = Column(String(50), default="monthly", nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # ACTIVE, FAILED, RETRYING, CANCELLED, RECOVERED, ESCALATED
    failure_reason = Column(String(100), nullable=True)
    escalation_reason = Column(String(255), nullable=True)
    provider_mandate_id = Column(String(100), nullable=True, index=True)
    next_retry_date = Column(DateTime(timezone=True), nullable=True)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    merchant = relationship("Merchant")
    customer = relationship("Customer")
    attempts = relationship("MandateRetryAttempt", back_populates="mandate", cascade="all, delete-orphan")


class MandateRetryAttempt(Base):
    __tablename__ = "mandate_retry_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    mandate_id = Column(String(36), ForeignKey("mandates.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    idempotency_key = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, PROCESSING, SUCCEEDED, FAILED, BLOCKED
    failure_reason = Column(String(255), nullable=True)
    provider_payment_id = Column(String(100), nullable=True, index=True)
    policy_decision = Column(String(100), nullable=True)
    attempted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    mandate = relationship("Mandate", back_populates="attempts")

class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    promised_amount = Column(Float, nullable=False)
    promise_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="PROMISED", nullable=False, index=True)  # PROMISED, PAYMENT_REQUESTED, PAYMENT_PENDING, PAID, BROKEN_PROMISE, ESCALATED, STOPPED
    session_id = Column(String(100), nullable=True, index=True)
    
    actual_payment_date = Column(DateTime(timezone=True), nullable=True)
    actual_recovered_amount = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    merchant = relationship("Merchant")
    invoice = relationship("Invoice")
    customer = relationship("Customer")

