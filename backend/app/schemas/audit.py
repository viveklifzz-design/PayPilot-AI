from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class AuditLogItemResponse(BaseModel):
    id: str
    case_id: Optional[str] = None
    actor: str
    event_type: str
    description: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TimelineStageItem(BaseModel):
    stage: str  # DETECT, DIAGNOSE, DECIDE, POLICY, EXECUTE, VERIFY, RECOVER
    stage_number: int
    event: str
    timestamp: datetime
    status: str  # completed, allowed, blocked, failed, pending
    title: str
    description: str
    details: Optional[Dict[str, Any]] = None

class CaseTimelineResponse(BaseModel):
    case_id: str
    case_type: str = "PAYMENT_FAILURE"
    status: str
    amount: float
    currency: str = "INR"
    timeline: List[TimelineStageItem]

class ExplainabilityCheckItem(BaseModel):
    check_name: str
    passed: bool
    title: str
    details: str

class DecisionSummaryResponse(BaseModel):
    case_id: str
    case_type: str = "PAYMENT_FAILURE"
    amount: float
    currency: str = "INR"
    failure_category: str
    error_code: str
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
    classification_reason: Optional[str] = None
    ai_confidence: float
    recommended_action: str
    effective_action: str
    policy_allowed: bool
    policy_reason: Optional[str] = None
    execution_status: str
    recovery_status: str
    recovered_amount: float
    provider: str = "RAZORPAY"
    provider_reference: Optional[str] = None
    decision_reason: str
    explainability_checklist: List[ExplainabilityCheckItem]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
