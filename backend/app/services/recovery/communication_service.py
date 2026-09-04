from pydantic import BaseModel
from typing import Optional

class RecoveryCommunicationPayload(BaseModel):
    customer_name: str
    amount: float
    currency: str = "INR"
    payment_link_url: Optional[str] = None
    language: str = "hinglish"

class RecoveryCommunicationResult(BaseModel):
    language: str
    text_message: str
    voice_script: str
    disclaimer: str = "Voice and text communication assistance only. Money movement strictly requires Policy Gate approval & Razorpay Payment Link."

class CommunicationService:
    """
    Hinglish Voice & Text Recovery Communication Layer.
    Provides localized Hinglish/English/Hindi recovery templates for customer notifications.
    AI / Voice scripts are bounded: Money movement CANNOT be executed via voice.
    """

    def generate_recovery_message(self, payload: RecoveryCommunicationPayload) -> RecoveryCommunicationResult:
        name = payload.customer_name or "Customer"
        amt_str = f"₹{payload.amount:,.2f}"
        url_str = payload.payment_link_url or "<Payment Link>"

        if payload.language.lower() == "hinglish":
            text_msg = (
                f"Namaste {name}, aapka {amt_str} ka payment complete nahi ho paya. "
                f"Aap niche diye gaye link se dobara secure payment kar sakte hain: {url_str}"
            )
            voice = (
                f"Namaste {name}, PayPilot AI notification. Aapka {amt_str} ka recent transaction "
                f"fail ho gaya tha. Aapse request hai ki SMS par bheje gaye link par click karke payment retry karein."
            )
        elif payload.language.lower() == "hindi":
            text_msg = (
                f"नमस्कार {name}, आपका {amt_str} का भुगतान अधूरा रह गया है। "
                f"कृपया इस सुरक्षित लिंक से भुगतान पूरा करें: {url_str}"
            )
            voice = (
                f"नमस्कार {name}, आपकी {amt_str} की भुगतान प्रक्रिया विफल हो गई थी। "
                f"कृपया अपने फ़ोन पर प्राप्त लिंक से पुनः प्रयास करें।"
            )
        else:
            text_msg = (
                f"Hello {name}, your payment of {amt_str} could not be completed. "
                f"Please retry securely using this link: {url_str}"
            )
            voice = (
                f"Hello {name}, this is an automated update regarding your payment of {amt_str}. "
                f"Please click the link sent via SMS to complete your transaction."
            )

        return RecoveryCommunicationResult(
            language=payload.language,
            text_message=text_msg,
            voice_script=voice
        )

    async def send_whatsapp_notification(self, payload: RecoveryCommunicationPayload, phone_number: Optional[str] = None) -> dict:
        if not phone_number:
            return {"status": "skipped", "reason": "no_phone_number"}
        
        msg_res = self.generate_recovery_message(payload)
        from app.services.whatsapp_service import whatsapp_service
        return await whatsapp_service.send_text_message(to_phone=phone_number, text=msg_res.text_message)

communication_service = CommunicationService()
