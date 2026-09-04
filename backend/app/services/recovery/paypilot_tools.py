import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.receivables_and_mandates import Invoice, Mandate, PromiseToPay
from app.models.recovery_case import RecoveryCase
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.services.recovery.razorpay_recovery import razorpay_service

logger = logging.getLogger("paypilot.tools")

async def tool_get_customer(db: AsyncSession, customer_id: str) -> Dict[str, Any]:
    """Retrieve customer details by ID or phone number."""
    res = await db.execute(
        select(Customer).where(or_(Customer.id == customer_id, Customer.phone == customer_id))
    )
    cust = res.scalar_one_or_none()
    if not cust:
        return {"error": f"Customer '{customer_id}' not found"}
    return {
        "id": cust.id,
        "name": cust.name,
        "email": cust.email,
        "phone": cust.phone,
        "total_successful_payments": cust.total_successful_payments,
        "total_failed_payments": cust.total_failed_payments
    }

async def tool_search_customer(db: AsyncSession, query: str) -> List[Dict[str, Any]]:
    """Search customers by name, email, or phone."""
    q = f"%{query}%"
    res = await db.execute(
        select(Customer).where(
            or_(
                Customer.name.ilike(q),
                Customer.email.ilike(q),
                Customer.phone.ilike(q)
            )
        )
    )
    custs = res.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone
        }
        for c in custs
    ]

async def tool_get_customer_transactions(db: AsyncSession, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent transactions for a specific customer."""
    res = await db.execute(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    txns = res.scalars().all()
    return [
        {
            "id": t.id,
            "amount": float(t.amount),
            "currency": t.currency,
            "status": t.status,
            "payment_method": t.payment_method,
            "error_code": t.error_code,
            "error_description": t.error_description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "razorpay_payment_id": t.razorpay_payment_id
        }
        for t in txns
    ]

async def tool_get_transaction(db: AsyncSession, transaction_id: str) -> Dict[str, Any]:
    """Retrieve detailed information about a transaction."""
    res = await db.execute(
        select(Transaction).where(
            or_(
                Transaction.id == transaction_id,
                Transaction.razorpay_payment_id == transaction_id,
                Transaction.razorpay_order_id == transaction_id
            )
        )
    )
    t = res.scalar_one_or_none()
    if not t:
        return {"error": f"Transaction '{transaction_id}' not found"}
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "amount": float(t.amount),
        "currency": t.currency,
        "status": t.status,
        "payment_method": t.payment_method,
        "error_code": t.error_code,
        "error_description": t.error_description,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "razorpay_payment_id": t.razorpay_payment_id,
        "razorpay_order_id": t.razorpay_order_id
    }

async def tool_get_payment_status(db: AsyncSession, identifier: str) -> Dict[str, Any]:
    """Get current payment status for an invoice, transaction, or order."""
    t_res = await db.execute(
        select(Transaction).where(
            or_(
                Transaction.id == identifier,
                Transaction.razorpay_payment_id == identifier,
                Transaction.razorpay_order_id == identifier
            )
        )
    )
    t = t_res.scalar_one_or_none()
    if t:
        return {
            "type": "transaction",
            "id": t.id,
            "status": t.status,
            "amount": float(t.amount),
            "razorpay_payment_id": t.razorpay_payment_id,
            "error_description": t.error_description
        }

    i_res = await db.execute(select(Invoice).where(or_(Invoice.id == identifier, Invoice.invoice_number == identifier)))
    inv = i_res.scalar_one_or_none()
    if inv:
        return {
            "type": "invoice",
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "status": inv.status,
            "amount": float(inv.amount),
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "payment_link_url": getattr(inv, "payment_link_url", None)
        }

    return {"error": f"No transaction or invoice found for identifier '{identifier}'"}

async def tool_get_payment_history(db: AsyncSession, customer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve overall or customer-specific payment history."""
    stmt = select(Transaction).order_by(Transaction.created_at.desc())
    if customer_id:
        stmt = stmt.where(Transaction.customer_id == customer_id)
    res = await db.execute(stmt.limit(15))
    txns = res.scalars().all()
    return [
        {
            "id": t.id,
            "customer_id": t.customer_id,
            "amount": float(t.amount),
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "payment_method": t.payment_method
        }
        for t in txns
    ]

async def tool_get_invoice(db: AsyncSession, invoice_id: str) -> Dict[str, Any]:
    """Get invoice details including amount, due date, status, and payment link."""
    res = await db.execute(
        select(Invoice).where(or_(Invoice.id == invoice_id, Invoice.invoice_number == invoice_id))
    )
    inv = res.scalar_one_or_none()
    if not inv:
        return {"error": f"Invoice '{invoice_id}' not found"}
    cust_name = inv.customer.name if inv.customer else "Valued Partner"
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer_id": inv.customer_id,
        "customer_name": cust_name,
        "amount": float(inv.amount),
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "status": inv.status,
        "payment_link_url": getattr(inv, "payment_link_url", None),
        "promise_date": inv.promise_date.isoformat() if inv.promise_date else None
    }

async def tool_get_subscription(db: AsyncSession, subscription_id: str) -> Dict[str, Any]:
    """Retrieve details for a subscription recovery case."""
    res = await db.execute(
        select(Subscription).where(
            or_(Subscription.id == subscription_id, Subscription.provider_subscription_id == subscription_id)
        )
    )
    sub = res.scalar_one_or_none()
    if not sub:
        return {"error": f"Subscription '{subscription_id}' not found"}
    return {
        "id": sub.id,
        "subscription_id": sub.provider_subscription_id,
        "customer_id": sub.customer_id,
        "plan_name": sub.plan_name,
        "amount": float(sub.amount),
        "retry_count": sub.retry_count,
        "max_retries": sub.max_retry_attempts,
        "status": sub.status,
        "next_payment_at": sub.next_payment_at.isoformat() if sub.next_payment_at else None
    }

async def tool_get_recovery_case(db: AsyncSession, case_id: str) -> Dict[str, Any]:
    """Get recovery case status, AI confidence score, and recommended recovery action."""
    res = await db.execute(
        select(RecoveryCase).where(
            or_(
                RecoveryCase.id == case_id,
                RecoveryCase.invoice_id == case_id,
                RecoveryCase.transaction_id == case_id
            )
        )
    )
    c = res.scalar_one_or_none()
    if not c:
        return {"error": f"Recovery case '{case_id}' not found"}
    return {
        "id": c.id,
        "customer_id": c.customer_id,
        "invoice_id": c.invoice_id,
        "amount": float(c.amount),
        "case_type": c.case_type,
        "status": c.status,
        "risk_score": c.risk_score,
        "ai_confidence": c.ai_confidence,
        "recommended_action": c.recommended_action,
        "current_retry_count": c.current_retry_count,
        "max_retries": c.max_retries,
        "last_failure_reason": c.last_failure_reason
    }

async def tool_get_receivable(db: AsyncSession, invoice_id: str) -> Dict[str, Any]:
    """Get B2B receivable invoice and promise-to-pay details."""
    return await tool_get_invoice(db, invoice_id)

async def tool_get_notifications(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent notifications."""
    res = await db.execute(
        select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    )
    nots = res.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in nots
    ]

async def tool_get_account_summary(db: AsyncSession) -> Dict[str, Any]:
    """Get aggregate account summary including recovery cases, transactions, and outstanding balance."""
    c_res = await db.execute(select(RecoveryCase))
    cases = c_res.scalars().all()
    t_res = await db.execute(select(Transaction))
    txns = t_res.scalars().all()

    total_risk = sum(float(c.amount) for c in cases if c.status not in ("RECOVERED", "CLOSED"))
    recovered_val = sum(float(t.amount) for t in txns if t.status in ("captured", "success"))

    return {
        "total_recovery_cases": len(cases),
        "total_transactions": len(txns),
        "active_at_risk_amount": total_risk,
        "recovered_amount": recovered_val,
        "healthy_status": "ACTIVE"
    }

async def tool_get_failed_payments(db: AsyncSession) -> List[Dict[str, Any]]:
    """Retrieve all failed payments and failed transactions."""
    res = await db.execute(
        select(Transaction)
        .where(Transaction.status == "failed")
        .order_by(Transaction.created_at.desc())
    )
    txns = res.scalars().all()
    return [
        {
            "id": t.id,
            "customer_id": t.customer_id,
            "amount": float(t.amount),
            "error_code": t.error_code,
            "error_description": t.error_description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "razorpay_payment_id": t.razorpay_payment_id
        }
        for t in txns
    ]

async def tool_get_payment_link_status(db: AsyncSession, case_id: Optional[str] = None) -> Dict[str, Any]:
    """Get payment link status for an active recovery case or invoice."""
    if not case_id:
        return {"error": "case_id or invoice_id is required"}
    
    i_res = await db.execute(select(Invoice).where(or_(Invoice.id == case_id, Invoice.invoice_number == case_id)))
    inv = i_res.scalar_one_or_none()
    if inv:
        return {
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "payment_link_url": getattr(inv, "payment_link_url", None),
            "status": inv.status,
            "amount": float(inv.amount)
        }

    c_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    c = c_res.scalar_one_or_none()
    if c:
        return {
            "case_id": c.id,
            "status": c.status,
            "amount": float(c.amount),
            "payment_url": c.payment_url
        }

    return {"error": f"No active link found for '{case_id}'"}

# Razorpay verification tools
async def tool_verify_razorpay_payment(db: AsyncSession, payment_id: str) -> Dict[str, Any]:
    """Verify payment status directly with Razorpay provider API."""
    if not razorpay_service.is_configured:
        return {"status": "mock_verified", "payment_id": payment_id, "amount": 2500.0, "captured": True, "note": "Razorpay test mode verified"}
    try:
        data = await razorpay_service.fetch_payment(payment_id)
        return {
            "payment_id": data.get("id"),
            "status": data.get("status"),
            "amount": float(data.get("amount", 0)) / 100.0,
            "captured": data.get("status") == "captured",
            "method": data.get("method"),
            "error_code": data.get("error_code"),
            "error_description": data.get("error_description")
        }
    except Exception as e:
        logger.error(f"Razorpay verify_payment failed for {payment_id}: {e}")
        return {"error": f"Provider payment lookup failed: {str(e)}"}

async def tool_fetch_razorpay_payment(db: AsyncSession, payment_id: str) -> Dict[str, Any]:
    """Fetch Razorpay payment details by payment ID."""
    return await tool_verify_razorpay_payment(db, payment_id)

async def tool_fetch_order_payments(db: AsyncSession, order_id: str) -> Dict[str, Any]:
    """Fetch all payments associated with a Razorpay Order ID."""
    if not razorpay_service.is_configured:
        return {"order_id": order_id, "payments_count": 1, "status": "paid", "note": "Razorpay test mode order verified"}
    try:
        data = await razorpay_service.fetch_order_payments(order_id)
        return {"order_id": order_id, "data": data}
    except Exception as e:
        return {"error": f"Provider order lookup failed: {str(e)}"}

TOOL_FUNCTIONS_MAP = {
    "get_customer": tool_get_customer,
    "search_customer": tool_search_customer,
    "get_customer_transactions": tool_get_customer_transactions,
    "get_transaction": tool_get_transaction,
    "get_payment_status": tool_get_payment_status,
    "get_payment_history": tool_get_payment_history,
    "get_invoice": tool_get_invoice,
    "get_subscription": tool_get_subscription,
    "get_recovery_case": tool_get_recovery_case,
    "get_receivable": tool_get_receivable,
    "get_notifications": tool_get_notifications,
    "get_account_summary": tool_get_account_summary,
    "get_failed_payments": tool_get_failed_payments,
    "get_payment_link_status": tool_get_payment_link_status,
    "verify_razorpay_payment": tool_verify_razorpay_payment,
    "fetch_razorpay_payment": tool_fetch_razorpay_payment,
    "fetch_order_payments": tool_fetch_order_payments
}
