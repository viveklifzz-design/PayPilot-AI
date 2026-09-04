import hmac
import hashlib
from typing import Optional
from app.core.config import settings
from app.core.logging import logger

def verify_webhook_signature(raw_body: bytes, signature: str, secret: Optional[str] = None) -> bool:
    """
    Verify Razorpay webhook signature using HMAC SHA256 in constant time.
    MUST be computed against the raw HTTP request body bytes.
    """
    webhook_secret = secret or settings.RAZORPAY_WEBHOOK_SECRET
    sig_present = bool(signature and signature.strip())
    sec_present = bool(webhook_secret and webhook_secret.strip())

    body_sha = hashlib.sha256(raw_body).hexdigest()[:12] if raw_body else "EMPTY"
    secret_sha = hashlib.sha256(webhook_secret.encode("utf-8")).hexdigest()[:12] if sec_present else "NONE"
    secret_len = len(webhook_secret) if webhook_secret else 0

    if not sig_present or not sec_present:
        logger.warning(
            f"Webhook signature verification failed: signature_header_exists={sig_present}, "
            f"configured_secret_exists={sec_present}, body_sha256_12={body_sha}, "
            f"secret_sha256_12={secret_sha}, secret_len={secret_len}, verification_result=FAIL"
        )
        return False

    try:
        expected_signature = hmac.new(
            key=webhook_secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        cleaned_signature = signature.strip()
        is_valid = hmac.compare_digest(expected_signature, cleaned_signature)
        result_str = "PASS" if is_valid else "FAIL"

        rx_prefix = cleaned_signature[:8] if len(cleaned_signature) >= 8 else cleaned_signature
        exp_prefix = expected_signature[:8] if len(expected_signature) >= 8 else expected_signature

        # Safe diagnostic logging without revealing raw secret
        log_msg = (
            f"Webhook signature verification: request_received=True, signature_header_exists=True, "
            f"body_sha256_12={body_sha}, secret_sha256_12={secret_sha}, secret_len={secret_len}, "
            f"rx_sig_prefix={rx_prefix}..., exp_sig_prefix={exp_prefix}..., verification_result={result_str}"
        )

        if is_valid:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

        return is_valid
    except Exception as e:
        logger.error(f"Error during webhook signature verification: {e}")
        return False
