import time
from typing import Dict, Any
from app.services.recovery.base import BaseActionExecutor
from app.models.recovery_case import RecoveryCase
from app.services.razorpay import razorpay_service
from app.core.logging import logger

class RazorpayPaymentLinkExecutor(BaseActionExecutor):
    """Executes REAL Razorpay Test Mode Payment Link creation."""

    @property
    def action_name(self) -> str:
        return "RECOVERY_LINK"

    def execute_action(self, case: RecoveryCase, context: Dict[str, Any]) -> Dict[str, Any]:
        amount = float(case.amount)
        ref_id = f"PP-RECOVERY-{case.id[:8]}-{int(time.time())}"
        logger.info(f"Executing Razorpay Payment Link creation for case '{case.id}' (Amount: INR {amount}, ref: {ref_id})")
        
        description = f"PayPilot AI Payment Recovery (Case #{case.id[:8]})"
        customer_details = {
            "name": context.get("customer_name") or "Valued Customer",
            "email": context.get("customer_email") or "customer@merchant.com"
        }
        notes = {
            "case_id": case.id,
            "merchant_id": case.merchant_id,
            "transaction_id": case.transaction_id
        }

        res = razorpay_service.create_payment_link(
            amount=amount,
            currency="INR",
            reference_id=ref_id,
            description=description,
            customer_details=customer_details,
            notes=notes
        )

        payment_link_id = res.get("id")
        short_url = res.get("short_url")

        return {
            "status": "CREATED",
            "provider": "RAZORPAY",
            "provider_reference": payment_link_id,
            "payment_link_url": short_url,
            "reference_id": ref_id,
            "amount": amount,
            "currency": "INR",
            "raw_response": res,
            "message": f"Razorpay Payment Link '{payment_link_id}' successfully created."
        }

razorpay_link_executor = RazorpayPaymentLinkExecutor()
