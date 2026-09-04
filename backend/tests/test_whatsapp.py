import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.whatsapp_service import WhatsAppService, whatsapp_service

client = TestClient(app)

def test_whatsapp_webhook_verification_success(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test_verify_token_123")
    response = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token_123",
            "hub.challenge": "challenge_string_9999"
        }
    )
    assert response.status_code == 200
    assert response.text == "challenge_string_9999"

def test_whatsapp_webhook_verification_failure(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test_verify_token_123")
    response = client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_string_9999"
        }
    )
    assert response.status_code == 403
    assert response.text == "Verification failed"

def test_whatsapp_webhook_verification_no_params():
    response = client.get("/api/v1/webhooks/whatsapp")
    assert response.status_code == 403
    assert response.text == "Verification failed"

def test_whatsapp_webhook_post_text_message():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "12345",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"profile": {"name": "Test Customer"}, "wa_id": "919876543210"}],
                    "messages": [{
                        "from": "919876543210",
                        "id": "wamid.test_msg_001",
                        "timestamp": "1678901234",
                        "text": {"body": "Payment status check"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    response = client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_whatsapp_webhook_post_unknown_event():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "12345",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "statuses": [{
                        "id": "wamid.test_msg_001",
                        "recipient_id": "919876543210",
                        "status": "delivered",
                        "timestamp": "1678901235"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    response = client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_whatsapp_webhook_post_malformed_payload():
    response = client.post(
        "/api/v1/webhooks/whatsapp",
        content=b"invalid-raw-body-not-json{",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_whatsapp_service_unconfigured():
    mock_config = MagicMock()
    mock_config.WHATSAPP_ACCESS_TOKEN = None
    mock_config.WHATSAPP_PHONE_NUMBER_ID = None
    mock_service = WhatsAppService(config=mock_config)

    assert mock_service.is_configured is False
    res = await mock_service.send_text_message("919876543210", "Hello Test")
    assert res["status"] == "skipped"
    assert res["reason"] == "whatsapp_not_configured"

@pytest.mark.asyncio
async def test_whatsapp_service_successful_send_mocked():
    mock_config = MagicMock()
    mock_config.WHATSAPP_ACCESS_TOKEN = "fake_access_token"
    mock_config.WHATSAPP_PHONE_NUMBER_ID = "100609346302247"
    mock_config.WHATSAPP_API_VERSION = "v20.0"
    service = WhatsAppService(config=mock_config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "919876543210", "wa_id": "919876543210"}],
        "messages": [{"id": "wamid.HBgL12345678"}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        res = await service.send_payment_link_message(
            to_phone="919876543210",
            customer_name="John Doe",
            invoice_number="INV-1002",
            amount=1500.0,
            payment_url="http://localhost:3000/recover/case_123"
        )
        assert res["status"] == "success"
        assert res["response"]["messages"][0]["id"] == "wamid.HBgL12345678"

        # Verify token or secret is NOT in args/url in plain sight
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "100609346302247" in args[0]
        assert kwargs["headers"]["Authorization"] == "Bearer fake_access_token"

def test_whatsapp_test_endpoint_mocked(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "123456789")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "919876543210", "wa_id": "919876543210"}],
        "messages": [{"id": "wamid.HBgL_test_endpoint"}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        response = client.post(
            "/api/v1/test/whatsapp",
            json={
                "to_phone": "919876543210",
                "message": "PayPilot AI WhatsApp integration test successful."
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["response"]["messages"][0]["id"] == "wamid.HBgL_test_endpoint"

