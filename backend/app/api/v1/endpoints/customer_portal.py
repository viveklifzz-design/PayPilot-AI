from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.services.revenue_risk.failure_explanation import explain_razorpay_failure

router = APIRouter(prefix="/customer", tags=["Customer Portal"])

class CustomerLoginRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    customer_id: Optional[str] = None

class CustomerLoginResponse(BaseModel):
    customer_id: str
    name: str
    email: Optional[str] = None
    auth_token: str

class CustomerTransactionResponse(BaseModel):
    transaction_id: str
    razorpay_payment_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    payment_method: Optional[str] = None
    error_code: Optional[str] = None
    error_reason: Optional[str] = None
    error_explanation: str
    recovery_status: Optional[str] = None
    recovery_link_url: Optional[str] = None
    created_at: str

@router.post("/login", response_model=CustomerLoginResponse)
async def customer_login(payload: CustomerLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates a customer by email/phone or customer_id."""
    query = select(Customer)
    if payload.customer_id:
        query = query.where(Customer.id == payload.customer_id)
    elif payload.email:
        query = query.where(Customer.email == payload.email)
    elif payload.phone:
        query = query.where(Customer.phone == payload.phone)
    else:
        raise HTTPException(status_code=400, detail="Must provide customer_id, email, or phone.")

    res = await db.execute(query)
    cust = res.scalar_one_or_none()

    if not cust:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        m_id = merchant.id if merchant else "merch_demo"

        cust = Customer(
            merchant_id=m_id,
            name=payload.email.split("@")[0] if payload.email else "Demo Customer",
            email=payload.email,
            phone=payload.phone
        )
        db.add(cust)
        await db.commit()
        await db.refresh(cust)

    return CustomerLoginResponse(
        customer_id=cust.id,
        name=cust.name or "Customer",
        email=cust.email,
        auth_token=f"cust_token_{cust.id}"
    )

@router.get("/transactions", response_model=List[CustomerTransactionResponse])
async def list_customer_transactions(
    x_customer_id: str = Header(..., description="Authenticated Customer ID"),
    db: AsyncSession = Depends(get_db)
):
    """Lists all transactions belonging to the authenticated customer."""
    res = await db.execute(
        select(Transaction).where(Transaction.customer_id == x_customer_id).order_by(Transaction.created_at.desc())
    )
    txns = res.scalars().all()

    out = []
    for txn in txns:
        exp = explain_razorpay_failure(
            error_code=txn.error_code,
            error_source=txn.error_source,
            error_step=txn.error_step,
            error_reason=txn.error_reason,
            error_description=txn.error_description
        )
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == txn.id))
        case = case_res.scalar_one_or_none()
        recovery_status = case.status if case else None
        recovery_link = None
        if case:
            act_res = await db.execute(select(RecoveryAction).where(RecoveryAction.case_id == case.id))
            actions = act_res.scalars().all()
            for a in actions:
                if a.short_url:
                    recovery_link = a.short_url
                    break
        out.append(
            CustomerTransactionResponse(
                transaction_id=txn.id,
                razorpay_payment_id=txn.razorpay_payment_id,
                amount=float(txn.amount),
                currency=txn.currency,
                status=txn.status,
                payment_method=txn.payment_method,
                error_code=txn.error_code,
                error_reason=txn.error_reason,
                error_explanation=exp,
                recovery_status=recovery_status,
                recovery_link_url=recovery_link,
                created_at=str(txn.created_at)
            )
        )
    return out

@router.get("/transactions/{transaction_id}", response_model=CustomerTransactionResponse)
async def get_customer_transaction(
    transaction_id: str,
    x_customer_id: str = Header(..., description="Authenticated Customer ID for ownership verification"),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure Customer Portal Transaction Lookup.
    Lookup by internal UUID or razorpay_payment_id (pay_...).
    STRICT SECURITY ENFORCEMENT: Verifies transaction ownership. Returns 403 Forbidden if transaction belongs to another customer.
    """
    res = await db.execute(
        select(Transaction).where(
            or_(Transaction.id == transaction_id, Transaction.razorpay_payment_id == transaction_id)
        )
    )
    txn = res.scalar_one_or_none()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    # OWNERSHIP SECURITY RULE
    if txn.customer_id and txn.customer_id != x_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view another customer's transaction."
        )

    exp = explain_razorpay_failure(
        error_code=txn.error_code,
        error_source=txn.error_source,
        error_step=txn.error_step,
        error_reason=txn.error_reason,
        error_description=txn.error_description
    )

    case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == txn.id))
    case = case_res.scalar_one_or_none()

    recovery_status = case.status if case else None
    recovery_link = None

    if case:
        act_res = await db.execute(select(RecoveryAction).where(RecoveryAction.case_id == case.id))
        actions = act_res.scalars().all()
        for a in actions:
            if a.short_url:
                recovery_link = a.short_url
                break

    return CustomerTransactionResponse(
        transaction_id=txn.id,
        razorpay_payment_id=txn.razorpay_payment_id,
        amount=float(txn.amount),
        currency=txn.currency,
        status=txn.status,
        payment_method=txn.payment_method,
        error_code=txn.error_code,
        error_reason=txn.error_reason,
        error_explanation=exp,
        recovery_status=recovery_status,
        recovery_link_url=recovery_link,
        created_at=str(txn.created_at)
    )
