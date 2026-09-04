from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.receivables_and_mandates import Mandate, MandateRetryAttempt
from app.models.merchant import Merchant
from app.services.revenue_risk.mandate_service import mandate_retry_sequencer_service

router = APIRouter(prefix="/mandates", tags=["Mandate Retry Sequencer"])

class CreateMandateRequest(BaseModel):
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    mandate_number: str
    amount: float
    billing_interval: str = "monthly"

class MandateResponse(BaseModel):
    id: str
    mandate_number: str
    amount: float
    currency: str
    billing_interval: str
    attempt_count: int
    max_attempts: int
    status: str
    next_retry_date: Optional[str] = None
    created_at: str

class MandateAttemptRequest(BaseModel):
    mandate_id: str
    failure_reason: Optional[str] = "Bank auto-debit failed"

class MandateAttemptResponse(BaseModel):
    id: str
    attempt_number: int
    idempotency_key: str
    status: str
    failure_reason: Optional[str] = None
    provider_payment_id: Optional[str] = None
    policy_decision: Optional[str] = None
    attempted_at: str
    next_retry_at: Optional[str] = None

class MandateDetailResponse(MandateResponse):
    failure_reason: Optional[str] = None
    escalation_reason: Optional[str] = None
    last_retry_at: Optional[str] = None
    attempts: List[MandateAttemptResponse] = []

class ExecuteRetryRequest(BaseModel):
    idempotency_key: Optional[str] = None
    simulate_success: bool = True

class EscalateMandateRequest(BaseModel):
    reason: Optional[str] = "Manual merchant escalation requested"

@router.get("", response_model=List[MandateResponse])
async def list_mandates(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Mandate).order_by(Mandate.created_at.desc()))
    mandates = res.scalars().all()
    return [
        MandateResponse(
            id=m.id,
            mandate_number=m.mandate_number,
            amount=float(m.amount),
            currency=m.currency,
            billing_interval=m.billing_interval,
            attempt_count=m.attempt_count,
            max_attempts=m.max_attempts,
            status=m.status,
            next_retry_date=m.next_retry_date.isoformat() if m.next_retry_date else None,
            created_at=m.created_at.isoformat()
        )
        for m in mandates
    ]

@router.get("/{mandate_id}", response_model=MandateDetailResponse)
async def get_mandate_details(mandate_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Mandate).where(Mandate.id == mandate_id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail=f"Mandate '{mandate_id}' not found")

    att_res = await db.execute(
        select(MandateRetryAttempt).where(MandateRetryAttempt.mandate_id == mandate_id).order_by(MandateRetryAttempt.attempt_number.asc())
    )
    attempts = att_res.scalars().all()

    return MandateDetailResponse(
        id=m.id,
        mandate_number=m.mandate_number,
        amount=float(m.amount),
        currency=m.currency,
        billing_interval=m.billing_interval,
        attempt_count=m.attempt_count,
        max_attempts=m.max_attempts,
        status=m.status,
        failure_reason=m.failure_reason,
        escalation_reason=m.escalation_reason,
        next_retry_date=m.next_retry_date.isoformat() if m.next_retry_date else None,
        last_retry_at=m.last_retry_at.isoformat() if m.last_retry_at else None,
        created_at=m.created_at.isoformat(),
        attempts=[
            MandateAttemptResponse(
                id=a.id,
                attempt_number=a.attempt_number,
                idempotency_key=a.idempotency_key,
                status=a.status,
                failure_reason=a.failure_reason,
                provider_payment_id=a.provider_payment_id,
                policy_decision=a.policy_decision,
                attempted_at=a.attempted_at.isoformat(),
                next_retry_at=a.next_retry_at.isoformat() if a.next_retry_at else None
            )
            for a in attempts
        ]
    )

@router.post("/create", response_model=MandateResponse)
async def create_mandate(payload: CreateMandateRequest, db: AsyncSession = Depends(get_db)):
    m_id = payload.merchant_id
    if not m_id:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        m_id = merchant.id if merchant else "merch_demo"

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db,
        merchant_id=m_id,
        mandate_number=payload.mandate_number,
        amount=payload.amount,
        billing_interval=payload.billing_interval,
        customer_id=payload.customer_id
    )
    return MandateResponse(
        id=mandate.id,
        mandate_number=mandate.mandate_number,
        amount=float(mandate.amount),
        currency=mandate.currency,
        billing_interval=mandate.billing_interval,
        attempt_count=mandate.attempt_count,
        max_attempts=mandate.max_attempts,
        status=mandate.status,
        next_retry_date=mandate.next_retry_date.isoformat() if mandate.next_retry_date else None,
        created_at=mandate.created_at.isoformat()
    )

@router.post("/attempt-failure", response_model=MandateResponse)
async def trigger_failed_attempt(payload: MandateAttemptRequest, db: AsyncSession = Depends(get_db)):
    mandate, case = await mandate_retry_sequencer_service.process_failed_mandate_attempt(
        db=db,
        mandate_id=payload.mandate_id,
        failure_reason=payload.failure_reason or "Bank auto-debit failed"
    )
    return MandateResponse(
        id=mandate.id,
        mandate_number=mandate.mandate_number,
        amount=float(mandate.amount),
        currency=mandate.currency,
        billing_interval=mandate.billing_interval,
        attempt_count=mandate.attempt_count,
        max_attempts=mandate.max_attempts,
        status=mandate.status,
        next_retry_date=mandate.next_retry_date.isoformat() if mandate.next_retry_date else None,
        created_at=mandate.created_at.isoformat()
    )

@router.post("/{mandate_id}/execute-retry", response_model=MandateResponse)
async def execute_retry(mandate_id: str, payload: Optional[ExecuteRetryRequest] = None, db: AsyncSession = Depends(get_db)):
    idem_key = payload.idempotency_key if payload else None
    sim_succ = payload.simulate_success if payload is not None else True
    mandate, attempt, res = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db,
        mandate_id=mandate_id,
        idempotency_key=idem_key,
        simulate_success=sim_succ
    )
    return MandateResponse(
        id=mandate.id,
        mandate_number=mandate.mandate_number,
        amount=float(mandate.amount),
        currency=mandate.currency,
        billing_interval=mandate.billing_interval,
        attempt_count=mandate.attempt_count,
        max_attempts=mandate.max_attempts,
        status=mandate.status,
        next_retry_date=mandate.next_retry_date.isoformat() if mandate.next_retry_date else None,
        created_at=mandate.created_at.isoformat()
    )

@router.post("/{mandate_id}/escalate", response_model=MandateResponse)
async def escalate_mandate_endpoint(mandate_id: str, payload: Optional[EscalateMandateRequest] = None, db: AsyncSession = Depends(get_db)):
    reason = payload.reason if payload else "Manual merchant escalation requested"
    mandate = await mandate_retry_sequencer_service.escalate_mandate(
        db=db,
        mandate_id=mandate_id,
        reason=reason
    )
    return MandateResponse(
        id=mandate.id,
        mandate_number=mandate.mandate_number,
        amount=float(mandate.amount),
        currency=mandate.currency,
        billing_interval=mandate.billing_interval,
        attempt_count=mandate.attempt_count,
        max_attempts=mandate.max_attempts,
        status=mandate.status,
        next_retry_date=mandate.next_retry_date.isoformat() if mandate.next_retry_date else None,
        created_at=mandate.created_at.isoformat()
    )

@router.post("/{mandate_id}/reset-escalation", response_model=MandateResponse)
async def reset_escalation_endpoint(mandate_id: str, db: AsyncSession = Depends(get_db)):
    mandate = await mandate_retry_sequencer_service.reset_mandate_escalation(
        db=db,
        mandate_id=mandate_id
    )
    return MandateResponse(
        id=mandate.id,
        mandate_number=mandate.mandate_number,
        amount=float(mandate.amount),
        currency=mandate.currency,
        billing_interval=mandate.billing_interval,
        attempt_count=mandate.attempt_count,
        max_attempts=mandate.max_attempts,
        status=mandate.status,
        next_retry_date=mandate.next_retry_date.isoformat() if mandate.next_retry_date else None,
        created_at=mandate.created_at.isoformat()
    )
