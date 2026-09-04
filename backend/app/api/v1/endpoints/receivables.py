from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.receivables_and_mandates import Invoice
from app.models.merchant import Merchant
from app.services.revenue_risk.receivables_service import receivables_chaser_service
from app.models.base import utc_now

router = APIRouter(prefix="/receivables", tags=["B2B Receivables"])

class CreateInvoiceRequest(BaseModel):
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    invoice_number: str
    amount: float
    due_date: datetime

class PromiseToPayRequest(BaseModel):
    invoice_id: str
    promise_date: datetime

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    amount: float
    currency: str
    due_date: str
    status: str
    days_overdue: int
    promise_date: Optional[str] = None
    reminder_count: int
    created_at: str

@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(db: AsyncSession = Depends(get_db)):
    """Lists all B2B invoices and processes overdue statuses."""
    await receivables_chaser_service.process_overdue_invoices(db)
    res = await db.execute(select(Invoice).order_by(Invoice.created_at.desc()))
    invoices = res.scalars().all()
    return [
        InvoiceResponse(
            id=inv.id,
            invoice_number=inv.invoice_number,
            amount=float(inv.amount),
            currency=inv.currency,
            due_date=inv.due_date.isoformat(),
            status=inv.status,
            days_overdue=inv.days_overdue,
            promise_date=inv.promise_date.isoformat() if inv.promise_date else None,
            reminder_count=inv.reminder_count,
            created_at=inv.created_at.isoformat()
        )
        for inv in invoices
    ]

@router.post("/create", response_model=InvoiceResponse)
async def create_invoice(payload: CreateInvoiceRequest, db: AsyncSession = Depends(get_db)):
    m_id = payload.merchant_id
    if not m_id:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        m_id = merchant.id if merchant else "merch_demo"

    inv = await receivables_chaser_service.create_invoice(
        db=db,
        merchant_id=m_id,
        invoice_number=payload.invoice_number,
        amount=payload.amount,
        due_date=payload.due_date,
        customer_id=payload.customer_id
    )
    return InvoiceResponse(
        id=inv.id,
        invoice_number=inv.invoice_number,
        amount=float(inv.amount),
        currency=inv.currency,
        due_date=inv.due_date.isoformat(),
        status=inv.status,
        days_overdue=inv.days_overdue,
        promise_date=inv.promise_date.isoformat() if inv.promise_date else None,
        reminder_count=inv.reminder_count,
        created_at=inv.created_at.isoformat()
    )

@router.post("/promise-to-pay", response_model=InvoiceResponse)
async def register_promise_to_pay(payload: PromiseToPayRequest, db: AsyncSession = Depends(get_db)):
    inv = await receivables_chaser_service.register_promise_to_pay(
        db=db,
        invoice_id=payload.invoice_id,
        promise_date=payload.promise_date
    )
    return InvoiceResponse(
        id=inv.id,
        invoice_number=inv.invoice_number,
        amount=float(inv.amount),
        currency=inv.currency,
        due_date=inv.due_date.isoformat(),
        status=inv.status,
        days_overdue=inv.days_overdue,
        promise_date=inv.promise_date.isoformat() if inv.promise_date else None,
        reminder_count=inv.reminder_count,
        created_at=inv.created_at.isoformat()
    )
