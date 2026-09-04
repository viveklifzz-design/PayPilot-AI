from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    razorpay_order_id = Column(String(255), index=True, nullable=True)
    razorpay_payment_link_id = Column(String(255), index=True, nullable=True)
    
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(50), default="CREATED", nullable=False, index=True)  # CREATED, ACTIVE, DROPPED, RECOVERING, CONVERTED, EXPIRED, CANCELLED
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    dropoff_detected_at = Column(DateTime(timezone=True), nullable=True)
    
    source = Column(String(50), default="CHECKOUT", nullable=False)
    raw_metadata = Column(JSON, nullable=True)

    # Relationships
    merchant = relationship("Merchant")
    customer = relationship("Customer")
    recovery_cases = relationship("RecoveryCase", back_populates="checkout_session")
