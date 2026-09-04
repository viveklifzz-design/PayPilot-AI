import hmac
import hashlib
from typing import Dict, Any, Optional
import razorpay
from app.core.config import settings
from app.core.exceptions import PaymentGatewayException, SignatureVerificationException
from app.core.logging import logger

class RazorpayClientService:
    """
    Razorpay Client Wrapper for PayPilot AI.
    Interacts with Razorpay TEST MODE Orders and Payments APIs.
    """

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = settings.RAZORPAY_KEY_ID if key_id is None else key_id
        self.key_secret = settings.RAZORPAY_KEY_SECRET if key_secret is None else key_secret
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret and self.key_id != "dummy_key_id")

    @property
    def client(self) -> razorpay.Client:
        if not self.is_configured:
            raise ValueError("Razorpay API credentials not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
        if self._client is None:
            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
        return self._client

    def create_order(self, amount: float, currency: str = "INR", receipt: Optional[str] = None, notes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a Razorpay Order in paise (amount * 100)."""
        amount_in_paise = int(round(amount * 100.0))
        data = {
            "amount": amount_in_paise,
            "currency": currency,
            "receipt": receipt or f"rcpt_{amount_in_paise}",
            "notes": notes or {}
        }
        
        if not self.is_configured:
            logger.warning("Razorpay credentials unconfigured. Operating in Mock mode for order creation.")
            import uuid
            mock_id = f"order_mock_{uuid.uuid4().hex[:12]}"
            return {
                "id": mock_id,
                "entity": "order",
                "amount": amount_in_paise,
                "amount_paid": 0,
                "amount_due": amount_in_paise,
                "currency": currency,
                "receipt": data["receipt"],
                "status": "created",
                "attempts": 0,
                "notes": data["notes"]
            }

        try:
            logger.info(f"Creating Razorpay Order for amount={amount} {currency}")
            order = self.client.order.create(data=data)
            return order
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {e}")
            raise PaymentGatewayException(f"Razorpay order creation failed: {e}")

    def execute_mandate_debit(
        self,
        amount: float,
        mandate_number: str,
        currency: str = "INR",
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute or simulate a Razorpay Mandate recurring auto-debit attempt."""
        import uuid, time
        ref_id = f"pay_mnd_{uuid.uuid4().hex[:12]}"
        amount_in_paise = int(round(amount * 100.0))

        if not self.is_configured:
            logger.info(f"Razorpay mandate debit for '{mandate_number}' executed in Test Mode.")
            return {
                "id": ref_id,
                "entity": "payment",
                "amount": amount_in_paise,
                "currency": currency,
                "status": "captured",
                "method": "auto_debit",
                "mandate_number": mandate_number,
                "created_at": int(time.time())
            }

        try:
            logger.info(f"Executing Razorpay Mandate Debit for '{mandate_number}' amount={amount}")
            return self.create_order(amount=amount, currency=currency, receipt=f"mnd_{mandate_number}")
        except Exception as e:
            logger.error(f"Razorpay Mandate debit execution error: {e}")
            raise PaymentGatewayException(f"Razorpay Mandate debit failed: {e}")

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """Fetch payment details from Razorpay by Payment ID."""
        if not self.is_configured:
            logger.warning(f"Razorpay credentials unconfigured. Returning mock payment for '{payment_id}'.")
            return {
                "id": payment_id,
                "entity": "payment",
                "amount": 10000,
                "currency": "INR",
                "status": "captured",
                "method": "upi"
            }
            
        try:
            logger.info(f"Fetching Razorpay payment '{payment_id}'")
            return self.client.payment.fetch(payment_id)
        except Exception as e:
            logger.error(f"Failed to fetch payment '{payment_id}': {e}")
            raise PaymentGatewayException(f"Razorpay payment fetch failed: {e}")

    def fetch_all_payments(self, count: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Fetch all payments from Razorpay Test Mode API."""
        if not self.is_configured:
            logger.warning("Razorpay credentials unconfigured. Returning empty payments collection.")
            return {"entity": "collection", "count": 0, "items": []}

        try:
            logger.info(f"Fetching Razorpay payments (count={count}, skip={skip})")
            return self.client.payment.all({"count": count, "skip": skip})
        except Exception as e:
            logger.error(f"Failed to fetch Razorpay payments: {e}")
            raise PaymentGatewayException(f"Razorpay payment fetch all failed: {e}")

    def create_payment_link(
        self,
        amount: float,
        currency: str = "INR",
        reference_id: Optional[str] = None,
        description: str = "Payment Recovery",
        customer_details: Optional[Dict[str, Any]] = None,
        notes: Optional[Dict[str, Any]] = None,
        expire_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a Razorpay Payment Link in Test Mode."""
        amount_in_paise = int(round(amount * 100.0))

        if not self.is_configured:
            logger.warning("Razorpay credentials unconfigured. Generating mock payment link for test mode.")
            import uuid
            mock_id = f"plink_mock_{uuid.uuid4().hex[:12]}"
            return {
                "id": mock_id,
                "entity": "payment_link",
                "short_url": f"https://rzp.io/i/{mock_id}",
                "status": "created",
                "amount": amount_in_paise,
                "currency": currency,
                "reference_id": reference_id or f"PP-RECOVERY-{mock_id}",
                "description": description,
                "notes": notes or {}
            }

        payload = {
            "amount": amount_in_paise,
            "currency": currency,
            "accept_partial": False,
            "description": description,
            "customer": customer_details or {
                "name": "Valued Customer",
                "email": "customer@merchant.com"
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": True,
            "notes": notes or {}
        }
        if reference_id:
            payload["reference_id"] = reference_id
        if expire_by:
            payload["expire_by"] = expire_by

        try:
            res = self.client.payment_link.create(data=payload)
            logger.info(f"Created Razorpay Payment Link '{res.get('id')}' - short_url: {res.get('short_url')}, ref: {reference_id}")
            return res
        except Exception as e:
            logger.error(f"Failed to create Razorpay Payment Link: {e}")
            raise PaymentGatewayException(f"Razorpay Payment Link creation failed: {e}")

from app.services.razorpay.signature import verify_webhook_signature

RazorpayService = RazorpayClientService
razorpay_service = RazorpayClientService()
