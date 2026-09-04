from pydantic import BaseModel
from typing import Optional

class FailureClassificationResult(BaseModel):
    category: str
    reason: str
    confidence: float = 1.0

def classify_razorpay_failure(
    error_code: Optional[str] = None,
    error_source: Optional[str] = None,
    error_step: Optional[str] = None,
    error_reason: Optional[str] = None,
    error_description: Optional[str] = None
) -> FailureClassificationResult:
    """
    Deterministically maps raw Razorpay payment failure facts to a normalized failure category.
    Prioritizes exact error_reason/error_code matches, then error_source/error_step signals,
    then description heuristics. Falls back safely to UNKNOWN_FAILURE.
    """
    code = (error_code or "").lower()
    reason_str = (error_reason or "").lower()
    source = (error_source or "").lower()
    step = (error_step or "").lower()
    desc = (error_description or "").lower()

    # 1. AUTHENTICATION_FAILURE
    auth_keywords = ["otp", "authentication", "3d_secure", "pin", "verification_failed", "auth_failed", "incorrect_otp", "password"]
    if any(k in reason_str for k in auth_keywords) or any(k in code for k in auth_keywords) or step == "payment_authentication":
        return FailureClassificationResult(
            category="AUTHENTICATION_FAILURE",
            reason=f"Razorpay authentication error signal (reason='{error_reason or 'N/A'}', step='{error_step or 'N/A'}')",
            confidence=1.0
        )

    # 2. INSUFFICIENT_FUNDS
    funds_keywords = ["insufficient", "funds", "low_balance", "balance", "limit_exceeded", "credit_limit"]
    if any(k in reason_str for k in funds_keywords) or any(k in code for k in funds_keywords) or any(k in desc for k in funds_keywords):
        return FailureClassificationResult(
            category="INSUFFICIENT_FUNDS",
            reason=f"Razorpay balance/fund constraint signal (reason='{error_reason or 'N/A'}', code='{error_code or 'N/A'}')",
            confidence=1.0
        )

    # 3. BANK_FAILURE
    bank_keywords = ["bank", "issuer", "issuer_down", "decline_by_bank", "bank_server_down", "issuer_declined"]
    if source == "bank" or any(k in reason_str for k in bank_keywords) or any(k in code for k in bank_keywords):
        return FailureClassificationResult(
            category="BANK_FAILURE",
            reason=f"Razorpay bank/issuer decline signal (source='{error_source or 'bank'}', reason='{error_reason or 'N/A'}')",
            confidence=1.0
        )

    # 4. GATEWAY_FAILURE
    gateway_keywords = ["gateway", "gateway_error", "gateway_timeout", "gateway_technical_error", "acquirer"]
    if source == "gateway" or any(k in reason_str for k in gateway_keywords) or any(k in code for k in gateway_keywords):
        return FailureClassificationResult(
            category="GATEWAY_FAILURE",
            reason=f"Razorpay payment gateway error signal (source='{error_source or 'gateway'}', code='{error_code or 'N/A'}')",
            confidence=1.0
        )

    # 5. NETWORK_OR_TECHNICAL_FAILURE
    net_keywords = ["timed_out", "timeout", "network", "connection", "socket", "504", "502"]
    if any(k in reason_str for k in net_keywords) or any(k in code for k in net_keywords) or any(k in desc for k in net_keywords):
        return FailureClassificationResult(
            category="NETWORK_OR_TECHNICAL_FAILURE",
            reason=f"Razorpay technical/network timeout signal (code='{error_code or 'N/A'}', desc='{error_description or 'N/A'}')",
            confidence=1.0
        )

    # 6. CUSTOMER_ACTION_FAILURE
    customer_keywords = ["customer", "cancelled", "abandoned", "user_cancelled", "expired"]
    if source == "customer" or any(k in reason_str for k in customer_keywords) or any(k in code for k in customer_keywords):
        return FailureClassificationResult(
            category="CUSTOMER_ACTION_FAILURE",
            reason=f"Razorpay customer cancellation/action signal (source='{error_source or 'customer'}', reason='{error_reason or 'N/A'}')",
            confidence=1.0
        )

    # Safe Fallback
    fallback_reason = f"Unclassified Razorpay failure payload (code='{error_code or 'N/A'}', reason='{error_reason or 'N/A'}')"
    return FailureClassificationResult(
        category="UNKNOWN_FAILURE",
        reason=fallback_reason,
        confidence=0.70
    )
