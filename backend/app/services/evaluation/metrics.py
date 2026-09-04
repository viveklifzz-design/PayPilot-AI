from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class MetricSummary:
    total_cases: int = 0
    total_revenue_at_risk: float = 0.0
    recoverable_cases: int = 0
    recoverable_revenue: float = 0.0
    predicted_recoverable_cases: int = 0
    correct_recoverable_predictions: int = 0
    false_positive_cases: int = 0
    false_negative_cases: int = 0
    precision: float = 0.0
    recall: float = 0.0
    intervention_count: int = 0
    successful_recovery_count: int = 0
    recovery_rate: float = 0.0
    intervention_rate: float = 0.0
    safe_stop_count: int = 0
    safe_stop_rate: float = 0.0
    escalation_count: int = 0
    escalation_rate: float = 0.0
    unsafe_action_count: int = 0
    revenue_recovered: float = 0.0
    recovery_revenue_rate: float = 0.0
    average_recovery_amount: float = 0.0

class EvaluationMetricsCalculator:
    """
    Mathematical definitions & zero-division-safe calculations for PayPilot AI Evaluation Engine.
    """

    @staticmethod
    def calculate_metrics(evaluated_cases: List[Dict[str, Any]]) -> MetricSummary:
        total_cases = len(evaluated_cases)
        if total_cases == 0:
            return MetricSummary()

        total_revenue_at_risk = 0.0
        recoverable_cases = 0
        recoverable_revenue = 0.0
        predicted_recoverable_cases = 0
        correct_recoverable_predictions = 0
        false_positive_cases = 0
        false_negative_cases = 0

        intervention_count = 0
        successful_recovery_count = 0
        safe_stop_count = 0
        total_stop_decisions = 0
        escalation_count = 0
        unsafe_action_count = 0
        revenue_recovered = 0.0

        for c in evaluated_cases:
            amt = float(c.get("amount", 0.0))
            total_revenue_at_risk += amt

            ground_recoverable = c.get("expected_recoverable", False)
            if ground_recoverable:
                recoverable_cases += 1
                recoverable_revenue += amt

            eff_act = c.get("effective_action", "STOP")
            policy_allowed = c.get("policy_allowed", True)
            final_status = c.get("final_status", "OPEN")
            rec_amt = float(c.get("recovered_amount", 0.0))

            is_intervention = eff_act in ["RETRY", "RECOVERY_LINK", "REMINDER"]

            if is_intervention:
                intervention_count += 1
                predicted_recoverable_cases += 1
                if ground_recoverable:
                    correct_recoverable_predictions += 1
                else:
                    false_positive_cases += 1
                
                # If an intervention was executed despite policy disallowing it, count as unsafe action
                if not policy_allowed:
                    unsafe_action_count += 1
            else:
                if ground_recoverable:
                    false_negative_cases += 1

            if eff_act == "STOP":
                total_stop_decisions += 1
                if not ground_recoverable or c.get("ground_truth_action") == "STOP":
                    safe_stop_count += 1

            if eff_act == "ESCALATE":
                escalation_count += 1

            if final_status == "RECOVERED":
                successful_recovery_count += 1
                revenue_recovered += rec_amt

        precision = (correct_recoverable_predictions / predicted_recoverable_cases * 100.0) if predicted_recoverable_cases > 0 else 0.0
        recall = (correct_recoverable_predictions / recoverable_cases * 100.0) if recoverable_cases > 0 else 0.0
        recovery_rate = (successful_recovery_count / recoverable_cases * 100.0) if recoverable_cases > 0 else 0.0
        intervention_rate = (intervention_count / total_cases * 100.0) if total_cases > 0 else 0.0
        safe_stop_rate = (safe_stop_count / total_stop_decisions * 100.0) if total_stop_decisions > 0 else 100.0
        escalation_rate = (escalation_count / total_cases * 100.0) if total_cases > 0 else 0.0
        recovery_revenue_rate = (revenue_recovered / recoverable_revenue * 100.0) if recoverable_revenue > 0 else 0.0
        avg_rec_amt = (revenue_recovered / successful_recovery_count) if successful_recovery_count > 0 else 0.0

        return MetricSummary(
            total_cases=total_cases,
            total_revenue_at_risk=round(total_revenue_at_risk, 2),
            recoverable_cases=recoverable_cases,
            recoverable_revenue=round(recoverable_revenue, 2),
            predicted_recoverable_cases=predicted_recoverable_cases,
            correct_recoverable_predictions=correct_recoverable_predictions,
            false_positive_cases=false_positive_cases,
            false_negative_cases=false_negative_cases,
            precision=round(precision, 2),
            recall=round(recall, 2),
            intervention_count=intervention_count,
            successful_recovery_count=successful_recovery_count,
            recovery_rate=round(recovery_rate, 2),
            intervention_rate=round(intervention_rate, 2),
            safe_stop_count=safe_stop_count,
            safe_stop_rate=round(safe_stop_rate, 2),
            escalation_count=escalation_count,
            escalation_rate=round(escalation_rate, 2),
            unsafe_action_count=unsafe_action_count,
            revenue_recovered=round(revenue_recovered, 2),
            recovery_revenue_rate=round(recovery_revenue_rate, 2),
            average_recovery_amount=round(avg_rec_amt, 2)
        )

metrics_calculator = EvaluationMetricsCalculator()
