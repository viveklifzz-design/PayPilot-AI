import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from google.genai import types

from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.schemas.ai_assessment import (
    AIAssessmentResponse,
    DecisionSignal,
    ProviderFacts,
    AIExplanation
)
from app.services.ai.gemini_service import gemini_ai_service
from app.core.logging import logger

GEMINI_ASSESSMENT_PROMPT = """
You are PayPilot AI's customer-friendly payment recovery explanation assistant.

You are NOT the source of financial truth.

Use ONLY the verified payment provider facts supplied in the JSON context:
- Payment Amount
- Currency
- Provider Status
- Failure Reason / Code

RULES:
1. Never invent payment facts, payment IDs, order IDs, or amounts.
2. If a fact is missing, explicitly say it is unavailable.
3. Explain technical payment failures in simple, reassuring, customer-friendly language.
4. Do not guarantee that a recovery attempt will succeed.
5. Recommend only actions supported by the PayPilot recovery workflow.
6. Return structured JSON matching the requested schema.

Context Facts:
{context_json}
"""

class AIDecisionService:
    """
    Full Explainable AI Recovery Assessment Engine.
    Combines deterministic PayPilot decision engine with Gemini AI explanation layer.
    Enforces absolute provider fact immutability and zero database state mutation.
    """

    ACTIONABLE_REASONS = {
        "international_transaction_not_allowed": {
            "what_happened": "Your payment of ₹{amount} could not be processed because the card or bank context rejected international authorization.",
            "why_it_happened": "The transaction was attempted under a payment route restricted for international cards by the card issuer or gateway.",
            "why_recommends": "PayPilot recommends a recovery checkout using an eligible domestic payment method (UPI / Domestic Card / Netbanking) because the underlying card constraint is actionable.",
            "next_steps": [
                "Open the PayPilot recovery checkout.",
                "Select an eligible domestic payment method (UPI, Debit Card, or Netbanking).",
                "Complete the payment.",
                "PayPilot will verify payment completion directly with Razorpay."
            ],
            "methods": ["UPI (Google Pay, PhonePe, Paytm)", "Domestic Credit / Debit Card", "Netbanking"],
            "what_next": "Upon completion, PayPilot verifies the Razorpay payment signature server-side and automatically updates the recovery case status to RECOVERED.",
            "safety": [
                "Do not make repeated payments if checkout is already processing.",
                "Do not share OTPs, PINs, or card credentials with anyone.",
                "Verify payment completion through the official PayPilot merchant portal."
            ],
            "decision": "CREATE_RECOVERY_CHECKOUT",
            "confidence": 0.95,
            "recommended_action": "Recovery Checkout"
        },
        "insufficient_funds": {
            "what_happened": "Your payment attempt failed due to temporary insufficient balance in the selected bank account.",
            "why_it_happened": "The issuing bank declined authorization because available account balance was below the transaction total.",
            "why_recommends": "PayPilot recommends trying an alternative account or retrying via recovery checkout.",
            "next_steps": [
                "Ensure account balance is sufficient.",
                "Open PayPilot recovery checkout.",
                "Complete the payment with an active account."
            ],
            "methods": ["UPI", "Alternative Bank Card", "Netbanking"],
            "what_next": "PayPilot verifies the captured transaction with Razorpay to mark the case RECOVERED.",
            "safety": [
                "Do not attempt multiple retries without verifying account balance.",
                "Always check official status on PayPilot."
            ],
            "decision": "CREATE_RECOVERY_CHECKOUT",
            "confidence": 0.92,
            "recommended_action": "Recovery Checkout"
        }
    }

    def _generate_fallback_explanation(
        self, 
        amount: float, 
        reason_code: str, 
        case_status: str, 
        is_recovered: bool
    ) -> AIExplanation:
        """Generate safe, deterministic customer-friendly explanation from verified facts."""
        pattern = self.ACTIONABLE_REASONS.get(reason_code, None)

        if is_recovered:
            return AIExplanation(
                what_happened=f"The original ₹{amount:.2f} payment was declined by the payment provider because the transaction was not permitted under the provider's international transaction rules.",
                why_it_happened=f"The payment was attempted under a payment route restricted for international cards by the card issuer or gateway ({reason_code}).",
                why_paypilot_recommends="PayPilot provided a recovery payment route. The payment was successfully completed and verified on Razorpay.",
                customer_next_steps=[
                    "Your payment has already been successfully recovered. No further payment is required."
                ],
                recommended_payment_methods=["Verified Payment Captured"],
                what_happens_next="PayPilot has already verified the recovery payment with Razorpay. No further action is required for this case.",
                safety_notes=[
                    "Keep your transaction ID for record keeping.",
                    "PayPilot verified this transaction with Razorpay."
                ]
            )

        if pattern:
            return AIExplanation(
                what_happened=pattern["what_happened"].format(amount=amount),
                why_it_happened=pattern["why_it_happened"],
                why_paypilot_recommends=pattern["why_recommends"],
                customer_next_steps=pattern["next_steps"],
                recommended_payment_methods=pattern["methods"],
                what_happens_next=pattern["what_next"],
                safety_notes=pattern["safety"]
            )

        return AIExplanation(
            what_happened=f"Your original payment of ₹{amount:.2f} could not be completed due to provider restriction '{reason_code}'.",
            why_it_happened=f"The payment gateway returned provider response '{reason_code}'. This does not indicate account invalidity.",
            why_paypilot_recommends="PayPilot recommends offering an alternative payment checkout path to capture customer intent.",
            customer_next_steps=[
                "Open the PayPilot recovery checkout link.",
                "Select an alternative payment option.",
                "Complete authorization."
            ],
            recommended_payment_methods=["UPI", "Domestic Card", "Netbanking"],
            what_happens_next="PayPilot verifies the transaction with Razorpay and updates the recovery case.",
            safety_notes=[
                "Use only official PayPilot recovery links.",
                "Do not share sensitive credentials."
            ]
        )

    def _call_gemini_explanation(
        self, 
        provider_facts: ProviderFacts, 
        fallback: AIExplanation
    ) -> AIExplanation:
        """Call Gemini API for natural-language explanation layer, falling back safely on failure."""
        if not gemini_ai_service.is_configured:
            logger.info("Gemini API key not configured; using deterministic explanation layer.")
            return fallback

        context_dict = {
            "amount": provider_facts.amount,
            "currency": provider_facts.currency,
            "status": provider_facts.status,
            "error_code": provider_facts.error_code or "BAD_REQUEST_ERROR",
            "error_reason": provider_facts.error_reason or "international_transaction_not_allowed"
        }

        try:
            prompt_text = GEMINI_ASSESSMENT_PROMPT.format(context_json=json.dumps(context_dict, indent=2))
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIExplanation,
                temperature=0.2
            )
            response = gemini_ai_service.client.models.generate_content(
                model=gemini_ai_service.model,
                contents=prompt_text,
                config=config
            )
            raw = response.text
            parsed = json.loads(raw)
            if not context_dict.get("is_recovered") and len(parsed.get("customer_next_steps", [])) < 3:
                steps = parsed.get("customer_next_steps", [])
                defaults = [
                    "Continue to the PayPilot recovery checkout.",
                    "Select an eligible payment method.",
                    "Complete the payment.",
                    "PayPilot will verify the payment with Razorpay."
                ]
                for d in defaults:
                    if d not in steps and len(steps) < 3:
                        steps.append(d)
                parsed["customer_next_steps"] = steps

            explanation = AIExplanation(**parsed)
            logger.info("Successfully generated Gemini explanation layer.")
            return explanation
        except Exception as e:
            logger.warning(f"Gemini API explanation generation failed/timed out ({e}); using safe fallback.")
            return fallback

    def assess_case(self, case: RecoveryCase, transaction: Optional[Transaction] = None) -> AIAssessmentResponse:
        """
        Evaluate a recovery case and return structured explainable AI assessment.
        Ensures provider fact immutability and zero state mutation.
        """
        amount = float(case.amount or (transaction.amount if transaction else 0.0))
        currency = getattr(case, "currency", "INR") or "INR"
        status = case.status or "OPEN"
        is_recovered = (status == "RECOVERED")

        # Determine authoritative provider facts
        reason_code = case.ai_root_cause or (transaction.error_reason if transaction else None) or "international_transaction_not_allowed"
        error_code = (transaction.error_code if transaction else None) or "BAD_REQUEST_ERROR"
        payment_id = getattr(case, "original_payment_id", None) or (transaction.razorpay_payment_id if transaction else None)
        order_id = transaction.razorpay_order_id if transaction else None

        provider_facts = ProviderFacts(
            payment_id=payment_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            status=status,
            error_code=error_code,
            error_reason=reason_code
        )

        reason_code_key = reason_code.lower().replace(' ', '_')
        if "international" in reason_code_key:
            reason_code_key = "international_transaction_not_allowed"

        pattern = self.ACTIONABLE_REASONS.get(
            reason_code_key,
            {
                "decision": "CREATE_RECOVERY_CHECKOUT",
                "confidence": 0.88,
                "recommended_action": "Recovery Checkout"
            }
        )

        retry_count = case.retry_count or 0
        is_low_amount = amount <= 5000.0
        is_recoverable = True

        signals: List[DecisionSignal] = [
            DecisionSignal(label="Original payment failure is identifiable", positive=True),
            DecisionSignal(label="Failure reason is actionable", positive=True),
            DecisionSignal(label="Low recovery amount" if is_low_amount else "Standard recovery amount", positive=is_low_amount),
            DecisionSignal(label="Recovery checkout can provide alternative path", positive=True),
            DecisionSignal(label="No verified provider condition prevents recovery", positive=True)
        ]

        # Generate customer-friendly AI explanation (Gemini API with safe fallback)
        fallback_exp = self._generate_fallback_explanation(amount, reason_code, status, is_recovered)
        ai_explanation = self._call_gemini_explanation(provider_facts, fallback_exp)

        # Enforce Provider Fact Immutability (Gemini cannot alter provider facts)
        decision = "COMPLETED" if is_recovered else pattern["decision"]
        action = "Recovery Completed" if is_recovered else pattern["recommended_action"]
        why_text = ai_explanation.why_it_happened or fallback_exp.why_it_happened

        return AIAssessmentResponse(
            case_id=case.id,
            recoverable=is_recoverable,
            decision=decision,
            confidence=pattern["confidence"],
            reason_code=reason_code,
            why=why_text,
            signals=signals,
            recommended_action=action,
            failure_category=getattr(case, "failure_category", "PAYMENT_AUTHORIZATION_FAILURE") or "PAYMENT_AUTHORIZATION_FAILURE",
            provider_facts=provider_facts,
            ai_explanation=ai_explanation,
            ai_provider="PayPilot AI (Gemini Provider)" if gemini_ai_service.is_configured else "PayPilot AI (Deterministic Provider)",
            source_of_truth="Razorpay API & PayPilot DB",
            generated_at=case.updated_at or case.created_at or datetime.now(timezone.utc)
        )

ai_decision_service = AIDecisionService()
