from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.api.deps import get_db
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.services.analytics.recovery_funnel import recovery_funnel, RecoveryFunnelResponse
from app.services.analytics.ai_metrics import ai_metrics, AIMetricsResponse
from app.services.recovery.checkout_abandonment import checkout_abandonment_service, CheckoutAbandonmentMetrics

router = APIRouter()

@router.get("/analytics/metrics", tags=["Analytics"])
async def get_analytics_metrics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get aggregated merchant dashboard metrics dynamically calculated from live provider database state.
    Calculates active revenue at risk only for active unrecovered merchant cases (amount <= 5000.0).
    """
    live_filter = RecoveryCase.amount <= 5000.0
    active_status_filter = RecoveryCase.status.in_(["OPEN", "DIAGNOSED", "RECOVERING"])

    total_cases_res = await db.execute(select(func.count(RecoveryCase.id)).where(live_filter))
    total_cases = total_cases_res.scalar() or 0

    risk_sum_res = await db.execute(select(func.sum(RecoveryCase.amount)).where(and_(live_filter, active_status_filter)))
    revenue_at_risk = float(risk_sum_res.scalar() or 0.0)

    pf_risk_res = await db.execute(select(func.sum(RecoveryCase.amount)).where(and_(live_filter, RecoveryCase.case_type == "PAYMENT_FAILURE", active_status_filter)))
    payment_failure_risk = float(pf_risk_res.scalar() or 0.0)

    cd_risk_res = await db.execute(select(func.sum(RecoveryCase.amount)).where(and_(live_filter, RecoveryCase.case_type == "CHECKOUT_DROPOFF", active_status_filter)))
    checkout_dropoff_risk = float(cd_risk_res.scalar() or 0.0)

    sub_risk_res = await db.execute(select(func.sum(RecoveryCase.amount)).where(and_(live_filter, RecoveryCase.case_type == "SUBSCRIPTION_FAILURE", active_status_filter)))
    subscription_risk = float(sub_risk_res.scalar() or 0.0)

    cd_cases_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.case_type == "CHECKOUT_DROPOFF")))
    checkout_dropoff_cases_count = cd_cases_res.scalar() or 0

    sub_cases_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.case_type == "SUBSCRIPTION_FAILURE")))
    subscription_cases_count = sub_cases_res.scalar() or 0

    recovered_sum_res = await db.execute(select(func.sum(RecoveryCase.recovered_amount)).where(live_filter))
    recovered_revenue = float(recovered_sum_res.scalar() or 0.0)

    rec_cases_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.status == "RECOVERED")))
    recovered_cases = rec_cases_res.scalar() or 0

    attempts_res = await db.execute(select(func.count(RecoveryAction.id)).where(RecoveryAction.status.in_(["SUCCEEDED", "CREATED"])))
    recovery_attempts = attempts_res.scalar() or 0

    blocked_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.policy_passed == False)))
    policy_blocked = blocked_res.scalar() or 0

    escalated_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.status == "ESCALATED")))
    escalated = escalated_res.scalar() or 0

    total_denom = revenue_at_risk + recovered_revenue
    recovery_rate = round((recovered_revenue / total_denom * 100.0), 2) if total_denom > 0 else 0.0
    remaining_risk = round(max(0.0, revenue_at_risk), 2)

    return {
        "revenue_at_risk": revenue_at_risk,
        "payment_failure_risk": payment_failure_risk,
        "checkout_dropoff_risk": checkout_dropoff_risk,
        "subscription_risk": subscription_risk,
        "recovered_revenue": recovered_revenue,
        "recovery_rate": recovery_rate,
        "failed_payments_count": total_cases,
        "checkout_dropoff_cases_count": checkout_dropoff_cases_count,
        "subscription_cases_count": subscription_cases_count,
        "recovered_cases_count": recovered_cases,
        "recovery_attempts_count": recovery_attempts,
        "policy_allowed_count": max(0, total_cases - policy_blocked),
        "policy_blocked_count": policy_blocked,
        "escalated_count": escalated,
        "remaining_risk": remaining_risk
    }

@router.get("/analytics/funnel", tags=["Analytics"])
async def get_analytics_funnel(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    live_filter = RecoveryCase.amount <= 5000.0

    total_res = await db.execute(select(func.count(RecoveryCase.id)).where(live_filter))
    total = total_res.scalar() or 0

    diagnosed_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.ai_recommended_action.isnot(None))))
    diagnosed = diagnosed_res.scalar() or 0

    approved_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.policy_passed == True)))
    approved = approved_res.scalar() or 0

    attempts_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.retry_count > 0)))
    attempted = attempts_res.scalar() or 0

    recovered_res = await db.execute(select(func.count(RecoveryCase.id)).where(and_(live_filter, RecoveryCase.status == "RECOVERED")))
    recovered = recovered_res.scalar() or 0

    return {
        "funnel": [
            {"stage": "Failed Payments", "count": total, "conversion": 100.0},
            {"stage": "AI Diagnosed", "count": diagnosed, "conversion": round((diagnosed / total * 100.0), 2) if total > 0 else 0.0},
            {"stage": "Policy Approved", "count": approved, "conversion": round((approved / total * 100.0), 2) if total > 0 else 0.0},
            {"stage": "Recovery Attempted", "count": attempted, "conversion": round((attempted / total * 100.0), 2) if total > 0 else 0.0},
            {"stage": "Revenue Recovered", "count": recovered, "conversion": round((recovered / total * 100.0), 2) if total > 0 else 0.0}
        ]
    }

@router.get("/analytics/recent-activity", tags=["Analytics"])
async def get_recent_activity(limit: int = 20, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    res = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    audits = res.scalars().all()
    
    activity = []
    for a in audits:
        activity.append({
            "id": a.id,
            "case_id": a.case_id,
            "actor": a.actor,
            "event_type": a.event_type,
            "description": a.description,
            "metadata": a.metadata_json or {},
            "timestamp": a.created_at
        })
    return activity

@router.get("/analytics/recovery-funnel", response_model=RecoveryFunnelResponse, tags=["Analytics"])
async def get_detailed_recovery_funnel(db: AsyncSession = Depends(get_db)):
    """
    Retrieve deterministic 8-stage Recovery Funnel analytics, conversion/drop-off rates,
    monetary funnel values, drop-off reasons, and timing metrics.
    """
    return await recovery_funnel.get_funnel_metrics(db)

@router.get("/analytics/ai-metrics", response_model=AIMetricsResponse, tags=["Analytics"])
async def get_ai_evaluation_metrics(db: AsyncSession = Depends(get_db)):
    """
    Retrieve structured AI Decision Evaluation metrics, confidence calibration bands,
    recommendation agreement rates, policy/stopping/human alignment metrics, and limitation notices.
    """
    return await ai_metrics.get_ai_metrics(db)

@router.get("/analytics/checkout-abandonment", response_model=CheckoutAbandonmentMetrics, tags=["Analytics"])
async def get_checkout_abandonment_analytics(db: AsyncSession = Depends(get_db)):
    """
    Retrieve aggregated checkout abandonment analytics, abandonment rates, completion rates,
    and recovered abandoned revenue.
    """
    return await checkout_abandonment_service.get_abandonment_metrics(db)

