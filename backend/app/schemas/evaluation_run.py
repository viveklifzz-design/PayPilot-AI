from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any
from datetime import datetime

class EvaluationRunBase(BaseModel):
    run_name: str
    total_cases: int = Field(..., ge=0)
    revenue_at_risk: float = Field(..., ge=0)
    recoverable_revenue: float = Field(..., ge=0)
    total_recovered: float = Field(..., ge=0)
    recovery_rate: float = Field(..., ge=0, le=100)
    precision_rate: float = Field(..., ge=0, le=100)
    false_intervention_rate: float = Field(..., ge=0, le=100)
    escalation_rate: float = Field(..., ge=0, le=100)
    safe_stop_rate: float = Field(..., ge=0, le=100)
    metrics: Dict[str, Any]

class EvaluationRunCreate(EvaluationRunBase):
    pass

class EvaluationRunResponse(EvaluationRunBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
