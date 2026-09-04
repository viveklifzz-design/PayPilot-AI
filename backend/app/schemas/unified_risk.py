from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class UnifiedRiskItem(BaseModel):
    case_id: str
    case_type: str = Field(..., description="PAYMENT_FAILURE | CHECKOUT_DROPOFF | SUBSCRIPTION_FAILURE")
    customer_id: Optional[str] = None
    transaction_id: Optional[str] = None
    checkout_session_id: Optional[str] = None
    subscription_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    risk_amount: float
    recoverability_score: float
    priority_score: float
    priority_level: str
    priority_factors: List[str] = []
    failure_category: Optional[str] = None
    status: str
    unified_status: str = Field(..., description="AT_RISK | RECOVERING | RECOVERED | STOPPED | ESCALATED | EXPIRED")
    created_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)

class UnifiedRiskSummaryResponse(BaseModel):
    total_revenue_at_risk: float
    payment_failure_risk: float
    checkout_dropoff_risk: float
    subscription_risk: float
    recoverable_revenue: float
    total_recovered_revenue: float
    unified_recovery_rate: float
    total_cases_count: int
    active_opportunities_count: int
    high_priority_count: int
    cases_by_source: Dict[str, int]
    cases_by_unified_status: Dict[str, int]

class UnifiedOpportunitiesResponse(BaseModel):
    summary: UnifiedRiskSummaryResponse
    opportunities: List[UnifiedRiskItem]
