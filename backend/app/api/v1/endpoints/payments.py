import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.schemas.payment import OrderCreate, OrderResponse
from app.schemas.transaction import TransactionResponse
from app.models.transaction import Transaction
from app.models.merchant import Merchant
from app.models.recovery_case import RecoveryCase
from app.services.razorpay import razorpay_service
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger

router = APIRouter()

@router.post("/payments/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Payments"])
async def create_order(order_in: OrderCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new payment order.
    If Razorpay Test credentials are configured in .env, calls Razorpay Test API to create a live Test Order.
    Otherwise, generates a simulated Test Order ID for local sandbox testing.
    """
    result = await db.execute(select(Merchant).where(Merchant.id == order_in.merchant_id))
    merchant = result.scalar_one_or_none()
    
    if not merchant:
        merchant = Merchant(
            id=order_in.merchant_id,
            name="Default Test Merchant",
            email=f"merchant_{order_in.merchant_id[:8]}@example.com"
        )
        db.add(merchant)
        await db.commit()

    razorpay_order_id = None
    if razorpay_service.is_configured:
        try:
            rzp_order = razorpay_service.create_order(
                amount=order_in.amount,
                currency=order_in.currency,
                receipt=order_in.receipt or f"rcpt_{uuid.uuid4().hex[:8]}",
                notes=order_in.notes
            )
            razorpay_order_id = rzp_order.get("id")
        except Exception as e:
            logger.error(f"Error calling Razorpay Order API: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Razorpay API Error: {str(e)}"
            )
    else:
        razorpay_order_id = f"order_test_{uuid.uuid4().hex[:12]}"
        logger.info(f"Razorpay credentials not set; generated sandbox order ID: {razorpay_order_id}")

    transaction = Transaction(
        merchant_id=order_in.merchant_id,
        customer_id=order_in.customer_id,
        razorpay_order_id=razorpay_order_id,
        amount=order_in.amount,
        currency=order_in.currency,
        status="created"
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return OrderResponse(
        id=transaction.id,
        merchant_id=transaction.merchant_id,
        customer_id=transaction.customer_id,
        razorpay_order_id=transaction.razorpay_order_id,
        amount=float(transaction.amount),
        currency=transaction.currency,
        status=transaction.status,
        created_at=transaction.created_at
    )

@router.get("/transactions", response_model=List[TransactionResponse], tags=["Transactions"])
async def list_transactions(
    merchant_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve transactions list with optional status, merchant filters, and recovery case info."""
    query = select(Transaction)
    if merchant_id:
        query = query.where(Transaction.merchant_id == merchant_id)
    if status_filter:
        query = query.where(Transaction.status == status_filter)
        
    query = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    transactions = result.scalars().all()

    res_list = []
    for t in transactions:
        t_dict = TransactionResponse.model_validate(t).model_dump(mode="json")
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == t.id).order_by(RecoveryCase.created_at.desc()))
        case = case_res.scalars().first()
        if case:
            t_dict["recovery_case_id"] = case.id
            t_dict["recovery_status"] = case.status
        res_list.append(t_dict)

    return res_list

@router.get("/transactions/{transaction_id}", response_model=TransactionResponse, tags=["Transactions"])
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific transaction by ID with recovery case info."""
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise ResourceNotFoundException(resource="Transaction", resource_id=transaction_id)
    
    t_dict = TransactionResponse.model_validate(transaction).model_dump(mode="json")
    case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == transaction.id).order_by(RecoveryCase.created_at.desc()))
    case = case_res.scalars().first()
    if case:
        t_dict["recovery_case_id"] = case.id
        t_dict["recovery_status"] = case.status

    return t_dict
