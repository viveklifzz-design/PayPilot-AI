from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, Literal
from datetime import datetime

class RecoveryActionBase(BaseModel):
    case_id: str
    action_type: Literal["RETRY", "RECOVERY_LINK", "REMINDER", "ESCALATE", "STOP"]
    status: Literal["INITIATED", "SUCCESS", "FAILED", "EXPIRED"]
    razorpay_payment_link_id: Optional[str] = None
    short_url: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None

class RecoveryActionCreate(RecoveryActionBase):
    pass

class RecoveryActionResponse(RecoveryActionBase):
    id: str
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)
