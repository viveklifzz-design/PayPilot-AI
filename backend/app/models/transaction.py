from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    razorpay_payment_id = Column(String(255), unique=True, index=True, nullable=True)
    razorpay_order_id = Column(String(255), index=True, nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), nullable=False, index=True)  # created, authorized, captured, failed
    error_code = Column(String(100), nullable=True)
    error_description = Column(Text, nullable=True)
    error_source = Column(String(100), nullable=True)
    error_step = Column(String(100), nullable=True)
    error_reason = Column(String(100), nullable=True)
    payment_method = Column(String(50), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    merchant = relationship("Merchant", back_populates="transactions")
    customer = relationship("Customer", back_populates="transactions")
    recovery_cases = relationship("RecoveryCase", back_populates="transaction")
