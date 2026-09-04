from sqlalchemy import Column, String, Numeric, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String(50), default="RAZORPAY", nullable=False)
    provider_subscription_id = Column(String(255), index=True, nullable=True)
    
    plan_name = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    billing_interval = Column(String(20), default="monthly", nullable=False)  # monthly, quarterly, yearly
    
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # ACTIVE, PAYMENT_DUE, PAYMENT_FAILED, RETRY_ELIGIBLE, RETRY_PENDING, PAYMENT_RECOVERED, GRACE_PERIOD, HUMAN_REVIEW, STOPPED, CANCELLED
    
    next_payment_at = Column(DateTime(timezone=True), nullable=True)
    last_payment_at = Column(DateTime(timezone=True), nullable=True)
    
    # Step 10 Recovery State & Policy Fields
    failure_reason = Column(String(100), default="UNKNOWN", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retry_attempts = Column(Integer, default=3, nullable=False)
    grace_period_until = Column(DateTime(timezone=True), nullable=True)
    recovery_status = Column(String(50), default="NOT_STARTED", nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    merchant = relationship("Merchant")
    customer = relationship("Customer")
    attempts = relationship("SubscriptionPaymentAttempt", back_populates="subscription", cascade="all, delete-orphan")
    recovery_cases = relationship("RecoveryCase", back_populates="subscription")


class SubscriptionPaymentAttempt(Base):
    __tablename__ = "subscription_payment_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    attempt_number = Column(Integer, default=1, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), default="FAILED", nullable=False, index=True)  # PENDING, FAILED, SUCCEEDED
    failure_reason = Column(Text, nullable=True)
    
    attempted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="attempts")
    transaction = relationship("Transaction")
