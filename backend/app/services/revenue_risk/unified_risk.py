from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.checkout_session import CheckoutSession
from app.models.subscription import Subscription
from app.schemas.unified_risk import UnifiedRiskItem, UnifiedRiskSummaryResponse, UnifiedOpportunitiesResponse
from app.services.revenue_risk.priority_engine import priority_engine
from app.services.revenue_risk.failure_classifier import classify_razorpay_failure

STATUS_MAP = {
    "OPEN": "AT_RISK",
    "DIAGNOSED": "AT_RISK",
    "ACTION_PENDING": "RECOVERING",
    "IN_PROGRESS": "RECOVERING",
    "RECOVERING": "RECOVERING",
    "RECOVERED": "RECOVERED",
    "STOPPED": "STOPPED",
    "ESCALATED": "ESCALATED",
    "FAILED": "EXPIRED",
    "EXPIRED": "EXPIRED"
}

class UnifiedRevenueRiskService:
    """
    Unified Revenue Recovery Intelligence Service for PayPilot AI.
    Normalizes PAYMENT_FAILURE, CHECKOUT_DROPOFF, and SUBSCRIPTION_FAILURE cases into a canonical risk layer.
    """

    def map_unified_status(self, case_status: str) -> str:
        return STATUS_MAP.get(case_status.upper(), "AT_RISK")

    async def get_all_unified_risk_items(self, db: AsyncSession) -> List[UnifiedRiskItem]:
        res = await db.execute(
            select(RecoveryCase)
            .order_by(RecoveryCase.created_at.desc())
        )
        cases = res.scalars().all()

        items: List[UnifiedRiskItem] = []

        for case in cases:
            # Fetch linked transaction for failure details
            txn = None
            if case.transaction_id:
                t_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
                txn = t_res.scalar_one_or_none()

            classified = classify_razorpay_failure(
                error_code=txn.error_code if txn else None,
                error_source=txn.error_source if txn else None,
                error_step=txn.error_step if txn else None,
                error_reason=txn.error_reason if txn else None,
                error_description=txn.error_description if txn else None
            )

            # Compute priority score & factors using PriorityEngine
            p_res = priority_engine.calculate_priority(
                amount=float(case.amount),
                recoverability_score=0.70 if case.risk_level in ["LOW", "MEDIUM"] else 0.40,
                customer_successful_payments=0,
                retry_count=case.retry_count,
                case_type=case.case_type,
                failure_category=classified.category
            )

            uni_status = self.map_unified_status(case.status)
            risk_amt = float(case.amount) if uni_status in ["AT_RISK", "RECOVERING"] else 0.0

            source_str = "RAZORPAY_WEBHOOK"
            if case.case_type == "CHECKOUT_DROPOFF":
                source_str = "CHECKOUT_DETECTOR"
            elif case.case_type == "SUBSCRIPTION_FAILURE":
                source_str = "SUBSCRIPTION_ENGINE"
            elif case.case_type == "B2B_RECEIVABLE":
                source_str = "RECEIVABLES_CHASER"
            elif case.case_type == "MANDATE_RETRY":
                source_str = "MANDATE_SEQUENCER"

            item = UnifiedRiskItem(
                case_id=case.id,
                case_type=case.case_type,
                customer_id=case.customer_id,
                transaction_id=case.transaction_id,
                checkout_session_id=case.checkout_session_id,
                subscription_id=case.subscription_id,
                amount=float(case.amount),
                currency="INR",
                risk_amount=risk_amt,
                recoverability_score=0.70 if case.risk_level in ["LOW", "MEDIUM"] else 0.40,
                priority_score=p_res.priority_score,
                priority_level=p_res.priority_level,
                priority_factors=p_res.priority_factors,
                failure_category=classified.category if (txn and case.case_type != "CHECKOUT_DROPOFF") else case.case_type,
                status=case.status,
                unified_status=uni_status,
                created_at=case.created_at,
                source=source_str
            )
            items.append(item)

        # Sort by priority_score descending
        items.sort(key=lambda x: x.priority_score, reverse=True)
        return items

    async def get_unified_opportunities(self, db: AsyncSession) -> UnifiedOpportunitiesResponse:
        items = await self.get_all_unified_risk_items(db)

        # Deduplicated Risk Summaries
        total_risk = 0.0
        pf_risk = 0.0
        cd_risk = 0.0
        sub_risk = 0.0
        rec_revenue = 0.0
        total_rec_revenue = 0.0
        active_count = 0
        high_pri_count = 0

        cases_by_src: Dict[str, int] = {
            "PAYMENT_FAILURE": 0,
            "CHECKOUT_DROPOFF": 0,
            "SUBSCRIPTION_FAILURE": 0,
            "B2B_RECEIVABLE": 0,
            "MANDATE_RETRY": 0
        }
        cases_by_status: Dict[str, int] = {"AT_RISK": 0, "RECOVERING": 0, "RECOVERED": 0, "STOPPED": 0, "ESCALATED": 0, "EXPIRED": 0}

        active_opps: List[UnifiedRiskItem] = []

        for item in items:
            cases_by_src[item.case_type] = cases_by_src.get(item.case_type, 0) + 1
            cases_by_status[item.unified_status] = cases_by_status.get(item.unified_status, 0) + 1

            if item.status == "RECOVERED":
                total_rec_revenue += item.amount

            if item.unified_status in ["AT_RISK", "RECOVERING"]:
                total_risk += item.amount
                active_count += 1
                active_opps.append(item)

                if item.case_type == "PAYMENT_FAILURE":
                    pf_risk += item.amount
                elif item.case_type == "CHECKOUT_DROPOFF":
                    cd_risk += item.amount
                elif item.case_type == "SUBSCRIPTION_FAILURE":
                    sub_risk += item.amount

                if item.priority_level in ["HIGH", "CRITICAL"]:
                    high_pri_count += 1

                rec_revenue += (item.amount * item.recoverability_score)

        total_cases = len(items)
        denom = (total_risk + total_rec_revenue)
        recovery_rate = round((total_rec_revenue / denom * 100.0), 2) if denom > 0 else 0.0

        summary = UnifiedRiskSummaryResponse(
            total_revenue_at_risk=round(total_risk, 2),
            payment_failure_risk=round(pf_risk, 2),
            checkout_dropoff_risk=round(cd_risk, 2),
            subscription_risk=round(sub_risk, 2),
            recoverable_revenue=round(rec_revenue, 2),
            total_recovered_revenue=round(total_rec_revenue, 2),
            unified_recovery_rate=recovery_rate,
            total_cases_count=total_cases,
            active_opportunities_count=active_count,
            high_priority_count=high_pri_count,
            cases_by_source=cases_by_src,
            cases_by_unified_status=cases_by_status
        )

        return UnifiedOpportunitiesResponse(
            summary=summary,
            opportunities=active_opps
        )

unified_risk_service = UnifiedRevenueRiskService()
