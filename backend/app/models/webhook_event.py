from sqlalchemy import Column, String, Boolean, DateTime, JSON
from app.db.session import Base
from app.models.base import generate_uuid, utc_now

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(255), unique=True, index=True, nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
