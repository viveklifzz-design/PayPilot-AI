from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recovery_case import RecoveryCase
from app.models.audit_log import AuditLog
from app.core.config import settings
from app.core.logging import logger

class FailureCategory(str, Enum):
    AI_SERVICE_FAILURE = "AI_SERVICE_FAILURE"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_INVALID_RESPONSE = "AI_INVALID_RESPONSE"
    API_UNAVAILABLE = "API_UNAVAILABLE"
    API_TIMEOUT = "API_TIMEOUT"
    API_5XX = "API_5XX"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    RAZORPAY_ORDER_FAILURE = "RAZORPAY_ORDER_FAILURE"
    RAZORPAY_CHECKOUT_FAILURE = "RAZORPAY_CHECKOUT_FAILURE"
    RAZORPAY_CALLBACK_FAILURE = "RAZORPAY_CALLBACK_FAILURE"
    RAZORPAY_PROVIDER_FAILURE = "RAZORPAY_PROVIDER_FAILURE"
    PAYMENT_VERIFICATION_FAILURE = "PAYMENT_VERIFICATION_FAILURE"
    POLICY_GATE_FAILURE = "POLICY_GATE_FAILURE"
    STOPPING_RULE_FAILURE = "STOPPING_RULE_FAILURE"
    HUMAN_ESCALATION_FAILURE = "HUMAN_ESCALATION_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"

class RetryPolicy(str, Enum):
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class FailureStepLineage(BaseModel):
    step: int
    title: str
    description: str
    status: str

class FailureScenarioDetail(BaseModel):
    scenario_key: str
    category: FailureCategory
    title: str
    description: str
    error_code: str
    retryable: bool
    retry_policy: RetryPolicy
    detection_mechanism: str
    fallback_action: str
    final_case_state: str
    user_message: str

class SimulateFailureRequest(BaseModel):
    scenario_key: str
    target_case_id: Optional[str] = None

class SimulateFailureResponse(BaseModel):
    scenario_key: str
    category: FailureCategory
    error_code: str
    message: str
    user_message: str
    retryable: bool
    retry_policy: RetryPolicy
    step_by_step_lineage: List[FailureStepLineage]
    case_state_preserved: str
    recovered_amount_preserved: float
    audit_logged: bool
    simulated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FailureFallbackService:
    """
    PayPilot AI Failure Taxonomy & Safe Fallback Engine.
    Classifies system failures, enforces fail-closed safety boundaries,
    resolves safe fallbacks, and executes test-mode failure simulations.
    """

    SCENARIOS: Dict[str, FailureScenarioDetail] = {
        "AI_UNAVAILABLE": FailureScenarioDetail(
            scenario_key="AI_UNAVAILABLE",
            category=FailureCategory.AI_SERVICE_FAILURE,
            title="AI Explanation Service Unavailable",
            description="Gemini API endpoint timeout, rate limit (429), or network drop.",
            error_code="ERR_AI_TIMEOUT",
            retryable=True,
            retry_policy=RetryPolicy.RETRYABLE,
            detection_mechanism="Gemini client exception handler catches timeout & fallback to Provider Facts.",
            fallback_action="Use deterministic provider facts explanation; display N/A for AI confidence; Policy Gate remains authoritative.",
            final_case_state="OPEN (Unchanged)",
            user_message="AI explanation is temporarily unavailable. Displaying verified payment provider facts."
        ),
        "RAZORPAY_ORDER_FAILURE": FailureScenarioDetail(
            scenario_key="RAZORPAY_ORDER_FAILURE",
            category=FailureCategory.RAZORPAY_ORDER_FAILURE,
            title="Razorpay Recovery Order Creation Failed",
            description="Payment gateway rejects order creation due to network drop or provider outage.",
            error_code="ERR_RAZORPAY_ORDER_FAILED",
            retryable=True,
            retry_policy=RetryPolicy.RETRYABLE,
            detection_mechanism="Razorpay HTTP client catches 5xx / connection error.",
            fallback_action="Do not launch checkout modal; preserve case state; log audit event; prompt retry button.",
            final_case_state="OPEN (Unchanged)",
            user_message="Secure recovery checkout could not be initiated. Please click Retry Checkout."
        ),
        "PAYMENT_VERIFICATION_FAILURE": FailureScenarioDetail(
            scenario_key="PAYMENT_VERIFICATION_FAILURE",
            category=FailureCategory.PAYMENT_VERIFICATION_FAILURE,
            title="Razorpay HMAC Signature Mismatch",
            description="Invalid payment signature or tampered callback credentials received.",
            error_code="ERR_HMAC_SIGNATURE_INVALID",
            retryable=False,
            retry_policy=RetryPolicy.NON_RETRYABLE,
            detection_mechanism="Server-side HMAC-SHA256 signature verification mismatch against secret.",
            fallback_action="Reject transaction; do NOT mark case RECOVERED; audit security anomaly; escalate for review.",
            final_case_state="OPEN / ESCALATED",
            user_message="Payment signature verification failed. Case marked for security inspection."
        ),
        "PROVIDER_VERIFICATION_FAILURE": FailureScenarioDetail(
            scenario_key="PROVIDER_VERIFICATION_FAILURE",
            category=FailureCategory.RAZORPAY_PROVIDER_FAILURE,
            title="Razorpay Provider API Verification Failed",
            description="Razorpay API returns uncaptured status, wrong order ID, or amount mismatch.",
            error_code="ERR_PROVIDER_NOT_CAPTURED",
            retryable=False,
            retry_policy=RetryPolicy.NON_RETRYABLE,
            detection_mechanism="Direct Razorpay REST API call GET /v1/payments/{id} fails status assertion.",
            fallback_action="Reject recovery update; zero financial mutation; preserve open case state.",
            final_case_state="OPEN (Unchanged)",
            user_message="Payment captured status could not be verified on Razorpay. Recovery not recorded."
        ),
        "POLICY_GATE_FAIL_CLOSED": FailureScenarioDetail(
            scenario_key="POLICY_GATE_FAIL_CLOSED",
            category=FailureCategory.POLICY_GATE_FAILURE,
            title="Policy Gate Anomaly / Fail-Closed",
            description="Policy evaluation encounters missing database fields or anomaly.",
            error_code="ERR_POLICY_EVAL_ANOMALY",
            retryable=False,
            retry_policy=RetryPolicy.REVIEW_REQUIRED,
            detection_mechanism="PolicyGate exception catch block forces fail-closed decision.",
            fallback_action="Default to REVIEW_REQUIRED; block autonomous recovery checkout; notify operator.",
            final_case_state="ESCALATED (Review Required)",
            user_message="Policy Gate evaluation encountered an anomaly. Case escalated for human review."
        ),
        "STOPPING_RULES_FAIL_CLOSED": FailureScenarioDetail(
            scenario_key="STOPPING_RULES_FAIL_CLOSED",
            category=FailureCategory.STOPPING_RULE_FAILURE,
            title="Stopping Rules Mandatory Halt",
            description="Case exceeds 3 retry attempts or violates safe recovery boundary.",
            error_code="ERR_STOPPING_HALT_REACHED",
            retryable=False,
            retry_policy=RetryPolicy.NON_RETRYABLE,
            detection_mechanism="StoppingRules engine detects retry_count >= 3.",
            fallback_action="Halt automated recovery; lock checkout session; audit termination event.",
            final_case_state="STOPPED",
            user_message="Automated recovery halted after maximum retry attempts to protect customer."
        ),
        "HUMAN_ESCALATION_FAILURE": FailureScenarioDetail(
            scenario_key="HUMAN_ESCALATION_FAILURE",
            category=FailureCategory.HUMAN_ESCALATION_FAILURE,
            title="Human Escalation Operator Unavailable",
            description="Operator queue offline or action payload malformed.",
            error_code="ERR_HUMAN_QUEUE_OFFLINE",
            retryable=True,
            retry_policy=RetryPolicy.REVIEW_REQUIRED,
            detection_mechanism="HumanEscalation service exception handler.",
            fallback_action="Preserve escalated status; preserve case state; block automated checkout.",
            final_case_state="ESCALATED (Unchanged)",
            user_message="Human operator status could not be updated. Case remains safely in review queue."
        )
    }

    def list_scenarios(self) -> List[FailureScenarioDetail]:
        return list(self.SCENARIOS.values())

    async def simulate_failure(
        self,
        request: SimulateFailureRequest,
        db: AsyncSession
    ) -> SimulateFailureResponse:
        scenario = self.SCENARIOS.get(request.scenario_key)
        if not scenario:
            scenario = FailureScenarioDetail(
                scenario_key=request.scenario_key,
                category=FailureCategory.UNKNOWN_FAILURE,
                title="Unknown Failure Scenario",
                description="Unclassified system failure event.",
                error_code="ERR_UNKNOWN",
                retryable=True,
                retry_policy=RetryPolicy.RETRYABLE,
                detection_mechanism="Generic Exception Handler",
                fallback_action="Preserve case state; log diagnostic traceback; prompt safe retry.",
                final_case_state="OPEN",
                user_message="An unexpected system anomaly occurred. Please try again."
            )

        # Target Case State Inspection (Default to test case or authoritative case d669... protection)
        case_id = request.target_case_id or "e666a5b2-3c8d-4f1e-9a2b-7c4d1e8f3a5b"
        
        # Absolute Protected Case Protection: If d669dce3-b855-4348-b457-f0ef7c34b6b1 passed, do NOT mutate it!
        if case_id == "d669dce3-b855-4348-b457-f0ef7c34b6b1":
            case_id = "e666a5b2-3c8d-4f1e-9a2b-7c4d1e8f3a5b"

        case = await db.get(RecoveryCase, case_id)
        current_state = case.status if case else "OPEN"
        rec_amt = float(case.recovered_amount if case and case.recovered_amount else 0.0)

        # Build Step-by-Step Lineage (Failure -> Detection -> Fallback -> Final State)
        lineage = [
            FailureStepLineage(
                step=1,
                title="1. Failure Event Occurred",
                description=f"{scenario.title}: {scenario.description}",
                status="FAILED"
            ),
            FailureStepLineage(
                step=2,
                title="2. Failure Detection",
                description=scenario.detection_mechanism,
                status="DETECTED"
            ),
            FailureStepLineage(
                step=3,
                title="3. Safe Fallback Executed",
                description=scenario.fallback_action,
                status="FALLBACK_APPLIED"
            ),
            FailureStepLineage(
                step=4,
                title="4. Final Verified State",
                description=f"Case status: {current_state} (Zero false recovery). {scenario.user_message}",
                status="SAFE_STATE_CONFIRMED"
            )
        ]

        # Audit Log Entry (Safe Diagnostic Logging)
        try:
            audit = AuditLog(
                case_id=case_id if case else None,
                event_type=f"FAILURE_SIMULATION_{scenario.category}",
                actor="SYSTEM_FAILURE_ENGINE",
                description=f"Simulated failure scenario {scenario.scenario_key}: {scenario.user_message}",
                metadata_json={
                    "scenario_key": scenario.scenario_key,
                    "error_code": scenario.error_code,
                    "retry_policy": scenario.retry_policy,
                    "preserved_status": current_state
                }
            )
            db.add(audit)
            await db.commit()
            audit_logged = True
        except Exception as e:
            logger.warning(f"Audit log writing failed during failure simulation: {e}")
            audit_logged = False

        return SimulateFailureResponse(
            scenario_key=scenario.scenario_key,
            category=scenario.category,
            error_code=scenario.error_code,
            message=scenario.description,
            user_message=scenario.user_message,
            retryable=scenario.retryable,
            retry_policy=scenario.retry_policy,
            step_by_step_lineage=lineage,
            case_state_preserved=current_state,
            recovered_amount_preserved=rec_amt,
            audit_logged=audit_logged
        )

failure_fallback = FailureFallbackService()
