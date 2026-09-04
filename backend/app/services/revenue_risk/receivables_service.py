from typing import Optional, Tuple, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.receivables_and_mandates import Invoice
from app.models.recovery_case import RecoveryCase
from app.models.base import utc_now
from app.services.revenue_risk.risk_engine import risk_engine
from app.core.logging import logger

MAX_RECEIVABLE_REMINDERS = 3

class ReceivablesChaserService:
    """
    B2B Receivables Chaser & Promise-to-Pay Tracker Service.
    Tracks overdue invoices, enforces reminder stopping rules (max 3 reminders),
    monitors promised payment dates, and escalates missed promises.
    """

    async def create_invoice(
        self,
        db: AsyncSession,
        merchant_id: str,
        invoice_number: str,
        amount: float,
        due_date: datetime,
        customer_id: Optional[str] = None
    ) -> Invoice:
        inv = Invoice(
            merchant_id=merchant_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            amount=amount,
            currency="INR",
            due_date=due_date,
            status="DUE"
        )
        db.add(inv)
        await db.commit()
        await db.refresh(inv)
        return inv

    async def register_promise_to_pay(
        self,
        db: AsyncSession,
        invoice_id: str,
        promise_date: datetime
    ) -> Invoice:
        """Registers a customer's Promise-to-Pay date."""
        res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(f"Invoice '{invoice_id}' not found.")

        inv.status = "PROMISE_TO_PAY"
        inv.promise_date = promise_date
        db.add(inv)

        # Update associated RecoveryCase if present
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.invoice_id == inv.id))
        case = case_res.scalar_one_or_none()
        if case:
            case.status = "IN_PROGRESS"
            case.stop_reason = f"Customer promised to pay on {promise_date.strftime('%Y-%m-%d')}"
            db.add(case)

        await db.commit()
        await db.refresh(inv)
        logger.info(f"Registered Promise-to-Pay for Invoice '{inv.invoice_number}' on {promise_date}")
        return inv

    async def process_overdue_invoices(self, db: AsyncSession) -> List[RecoveryCase]:
        """Queries overdue invoices and creates/updates recovery cases with stopping rules."""
        now = utc_now()
        res = await db.execute(
            select(Invoice).where(Invoice.status.in_(["DUE", "OVERDUE", "PROMISE_TO_PAY"]))
        )
        invoices = res.scalars().all()
        created_cases = []

        for inv in invoices:
            due_dt = inv.due_date.replace(tzinfo=timezone.utc) if inv.due_date and inv.due_date.tzinfo is None else inv.due_date
            prom_dt = inv.promise_date.replace(tzinfo=timezone.utc) if inv.promise_date and inv.promise_date.tzinfo is None else inv.promise_date

            # Check missed promise date
            if inv.status == "PROMISE_TO_PAY" and prom_dt and now > prom_dt:
                inv.status = "ESCALATED"
                db.add(inv)
                case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.invoice_id == inv.id))
                case = case_res.scalar_one_or_none()
                if case:
                    case.status = "ESCALATED"
                    case.policy_failure_reason = "Missed promise-to-pay date"
                    db.add(case)
                logger.warning(f"Invoice '{inv.invoice_number}' missed promise-to-pay date -> ESCALATED")
                continue

            # Calculate days overdue
            if due_dt and now > due_dt:
                delta = (now - due_dt).days
                inv.days_overdue = delta
                if inv.status == "DUE":
                    inv.status = "OVERDUE"
                db.add(inv)

                # Check stopping rule: Max 3 reminders
                if inv.reminder_count >= MAX_RECEIVABLE_REMINDERS:
                    inv.status = "ESCALATED"
                    db.add(inv)

                # Check existing RecoveryCase
                case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.invoice_id == inv.id))
                case = case_res.scalar_one_or_none()

                if not case and inv.status != "ESCALATED":
                    risk_assessment = risk_engine.assess_transaction(
                        amount=float(inv.amount),
                        error_code="OVERDUE_RECEIVABLE",
                        error_description=f"B2B invoice #{inv.invoice_number} overdue by {delta} days"
                    )
                    case = RecoveryCase(
                        case_type="B2B_RECEIVABLE",
                        merchant_id=inv.merchant_id,
                        invoice_id=inv.id,
                        customer_id=inv.customer_id,
                        amount=float(inv.amount),
                        risk_score=risk_assessment.risk_score,
                        risk_level=risk_assessment.risk_level,
                        priority_score=risk_assessment.priority_score,
                        priority_level=risk_assessment.priority_level,
                        risk_factors=risk_assessment.risk_factors,
                        status="OPEN",
                        policy_passed=True
                    )
                    db.add(case)
                    created_cases.append(case)

        await db.commit()
        return created_cases

receivables_chaser_service = ReceivablesChaserService()
