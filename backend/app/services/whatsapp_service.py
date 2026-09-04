import re
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger

class WhatsAppService:
    """
    WhatsApp Cloud API Integration Service for PayPilot AI.
    Handles async communication with Meta Graph API for payment links & customer recovery updates.
    Gracefully handles missing credentials and errors without failing recovery execution.
    """

    def __init__(self, config=settings):
        self.config = config

    @property
    def is_configured(self) -> bool:
        token = str(self.config.WHATSAPP_ACCESS_TOKEN or "")
        phone_id = str(self.config.WHATSAPP_PHONE_NUMBER_ID or "")
        return bool(
            token
            and phone_id
            and not token.startswith("your_")
            and not phone_id.startswith("your_")
        )

    def _sanitize_phone(self, phone: str) -> str:
        """Removes spaces, plus signs, dashes, and non-digit characters from phone numbers."""
        if not phone:
            return ""
        clean = re.sub(r"\D", "", str(phone))
        # Default to India country code 91 if 10-digit number provided
        if len(clean) == 10:
            clean = f"91{clean}"
        return clean

    async def send_text_message(self, to_phone: str, text: str) -> Dict[str, Any]:
        """
        Sends a plain text WhatsApp message via Meta Cloud API.
        """
        phone = self._sanitize_phone(to_phone)
        if not phone:
            logger.warning("WhatsApp send skipped: invalid or empty phone number")
            return {"status": "failed", "reason": "invalid_phone_number"}

        if not self.is_configured:
            logger.info(f"WhatsApp Cloud API credentials not configured. Skipping text message to '{phone[:4]}***'.")
            return {
                "status": "skipped",
                "reason": "whatsapp_not_configured",
                "to": phone,
                "message": text
            }

        url = f"https://graph.facebook.com/{self.config.WHATSAPP_API_VERSION}/{self.config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {self.config.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": text
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                data = response.json()
                if response.status_code in [200, 201]:
                    logger.info(f"Successfully sent WhatsApp message to '{phone[:4]}***'")
                    return {"status": "success", "response": data}
                else:
                    logger.error(f"WhatsApp Cloud API returned status {response.status_code}")
                    return {"status": "failed", "error": data, "http_status": response.status_code}
        except Exception as err:
            logger.error(f"Error executing WhatsApp Cloud API request: {err}")
            return {"status": "error", "message": str(err)}

    async def send_payment_link_message(
        self,
        to_phone: str,
        customer_name: str,
        invoice_number: str,
        amount: float,
        payment_url: str
    ) -> Dict[str, Any]:
        """
        Sends a formatted payment-link recovery message via WhatsApp.
        """
        name = customer_name or "Valued Customer"
        message_body = (
            f"Namaste {name},\n\n"
            f"Aapka Invoice #{invoice_number} (₹{amount:,.2f}) ka payment link ready hai.\n\n"
            f"Aap niche diye gaye secure link se payment complete kar sakte hain:\n"
            f"{payment_url}\n\n"
            f"— PayPilot AI Revenue Recovery"
        )
        return await self.send_text_message(to_phone=to_phone, text=message_body)

whatsapp_service = WhatsAppService()
