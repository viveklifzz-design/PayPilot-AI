from pydantic import BaseModel, Field

class AnalyticsMetricsResponse(BaseModel):
    revenue_at_risk: float = Field(..., description="Total value of failed/at-risk payments")
    payment_failure_risk: float = Field(0.0, description="Revenue at risk from payment failures")
    checkout_dropoff_risk: float = Field(0.0, description="Revenue at risk from checkout drop-offs")
    subscription_risk: float = Field(0.0, description="Revenue at risk from subscription failures")
    recovered_revenue: float = Field(..., description="Total successfully recovered revenue")
    recovery_rate: float = Field(..., description="Percentage of at-risk revenue recovered")
    total_failed_payments: int = Field(..., description="Total count of failed payment attempts")
    checkout_dropoff_cases_count: int = Field(0, description="Total count of checkout drop-off cases")
    subscription_cases_count: int = Field(0, description="Total count of subscription failure cases")
    recoverable_cases: int = Field(..., description="Count of cases flagged as recoverable")
    active_recoveries: int = Field(..., description="Count of cases currently in progress")
    escalated_cases: int = Field(..., description="Count of cases requiring human review")
    safely_stopped_cases: int = Field(..., description="Count of cases safely stopped by policy")

class RecoveryFunnelStage(BaseModel):
    stage: str
    count: int
    amount: float

class RecoveryFunnelResponse(BaseModel):
    funnel: list[RecoveryFunnelStage]

class B2BReceivablesAnalytics(BaseModel):
    total_receivables: int = Field(..., description="Total B2B receivables tracked")
    total_outstanding_amount: float = Field(..., description="Total value of outstanding B2B invoices")
    total_revenue_at_risk: float = Field(..., description="Total B2B revenue at risk")
    overdue_invoices_count: int = Field(..., description="Count of overdue B2B invoices")
    promises_count: int = Field(..., description="Count of Promise-to-Pay agreements recorded")
    promises_fulfilled_count: int = Field(..., description="Count of fulfilled Promise-to-Pay agreements")
    broken_promises_count: int = Field(..., description="Count of broken Promise-to-Pay agreements")
    payment_requests_count: int = Field(..., description="Count of payment requests issued")
    payments_completed_count: int = Field(..., description="Count of completed payments")
    b2b_recovered_amount: float = Field(..., description="Total B2B revenue recovered")
    recovery_rate: float = Field(..., description="B2B recovery rate percentage")
    escalated_count: int = Field(..., description="Count of B2B cases escalated to human review")
