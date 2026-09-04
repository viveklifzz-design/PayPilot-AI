import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.evaluation_run import EvaluationRun
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.audit_log import AuditLog
from app.services.revenue_risk import risk_engine
from app.services.ai import get_ai_service, fallback_ai_service
from app.services.policy import policy_engine
from app.core.logging import logger

@dataclass
class CaseEvaluationDetail:
    case_num: int
    amount: float
    error_code: str
    risk_level: str
    risk_score: float
    recoverability_score: float
    ai_root_cause: str
    ai_recommended_action: str
    ai_confidence: float
    policy_allowed: bool
    effective_action: str
    policy_violations: List[str]
    final_status: str
    recovered_amount: float
    simulation_notes: str

@dataclass
class BatchEvaluationResult:
    run_id: str
    run_name: str
    seed: int
    batch_size: int
    mode: str
    total_failed_amount: float
    total_recovered: float
    remaining_revenue_at_risk: float
    diagnosed_count: int
    policy_allowed_count: int
    policy_blocked_count: int
    escalated_count: int
    recovery_attempt_count: int
    recovered_count: int
    failed_recovery_count: int
    stopped_count: int
    recovery_rate: float
    recovery_success_rate: float
    precision_rate: float
    false_intervention_rate: float
    escalation_rate: float
    safe_stop_rate: float
    cases: List[CaseEvaluationDetail] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class BatchEvaluatorService:
    """
    Deterministic Batch Evaluation Engine for PayPilot AI.
    Runs N synthetic payment failure cases through the complete PayPilot AI pipeline:
    Risk Engine -> AI Diagnosis -> Policy Safety Gate -> Recovery Outcome Simulation.
    Guarantees 100% seed-reproducible metric calculations.
    """

    SAMPLE_AMOUNTS = [500.0, 1200.0, 2500.0, 3500.0, 7500.0, 15000.0, 35000.0, 60000.0, 85000.0]
    SAMPLE_ERRORS = [
        "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "GATEWAY_ERROR",
        "INSUFFICIENT_FUNDS",
        "OTP_TIMEOUT",
        "EXPIRED_CARD",
        "SUSPECTED_FRAUD",
        "BAD_REQUEST_PAYMENT_DECLINED"
    ]
    SAMPLE_METHODS = ["upi", "card", "netbanking"]

    async def run_batch_evaluation(
        self,
        db: AsyncSession,
        batch_size: int = 100,
        seed: int = 42,
        run_name: Optional[str] = None
    ) -> BatchEvaluationResult:
        logger.info(f"Starting Batch Evaluation Run: batch_size={batch_size}, seed={seed}...")
        rng = random.Random(seed)

        # 1. Fetch or create Default Evaluation Merchant
        res = await db.execute(select(Merchant))
        merchant = res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Evaluation Merchant", email="eval@merchant.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        ai_service = fallback_ai_service

        case_details: List[CaseEvaluationDetail] = []
        total_failed_amount = 0.0
        diagnosed_count = 0
        policy_allowed_count = 0
        policy_blocked_count = 0
        escalated_count = 0
        recovery_attempt_count = 0
        recovered_count = 0
        failed_recovery_count = 0
        stopped_count = 0
        total_recovered = 0.0

        for i in range(1, batch_size + 1):
            amount = rng.choice(self.SAMPLE_AMOUNTS)
            error_code = rng.choice(self.SAMPLE_ERRORS)
            method = rng.choice(self.SAMPLE_METHODS)
            succ_payments = rng.choice([0, 1, 3, 7, 12])
            fail_payments = rng.choice([0, 1, 2, 4])
            retry_count = rng.choice([0, 0, 0, 1, 2, 3])  # Includes MAX_RETRIES cases

            total_failed_amount += amount

            # Step A: Revenue Risk Engine Assessment
            risk_res = risk_engine.assess_transaction(
                amount=amount,
                error_code=error_code,
                customer_successful_payments=succ_payments,
                customer_failed_payments=fail_payments,
                retry_count=retry_count,
                payment_method=method
            )

            # Step B: AI Diagnosis
            ctx = {
                "amount": amount,
                "currency": "INR",
                "payment_method": method,
                "error_code": error_code,
                "customer_successful_payments": succ_payments,
                "customer_failed_payments": fail_payments,
                "risk_level": risk_res.risk_level,
                "risk_score": risk_res.risk_score,
                "recoverability_score": risk_res.recoverability_score,
                "priority_level": risk_res.priority_level,
                "risk_factors": risk_res.risk_factors
            }
            ai_diag = ai_service.diagnose_payment_failure(ctx)
            diagnosed_count += 1

            # Step C: Policy Gate Evaluation
            pol_res = policy_engine.evaluate_action(
                proposed_action=ai_diag.recommended_action,
                case_status="OPEN",
                amount=amount,
                retry_count=retry_count,
                ai_confidence=ai_diag.confidence,
                error_code=error_code
            )

            final_status = "OPEN"
            rec_amt = 0.0
            notes = ""

            if pol_res.allowed:
                policy_allowed_count += 1
                eff_act = pol_res.effective_action

                if eff_act in {"RECOVERY_LINK", "RETRY", "REMINDER"}:
                    recovery_attempt_count += 1
                    
                    # Deterministic Outcome Simulation
                    prob_success = risk_res.recoverability_score
                    if eff_act == "RECOVERY_LINK" and succ_payments > 0:
                        prob_success += 0.10
                    elif eff_act == "RETRY" and error_code == "BAD_REQUEST_PAYMENT_TIMED_OUT":
                        prob_success += 0.15
                    prob_success = max(0.05, min(0.95, prob_success))

                    if rng.random() <= prob_success:
                        final_status = "RECOVERED"
                        rec_amt = amount
                        recovered_count += 1
                        total_recovered += rec_amt
                        notes = f"Simulated recovery SUCCEEDED via {eff_act}"
                    else:
                        final_status = "FAILED"
                        failed_recovery_count += 1
                        notes = f"Simulated recovery FAILED via {eff_act}"
                elif eff_act == "ESCALATE":
                    final_status = "ESCALATED"
                    escalated_count += 1
                    notes = "Policy allowed action, but effective action was ESCALATE"
                elif eff_act == "STOP":
                    final_status = "STOPPED"
                    stopped_count += 1
                    notes = "Policy allowed action, but effective action was STOP"
            else:
                policy_blocked_count += 1
                eff_act = pol_res.effective_action
                if eff_act == "ESCALATE":
                    final_status = "ESCALATED"
                    escalated_count += 1
                    notes = f"Policy BLOCKED action ({', '.join(pol_res.violations)}). Overridden to ESCALATE"
                elif eff_act == "STOP":
                    final_status = "STOPPED"
                    stopped_count += 1
                    notes = f"Policy BLOCKED action ({', '.join(pol_res.violations)}). Overridden to STOP"
                else:
                    final_status = "BLOCKED"
                    notes = f"Policy BLOCKED action: {', '.join(pol_res.violations)}"

            case_details.append(CaseEvaluationDetail(
                case_num=i,
                amount=amount,
                error_code=error_code,
                risk_level=risk_res.risk_level,
                risk_score=risk_res.risk_score,
                recoverability_score=risk_res.recoverability_score,
                ai_root_cause=ai_diag.root_cause,
                ai_recommended_action=ai_diag.recommended_action,
                ai_confidence=ai_diag.confidence,
                policy_allowed=pol_res.allowed,
                effective_action=eff_act,
                policy_violations=pol_res.violations,
                final_status=final_status,
                recovered_amount=rec_amt,
                simulation_notes=notes
            ))

        # Metrics Calculations (Handling zero division safely)
        remaining_risk = round(total_failed_amount - total_recovered, 2)
        recovery_rate = round((total_recovered / total_failed_amount * 100.0), 2) if total_failed_amount > 0 else 0.0
        recovery_success_rate = round((recovered_count / recovery_attempt_count * 100.0), 2) if recovery_attempt_count > 0 else 0.0
        precision_rate = round((policy_allowed_count / batch_size * 100.0), 2) if batch_size > 0 else 0.0
        false_intervention_rate = round((policy_blocked_count / batch_size * 100.0), 2) if batch_size > 0 else 0.0
        escalation_rate = round((escalated_count / batch_size * 100.0), 2) if batch_size > 0 else 0.0
        safe_stop_rate = round((stopped_count / batch_size * 100.0), 2) if batch_size > 0 else 0.0

        run_name_str = run_name or f"Batch Eval (Size: {batch_size}, Seed: {seed})"

        # JSON metrics audit payload
        json_metrics = {
            "batch_size": batch_size,
            "seed": seed,
            "mode": "simulation",
            "total_failed_amount": total_failed_amount,
            "total_recovered": total_recovered,
            "remaining_revenue_at_risk": remaining_risk,
            "diagnosed_count": diagnosed_count,
            "policy_allowed_count": policy_allowed_count,
            "policy_blocked_count": policy_blocked_count,
            "escalated_count": escalated_count,
            "recovery_attempt_count": recovery_attempt_count,
            "recovered_count": recovered_count,
            "failed_recovery_count": failed_recovery_count,
            "stopped_count": stopped_count,
            "recovery_rate": recovery_rate,
            "recovery_success_rate": recovery_success_rate,
            "precision_rate": precision_rate,
            "false_intervention_rate": false_intervention_rate,
            "escalation_rate": escalation_rate,
            "safe_stop_rate": safe_stop_rate,
            "cases_summary": [c.__dict__ for c in case_details]
        }

        # Persist EvaluationRun record
        eval_run = EvaluationRun(
            run_name=run_name_str,
            seed=seed,
            batch_size=batch_size,
            mode="simulation",
            total_cases=batch_size,
            revenue_at_risk=total_failed_amount,
            recoverable_revenue=round(total_failed_amount * 0.70, 2),
            total_recovered=total_recovered,
            diagnosed_count=diagnosed_count,
            policy_allowed_count=policy_allowed_count,
            policy_blocked_count=policy_blocked_count,
            escalated_count=escalated_count,
            recovery_attempt_count=recovery_attempt_count,
            recovered_count=recovered_count,
            failed_recovery_count=failed_recovery_count,
            stopped_count=stopped_count,
            remaining_revenue_at_risk=remaining_risk,
            recovery_rate=recovery_rate,
            recovery_success_rate=recovery_success_rate,
            precision_rate=precision_rate,
            false_intervention_rate=false_intervention_rate,
            escalation_rate=escalation_rate,
            safe_stop_rate=safe_stop_rate,
            metrics=json_metrics,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(eval_run)
        await db.commit()
        await db.refresh(eval_run)

        logger.info(
            f"Batch Evaluation Complete (Run ID: {eval_run.id}): "
            f"Risk=INR {total_failed_amount}, Recovered=INR {total_recovered} ({recovery_rate}%), "
            f"Allowed={policy_allowed_count}, Blocked={policy_blocked_count}, Escalated={escalated_count}"
        )

        return BatchEvaluationResult(
            run_id=eval_run.id,
            run_name=run_name_str,
            seed=seed,
            batch_size=batch_size,
            mode="simulation",
            total_failed_amount=total_failed_amount,
            total_recovered=total_recovered,
            remaining_revenue_at_risk=remaining_risk,
            diagnosed_count=diagnosed_count,
            policy_allowed_count=policy_allowed_count,
            policy_blocked_count=policy_blocked_count,
            escalated_count=escalated_count,
            recovery_attempt_count=recovery_attempt_count,
            recovered_count=recovered_count,
            failed_recovery_count=failed_recovery_count,
            stopped_count=stopped_count,
            recovery_rate=recovery_rate,
            recovery_success_rate=recovery_success_rate,
            precision_rate=precision_rate,
            false_intervention_rate=false_intervention_rate,
            escalation_rate=escalation_rate,
            safe_stop_rate=safe_stop_rate,
            cases=case_details
        )

batch_evaluator = BatchEvaluatorService()
