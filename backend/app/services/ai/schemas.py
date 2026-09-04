from pydantic import BaseModel, Field
from typing import Literal, Optional

class AIDiagnosisOutput(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recoverability_score: float = Field(..., ge=0.0, le=1.0)
    failure_category: Literal[
        "NETWORK",
        "AUTHENTICATION",
        "INSUFFICIENT_FUNDS",
        "LIMIT_EXCEEDED",
        "USER_CANCELLED",
        "PAYMENT_METHOD",
        "BANK_DECLINED",
        "FRAUD_OR_SECURITY",
        "UNKNOWN"
    ]
    root_cause: str = Field(..., description="Short title of the failure root cause")
    recommended_action: Literal["RETRY", "RECOVERY_LINK", "REMINDER", "ESCALATE", "STOP"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., description="Merchant-facing explanation of decision logic")
    explanation: Optional[str] = Field(None, description="Technical summary for audit trail")
    escalation_required: bool = False
