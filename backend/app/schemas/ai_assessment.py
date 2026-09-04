from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class DecisionSignal(BaseModel):
    label: str
    positive: bool

class ProviderFacts(BaseModel):
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str
    error_code: Optional[str] = None
    error_reason: Optional[str] = None

class AIExplanation(BaseModel):
    what_happened: str
    why_it_happened: str
    why_paypilot_recommends: str
    customer_next_steps: List[str]
    recommended_payment_methods: List[str]
    what_happens_next: str
    safety_notes: List[str]

class AIAssessmentResponse(BaseModel):
    case_id: str
    recoverable: bool
    decision: str
    confidence: float
    reason_code: str
    why: str
    signals: List[DecisionSignal]
    recommended_action: str
    failure_category: Optional[str] = "PAYMENT_AUTHORIZATION_FAILURE"
    provider_facts: ProviderFacts
    ai_explanation: AIExplanation
    ai_provider: str = "PayPilot AI (Gemini Provider)"
    source_of_truth: str = "Razorpay API & PayPilot DB"
    generated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
