from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class EvaluationRunRequest(BaseModel):
    dataset_size: Optional[int] = Field(None, ge=1, le=5000)
    batch_size: Optional[int] = Field(None, ge=1, le=5000)
    seed: int = Field(42, ge=0)
    mode: str = Field("deterministic", description="Must be 'deterministic' or 'live_ai'")
    run_name: Optional[str] = None

    @property
    def effective_size(self) -> int:
        return self.dataset_size or self.batch_size or 1000

class CaseDetailResponse(BaseModel):
    case_num: Optional[int] = None
    case_id: Optional[str] = None
    amount: float
    error_code: Optional[str] = None
    failure_reason: Optional[str] = None
    risk_level: str
    risk_score: float
    recoverability_score: Optional[float] = 0.0
    ai_root_cause: Optional[str] = "N/A"
    ai_recommended_action: Optional[str] = "RECOVERY_LINK"
    ai_confidence: Optional[float] = 0.85
    policy_allowed: bool
    effective_action: str
    policy_violations: List[str] = []
    final_status: str
    recovered_amount: float = 0.0
    simulation_notes: Optional[str] = None
    ground_truth_category: Optional[str] = None
    ground_truth_action: Optional[str] = None
    expected_recoverable: Optional[bool] = False

class EvaluationRunSummaryResponse(BaseModel):
    run_id: str
    run_name: str
    seed: int
    dataset_size: int
    batch_size: int
    mode: str
    total_cases: int = 1000
    revenue_at_risk: float
    total_failed_amount: float
    recoverable_revenue: float = 0.0
    total_recovered: float
    revenue_recovered: float = 0.0
    remaining_revenue_at_risk: float
    diagnosed_count: int = 0
    policy_allowed_count: int = 0
    policy_blocked_count: int = 0
    escalated_count: int = 0
    recovery_attempt_count: int = 0
    recovered_count: int = 0
    failed_recovery_count: int = 0
    stopped_count: int = 0
    recovery_rate: float
    recovery_success_rate: float = 0.0
    precision: float = 0.0
    precision_rate: float = 0.0
    recall: float = 0.0
    intervention_rate: float = 0.0
    false_intervention_rate: float = 0.0
    escalation_rate: float = 0.0
    safe_stop_rate: float = 0.0
    unsafe_action_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
