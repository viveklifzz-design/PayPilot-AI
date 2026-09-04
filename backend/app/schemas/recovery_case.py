from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

class RecoveryCaseBase(BaseModel):
    merchant_id: str
    case_type: str = "PAYMENT_FAILURE"
    transaction_id: Optional[str] = None
    checkout_session_id: Optional[str] = None
    customer_id: Optional[str] = None
    amount: float = Field(..., ge=0)

    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str
    priority_score: float = Field(0.0, ge=0.0, le=100.0)
    priority_level: str = "MEDIUM"
    risk_factors: Optional[List[str]] = None
    status: str

    ai_root_cause: Optional[str] = None
    ai_recommended_action: Optional[str] = None
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_reasoning: Optional[str] = None
    policy_passed: bool = False
    policy_failure_reason: Optional[str] = None
    actual_action_taken: Optional[str] = None
    retry_count: int = 0
    recovered_amount: float = 0.0
    stop_reason: Optional[str] = None

class RecoveryCaseCreate(RecoveryCaseBase):
    pass

class RecoveryCaseResponse(RecoveryCaseBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
