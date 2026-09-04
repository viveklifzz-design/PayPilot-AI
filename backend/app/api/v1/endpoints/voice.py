from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.models.receivables_and_mandates import Invoice, PromiseToPay
from app.models.audit_log import AuditLog
from app.services.recovery.voice_recovery_service import (
    voice_recovery_service,
    VoiceSimulateResponse,
    PromiseToPayResponse,
    B2BReceivablesAnalytics
)
from app.core.exceptions import ResourceNotFoundException

router = APIRouter()

class VoiceSimulateRequest(BaseModel):
    invoice_id: str
    customer_speech: str
    session_id: Optional[str] = None

class PromiseToPayRequest(BaseModel):
    invoice_id: str
    promise_date: datetime
    session_id: Optional[str] = None

@router.post("/voice/simulate-intent", response_model=VoiceSimulateResponse, tags=["Voice Recovery Engine"])
async def simulate_voice_intent_endpoint(
    req: VoiceSimulateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Parse customer speech (Hinglish/English), evaluate Policy Gate + Stopping Rules + Escalation,
    generate soft female voice response, and execute safe automated actions.
    """
    try:
        return await voice_recovery_service.handle_voice_interaction(
            db=db,
            invoice_id=req.invoice_id,
            customer_speech=req.customer_speech,
            session_id=req.session_id
        )
    except ValueError as val_err:
        raise ResourceNotFoundException(resource="Invoice", resource_id=req.invoice_id)

@router.post("/voice/promise-to-pay", response_model=PromiseToPayResponse, tags=["Voice Recovery Engine"])
async def register_promise_to_pay_endpoint(
    req: PromiseToPayRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a customer's Promise-to-Pay date for a B2B invoice.
    """
    res = await db.execute(select(Invoice).where(Invoice.id == req.invoice_id))
    inv = res.scalar_one_or_none()
    if not inv:
        raise ResourceNotFoundException(resource="Invoice", resource_id=req.invoice_id)

    sess_id = req.session_id or f"v_sess_{req.invoice_id[:8]}"
    p2p = PromiseToPay(
        merchant_id=inv.merchant_id,
        invoice_id=inv.id,
        customer_id=inv.customer_id,
        promised_amount=float(inv.amount),
        promise_date=req.promise_date,
        status="PROMISED",
        session_id=sess_id
    )
    db.add(p2p)
    inv.status = "PROMISE_TO_PAY"
    inv.promise_date = req.promise_date
    db.add(inv)
    await db.commit()
    await db.refresh(p2p)

    cust_name = "Valued Partner"
    if inv.customer:
        cust_name = inv.customer.name

    return PromiseToPayResponse(
        promise_id=p2p.id,
        invoice_id=inv.id,
        invoice_number=inv.invoice_number,
        customer_name=cust_name,
        promised_amount=float(p2p.promised_amount),
        promise_date=p2p.promise_date,
        status=p2p.status,
        session_id=sess_id
    )

@router.get("/voice/sessions/{session_id}", tags=["Voice Recovery Engine"])
async def get_voice_session_audit_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve structured voice interaction audit logs for a specific conversation session."""
    res = await db.execute(
        select(AuditLog)
        .where(AuditLog.actor == "FEMALE_AI_VOICE_AGENT")
        .order_by(AuditLog.created_at.asc())
    )
    logs = res.scalars().all()
    filtered = [l for l in logs if (l.metadata_json and l.metadata_json.get("session_id") == session_id)]

    return {
        "session_id": session_id,
        "total_turns": len(filtered),
        "audit_logs": [
            {
                "id": l.id,
                "event_type": l.event_type,
                "description": l.description,
                "metadata": l.metadata_json,
                "created_at": l.created_at
            }
            for l in filtered
        ]
    }

@router.get("/analytics/b2b-receivables", response_model=B2BReceivablesAnalytics, tags=["Analytics"])
async def get_b2b_receivables_analytics_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """Retrieve aggregated B2B receivables analytics, promise-to-pay conversion rates, and recovered revenue."""
    return await voice_recovery_service.get_b2b_analytics(db=db)
