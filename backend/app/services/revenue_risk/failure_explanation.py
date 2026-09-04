from typing import Optional

def explain_razorpay_failure(
    error_code: Optional[str] = None,
    error_source: Optional[str] = None,
    error_step: Optional[str] = None,
    error_reason: Optional[str] = None,
    error_description: Optional[str] = None
) -> str:
    """
    Provides a safe, deterministic human-readable explanation of Razorpay payment failures.
    Cites payment provider facts when available. NEVER invents specific financial causes if absent.
    """
    reason_str = (error_reason or "").lower()
    code_str = (error_code or "").lower()
    desc_str = (error_description or "").lower()

    if not error_reason and not error_code and not error_description:
        return "Razorpay did not provide a failure reason."

    # Specific Reason Mappings
    if "insufficient" in reason_str or "insufficient" in desc_str or "low_balance" in reason_str:
        return "Payment failed because the payment provider reported insufficient funds or balance constraint."
    
    if "card_expired" in reason_str or "expired_card" in reason_str or "expired" in code_str:
        return "Payment failed because the payment card is expired or invalid."

    if "otp" in reason_str or "authentication" in reason_str or "3d_secure" in reason_str or "auth_failed" in reason_str:
        return "Payment failed due to customer authentication failure or OTP verification timeout."

    if "bank_server_down" in reason_str or "issuer_down" in reason_str or error_source == "bank":
        return "Payment failed due to an issuer bank authorization failure or server downtime."

    if "network_error" in reason_str or "timeout" in code_str or "timed_out" in reason_str:
        return "Payment failed due to a network or technical connection error reported by the payment provider."

    if "user_cancelled" in reason_str or "cancelled" in reason_str or error_source == "customer":
        return "Payment was cancelled or abandoned by the customer during checkout."

    if error_description:
        return f"Payment failed per provider response: {error_description}"

    return f"Payment failed with provider code '{error_code or 'UNKNOWN'}'."
