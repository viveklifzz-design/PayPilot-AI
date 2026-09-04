import json
import hashlib
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.schemas.payment import WebhookResponse
from app.models.webhook_event import WebhookEvent
from app.models.transaction import Transaction
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.checkout_session import CheckoutSession
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.services.razorpay import verify_webhook_signature
from app.services.revenue_risk import risk_engine
from app.core.config import settings
from app.core.exceptions import SignatureVerificationException
from app.core.logging import logger
from pydantic import BaseModel
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()

SUPPORTED_EVENTS = {
    "payment.authorized",
    "payment.captured",
    "payment.failed",
    "payment_link.paid"
}

@router.post("/webhooks/razorpay", response_model=WebhookResponse, status_code=status.HTTP_200_OK, tags=["Webhooks"])
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    x_razorpay_event_id: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    signature = x_razorpay_signature or request.headers.get("x-razorpay-signature") or request.headers.get("X-Razorpay-Signature")
    event_id_hdr = x_razorpay_event_id or request.headers.get("x-razorpay-event-id") or request.headers.get("X-Razorpay-Event-Id")
    raw_body = await request.body()
    
    # 1. Verify Signature
    if not signature:
        logger.warning("Rejecting webhook: missing x-razorpay-signature header")
        raise SignatureVerificationException("Missing x-razorpay-signature header")

    if not verify_webhook_signature(raw_body, signature):
        raise SignatureVerificationException("Invalid Razorpay webhook signature")

    # 2. Parse JSON Payload
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Malformed webhook JSON payload: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload")

    event_type = payload.get("event")
    if not event_type:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing 'event' field in webhook payload")

    # 3. Determine Unique Event ID for Idempotency
    event_id = x_razorpay_event_id or payload.get("event_id") or payload.get("id")
    if not event_id:
        hash_digest = hashlib.sha256(raw_body).hexdigest()[:16]
        event_id = f"evt_{event_type}_{hash_digest}"

    # 4. Check Idempotency
    existing_evt = await db.execute(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
    if existing_evt.scalar_one_or_none():
        logger.info(f"Duplicate webhook event '{event_id}' detected. Skipping duplicate processing.")
        return WebhookResponse(
            status="ignored",
            event_id=event_id,
            event_type=event_type,
            message="Duplicate webhook event already processed"
        )

    # 5. Persist Webhook Event
    webhook_record = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        processed=True
    )
    db.add(webhook_record)
    await db.commit()

    # 6. Extract Entity Metadata & Process Supported Events
    if event_type in SUPPORTED_EVENTS:
        await _process_supported_webhook_event(event_type, payload, db)

    logger.info(f"Webhook event '{event_id}' ({event_type}) successfully processed.")
    return WebhookResponse(
        status="success",
        event_id=event_id,
        event_type=event_type,
        message="Webhook event processed successfully"
    )

async def _process_supported_webhook_event(event_type: str, payload: Dict[str, Any], db: AsyncSession):
    payload_data = payload.get("payload", {})
    payment_entity = payload_data.get("payment", {}).get("entity", {})
    plink_entity = payload_data.get("payment_link", {}).get("entity", {})
    
    if not payment_entity and plink_entity:
        payment_entity = plink_entity

    payment_id = payment_entity.get("id")
    order_id = payment_entity.get("order_id")
    amount_in_paise = payment_entity.get("amount", 0)
    amount = float(amount_in_paise) / 100.0 if amount_in_paise else 0.0
    currency = payment_entity.get("currency", "INR")
    payment_method = payment_entity.get("method")
    error_code = payment_entity.get("error_code")
    error_description = payment_entity.get("error_description")
    error_source = payment_entity.get("error_source")
    error_step = payment_entity.get("error_step")
    error_reason = payment_entity.get("error_reason")
    plink_id = plink_entity.get("id")

    # Map Razorpay event to transaction status
    status_mapping = {
        "payment.authorized": "authorized",
        "payment.captured": "captured",
        "payment.failed": "failed",
        "payment_link.paid": "captured"
    }
    new_status = status_mapping.get(event_type, "processed")

    # Find existing transaction
    txn = None
    if payment_id:
        result = await db.execute(select(Transaction).where(Transaction.razorpay_payment_id == payment_id))
        txn = result.scalar_one_or_none()
    
    if not txn and order_id:
        result = await db.execute(select(Transaction).where(Transaction.razorpay_order_id == order_id))
        txn = result.scalar_one_or_none()

    if txn:
        txn.status = new_status
        if payment_id:
            txn.razorpay_payment_id = payment_id
        if error_code:
            txn.error_code = error_code
        if error_description:
            txn.error_description = error_description
        if error_source:
            txn.error_source = error_source
        if error_step:
            txn.error_step = error_step
        if error_reason:
            txn.error_reason = error_reason
        if payment_method:
            txn.payment_method = payment_method
        txn.raw_payload = payload
        db.add(txn)
    else:
        res = await db.execute(select(Merchant))
        merchant = res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Default Merchant", email="default@merchant.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        txn = Transaction(
            merchant_id=merchant.id,
            razorpay_payment_id=payment_id,
            razorpay_order_id=order_id,
            amount=amount if amount > 0 else 100.0,
            currency=currency,
            status=new_status,
            error_code=error_code,
            error_description=error_description,
            error_source=error_source,
            error_step=error_step,
            error_reason=error_reason,
            payment_method=payment_method,
            raw_payload=payload
        )
        db.add(txn)

    await db.commit()
    await db.refresh(txn)

    # Webhook Audit Record
    db.add(AuditLog(
        case_id=None,
        actor="RAZORPAY_WEBHOOK",
        event_type=f"WEBHOOK_{event_type.upper().replace('.', '_')}",
        description=f"Received webhook {event_type} for payment_id '{payment_id or 'N/A'}'",
        metadata_json={
            "event_type": event_type,
            "payment_id": payment_id,
            "order_id": order_id,
            "status": new_status,
            "plink_id": plink_id
        }
    ))
    await db.commit()

    # Trigger Revenue Risk Engine on payment.failed
    if new_status == "failed":
        await _trigger_risk_assessment_and_case_creation(txn, db)
    
    # Process payment_link.paid / captured recovery transition
    elif new_status == "captured":
        case = None
        # 1. Check notes.case_id attached to payment_link or payment entity
        notes_case_id = (
            plink_entity.get("notes", {}).get("case_id")
            or payment_entity.get("notes", {}).get("case_id")
        )
        if notes_case_id:
            case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == notes_case_id))
            case = case_res.scalar_one_or_none()

        matched_action = None
        if case and plink_id:
            act_res = await db.execute(
                select(RecoveryAction).where(
                    RecoveryAction.case_id == case.id,
                    RecoveryAction.razorpay_payment_link_id == plink_id
                )
            )
            matched_action = act_res.scalar_one_or_none()

        # 2. Match via payment link ID in RecoveryAction
        if not case and plink_id:
            actions_res = await db.execute(
                select(RecoveryAction).where(
                    RecoveryAction.razorpay_payment_link_id == plink_id
                )
            )
            matched_action = actions_res.scalars().first()
            if matched_action:
                case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == matched_action.case_id))
                case = case_res.scalar_one_or_none()

        # 3. Fallback: match via transaction_id
        if not case:
            case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == txn.id))
            case = case_res.scalar_one_or_none()

        if matched_action and matched_action.status != "COMPLETED":
            matched_action.status = "COMPLETED"
            db.add(matched_action)

        if case and case.status != "RECOVERED":
            case.status = "RECOVERED"
            case.recovered_amount = amount if amount > 0 else case.amount
            db.add(case)

            if case.checkout_session_id:
                cs_res = await db.execute(select(CheckoutSession).where(CheckoutSession.id == case.checkout_session_id))
                cs = cs_res.scalar_one_or_none()
                if cs and cs.status != "CONVERTED":
                    from app.models.base import utc_now
                    cs.status = "CONVERTED"
                    cs.converted_at = utc_now()
                    db.add(cs)
                    db.add(AuditLog(
                        case_id=case.id,
                        actor="RAZORPAY_WEBHOOK",
                        event_type="CHECKOUT_CONVERTED",
                        description=f"Checkout session '{cs.id}' converted via recovery payment of ₹{case.recovered_amount}",
                        metadata_json={"session_id": cs.id, "amount": float(case.recovered_amount)}
                    ))

            await db.commit()

            audit = AuditLog(
                case_id=case.id,
                actor="RAZORPAY_WEBHOOK",
                event_type="RECOVERY_PAYMENT_RECEIVED",
                description=f"Received recovery payment of ₹{case.recovered_amount} via Razorpay Payment Link '{plink_id or 'N/A'}'",
                metadata_json={
                    "provider": "RAZORPAY",
                    "provider_reference": plink_id,
                    "payment_id": payment_id,
                    "amount": float(case.recovered_amount),
                    "currency": currency
                }
            )
            db.add(audit)
            await db.commit()
            logger.info(f"RecoveryCase '{case.id}' successfully marked RECOVERED for amount ₹{case.recovered_amount}")

async def _trigger_risk_assessment_and_case_creation(txn: Transaction, db: AsyncSession):
    customer_succ = 0
    customer_fail = 0
    if txn.customer_id:
        c_res = await db.execute(select(Customer).where(Customer.id == txn.customer_id))
        cust = c_res.scalar_one_or_none()
        if cust:
            customer_succ = cust.total_successful_payments
            customer_fail = cust.total_failed_payments

    risk_assessment = risk_engine.assess_transaction(
        amount=float(txn.amount),
        error_code=txn.error_code,
        error_description=txn.error_description,
        customer_successful_payments=customer_succ,
        customer_failed_payments=customer_fail,
        retry_count=0,
        payment_method=txn.payment_method
    )

    case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == txn.id))
    case = case_res.scalar_one_or_none()

    if not case:
        case = RecoveryCase(
            merchant_id=txn.merchant_id,
            transaction_id=txn.id,
            customer_id=txn.customer_id,
            amount=txn.amount,
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level,
            priority_score=risk_assessment.priority_score,
            priority_level=risk_assessment.priority_level,
            risk_factors=risk_assessment.risk_factors,
            status="OPEN"
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        logger.info(f"Created new RecoveryCase '{case.id}' for failed transaction '{txn.id}'")
    else:
        case.risk_score = risk_assessment.risk_score
        case.risk_level = risk_assessment.risk_level
        case.priority_score = risk_assessment.priority_score
        case.priority_level = risk_assessment.priority_level
        case.risk_factors = risk_assessment.risk_factors
        db.add(case)
        await db.commit()

    audit = AuditLog(
        case_id=case.id,
        actor="REVENUE_RISK_ENGINE",
        event_type="REVENUE_RISK_ASSESSED",
        description=f"Assessed payment failure: risk_score={risk_assessment.risk_score} ({risk_assessment.risk_level}), priority={risk_assessment.priority_level}",
        metadata_json={
            "risk_score": risk_assessment.risk_score,
            "risk_level": risk_assessment.risk_level,
            "recoverability_score": risk_assessment.recoverability_score,
            "priority_score": risk_assessment.priority_score,
            "priority_level": risk_assessment.priority_level,
            "risk_factors": risk_assessment.risk_factors
        }
    )
    db.add(audit)
    await db.commit()


@router.get("/webhooks/whatsapp", tags=["Webhooks"])
async def whatsapp_webhook_verification(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """
    Meta WhatsApp Cloud API Webhook Verification Endpoint (GET).
    Responds to Meta verification requests when hub.verify_token matches WHATSAPP_VERIFY_TOKEN.
    """
    configured_token = settings.WHATSAPP_VERIFY_TOKEN
    if (
        hub_mode == "subscribe" 
        and hub_verify_token 
        and configured_token 
        and hub_verify_token == configured_token
        and hub_challenge
    ):
        logger.info("Meta WhatsApp webhook verification successful.")
        return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)
    
    logger.warning("Meta WhatsApp webhook verification failed: invalid token or missing parameters")
    return Response(content="Verification failed", media_type="text/plain", status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhooks/whatsapp", tags=["Webhooks"])
async def whatsapp_webhook_receiver(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Meta WhatsApp Cloud API Incoming Webhook Event Receiver (POST).
    Parses incoming messages, statuses, and customer responses.
    """
    try:
        raw_body = await request.body()
        if not raw_body:
            return {"status": "ok", "message": "Empty body acknowledged"}
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as err:
        logger.error(f"Malformed WhatsApp webhook JSON payload: {err}")
        return {"status": "ok", "message": "Malformed JSON acknowledged"}

    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                profile_name = contacts[0].get("profile", {}).get("name") if contacts else None
                
                messages = value.get("messages", [])
                for msg in messages:
                    msg_id = msg.get("id", "N/A")
                    from_phone = msg.get("from", "N/A")
                    msg_type = msg.get("type", "unknown")
                    text_body = msg.get("text", {}).get("body", "") if msg_type == "text" else f"[{msg_type} content]"
                    timestamp = msg.get("timestamp")

                    logger.info(
                        f"Received WhatsApp message from '{from_phone[:4] if len(from_phone) >= 4 else from_phone}***' "
                        f"(ID: {msg_id}, Type: {msg_type}, Profile: {profile_name or 'N/A'})"
                    )

                    evt_id = f"wa_{msg_id}"
                    existing = await db.execute(select(WebhookEvent).where(WebhookEvent.event_id == evt_id))
                    if not existing.scalar_one_or_none():
                        db.add(WebhookEvent(
                            event_id=evt_id,
                            event_type=f"whatsapp.message.{msg_type}",
                            payload={
                                "from_phone": from_phone,
                                "message_id": msg_id,
                                "message_type": msg_type,
                                "text": text_body,
                                "profile_name": profile_name,
                                "timestamp": timestamp
                            },
                            processed=True
                        ))
                        await db.commit()

                statuses = value.get("statuses", [])
                for st in statuses:
                    st_id = st.get("id", "N/A")
                    recipient_id = st.get("recipient_id", "N/A")
                    status_type = st.get("status", "unknown")
                    logger.info(f"WhatsApp status update for '{recipient_id[:4] if len(recipient_id) >= 4 else recipient_id}***': status={status_type} (ID: {st_id})")

    except Exception as err:
        logger.error(f"Error parsing WhatsApp webhook payload: {err}")

    return {"status": "ok", "message": "WhatsApp webhook event acknowledged"}


class WhatsAppTestRequest(BaseModel):
    to_phone: str
    message: str = "PayPilot AI WhatsApp integration test successful."


@router.post("/test/whatsapp", tags=["Webhooks"])
async def test_whatsapp_send(payload: WhatsAppTestRequest):
    """
    Development/Test endpoint to manually trigger a real WhatsApp Cloud API test message.
    Calls the same WhatsAppService used by the real PayPilot recovery flow.
    """
    return await whatsapp_service.send_text_message(to_phone=payload.to_phone, text=payload.message)


