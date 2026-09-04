from typing import Dict, Any
from app.services.ai.base import BaseAIService
from app.services.ai.schemas import AIDiagnosisOutput
from app.core.logging import logger

class DeterministicAIFallbackService(BaseAIService):
    """
    Guaranteed deterministic fallback service for AI payment diagnosis.
    Engaged automatically when Gemini API is unconfigured, timed out, or returning errors.
    """

    @property
    def provider_name(self) -> str:
        return "fallback"

    @property
    def model_name(self) -> str:
        return "deterministic-rules-fallback"

    @property
    def is_configured(self) -> bool:
        return True

    def diagnose_payment_failure(self, context: Dict[str, Any]) -> AIDiagnosisOutput:
        logger.info("Executing Deterministic AI Fallback Diagnosis...")
        err = (context.get("error_code") or "").upper()
        amount = context.get("amount", 0.0)
        risk_level = context.get("risk_level", "MEDIUM")
        rec_score = context.get("recoverability_score", 0.50)
        
        # Categorize failure code deterministically
        if err in {"BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "NETWORK_ERROR", "BANK_SERVER_DOWN"}:
            category = "NETWORK"
            root_cause = "Bank or Network Gateway Timeout"
            action = "RETRY" if amount <= 50000.0 else "ESCALATE"
            confidence = 0.85
            reason = "Temporary network timeout detected for standard transaction amount."
        elif err in {"OTP_TIMEOUT", "BAD_REQUEST_PAYMENT_CANCELLED"}:
            category = "AUTHENTICATION"
            root_cause = "User Authentication Timeout or Cancellation"
            action = "RECOVERY_LINK"
            confidence = 0.75
            reason = "Customer dropped off during 3DS authentication; recovery link recommended."
        elif err in {"INSUFFICIENT_FUNDS", "BAD_REQUEST_PAYMENT_DECLINED"}:
            category = "INSUFFICIENT_FUNDS"
            root_cause = "Card or Bank Balance Insufficient"
            action = "RECOVERY_LINK"
            confidence = 0.70
            reason = "Payment declined due to balance or limit; payment link allows alternate payment method."
        elif err in {"EXPIRED_CARD", "INVALID_CARD_DETAILS", "INVALID_ACCOUNT"}:
            category = "PAYMENT_METHOD"
            root_cause = "Expired or Invalid Payment Instrument"
            action = "STOP"
            confidence = 0.90
            reason = "Payment method instrument is invalid or expired. Automated retries stopped."
        elif err in {"SUSPECTED_FRAUD", "RISK_CHECK_FAILED", "BLACKLISTED_CARD"}:
            category = "FRAUD_OR_SECURITY"
            root_cause = "Security or Suspected Fraud Flag"
            action = "ESCALATE"
            confidence = 0.95
            reason = "Transaction flagged by provider security checks. Human escalation required."
        else:
            category = "UNKNOWN"
            root_cause = f"Unspecified Payment Failure ({err or 'N/A'})"
            action = "ESCALATE"
            confidence = 0.0
            reason = "AI diagnosis fallback active due to API unavailability or unconfigured credentials."

        return AIDiagnosisOutput(
            risk_level=risk_level,
            recoverability_score=rec_score,
            failure_category=category,
            root_cause=root_cause,
            recommended_action=action,
            confidence=confidence,
            reason=reason,
            explanation=f"Fallback rule applied based on provider error_code '{err}'",
            escalation_required=(action == "ESCALATE")
        )

fallback_ai_service = DeterministicAIFallbackService()
