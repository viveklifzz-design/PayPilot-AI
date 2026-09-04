import hmac
import hashlib
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.schemas.recovery import ExecutionRequest, ExecutionResponse
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.recovery import recovery_executor
from app.services.recovery.policy_gate import policy_gate
from app.services.recovery.stopping_rules import stopping_rules
from app.services.recovery.human_escalation import human_escalation
from app.services.razorpay import razorpay_service
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger

router = APIRouter()

class CheckoutVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    recovery_case_id: Optional[str] = None

class CreateCheckoutOrderRequest(BaseModel):
    case_id: Optional[str] = None
    amount: Optional[float] = 20.0
    currency: str = "INR"

class CheckoutOrderResponse(BaseModel):
    order_id: str
    amount: float
    amount_paise: int
    currency: str
    key_id: str
    case_id: Optional[str] = None
    status: str = "created"

async def _get_case_by_id_or_prefix(case_id: str, db: AsyncSession) -> Optional[RecoveryCase]:
    if not case_id or not isinstance(case_id, str):
        return None
    cid = case_id.strip()
    if not cid:
        return None

    # 1. Exact UUID match
    exact_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == cid))
    exact_case = exact_res.scalar_one_or_none()
    if exact_case:
        return exact_case

    # 2. Prefix match (must be at least 4 characters long)
    if len(cid) < 4:
        return None

    prefix_res = await db.execute(
        select(RecoveryCase).where(
            ~RecoveryCase.case_type.in_(["B2B_RECEIVABLE", "MANDATE_RETRY"]),
            RecoveryCase.id.like(f"{cid}%")
        ).order_by(RecoveryCase.created_at.desc())
    )
    matches = prefix_res.scalars().all()
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ambiguous case ID prefix '{cid}' matches multiple cases ({len(matches)} matches found)."
        )
    return None

@router.post("/checkout/create-order", response_model=CheckoutOrderResponse, tags=["Recovery Checkout"])
@router.post("/test/create-checkout-order", response_model=CheckoutOrderResponse, tags=["Recovery Checkout"])
async def create_checkout_order(
    req: Optional[CreateCheckoutOrderRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new Razorpay Test Mode Order for Standard Checkout.
    Guarantees no Razorpay Payment Link is created.
    Logs request diagnostics safely without exposing secret keys or credentials.
    """
    case_id = req.case_id if req else None
    requested_amount = req.amount if (req and req.amount) else 20.0
    currency = req.currency if req else "INR"

    logger.info(f"Initiating Razorpay Order creation request: case_id='{case_id}', requested_amount={requested_amount} {currency}")

    case = None
    if case_id:
        case = await _get_case_by_id_or_prefix(case_id, db)

    # Enforce PayPilot Safety Policy Gate & Stopping Rules before Order Creation
    if case:
        policy_assessment = policy_gate.assess_case(case=case)
        if not policy_assessment.allowed:
            logger.warning(
                f"Razorpay Order creation BLOCKED by Policy Gate for case '{case.id}': "
                f"decision={policy_assessment.decision}, explanation={policy_assessment.explanation}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Order creation blocked by PayPilot Policy Gate: {policy_assessment.customer_explanation}"
            )

        stopping_assessment = stopping_rules.evaluate_case(case=case)
        if stopping_assessment.should_stop:
            logger.warning(
                f"Razorpay Order creation STOPPED by Stopping Rules for case '{case.id}': "
                f"rules={stopping_assessment.triggered_rules}, reason={stopping_assessment.stop_reason}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Order creation stopped by PayPilot Stopping Rules: {stopping_assessment.stop_reason}"
            )

        escalation_assessment = human_escalation.evaluate_case(case=case)
        if case.status in ["ESCALATED", "STOPPED"] or (escalation_assessment.escalation_level in ["CRITICAL", "HIGH_PRIORITY"] and case.status not in ["ACTION_PENDING"]):
            logger.warning(
                f"Razorpay Order creation PAUSED for Human Review for case '{case.id}': "
                f"level={escalation_assessment.escalation_level}, reason={escalation_assessment.escalation_reason}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Order creation paused for Human Review: {escalation_assessment.escalation_reason}"
            )

    # Determine amount from case if available
    amount = float(case.amount) if case else float(requested_amount)

    try:
        # Create Razorpay Order via Razorpay Client API
        receipt_id = f"rcpt_{case_id[:8]}" if case_id else f"rcpt_test_{int(time.time())}"
        order = razorpay_service.create_order(
            amount=amount,
            currency=currency,
            receipt=receipt_id,
            notes={
                "purpose": "PayPilot Recovery Checkout",
                "case_id": case_id or "test_checkout",
                "environment": settings.ENVIRONMENT
            }
        )

        order_id = order.get("id")
        amount_paise = order.get("amount") or int(round(amount * 100.0))

        logger.info(f"Successfully created Razorpay Test Mode Order '{order_id}' for amount {amount} {currency} (Status: {order.get('status')})")

        return CheckoutOrderResponse(
            order_id=order_id,
            amount=amount,
            amount_paise=amount_paise,
            currency=currency,
            key_id=settings.RAZORPAY_KEY_ID,
            case_id=case.id if case else case_id,
            status=order.get("status", "created")
        )
    except Exception as e:
        logger.error(f"Failed to create Razorpay Order for case '{case_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Razorpay order creation failed: {e}")

@router.post("/cases/{case_id}/execute", response_model=ExecutionResponse, tags=["Recovery Execution"])
async def execute_case_recovery(
    case_id: str,
    req: Optional[ExecutionRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    requested_action = req.action if req else None
    confidence = req.ai_confidence if req else None

    res = await recovery_executor.execute_recovery(
        case=case,
        db=db,
        proposed_action=requested_action,
        ai_confidence=confidence
    )
    return ExecutionResponse(**res)

@router.post("/checkout/verify", tags=["Recovery Verification"])
async def verify_checkout_payment(
    req: CheckoutVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Server-side HMAC-SHA256 signature verification & Razorpay provider API validation.
    Enforces amount, payment identity, and order invariants before transitioning case to RECOVERED.
    """
    logger.info(f"Initiating server-side checkout verification for case '{req.recovery_case_id}' (Payment ID: {req.razorpay_payment_id}, Order ID: {req.razorpay_order_id})")

    # 1. Load RecoveryCase if provided
    case = None
    if req.recovery_case_id:
        case = await _get_case_by_id_or_prefix(req.recovery_case_id, db)

    # 2. Idempotency Check A: Transaction already recorded in DB
    existing_txn_res = await db.execute(select(Transaction).where(Transaction.razorpay_payment_id == req.razorpay_payment_id))
    existing_txn = existing_txn_res.scalar_one_or_none()
    if existing_txn:
        logger.info(f"Payment '{req.razorpay_payment_id}' is already recorded in DB. Returning idempotent success.")
        return {
            "verified": True,
            "status": "RECOVERED" if case else "CAPTURED",
            "case_id": case.id if case else None,
            "payment_id": existing_txn.razorpay_payment_id,
            "order_id": existing_txn.razorpay_order_id,
            "recovered_amount": float(existing_txn.amount),
            "message": f"Payment '{req.razorpay_payment_id}' is already verified."
        }

    # Idempotency Check B: Case is already RECOVERED
    if case and case.status == "RECOVERED":
        logger.info(f"Case '{case.id}' is already RECOVERED. Returning idempotent success.")
        return {
            "verified": True,
            "status": "RECOVERED",
            "case_id": case.id,
            "payment_id": req.razorpay_payment_id,
            "order_id": req.razorpay_order_id,
            "recovered_amount": float(case.recovered_amount or case.amount),
            "message": "Case is already verified RECOVERED."
        }

    # 3. Server Order ID (Use exact order_id passed in request for Standard Checkout)
    server_order_id = req.razorpay_order_id

    # 4. HMAC-SHA256 Signature Verification
    secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
    msg = f"{server_order_id}|{req.razorpay_payment_id}".encode("utf-8")
    expected_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, req.razorpay_signature):
        logger.error(f"HMAC Signature Verification FAILED for order '{server_order_id}'. Expected: {expected_sig}, Got: {req.razorpay_signature}")
        if case:
            db.add(AuditLog(
                case_id=case.id,
                actor="CHECKOUT_VERIFIER",
                event_type="RECOVERY_PAYMENT_SIGNATURE_FAILED",
                description="HMAC SHA256 signature mismatch during checkout verification",
                metadata_json={"payment_id": req.razorpay_payment_id, "order_id": server_order_id}
            ))
            await db.commit()
        raise HTTPException(status_code=400, detail="Invalid Razorpay checkout signature")

    # 5. Fetch Payment Details directly from Razorpay Provider API
    try:
        payment_data = razorpay_service.fetch_payment(req.razorpay_payment_id)
    except Exception as e:
        logger.error(f"Provider API call failed fetching payment '{req.razorpay_payment_id}': {e}")
        raise HTTPException(status_code=502, detail=f"Provider payment verification failed: {e}")

    # 6. Invariant Checks
    p_amount_paise = payment_data.get("amount") or 2000
    p_amount_rs = float(p_amount_paise) / 100.0

    if case:
        original_txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
        original_txn = original_txn_res.scalar_one_or_none()
        orig_payment_id = original_txn.razorpay_payment_id if original_txn else None

        # Invariant A: NEW_PAYMENT_ID != ORIGINAL_FAILED_PAYMENT_ID
        if orig_payment_id and req.razorpay_payment_id == orig_payment_id:
            raise HTTPException(status_code=400, detail="Recovery payment ID cannot equal original failed payment ID")

        # Invariant B: Amount Match
        expected_paise = int(round(float(case.amount) * 100.0))
        if payment_data.get("amount") != expected_paise:
            raise HTTPException(status_code=400, detail=f"Payment amount mismatch: expected {expected_paise} paise, got {payment_data.get('amount')}")

    # Invariant C: Status Captured or Authorized
    p_status = payment_data.get("status")
    if p_status not in ["captured", "authorized"]:
        raise HTTPException(status_code=400, detail=f"Provider payment status '{p_status}' is not captured/authorized")

    # Invariant D: Provider Order ID Match
    p_order_id = payment_data.get("order_id")
    if p_order_id and p_order_id != server_order_id:
        raise HTTPException(
            status_code=400,
            detail=f"Provider order ID mismatch: payment belongs to order '{p_order_id}', expected '{server_order_id}'"
        )

    # 7. Update Case to RECOVERED if linked
    recovered_val = float(case.amount) if case else p_amount_rs
    if case:
        case.status = "RECOVERED"
        case.recovered_amount = recovered_val
        case.actual_action_taken = "RECOVERY_CHECKOUT"
        db.add(case)

    # 8. Record New Recovery Payment Transaction in DB
    rec_txn = Transaction(
        merchant_id=case.merchant_id if case else "265b7f74-43d9-4866-9f70-ab705671e0c0",
        customer_id=case.customer_id if case else None,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_order_id=server_order_id,
        amount=recovered_val,
        currency="INR",
        status="captured",
        payment_method=payment_data.get("method") or "card"
    )
    db.add(rec_txn)

    # 9. Log Audit Trail
    if case:
        db.add(AuditLog(
            case_id=case.id,
            actor="CHECKOUT_VERIFIER",
            event_type="RECOVERY_CHECKOUT_VERIFIED",
            description=f"Server signature verified & provider payment '{req.razorpay_payment_id}' confirmed captured ({p_status}). Recovered: INR {recovered_val:.2f}",
            metadata_json={
                "payment_id": req.razorpay_payment_id,
                "order_id": server_order_id,
                "amount": recovered_val,
                "currency": "INR",
                "provider_status": p_status
            }
        ))
    await db.commit()

    logger.info(f"Case '{case.id}' successfully RECOVERED for INR {recovered_val:.2f} via payment '{req.razorpay_payment_id}'")
    return {
        "verified": True,
        "status": "RECOVERED",
        "case_id": case.id,
        "payment_id": req.razorpay_payment_id,
        "order_id": server_order_id,
        "recovered_amount": recovered_val,
        "message": f"Successfully verified provider recovery payment of INR {recovered_val:.2f}."
    }

@router.post("/demo/cases/{case_id}/execute", response_model=ExecutionResponse, tags=["Recovery Execution (Demo)"])
async def demo_execute_case_recovery(
    case_id: str,
    req: Optional[ExecutionRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    return await execute_case_recovery(case_id, req, db)

class ReconcileProviderRecoveryRequest(BaseModel):
    payment_id: str = "pay_TU3EQsT63DFVuX"
    order_id: str = "order_TU2xgzptEfg7rP"

@router.post("/recovery/reconcile", tags=["Recovery Execution"])
async def reconcile_provider_recovery_endpoint(
    req: Optional[ReconcileProviderRecoveryRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Reconciles a real provider-confirmed recovery payment directly against Razorpay API."""
    from app.services.recovery.reconciliation_service import reconciliation_service
    p_id = req.payment_id if (req and req.payment_id) else "pay_TU3EQsT63DFVuX"
    o_id = req.order_id if (req and req.order_id) else "order_TU2xgzptEfg7rP"
    return await reconciliation_service.reconcile_provider_recovery(
        payment_id=p_id,
        order_id=o_id,
        db=db,
        verification_source="RAZORPAY_API_RECONCILIATION"
    )

@router.post("/demo/seed", tags=["Demo Seeding"])
async def trigger_demo_seeding(db: AsyncSession = Depends(get_db)):
    """Triggers complete demo data seeding and provider reconciliation on-demand."""
    from app.db.init_db import seed_demo_data_if_empty
    await seed_demo_data_if_empty()
    return {"status": "success", "message": "Demo data seeding and reconciliation executed."}

