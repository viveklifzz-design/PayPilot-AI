from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.receivables_and_mandates import Mandate, MandateRetryAttempt
from app.models.recovery_case import RecoveryCase
from app.models.audit_log import AuditLog
from app.models.base import utc_now
from app.services.revenue_risk.risk_engine import risk_engine
from app.services.recovery.policy_gate import policy_gate
from app.services.razorpay import razorpay_service
from app.services.notification_service import notification_service
from app.core.logging import logger

MAX_MANDATE_RETRIES = 3

class MandateRetrySequencerService:
    """
    Mandate Retry Sequencer Service (PayPilot Track 3).
    Enforces bounded, idempotent, policy-evaluated retry scheduling for recurring mandates
    integrated with Razorpay Test Mode, audit trails, and human escalation.
    """

    async def create_mandate(
        self,
        db: AsyncSession,
        merchant_id: str,
        mandate_number: str,
        amount: float,
        billing_interval: str = "monthly",
        customer_id: Optional[str] = None
    ) -> Mandate:
        mandate = Mandate(
            merchant_id=merchant_id,
            customer_id=customer_id,
            mandate_number=mandate_number,
            amount=amount,
            currency="INR",
            billing_interval=billing_interval,
            status="ACTIVE"
        )
        db.add(mandate)
        await db.commit()
        await db.refresh(mandate)
        return mandate

    async def process_failed_mandate_attempt(
        self,
        db: AsyncSession,
        mandate_id: str,
        failure_reason: str = "Bank auto-debit failed"
    ) -> Tuple[Mandate, Optional[RecoveryCase]]:
        res = await db.execute(select(Mandate).where(Mandate.id == mandate_id))
        mandate = res.scalar_one_or_none()
        if not mandate:
            raise ValueError(f"Mandate '{mandate_id}' not found.")

        mandate.failure_reason = failure_reason
        mandate.attempt_count += 1

        # Run Policy Gate evaluation before scheduling retry
        is_allowed, decision_reason, policy_action = policy_gate.evaluate_mandate_retry_policy(
            attempt_count=mandate.attempt_count,
            max_attempts=mandate.max_attempts,
            mandate_status=mandate.status,
            failure_reason=failure_reason
        )

        now = utc_now()

        # Check stopping rule: Max 3 retries or non-retryable failure
        if not is_allowed:
            if policy_action == "ESCALATE_TO_HUMAN" or mandate.attempt_count >= MAX_MANDATE_RETRIES:
                mandate.status = "ESCALATED"
                mandate.escalation_reason = decision_reason
            else:
                mandate.status = "CANCELLED"
            mandate.next_retry_date = None
            db.add(mandate)

            # Record blocked attempt
            idem_key = f"mandate_{mandate.id}_attempt_{mandate.attempt_count}_blocked"
            attempt = MandateRetryAttempt(
                mandate_id=mandate.id,
                attempt_number=mandate.attempt_count,
                idempotency_key=idem_key,
                status="BLOCKED",
                failure_reason=failure_reason,
                policy_decision=decision_reason,
                attempted_at=now
            )
            db.add(attempt)

            # Update or create RecoveryCase
            case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.mandate_id == mandate.id))
            case = case_res.scalar_one_or_none()
            if case:
                case.status = "ESCALATED"
                case.policy_failure_reason = decision_reason
                db.add(case)

            # Audit Log
            audit = AuditLog(
                case_id=case.id if case else None,
                actor="POLICY_GATE",
                event_type="MANDATE_RETRY_BLOCKED" if mandate.status != "ESCALATED" else "MANDATE_RETRY_ESCALATED",
                description=f"Mandate {mandate.mandate_number} retry blocked by policy gate: {decision_reason}",
                metadata_json={
                    "merchant_id": mandate.merchant_id,
                    "mandate_id": mandate.id,
                    "mandate_number": mandate.mandate_number,
                    "attempt_count": mandate.attempt_count,
                    "decision_reason": decision_reason,
                    "policy_action": policy_action,
                    "failure_reason": failure_reason
                }
            )
            db.add(audit)

            # Dispatch notification
            try:
                await notification_service.create_notification(
                    db=db,
                    type="MANDATE_ALERT",
                    severity="HIGH",
                    merchant_id=mandate.merchant_id,
                    title="Mandate Retry Sequence Stopped",
                    message=f"Mandate {mandate.mandate_number} stopped: {decision_reason}",
                    metadata_json={"mandate_id": mandate.id, "status": mandate.status}
                )
            except Exception as e:
                logger.warning(f"Notification error for mandate {mandate.id}: {e}")

            await db.commit()
            logger.warning(f"Mandate '{mandate.mandate_number}' blocked by policy: {decision_reason}")
            return mandate, case

        # Policy Gate Approved -> Schedule next retry
        mandate.status = "RETRYING"
        # Cooldown schedule: 24h for attempt 1, 48h for attempt 2, etc.
        cooldown_hours = 24 * mandate.attempt_count
        mandate.next_retry_date = now + timedelta(hours=cooldown_hours)
        db.add(mandate)

        # Create scheduled attempt record
        idem_key = f"mandate_{mandate.id}_attempt_{mandate.attempt_count}"
        attempt = MandateRetryAttempt(
            mandate_id=mandate.id,
            attempt_number=mandate.attempt_count,
            idempotency_key=idem_key,
            status="PENDING",
            failure_reason=failure_reason,
            policy_decision="SCHEDULED",
            attempted_at=now,
            next_retry_at=mandate.next_retry_date
        )
        db.add(attempt)

        # Create or update RecoveryCase
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.mandate_id == mandate.id))
        case = case_res.scalar_one_or_none()

        if not case:
            risk_assessment = risk_engine.assess_transaction(
                amount=float(mandate.amount),
                error_code="MANDATE_DEBIT_FAILED",
                error_description=f"Mandate attempt #{mandate.attempt_count} failed: {failure_reason}"
            )
            case = RecoveryCase(
                case_type="MANDATE_RETRY",
                merchant_id=mandate.merchant_id,
                mandate_id=mandate.id,
                customer_id=mandate.customer_id,
                amount=float(mandate.amount),
                risk_score=risk_assessment.risk_score,
                risk_level=risk_assessment.risk_level,
                priority_score=risk_assessment.priority_score,
                priority_level=risk_assessment.priority_level,
                risk_factors=risk_assessment.risk_factors,
                status="OPEN",
                retry_count=mandate.attempt_count,
                policy_passed=True
            )
            db.add(case)

        # Audit Log
        audit = AuditLog(
            case_id=case.id if case else None,
            actor="MANDATE_SEQUENCER",
            event_type="MANDATE_RETRY_SCHEDULED",
            description=f"Mandate {mandate.mandate_number} retry attempt #{mandate.attempt_count} scheduled.",
            metadata_json={
                "merchant_id": mandate.merchant_id,
                "mandate_id": mandate.id,
                "mandate_number": mandate.mandate_number,
                "attempt_count": mandate.attempt_count,
                "next_retry_date": mandate.next_retry_date.isoformat(),
                "cooldown_hours": cooldown_hours,
                "failure_reason": failure_reason
            }
        )
        db.add(audit)

        # Dispatch notification
        try:
            await notification_service.create_notification(
                db=db,
                type="MANDATE_ALERT",
                severity="INFO",
                merchant_id=mandate.merchant_id,
                title="Mandate Retry Scheduled",
                message=f"Mandate {mandate.mandate_number} attempt #{mandate.attempt_count} scheduled for retry.",
                metadata_json={"mandate_id": mandate.id, "next_retry_date": mandate.next_retry_date.isoformat()}
            )
        except Exception as e:
            logger.warning(f"Notification error for mandate {mandate.id}: {e}")

        await db.commit()
        await db.refresh(mandate)
        if case:
            await db.refresh(case)

        return mandate, case

    async def execute_mandate_retry(
        self,
        db: AsyncSession,
        mandate_id: str,
        idempotency_key: Optional[str] = None,
        simulate_success: bool = True
    ) -> Tuple[Mandate, MandateRetryAttempt, Dict[str, Any]]:
        """
        Executes a scheduled mandate retry via Razorpay Test Mode with idempotency protection.
        """
        res = await db.execute(select(Mandate).where(Mandate.id == mandate_id))
        mandate = res.scalar_one_or_none()
        if not mandate:
            raise ValueError(f"Mandate '{mandate_id}' not found.")

        attempt_num = mandate.attempt_count if mandate.attempt_count > 0 else 1
        idem_key = idempotency_key or f"mandate_{mandate.id}_attempt_{attempt_num}_exec"

        # Idempotency Guard: Check if attempt with this key already completed
        att_res = await db.execute(select(MandateRetryAttempt).where(MandateRetryAttempt.idempotency_key == idem_key))
        existing_attempt = att_res.scalar_one_or_none()
        if existing_attempt and existing_attempt.status in {"SUCCEEDED", "PROCESSING"}:
            logger.info(f"Idempotent request for mandate '{mandate.mandate_number}' key '{idem_key}' returning existing attempt.")
            return mandate, existing_attempt, {"status": "IDEMPOTENT_SKIPPED", "attempt_id": existing_attempt.id}

        # Policy Gate Evaluation
        is_allowed, decision_reason, policy_action = policy_gate.evaluate_mandate_retry_policy(
            attempt_count=mandate.attempt_count,
            max_attempts=mandate.max_attempts,
            mandate_status=mandate.status,
            failure_reason=mandate.failure_reason or "Scheduled Retry"
        )

        now = utc_now()

        if not is_allowed and mandate.status in {"CANCELLED", "ESCALATED", "RECOVERED"}:
            attempt = MandateRetryAttempt(
                mandate_id=mandate.id,
                attempt_number=attempt_num,
                idempotency_key=idem_key,
                status="BLOCKED",
                failure_reason=decision_reason,
                policy_decision=decision_reason,
                attempted_at=now
            )
            db.add(attempt)
            await db.commit()
            return mandate, attempt, {"status": "BLOCKED", "reason": decision_reason}

        # Execute Razorpay Test Mode Debit
        logger.info(f"Executing Razorpay debit for mandate '{mandate.mandate_number}' (Attempt #{attempt_num})...")
        try:
            if simulate_success:
                razorpay_res = razorpay_service.execute_mandate_debit(
                    amount=float(mandate.amount),
                    mandate_number=mandate.mandate_number
                )
                payment_id = razorpay_res.get("id") or f"pay_mnd_{now.strftime('%Y%m%d%H%M%S')}"
            else:
                raise Exception("Simulated provider auto-debit failure")
        except Exception as err:
            logger.error(f"Razorpay mandate debit failed for '{mandate.mandate_number}': {err}")
            attempt = MandateRetryAttempt(
                mandate_id=mandate.id,
                attempt_number=attempt_num,
                idempotency_key=idem_key,
                status="FAILED",
                failure_reason=str(err),
                policy_decision="PROVIDER_FAILED",
                attempted_at=now
            )
            db.add(attempt)
            await db.commit()

            m, c = await self.process_failed_mandate_attempt(
                db=db,
                mandate_id=mandate.id,
                failure_reason=f"Razorpay debit error: {err}"
            )
            return m, attempt, {"status": "FAILED", "error": str(err)}

        # Payment Succeeded -> Update Mandate to RECOVERED
        mandate.status = "RECOVERED"
        mandate.next_retry_date = None
        mandate.last_retry_at = now
        db.add(mandate)

        attempt = MandateRetryAttempt(
            mandate_id=mandate.id,
            attempt_number=attempt_num,
            idempotency_key=idem_key,
            status="SUCCEEDED",
            provider_payment_id=payment_id,
            policy_decision="APPROVED_AND_EXECUTED",
            attempted_at=now
        )
        db.add(attempt)

        # Update RecoveryCase to RECOVERED if present
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.mandate_id == mandate.id))
        case = case_res.scalar_one_or_none()
        if case:
            case.status = "RECOVERED"
            db.add(case)

        # Audit Log
        audit = AuditLog(
            case_id=case.id if case else None,
            actor="RAZORPAY_RETRY_EXECUTOR",
            event_type="MANDATE_RETRY_SUCCEEDED",
            description=f"Mandate {mandate.mandate_number} retry succeeded via Razorpay.",
            metadata_json={
                "merchant_id": mandate.merchant_id,
                "mandate_id": mandate.id,
                "mandate_number": mandate.mandate_number,
                "amount": float(mandate.amount),
                "attempt_number": attempt_num,
                "provider_payment_id": payment_id,
                "idempotency_key": idem_key
            }
        )
        db.add(audit)

        # Notification
        try:
            await notification_service.create_notification(
                db=db,
                type="PAYMENT_RECOVERED",
                severity="INFO",
                merchant_id=mandate.merchant_id,
                title="Mandate Payment Recovered",
                message=f"Mandate {mandate.mandate_number} successfully recovered via Razorpay (₹{mandate.amount:,.2f}).",
                metadata_json={"mandate_id": mandate.id, "payment_id": payment_id}
            )
        except Exception as e:
            logger.warning(f"Notification error for mandate {mandate.id}: {e}")

        await db.commit()
        await db.refresh(mandate)
        await db.refresh(attempt)
        return mandate, attempt, {"status": "SUCCEEDED", "payment_id": payment_id}

    async def escalate_mandate(
        self,
        db: AsyncSession,
        mandate_id: str,
        reason: str = "Manual merchant escalation requested"
    ) -> Mandate:
        """Escalates mandate to human review and halts further automatic retries."""
        res = await db.execute(select(Mandate).where(Mandate.id == mandate_id))
        mandate = res.scalar_one_or_none()
        if not mandate:
            raise ValueError(f"Mandate '{mandate_id}' not found.")

        mandate.status = "ESCALATED"
        mandate.escalation_reason = reason
        mandate.next_retry_date = None
        db.add(mandate)

        # Update case if present
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.mandate_id == mandate.id))
        case = case_res.scalar_one_or_none()
        if case:
            case.status = "ESCALATED"
            case.policy_failure_reason = reason
            db.add(case)

        # Audit Log
        audit = AuditLog(
            case_id=case.id if case else None,
            actor="MERCHANT_USER",
            event_type="MANDATE_RETRY_ESCALATED",
            description=f"Mandate {mandate.mandate_number} escalated for merchant review.",
            metadata_json={
                "merchant_id": mandate.merchant_id,
                "mandate_id": mandate.id,
                "mandate_number": mandate.mandate_number,
                "reason": reason,
                "attempt_count": mandate.attempt_count
            }
        )
        db.add(audit)

        await db.commit()
        await db.refresh(mandate)
        return mandate

    async def reset_mandate_escalation(
        self,
        db: AsyncSession,
        mandate_id: str
    ) -> Mandate:
        """Resets mandate escalation for authorized workflow."""
        res = await db.execute(select(Mandate).where(Mandate.id == mandate_id))
        mandate = res.scalar_one_or_none()
        if not mandate:
            raise ValueError(f"Mandate '{mandate_id}' not found.")

        mandate.status = "ACTIVE"
        mandate.attempt_count = 0
        mandate.escalation_reason = None
        mandate.next_retry_date = None
        db.add(mandate)

        # Audit Log
        audit = AuditLog(
            case_id=None,
            actor="MERCHANT_USER",
            event_type="MANDATE_ESCALATION_RESET",
            description=f"Mandate {mandate.mandate_number} escalation reset.",
            metadata_json={
                "merchant_id": mandate.merchant_id,
                "mandate_id": mandate.id,
                "mandate_number": mandate.mandate_number
            }
        )
        db.add(audit)

        await db.commit()
        await db.refresh(mandate)
        return mandate

mandate_retry_sequencer_service = MandateRetrySequencerService()
