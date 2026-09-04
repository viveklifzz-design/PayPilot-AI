from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.models.subscription import Subscription
from app.services.revenue_risk.subscription_recovery import (
    subscription_recovery_service,
    SubscriptionRecoveryStatusResponse,
    SubscriptionRetryResponse,
    SubscriptionAnalytics
)
from app.core.exceptions import ResourceNotFoundException

router = APIRouter()

@router.get("/subscriptions", tags=["Subscriptions"])
async def list_subscriptions(
    status: Optional[str] = Query(None, description="Filter by subscription status"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """List subscriptions with optional status filter."""
    stmt = select(Subscription)
    if status:
        stmt = stmt.where(Subscription.status == status)
    stmt = stmt.order_by(Subscription.created_at.desc()).limit(limit)

    res = await db.execute(stmt)
    subs = res.scalars().all()

    result = []
    for s in subs:
        result.append({
            "id": s.id,
            "merchant_id": s.merchant_id,
            "customer_id": s.customer_id,
            "plan_name": s.plan_name,
            "amount": float(s.amount),
            "currency": s.currency,
            "billing_interval": s.billing_interval,
            "status": s.status,
            "recovery_status": s.recovery_status,
            "failure_reason": s.failure_reason,
            "retry_count": s.retry_count,
            "max_retry_attempts": s.max_retry_attempts,
            "grace_period_until": s.grace_period_until,
            "created_at": s.created_at,
            "updated_at": s.updated_at
        })
    return result

@router.get("/subscriptions/{subscription_id}", tags=["Subscriptions"])
async def get_subscription_detail(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get single subscription detail by ID."""
    res = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    sub = res.scalar_one_or_none()
    if not sub:
        raise ResourceNotFoundException(resource="Subscription", resource_id=subscription_id)

    return {
        "id": sub.id,
        "merchant_id": sub.merchant_id,
        "customer_id": sub.customer_id,
        "plan_name": sub.plan_name,
        "amount": float(sub.amount),
        "currency": sub.currency,
        "billing_interval": sub.billing_interval,
        "status": sub.status,
        "recovery_status": sub.recovery_status,
        "failure_reason": sub.failure_reason,
        "retry_count": sub.retry_count,
        "max_retry_attempts": sub.max_retry_attempts,
        "grace_period_until": sub.grace_period_until,
        "created_at": sub.created_at,
        "updated_at": sub.updated_at
    }

@router.get("/subscriptions/{subscription_id}/recovery", response_model=SubscriptionRecoveryStatusResponse, tags=["Subscriptions"])
async def get_subscription_recovery_endpoint(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed subscription recovery status, state machine lineage, and retry eligibility."""
    try:
        return await subscription_recovery_service.get_subscription_recovery_status(db=db, subscription_id=subscription_id)
    except ValueError as val_err:
        raise ResourceNotFoundException(resource="Subscription", resource_id=subscription_id)

@router.get("/analytics/failed-subscriptions", response_model=SubscriptionAnalytics, tags=["Analytics"])
async def get_failed_subscriptions_analytics_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """Retrieve aggregated failed subscription recovery analytics."""
    return await subscription_recovery_service.get_subscription_analytics(db=db)

@router.post("/subscriptions/{subscription_id}/retry", response_model=SubscriptionRetryResponse, tags=["Subscriptions"])
async def retry_subscription_endpoint(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Initiate safe controlled subscription retry after evaluating Policy Gate, Stopping Rules, and Human Escalation."""
    try:
        return await subscription_recovery_service.evaluate_and_execute_subscription_retry(db=db, subscription_id=subscription_id)
    except ValueError as val_err:
        raise ResourceNotFoundException(resource="Subscription", resource_id=subscription_id)

@router.post("/subscriptions/{subscription_id}/stop", tags=["Subscriptions"])
async def stop_subscription_recovery_endpoint(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually stop automatic recovery for a recurring subscription."""
    res = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
    sub = res.scalar_one_or_none()
    if not sub:
        raise ResourceNotFoundException(resource="Subscription", resource_id=subscription_id)

    sub.status = "STOPPED"
    sub.recovery_status = "STOPPED"
    db.add(sub)
    await db.commit()

    return {
        "subscription_id": sub.id,
        "status": "STOPPED",
        "message": "Subscription automatic recovery stopped manually by operator."
    }
