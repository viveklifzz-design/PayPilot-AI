from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any
from datetime import datetime

class WebhookEventBase(BaseModel):
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    processed: bool = False

class WebhookEventCreate(WebhookEventBase):
    pass

class WebhookEventResponse(WebhookEventBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
