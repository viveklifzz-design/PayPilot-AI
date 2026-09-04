import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.evaluation_run import EvaluationRun
from app.services.evaluation.dataset import dataset_generator
from app.services.evaluation.metrics import metrics_calculator, MetricSummary
from app.services.revenue_risk import risk_engine
from app.services.policy import policy_engine
from app.services.ai import fallback_ai_service
from app.core.logging import logger

@dataclass
class EvaluationRunResult:
    run_id: str
    run_name: str
    seed: int
    dataset_size: int
    mode: str
    metrics: MetricSummary
    cases: List[Dict[str, Any]]
    created_at: datetime

class EvaluationEngine:
    """
    Main Evaluation Engine for PayPilot AI.
    Runs synthetic failure datasets through Risk Engine -> AI Diagnosis -> Policy Gate -> Outcome Simulation.
    Guarantees 100% seed-reproducible evaluation metrics.
    """

    async def run_evaluation(
        self,
        db: AsyncSession,
        dataset_size: int = 1000,
        seed: int = 42,
        mode: str = "deterministic",
        run_name: Optional[str] = None
    ) -> EvaluationRunResult:
        logger.info(f"Starting Evaluation Engine Run: dataset_size={dataset_size}, seed={seed}, mode={mode}...")
        
        # 1. Generate Synthetic Dataset
        synthetic_cases = dataset_generator.generate_dataset(dataset_size=dataset_size, seed=seed)
        
        # Random number generator for outcome simulation
        rng = random.Random(seed + 1000)

        evaluated_cases: List[Dict[str, Any]] = []

        for c in synthetic_cases:
            amount = c["amount"]
            failure_reason = c["failure_reason"]
            payment_method = c["payment_method"]
            prev_succ = c["previous_success_count"]
            prev_fail = c["previous_failure_count"]
            retry_count = c["retry_count"]

            # Step A: Risk Assessment
            risk_res = risk_engine.assess_transaction(
                amount=amount,
                error_code=failure_reason,
                customer_successful_payments=prev_succ,
                customer_failed_payments=prev_fail,
                retry_count=retry_count,
                payment_method=payment_method
            )

            # Step B: AI Diagnosis (fallback / deterministic adapter)
            ctx = {
                "amount": amount,
                "currency": "INR",
                "payment_method": payment_method,
                "error_code": failure_reason,
                "customer_successful_payments": prev_succ,
                "customer_failed_payments": prev_fail,
                "risk_level": risk_res.risk_level,
                "risk_score": risk_res.risk_score,
                "recoverability_score": risk_res.recoverability_score,
                "priority_level": risk_res.priority_level,
                "risk_factors": risk_res.risk_factors
            }
            ai_diag = fallback_ai_service.diagnose_payment_failure(ctx)

            # Step C: Policy Gate Validation
            pol_res = policy_engine.evaluate_action(
                proposed_action=ai_diag.recommended_action,
                case_status="OPEN",
                amount=amount,
                retry_count=retry_count,
                ai_confidence=ai_diag.confidence,
                error_code=failure_reason
            )

            eff_act = pol_res.effective_action
            final_status = "OPEN"
            rec_amt = 0.0
            simulation_notes = ""

            if pol_res.allowed:
                if eff_act in ["RECOVERY_LINK", "RETRY", "REMINDER"]:
                    # Simulated Recovery Outcome using Ground Truth Recovery Probability
                    prob_success = c["ground_truth_recovery_probability"]
                    if rng.random() <= prob_success:
                        final_status = "RECOVERED"
                        rec_amt = amount
                        simulation_notes = f"Simulated recovery SUCCEEDED via {eff_act}"
                    else:
                        final_status = "FAILED"
                        simulation_notes = f"Simulated recovery FAILED via {eff_act}"
                elif eff_act == "ESCALATE":
                    final_status = "ESCALATED"
                    simulation_notes = "Policy allowed action, but effective action was ESCALATE"
                elif eff_act == "STOP":
                    final_status = "STOPPED"
                    simulation_notes = "Policy allowed action, but effective action was STOP"
            else:
                if eff_act == "ESCALATE":
                    final_status = "ESCALATED"
                    simulation_notes = f"Policy BLOCKED action ({', '.join(pol_res.violations)}). Overridden to ESCALATE"
                elif eff_act == "STOP":
                    final_status = "STOPPED"
                    simulation_notes = f"Policy BLOCKED action ({', '.join(pol_res.violations)}). Overridden to STOP"
                else:
                    final_status = "BLOCKED"
                    simulation_notes = f"Policy BLOCKED action: {', '.join(pol_res.violations)}"

            case_eval = {
                **c,
                "risk_level": risk_res.risk_level,
                "risk_score": risk_res.risk_score,
                "recoverability_score": risk_res.recoverability_score,
                "ai_root_cause": ai_diag.root_cause,
                "ai_recommended_action": ai_diag.recommended_action,
                "ai_confidence": ai_diag.confidence,
                "policy_allowed": pol_res.allowed,
                "effective_action": eff_act,
                "policy_violations": pol_res.violations,
                "final_status": final_status,
                "recovered_amount": rec_amt,
                "simulation_notes": simulation_notes
            }

            evaluated_cases.append(case_eval)

        # 2. Compute Evaluation Metrics
        summary = metrics_calculator.calculate_metrics(evaluated_cases)

        run_name_str = run_name or f"Evaluation Benchmark (Size: {dataset_size}, Seed: {seed})"

        # JSON audit dump
        metrics_dump = {
            "dataset_size": dataset_size,
            "seed": seed,
            "mode": mode,
            "summary": summary.__dict__,
            "cases_summary": evaluated_cases
        }

        # 3. Persist into EvaluationRun DB Model
        eval_run = EvaluationRun(
            run_name=run_name_str,
            seed=seed,
            batch_size=dataset_size,
            mode=mode,
            total_cases=summary.total_cases,
            revenue_at_risk=summary.total_revenue_at_risk,
            recoverable_revenue=summary.recoverable_revenue,
            total_recovered=summary.revenue_recovered,
            diagnosed_count=summary.total_cases,
            policy_allowed_count=summary.predicted_recoverable_cases,
            policy_blocked_count=summary.unsafe_action_count,
            escalated_count=summary.escalation_count,
            recovery_attempt_count=summary.intervention_count,
            recovered_count=summary.successful_recovery_count,
            failed_recovery_count=summary.intervention_count - summary.successful_recovery_count,
            stopped_count=summary.safe_stop_count,
            remaining_revenue_at_risk=summary.total_revenue_at_risk - summary.revenue_recovered,
            recovery_rate=summary.recovery_rate,
            recovery_success_rate=summary.recovery_rate,
            precision_rate=summary.precision,
            false_intervention_rate=round(100.0 - summary.precision, 2) if summary.precision > 0 else 0.0,
            escalation_rate=summary.escalation_rate,
            safe_stop_rate=summary.safe_stop_rate,
            metrics=metrics_dump,
            completed_at=datetime.now(timezone.utc)
        )
        db.add(eval_run)
        await db.commit()
        await db.refresh(eval_run)

        logger.info(
            f"Evaluation Engine Run Complete (ID: {eval_run.id}): "
            f"Cases={summary.total_cases}, Risk=INR {summary.total_revenue_at_risk}, Recovered=INR {summary.revenue_recovered} ({summary.recovery_rate}%), "
            f"Precision={summary.precision}%, Recall={summary.recall}%, UnsafeActions={summary.unsafe_action_count}"
        )

        return EvaluationRunResult(
            run_id=eval_run.id,
            run_name=run_name_str,
            seed=seed,
            dataset_size=dataset_size,
            mode=mode,
            metrics=summary,
            cases=evaluated_cases,
            created_at=eval_run.created_at
        )

evaluation_engine = EvaluationEngine()
