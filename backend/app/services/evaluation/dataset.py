import random
from typing import List, Dict, Any
from app.services.evaluation.ground_truth import ground_truth_policy

class SyntheticDatasetGenerator:
    """
    Deterministic Synthetic Dataset Generator for PayPilot AI Evaluation Engine.
    Generates N synthetic payment failure cases using a fixed random seed.
    """

    SAMPLE_AMOUNTS = [499.0, 999.0, 1499.0, 2499.0, 4999.0, 7500.0, 12500.0, 24999.0, 49999.0, 75000.0]
    SAMPLE_METHODS = ["upi", "card", "netbanking"]
    SAMPLE_FAILURES = [
        "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "INSUFFICIENT_FUNDS",
        "BAD_REQUEST_PAYMENT_DECLINED",
        "OTP_TIMEOUT",
        "EXPIRED_CARD",
        "GATEWAY_ERROR",
        "REPEATED_FAILURE",
        "SUSPECTED_FRAUD",
        "CUSTOMER_ABANDONMENT"
    ]
    FAILURE_WEIGHTS = [0.25, 0.20, 0.15, 0.12, 0.10, 0.08, 0.04, 0.03, 0.03]
    CUSTOMER_TYPES = ["NEW", "RETURNING", "VIP", "RISKY"]

    def generate_dataset(self, dataset_size: int = 1000, seed: int = 42) -> List[Dict[str, Any]]:
        rng = random.Random(seed)
        dataset: List[Dict[str, Any]] = []

        for i in range(1, dataset_size + 1):
            case_id = f"eval_case_{seed}_{i:04d}"
            payment_id = f"pay_synth_{seed}_{i:04d}"
            customer_id = f"cust_synth_{seed}_{(i % 150) + 1:04d}"

            amount = rng.choice(self.SAMPLE_AMOUNTS)
            currency = "INR"
            payment_method = rng.choice(self.SAMPLE_METHODS)
            failure_reason = rng.choices(self.SAMPLE_FAILURES, weights=self.FAILURE_WEIGHTS, k=1)[0]
            customer_type = rng.choice(self.CUSTOMER_TYPES)

            if customer_type == "VIP":
                prev_succ = rng.randint(5, 20)
                prev_fail = rng.randint(0, 1)
            elif customer_type == "RETURNING":
                prev_succ = rng.randint(1, 4)
                prev_fail = rng.randint(0, 2)
            elif customer_type == "RISKY":
                prev_succ = rng.randint(0, 1)
                prev_fail = rng.randint(3, 6)
            else:  # NEW
                prev_succ = 0
                prev_fail = rng.randint(0, 1)

            retry_count = 3 if failure_reason == "REPEATED_FAILURE" else rng.choice([0, 0, 0, 1, 1, 2])
            time_since_failure = rng.randint(2, 240)
            customer_value = round(prev_succ * amount, 2)

            if failure_reason == "CUSTOMER_ABANDONMENT":
                case_type = "CHECKOUT_DROPOFF"
            elif failure_reason in ["EXPIRED_CARD", "REPEATED_FAILURE"] and (i % 4 == 0):
                case_type = "SUBSCRIPTION_FAILURE"
            else:
                case_type = rng.choices(["PAYMENT_FAILURE", "CHECKOUT_DROPOFF", "SUBSCRIPTION_FAILURE"], weights=[0.65, 0.20, 0.15], k=1)[0]

            case_data = {
                "case_id": case_id,
                "case_type": case_type,
                "payment_id": payment_id,
                "customer_id": customer_id,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
                "failure_reason": failure_reason,
                "customer_type": customer_type,
                "previous_success_count": prev_succ,
                "previous_failure_count": prev_fail,
                "retry_count": retry_count,
                "time_since_failure_minutes": time_since_failure,
                "customer_value": customer_value
            }

            category, ground_truth_action, prob = ground_truth_policy.evaluate_ground_truth(case_data)
            case_data["ground_truth_category"] = category
            case_data["ground_truth_action"] = ground_truth_action
            case_data["ground_truth_recovery_probability"] = prob
            case_data["expected_recoverable"] = (category == "RECOVERABLE")

            dataset.append(case_data)

        return dataset

dataset_generator = SyntheticDatasetGenerator()
