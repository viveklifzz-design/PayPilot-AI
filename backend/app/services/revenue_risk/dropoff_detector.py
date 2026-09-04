from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.checkout_session import CheckoutSession
from app.models.recovery_case import RecoveryCase
from app.models.customer import Customer
from app.models.audit_log import AuditLog
from app.services.revenue_risk.risk_engine import risk_engine
from app.models.base import utc_now
from app.core.logging import logger

CHECKOUT_DROPOFF_WINDOW_MINUTES = 30

class CheckoutDropoffDetector:
    """
    Deterministic Checkout Drop-off Detection Engine.
    Scans for unpaid checkout opportunities exceeding the inactivity window,
    idempotently transitions them to DROPPED, and creates a CHECKOUT_DROPOFF RecoveryCase.
    """

    async def create_checkout_session(
        self,
        db: AsyncSession,
        merchant_id: str,
        amount: float,
        currency: str = "INR",
        customer_id: Optional[str] = None,
        razorpay_order_id: Optional[str] = None,
        source: str = "CHECKOUT",
        metadata: Optional[dict] = None
    ) -> CheckoutSession:
        session = CheckoutSession(
            merchant_id=merchant_id,
            customer_id=customer_id,
            razorpay_order_id=razorpay_order_id,
            amount=amount,
            currency=currency,
            status="CREATED",
            source=source,
            raw_metadata=metadata
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        db.add(AuditLog(
            case_id=None,
            actor="CHECKOUT_SYSTEM",
            event_type="CHECKOUT_CREATED",
            description=f"New checkout session created for amount {currency} {amount:,.2f}",
            metadata_json={
                "session_id": session.id,
                "amount": float(amount),
                "currency": currency,
                "customer_id": customer_id
            }
        ))
        await db.commit()
        return session

    async def detect_and_process_dropoffs(
        self,
        db: AsyncSession,
        window_minutes: int = CHECKOUT_DROPOFF_WINDOW_MINUTES
    ) -> List[RecoveryCase]:
        cutoff_time = utc_now() - timedelta(minutes=window_minutes)

        # Query active checkout sessions created before cutoff
        query = select(CheckoutSession).where(
            and_(
                CheckoutSession.status.in_(["CREATED", "ACTIVE"]),
                CheckoutSession.created_at <= cutoff_time
            )
        )
        res = await db.execute(query)
        unpaid_sessions = res.scalars().all()

        created_cases: List[RecoveryCase] = []

        for session in unpaid_sessions:
            # Check idempotency: does a RecoveryCase already exist for this checkout session?
            existing_case_res = await db.execute(
                select(RecoveryCase).where(RecoveryCase.checkout_session_id == session.id)
            )
            existing_case = existing_case_res.scalar_one_or_none()

            # Transition CheckoutSession to DROPPED
            session.status = "DROPPED"
            session.dropoff_detected_at = utc_now()
            db.add(session)

            if existing_case:
                logger.info(f"CheckoutSession '{session.id}' already has RecoveryCase '{existing_case.id}'. Skipping duplicate case creation.")
                await db.commit()
                continue

            # Customer history lookup
            cust_succ = 0
            cust_fail = 0
            if session.customer_id:
                c_res = await db.execute(select(Customer).where(Customer.id == session.customer_id))
                cust = c_res.scalar_one_or_none()
                if cust:
                    cust_succ = cust.total_successful_payments
                    cust_fail = cust.total_failed_payments

            # Assess Revenue at Risk for Drop-off
            risk_assessment = risk_engine.assess_transaction(
                amount=float(session.amount),
                error_code="CHECKOUT_ABANDONED",
                error_description="Customer abandoned checkout page without attempting payment",
                customer_successful_payments=cust_succ,
                customer_failed_payments=cust_fail,
                retry_count=0
            )

            # Create CHECKOUT_DROPOFF RecoveryCase
            new_case = RecoveryCase(
                case_type="CHECKOUT_DROPOFF",
                merchant_id=session.merchant_id,
                transaction_id=None,
                checkout_session_id=session.id,
                customer_id=session.customer_id,
                amount=session.amount,
                risk_score=risk_assessment.risk_score,
                risk_level=risk_assessment.risk_level,
                priority_score=risk_assessment.priority_score,
                priority_level=risk_assessment.priority_level,
                risk_factors=risk_assessment.risk_factors + ["Customer abandoned checkout session"],
                status="OPEN"
            )
            db.add(new_case)
            await db.commit()
            await db.refresh(new_case)

            # Audit events
            db.add(AuditLog(
                case_id=new_case.id,
                actor="DROPOFF_DETECTOR",
                event_type="CHECKOUT_DROPOFF_DETECTED",
                description=f"Detected abandoned checkout session '{session.id}' after {window_minutes}m inactivity. Case #{new_case.id[:8]} initialized.",
                metadata_json={
                    "checkout_session_id": session.id,
                    "amount": float(session.amount),
                    "window_minutes": window_minutes
                }
            ))

            db.add(AuditLog(
                case_id=new_case.id,
                actor="REVENUE_RISK_ENGINE",
                event_type="REVENUE_RISK_ASSESSED",
                description=f"Assessed checkout drop-off: risk_score={risk_assessment.risk_score} ({risk_assessment.risk_level}), priority={risk_assessment.priority_level}",
                metadata_json={
                    "risk_score": risk_assessment.risk_score,
                    "risk_level": risk_assessment.risk_level,
                    "recoverability_score": risk_assessment.recoverability_score,
                    "priority_level": risk_assessment.priority_level
                }
            ))
            await db.commit()

            created_cases.append(new_case)
            logger.info(f"Created CHECKOUT_DROPOFF RecoveryCase '{new_case.id}' for session '{session.id}'")

        return created_cases

dropoff_detector = CheckoutDropoffDetector()
