from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.services.ai.schemas import AIDiagnosisOutput
from app.services.policy import PolicyCheckResult

class AIDiagnosisResponse(BaseModel):
    case_id: str
    provider: str
    model: str
    prompt_version: str
    diagnosis: AIDiagnosisOutput
    policy_result: PolicyCheckResult
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
