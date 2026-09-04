from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Literal
from datetime import datetime

class AuditLogBase(BaseModel):
    case_id: str
    actor: Literal["SYSTEM", "AI_AGENT", "POLICY_ENGINE", "HUMAN_OPERATOR", "RAZORPAY_WEBHOOK"]
    event_type: str
    description: str
    metadata_json: Optional[Dict[str, Any]] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogResponse(AuditLogBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
