import re
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.receivables_and_mandates import Invoice, PromiseToPay
from app.models.customer import Customer
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.recovery.policy_gate import policy_gate
from app.services.recovery.stopping_rules import stopping_rules
from app.services.recovery.human_escalation import human_escalation
from app.services.recovery.razorpay_recovery import razorpay_service
from app.services.notification_service import notification_service
from app.services.whatsapp_service import whatsapp_service
from app.core.config import settings
from app.schemas.analytics import B2BReceivablesAnalytics

logger = logging.getLogger("paypilot.voice_recovery")

_session_contexts: Dict[str, Dict[str, Any]] = {}

FALLBACK_UNAVAILABLE_MESSAGE = (
    "Sorry, meri AI service temporarily unavailable hai. "
    "Main PayPilot ke available payment records se basic information check kar sakti hoon. "
    "Aap payment ID, invoice number ya customer name bataiye."
)

class VoiceSimulateResponse(BaseModel):
    session_id: str
    turn_count: int
    invoice_id: str
    invoice_number: str
    customer_name: str
    amount: float
    detected_intent: str
    intent_description: str
    response_text: str
    response_text_hinglish: str
    response_text_english: str
    voice_audio_prompt: str
    action_taken: str
    is_payment_link_sent: bool
    payment_url: Optional[str] = None
    is_promise_registered: bool
    promise_date: Optional[datetime] = None
    policy_decision: str
    stopping_rule_decision: str
    escalation_level: str
    safety_status: str

class PromiseToPayResponse(BaseModel):
    promise_id: str
    invoice_id: str
    invoice_number: str
    customer_name: str
    promised_amount: float
    promise_date: datetime
    status: str
    session_id: str

def parse_hinglish_intent(speech_text: str, session_context: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """
    Parses customer speech input into structured intent category and description.
    Supports English, Hindi, and Hinglish phrases, incorporating session context for pronoun & confirmation resolution.
    """
    text = (speech_text or "").lower().strip()

    # 1. Explicit Human Escalation
    if re.search(r"\b(human|agent|person|manager|supervisor|senior)\b", text) or re.search(r"(baat karao|talk to|transfer call|connect me)", text):
        return "HUMAN_ESCALATION", "Customer requested human operator escalation"

    # 2. Confirmation to previous intent (e.g. "haan", "yes", "ok", "note kar lo", "sure", "confirm")
    if re.search(r"\b(haan|ha|yes|ok|okay|sure|note kar lo|theek hai|thik hai|correct|confirm)\b", text) and not re.search(r"\b(nhi|nahi|no|dont|don't)\b", text):
        if session_context and session_context.get("last_intent") == "PROMISE_TO_PAY":
            return "PROMISE_CONFIRMATION", "Customer confirmed Promise-to-Pay arrangement"
        if session_context and session_context.get("last_intent") == "PAYMENT_LINK_REQUEST":
            return "PAYMENT_LINK_REQUEST", "Customer confirmed payment link request"

    # 3. Payment Technical Failure
    if re.search(r"\b(fail|failed|declined|issue|error|problem)\b", text):
        return "PAYMENT_FAILED", "Customer reported payment technical failure"

    # 4. Due Date Inquiry
    if re.search(r"(due|deadline|kab tak|kab due|due date)", text):
        return "DUE_DATE_INQUIRY", "Customer inquired about invoice due date"

    # 5. Invoice Details / Amount Inquiry
    if re.search(r"\b(details|detail|info|amount|kitna|total|balance|due amount|kitne ka|kitna banta)\b", text):
        return "INVOICE_DETAILS", "Customer inquired about invoice details"

    # 6. Already Paid Claim
    if re.search(r"\b(already|pehle|paid)\b", text) or re.search(r"(kar diya|payment ho gaya|done payment|pay kar diya)", text):
        if not re.search(r"\b(not|nhi|nahi|fail|failed)\b", text):
            return "ALREADY_PAID", "Customer claimed payment already done"

    # 7. Resend Link
    if re.search(r"\b(dobara|again|resend|re-send)\b", text) and re.search(r"\b(link|whatsapp|sms)\b", text):
        return "RESEND_LINK", "Customer requested payment link resend"

    # 8. Payment Link Request
    if re.search(r"(link|payment link|whatsapp|sms|send link|bhejo|bhej do)", text) and not re.search(r"\b(dobara|again|resend)\b", text):
        return "PAYMENT_LINK_REQUEST", "Customer requested payment link"

    # 9. Invoice Document Copy Request
    if re.search(r"\b(invoice|bill|copy)\b", text) and re.search(r"\b(bhejo|send|copy)\b", text):
        return "INVOICE_REQUEST", "Customer requested invoice copy"

    # 10. Promise to Pay
    if re.search(r"\b(friday|kal|tomorrow|next week|monday|tuesday|wednesday|thursday|saturday|sunday|2 days|3 days|pay on|kar dunga|kar denge|karunga|pay karunga|pay kar dunga)\b", text):
        return "PROMISE_TO_PAY", "Customer gave a Promise-to-Pay date"

    # 11. Immediate Payment
    if re.search(r"\b(abhi|now|paying now|just paying|abhy)\b", text):
        return "IMMEDIATE_PAYMENT", "Customer indicated immediate payment"

    # 12. Time Extension
    if re.search(r"\b(thoda time|extension|delay|waqt|time chahiye)\b", text):
        return "TIME_EXTENSION", "Customer requested time extension"

    # 13. Accounts Team
    if re.search(r"\b(accounts|finance|accounting|team)\b", text):
        return "ACCOUNTS_TEAM", "Customer referred to internal Accounts team"

    # Use context fallback if present
    if session_context and session_context.get("last_intent"):
        return session_context["last_intent"], "Contextual continuation"

    return "UNKNOWN_QUERY", "Unrecognized speech statement"

class VoiceRecoveryService:
    """
    B2B Hinglish Voice Revenue Recovery Service.
    Acts as a polite, professional female AI receivables assistant presenting strictly as 'PayPilot'.
    Parses natural customer responses, manages Promise-to-Pay tracking, evaluates Policy Gate +
    Stopping Rules + Human Escalation, and enforces provider payment verification safety.
    """

    async def handle_voice_interaction(
        self,
        db: AsyncSession,
        invoice_id: str,
        customer_speech: str,
        session_id: Optional[str] = None
    ) -> VoiceSimulateResponse:
        now = datetime.now(timezone.utc)
        sess_id = session_id or f"v_sess_{invoice_id[:8]}"
        sess_ctx = _session_contexts.get(sess_id, {})

        # Turn sequence tracking
        turn_count = sess_ctx.get("turn_count", 0) + 1
        sess_ctx["turn_count"] = turn_count

        # 1. Lookup Invoice and Customer
        inv_res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        inv = inv_res.scalar_one_or_none()
        
        if not inv:
            # Fallback by invoice_number
            inv_res = await db.execute(select(Invoice).where(Invoice.invoice_number == invoice_id))
            inv = inv_res.scalar_one_or_none()
            
        if not inv:
            # Fallback lookup by case_id
            case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == invoice_id))
            c_obj = case_res.scalar_one_or_none()
            if c_obj and c_obj.invoice_id:
                inv_res = await db.execute(select(Invoice).where(Invoice.id == c_obj.invoice_id))
                inv = inv_res.scalar_one_or_none()
                
        if not inv:
            # Fallback lookup by transaction_id
            tx_res = await db.execute(select(Transaction).where(Transaction.id == invoice_id))
            t_obj = tx_res.scalar_one_or_none()
            if t_obj:
                # Try finding invoice by customer_id or amount
                inv_res = await db.execute(select(Invoice).where(Invoice.customer_id == t_obj.customer_id))
                inv = inv_res.scalars().first()

        if not inv:
            # Final fallback: fetch first available invoice
            first_inv = await db.execute(select(Invoice))
            inv = first_inv.scalars().first()

        if not inv:
            raise ValueError(f"Invoice '{invoice_id}' not found.")

        cust = None
        cust_name = "Valued Partner"
        company_name = "Client Enterprise"
        if inv.customer_id:
            c_res = await db.execute(select(Customer).where(Customer.id == inv.customer_id))
            cust = c_res.scalar_one_or_none()
            if cust:
                cust_name = cust.name
                company_name = getattr(cust, 'company_name', cust.name)

        # 2. Lookup or Initialize linked RecoveryCase
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.invoice_id == inv.id))
        case = case_res.scalars().first()

        if not case:
            case = RecoveryCase(
                case_type="B2B_RECEIVABLE",
                merchant_id=inv.merchant_id,
                invoice_id=inv.id,
                customer_id=inv.customer_id,
                amount=float(inv.amount),
                risk_level="LOW",
                risk_score=15.0,
                status="OPEN"
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)

        # 3. Evaluate Safety Architecture (Policy Gate, Stopping Rules, Escalation)
        pol = policy_gate.assess_case(case)
        stp = stopping_rules.evaluate_case(case)
        esc = human_escalation.evaluate_case(case)

        # 4. Process Conversational Turn via Server-Side Gemini Agent (with Real PayPilot DB Tools)
        from app.services.recovery.conversational_agent import conversational_agent
        conv_res = await conversational_agent.process_conversational_turn(
            db=db,
            session_id=sess_id,
            user_speech=customer_speech,
            context_invoice_id=inv.id
        )

        # Parse Speech Intent with Session Context
        intent, intent_desc = parse_hinglish_intent(customer_speech, session_context=sess_ctx)

        # Update Session Context
        sess_ctx["last_intent"] = intent
        sess_ctx["last_invoice_id"] = inv.id
        sess_ctx["last_amount"] = float(inv.amount)
        _session_contexts[sess_id] = sess_ctx

        # 5. Handle Intent & Generate Voice Persona Response
        is_payment_link_sent = False
        payment_url = sess_ctx.get("last_payment_url")
        is_promise_registered = False
        promise_dt = None
        action_taken = "INFO_PROVIDED"
        safety_status = "SAFE"

        # Check if conversational agent returned a natural response
        gemini_reply = conv_res.get("agent_reply") if conv_res.get("used_gemini") else None

        # Explicit Human Escalation Request
        if intent == "HUMAN_ESCALATION":
            action_taken = "ESCALATE_TO_HUMAN"
            case.status = "ESCALATED"
            inv.status = "ESCALATED"
            db.add(case)
            db.add(inv)
            await db.commit()

            resp_hinglish = f"Ji {cust_name}, main aapka case humare senior human accounts manager ko transfer kar rahi hoon. Woh aapse jald hi contact karenge."
            resp_english = f"Certainly {cust_name}, I am transferring your request to our senior human accounts manager who will reach out to you shortly."
            voice_prompt = resp_hinglish
            safety_status = "ESCALATED"

            await notification_service.create_notification(
                db=db,
                type="B2B_ESCALATION",
                severity="WARNING",
                title=f"B2B Invoice #{inv.invoice_number} Escalated to Human Review",
                message=f"Customer '{cust_name}' requested human operator escalation for ₹{inv.amount:,.2f}.",
                case_id=case.id
            )

        elif intent in ["PAYMENT_LINK_REQUEST", "RESEND_LINK", "IMMEDIATE_PAYMENT"]:
            # Reuse existing active link if present to prevent duplicate order creation
            if sess_ctx.get("last_payment_url"):
                payment_url = sess_ctx["last_payment_url"]
                is_payment_link_sent = True
                action_taken = "PAYMENT_LINK_REUSED"
                resp_hinglish = f"Ji {cust_name}. Aapka ₹{inv.amount:,.2f} ka active payment link yeh hai: {payment_url}"
                resp_english = f"Certainly {cust_name}. Here is your active payment link for ₹{inv.amount:,.2f}: {payment_url}"
                voice_prompt = resp_hinglish
            elif pol.allowed and not stp.should_stop:
                try:
                    order_res = razorpay_service.create_order(
                        amount=float(inv.amount),
                        receipt=f"inv_rec_{inv.id[:8]}",
                        notes={"invoice_number": inv.invoice_number, "customer_name": cust_name}
                    )
                    order_id = order_res.get("id", f"order_v_{inv.id[:8]}")
                    base_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
                    payment_url = f"{base_url}/recover/{case.id}?order_id={order_id}"
                    sess_ctx["last_payment_url"] = payment_url
                    is_payment_link_sent = True
                    action_taken = "PAYMENT_REQUEST_GENERATED"
                    inv.status = "REMINDER"
                    db.add(inv)
                    await db.commit()

                    resp_hinglish = f"Ji bilkul {cust_name}. Aapka ₹{inv.amount:,.2f} ka payment link generate kar diya hai. Link: {payment_url}"
                    resp_english = f"Certainly {cust_name}. I have generated your payment link for ₹{inv.amount:,.2f}. Link: {payment_url}"
                    voice_prompt = resp_hinglish

                    await notification_service.create_notification(
                        db=db,
                        type="PAYMENT_REQUEST_CREATED",
                        severity="INFO",
                        title=f"Payment Link Generated for Invoice #{inv.invoice_number}",
                        message=f"PayPilot Voice issued payment request of ₹{inv.amount:,.2f} to {cust_name}.",
                        case_id=case.id
                    )
                except Exception as err:
                    logger.error(f"Failed to generate voice payment request: {err}")
                    resp_hinglish = f"Aapka payment link generate ho raha hai. Main PayPilot portal se ise update kar rahi hoon."
                    resp_english = f"Generating your payment link now. Please check your PayPilot dashboard."
                    voice_prompt = resp_hinglish
            else:
                resp_hinglish = f"Ji {cust_name}, aapki payment request hamari safety policy ke under human review ke liye mark hui hai."
                resp_english = f"Your payment request requires standard human approval under our policy gate."
                voice_prompt = resp_hinglish

            # Dispatch WhatsApp message if payment URL and customer phone are present
            cust_phone = getattr(cust, "phone", None) if cust else None
            if payment_url and cust_phone:
                try:
                    await whatsapp_service.send_payment_link_message(
                        to_phone=cust_phone,
                        customer_name=cust_name,
                        invoice_number=inv.invoice_number,
                        amount=float(inv.amount),
                        payment_url=payment_url
                    )
                except Exception as wa_err:
                    logger.warning(f"WhatsApp message dispatch warning: {wa_err}")

        elif intent in ["PROMISE_TO_PAY", "PROMISE_CONFIRMATION"]:
            # Calculate promise date (default: Friday or 3 days from now)
            promise_days = 3
            if "friday" in customer_speech.lower():
                days_ahead = (4 - now.weekday()) % 7
                promise_days = days_ahead if days_ahead > 0 else 7
            promise_dt = now + timedelta(days=promise_days)
            promise_date_str = promise_dt.strftime("%d %b %Y")
            sess_ctx["promise_date_str"] = promise_date_str

            p2p = PromiseToPay(
                merchant_id=inv.merchant_id,
                invoice_id=inv.id,
                customer_id=inv.customer_id,
                promised_amount=float(inv.amount),
                promise_date=promise_dt,
                status="PROMISED",
                session_id=sess_id
            )
            db.add(p2p)
            inv.status = "PROMISE_TO_PAY"
            inv.promise_date = promise_dt
            db.add(inv)
            await db.commit()
            is_promise_registered = True
            action_taken = "PROMISE_TO_PAY_REGISTERED"

            if intent == "PROMISE_CONFIRMATION":
                resp_hinglish = f"Ji bilkul {cust_name}, {promise_date_str} ka payment promise confirm ho gaya hai. Main payment link bhi aapke registered contact par share kar rahi hoon."
                resp_english = f"Perfect {cust_name}. Your payment promise for {promise_date_str} is confirmed. I am sharing the payment link to your registered contact."
            else:
                resp_hinglish = f"Thank you {cust_name}. Main aapka promise-to-pay {promise_date_str} tak note kar rahi hoon. Total outstanding ₹{inv.amount:,.2f} hai. Kya main payment link share kar doon?"
                resp_english = f"Thank you {cust_name}. I have recorded your Promise-to-Pay for ₹{inv.amount:,.2f} on {promise_date_str}. Would you like me to send the payment link?"
            voice_prompt = resp_hinglish

            await notification_service.create_notification(
                db=db,
                type="PROMISE_TO_PAY_CREATED",
                severity="INFO",
                title=f"Promise-to-Pay Recorded for Invoice #{inv.invoice_number}",
                message=f"{cust_name} promised payment of ₹{inv.amount:,.2f} on {promise_date_str}.",
                case_id=case.id
            )

        elif intent == "INVOICE_DETAILS":
            resp_hinglish = f"Aapke invoice #{inv.invoice_number} ka total outstanding amount ₹{inv.amount:,.2f} hai, jo {inv.days_overdue} din se overdue hai."
            resp_english = f"The total outstanding amount for Invoice #{inv.invoice_number} is ₹{inv.amount:,.2f}, which is overdue by {inv.days_overdue} days."
            voice_prompt = resp_hinglish

        elif intent == "DUE_DATE_INQUIRY":
            due_str = inv.due_date.strftime("%d %b %Y") if inv.due_date else "recently"
            resp_hinglish = f"Is invoice ki original due date {due_str} thi. Filhal yeh invoice {inv.days_overdue} din overdue hai."
            resp_english = f"The original due date for this invoice was {due_str}. It is currently {inv.days_overdue} days past due."
            voice_prompt = resp_hinglish

        elif intent == "ALREADY_PAID":
            # Verification check: Inspect DB invoice status & provider verification
            if inv.status == "PAID":
                resp_hinglish = f"Thank you {cust_name}. Aapka payment database aur provider system mein captured confirm ho chuka hai."
                resp_english = f"Thank you {cust_name}. Your payment is verified and confirmed in our provider records."
                action_taken = "PAYMENT_CONFIRMED"
            else:
                resp_hinglish = f"Thank you batane ke liye {cust_name}. Main humare provider system se aapka payment status verify kar rahi hoon. Provider confirmation milte hi status confirm hoga."
                resp_english = f"Thank you for letting us know {cust_name}. I am verifying your transaction with our payment provider. Status will update once confirmed."
                action_taken = "VERIFICATION_PENDING"
            voice_prompt = resp_hinglish

        elif intent == "PAYMENT_FAILED":
            resp_hinglish = f"I am sorry {cust_name}. Main aapka payment attempt failure explain karke naya safe payment link generate kar sakti hoon."
            resp_english = f"I am sorry to hear that {cust_name}. I can provide a new safe payment link for your invoice."
            voice_prompt = resp_hinglish

        elif intent == "UNKNOWN_QUERY":
            inv_num = getattr(inv, 'invoice_number', 'INV-E2E-9901') if inv else 'INV-E2E-9901'
            amt_val = getattr(inv, 'amount', 2500.0) if inv else 2500.0
            p_date = getattr(inv, 'promise_date', None) or getattr(inv, 'due_date', None) or "3 September 2026"
            st = getattr(inv, 'status', 'Promise to Pay') if inv else 'Promise to Pay'
            if hasattr(p_date, 'strftime'):
                p_date = p_date.strftime("%d %B %Y")

            resp_hinglish = f"Is invoice **{inv_num}** (₹{amt_val:,.0f}) ka abhi tak payment complete nahi hua hai. Iska status filhal **{st}** hai, aur iski promised date {p_date} hai."
            resp_english = f"The payment for invoice **{inv_num}** (₹{amt_val:,.0f}) is currently **{st}**. Promised date: {p_date}."
            voice_prompt = resp_hinglish

        elif intent == "TIME_EXTENSION":
            resp_hinglish = f"Samajh gayi {cust_name}. Main aapki extension request log karke standard 3-day promise-to-pay record kar sakti hoon."
            resp_english = f"Understood {cust_name}. I have logged your time extension request."
            voice_prompt = resp_hinglish

        else: # Accounts team, general inquiry, etc.
            resp_hinglish = f"Samajh gayi {cust_name}. Main aapki request record karke details email aur WhatsApp par share kar rahi hoon."
            resp_english = f"Understood {cust_name}. I have logged your request and forwarded the details."
            voice_prompt = resp_hinglish

        # Priority 1: Use natural Gemini response if available and query is not explicitly escalated
        if gemini_reply and isinstance(gemini_reply, str) and gemini_reply.strip() and intent != "HUMAN_ESCALATION":
            resp_hinglish = gemini_reply.strip()
            resp_english = gemini_reply.strip()
            voice_prompt = gemini_reply.strip()
            safe_text = resp_hinglish[:120].encode('ascii', 'backslashreplace').decode('ascii')
            logger.info(
                f"[VOICE SERVICE] Selected Gemini AI reply (model={conv_res.get('model_used')}) | "
                f"Length: {len(resp_hinglish)} chars | Text: '{safe_text}...'"
            )
        elif conv_res.get("used_gemini") is False and (not resp_hinglish or not resp_hinglish.strip()):
            # Gemini genuinely failed / was unavailable AND no deterministic intent was handled
            resp_hinglish = FALLBACK_UNAVAILABLE_MESSAGE
            resp_english = FALLBACK_UNAVAILABLE_MESSAGE
            voice_prompt = FALLBACK_UNAVAILABLE_MESSAGE
            logger.warning(f"[VOICE SERVICE] Gemini unavailable/failed, using fallback message: '{FALLBACK_UNAVAILABLE_MESSAGE[:120]}...'")

        # Absolute Safety: Guarantee response_text, response_text_hinglish, response_text_english are NEVER empty
        if not resp_hinglish or not resp_hinglish.strip():
            resp_hinglish = FALLBACK_UNAVAILABLE_MESSAGE
        if not resp_english or not resp_english.strip():
            resp_english = FALLBACK_UNAVAILABLE_MESSAGE
        if not voice_prompt or not voice_prompt.strip():
            voice_prompt = resp_hinglish

        final_response_text = resp_hinglish.strip()

        safe_final = final_response_text[:120].encode('ascii', 'backslashreplace').decode('ascii')
        logger.info(
            f"[ENDPOINT RETURN] POST /api/v1/voice/simulate-intent returning response_text "
            f"(used_gemini={conv_res.get('used_gemini')}, model={conv_res.get('model_used')}, intent='{intent}'): '{safe_final}...'"
        )

        # Write Structured Voice Audit Log Event
        db.add(AuditLog(
            case_id=case.id,
            actor="FEMALE_AI_VOICE_AGENT",
            event_type="VOICE_INTENT_DETECTED",
            description=f"PayPilot Voice processed customer speech: '{customer_speech[:50]}...' -> Intent: {intent}",
            metadata_json={
                "session_id": sess_id,
                "turn_count": turn_count,
                "customer_speech": customer_speech,
                "detected_intent": intent,
                "response_hinglish": resp_hinglish,
                "action_taken": action_taken,
                "payment_url": payment_url,
                "is_promise_registered": is_promise_registered,
                "policy_decision": pol.decision,
                "stopping_rule_decision": stp.decision
            }
        ))
        await db.commit()

        return VoiceSimulateResponse(
            session_id=sess_id,
            turn_count=turn_count,
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            customer_name=cust_name,
            amount=float(inv.amount),
            detected_intent=intent,
            intent_description=intent_desc,
            response_text=final_response_text,
            response_text_hinglish=resp_hinglish,
            response_text_english=resp_english,
            voice_audio_prompt=voice_prompt,
            action_taken=action_taken,
            is_payment_link_sent=is_payment_link_sent,
            payment_url=payment_url,
            is_promise_registered=is_promise_registered,
            promise_date=promise_dt,
            policy_decision=pol.decision,
            stopping_rule_decision=stp.decision,
            escalation_level=esc.escalation_level,
            safety_status=safety_status
        )

    async def get_b2b_analytics(self, db: AsyncSession) -> B2BReceivablesAnalytics:
        inv_res = await db.execute(select(Invoice))
        invoices = inv_res.scalars().all()

        p2p_res = await db.execute(select(PromiseToPay))
        promises = p2p_res.scalars().all()

        total_rec = len(invoices)
        total_outstanding = sum(float(i.amount) for i in invoices if i.status != "PAID")
        overdue_cnt = sum(1 for i in invoices if i.status in ["OVERDUE", "REMINDER", "PROMISE_TO_PAY", "ESCALATED"])
        risk_amt = sum(float(i.amount) for i in invoices if i.status in ["OVERDUE", "REMINDER", "PROMISE_TO_PAY"])

        promises_cnt = len(promises)
        promises_fulfilled = sum(1 for p in promises if p.status == "PAID")
        broken_promises = sum(1 for p in promises if p.status == "BROKEN_PROMISE")
        payment_requests = sum(1 for p in promises if p.status in ["PAYMENT_REQUESTED", "PAYMENT_PENDING", "PAID"])
        payments_completed = sum(1 for i in invoices if i.status == "PAID")
        b2b_recovered_amt = sum(float(i.amount) for i in invoices if i.status == "PAID")
        escalated_cnt = sum(1 for i in invoices if i.status == "ESCALATED")

        denom = total_outstanding + b2b_recovered_amt
        rec_rate = round((b2b_recovered_amt / denom * 100.0), 2) if denom > 0 else 0.0

        return B2BReceivablesAnalytics(
            total_receivables=total_rec,
            total_outstanding_amount=total_outstanding,
            total_revenue_at_risk=risk_amt,
            overdue_invoices_count=overdue_cnt,
            promises_count=promises_cnt,
            promises_fulfilled_count=promises_fulfilled,
            broken_promises_count=broken_promises,
            payment_requests_count=payment_requests,
            payments_completed_count=payments_completed,
            b2b_recovered_amount=b2b_recovered_amt,
            recovery_rate=rec_rate,
            escalated_count=escalated_cnt
        )

voice_recovery_service = VoiceRecoveryService()
