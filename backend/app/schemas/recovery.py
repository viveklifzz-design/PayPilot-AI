from pydantic import BaseModel, ConfigDict
from typing import Optional

class ExecutionRequest(BaseModel):
    action: Optional[str] = None
    ai_confidence: Optional[float] = None

class ExecutionResponse(BaseModel):
    allowed: bool = True
    policy_allowed: bool = True
    case_id: str
    action_id: Optional[str] = None
    requested_action: str
    effective_action: str
    action: Optional[str] = None
    status: str
    execution_status: str
    provider: Optional[str] = "RAZORPAY"
    provider_reference: Optional[str] = None
    payment_url: Optional[str] = None
    payment_link_url: Optional[str] = None
    amount: float
    currency: str = "INR"
    recovered_amount: float = 0.0
    message: str

    model_config = ConfigDict(from_attributes=True)
