import pytest
from unittest.mock import MagicMock, patch
from app.services.razorpay import RazorpayService, verify_webhook_signature

def test_signature_verification_valid():
    secret = "whsec_test_secret_123"
    raw_body = b'{"event":"payment.failed","amount":1000}'
    import hmac, hashlib
    valid_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    
    assert verify_webhook_signature(raw_body, valid_sig, secret) is True

def test_signature_verification_invalid():
    secret = "whsec_test_secret_123"
    raw_body = b'{"event":"payment.failed","amount":1000}'
    invalid_sig = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    
    assert verify_webhook_signature(raw_body, invalid_sig, secret) is False

def test_signature_verification_missing_args():
    assert verify_webhook_signature(b"data", "", "secret") is False
    assert verify_webhook_signature(b"data", "sig", "") is False

def test_razorpay_service_unconfigured():
    service = RazorpayService(key_id="", key_secret="")
    assert service.is_configured is False
    with pytest.raises(ValueError, match="not configured"):
        _ = service.client
