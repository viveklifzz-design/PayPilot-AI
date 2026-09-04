import pytest
from app.services.recovery.communication_service import communication_service, RecoveryCommunicationPayload

def test_hinglish_voice_and_text_communication():
    payload = RecoveryCommunicationPayload(
        customer_name="Rahul",
        amount=1500.0,
        currency="INR",
        payment_link_url="https://rzp.io/rzp/demo123",
        language="hinglish"
    )

    res = communication_service.generate_recovery_message(payload)
    assert res.language == "hinglish"
    assert "Namaste Rahul" in res.text_message
    assert "₹1,500.00" in res.text_message
    assert "https://rzp.io/rzp/demo123" in res.text_message
    assert "PayPilot AI notification" in res.voice_script
    assert "Voice and text communication assistance only" in res.disclaimer
