from typing import Dict, Any, Tuple

class GroundTruthPolicy:
    """
    Deterministic Ground-Truth Policy Rules for PayPilot AI Evaluation Engine.
    Defines ideal recovery expectations, ground-truth actions, and recovery probabilities based on objective scenario rules.
    """

    @staticmethod
    def evaluate_ground_truth(case_data: Dict[str, Any]) -> Tuple[str, str, float]:
        """
        Evaluates synthetic case data against ground-truth rules.
        Returns: (category, ground_truth_action, recovery_probability)
        - category: 'RECOVERED_EXPECTED', 'NON_RECOVERABLE', 'REQUIRES_HUMAN_REVIEW'
        - ground_truth_action: 'RETRY', 'RECOVERY_LINK', 'REMINDER', 'ESCALATE', 'STOP'
        - recovery_probability: float between 0.0 and 1.0
        """
        failure_reason = case_data.get("failure_reason", "")
        amount = case_data.get("amount", 0.0)
        retry_count = case_data.get("retry_count", 0)
        prev_succ = case_data.get("previous_success_count", 0)
        prev_fail = case_data.get("previous_failure_count", 0)

        # Rule 1: High Risk / Fraud -> Human Review / Escalate
        if failure_reason == "SUSPECTED_FRAUD" or amount > 50000.0:
            return "REQUIRES_HUMAN_REVIEW", "ESCALATE", 0.10

        # Rule 2: Exceeded Retry Limits -> Non-recoverable Stop
        if retry_count >= 3 or prev_fail >= 5:
            return "NON_RECOVERABLE", "STOP", 0.05

        # Rule 3: Temporary Bank/Network Timeout with Loyal Customer -> High Recoverability Retry
        if failure_reason in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR"]:
            prob = 0.85 if prev_succ > 2 else 0.70
            return "RECOVERABLE", "RETRY", prob

        # Rule 4: Expired Card or Auth Failure -> Recovery Link (customer update needed)
        if failure_reason in ["EXPIRED_CARD", "OTP_TIMEOUT", "AUTHENTICATION_FAILED"]:
            prob = 0.80 if prev_succ > 0 else 0.65
            return "RECOVERABLE", "RECOVERY_LINK", prob

        # Rule 5: Insufficient Funds -> Payment Link / Reminder (delayed retry)
        if failure_reason == "INSUFFICIENT_FUNDS":
            prob = 0.60 if prev_succ > 1 else 0.40
            return "RECOVERABLE", "REMINDER", prob

        # Rule 6: Card Declined without customer history -> Low Recoverability / Stop
        if failure_reason == "BAD_REQUEST_PAYMENT_DECLINED" and prev_succ == 0:
            return "NON_RECOVERABLE", "STOP", 0.15

        # Rule 7: Default fallback for general failures
        if prev_succ > 0:
            return "RECOVERABLE", "RECOVERY_LINK", 0.60
        else:
            return "NON_RECOVERABLE", "STOP", 0.20

ground_truth_policy = GroundTruthPolicy()
