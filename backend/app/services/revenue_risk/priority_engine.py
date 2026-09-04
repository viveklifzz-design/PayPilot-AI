from dataclasses import dataclass
from typing import List, Literal, Optional

@dataclass
class PriorityResult:
    priority_score: float
    priority_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    priority_factors: List[str]

class PriorityEngine:
    """
    Deterministic Priority Engine for PayPilot AI.
    Calculates priority score (0-100) and human-readable priority factors.
    Contains NO LLM calls; purely rules-driven, deterministic, and explainable.
    """

    def calculate_priority(
        self,
        amount: float,
        recoverability_score: float = 0.5,
        customer_successful_payments: int = 0,
        retry_count: int = 0,
        case_type: str = "PAYMENT_FAILURE",
        failure_category: Optional[str] = None,
        age_hours: float = 0.0
    ) -> PriorityResult:
        factors: List[str] = []

        # 1. Amount Component (Max 40 points)
        amount_score = min(40.0, (amount / 50000.0) * 40.0)
        if amount >= 25000.0:
            factors.append(f"High transaction value (₹{amount:,.2f})")
        elif amount >= 5000.0:
            factors.append(f"Moderate transaction value (₹{amount:,.2f})")
        else:
            factors.append(f"Standard transaction value (₹{amount:,.2f})")

        # 2. Recoverability Component (Max 30 points)
        rec_score = recoverability_score * 30.0
        if recoverability_score >= 0.75:
            factors.append(f"High recovery probability ({int(recoverability_score * 100)}%)")
        elif recoverability_score >= 0.40:
            factors.append(f"Moderate recovery probability ({int(recoverability_score * 100)}%)")
        else:
            factors.append(f"Low recovery probability ({int(recoverability_score * 100)}%)")

        # 3. Customer History Component (Max 20 points)
        cust_score = min(20.0, (customer_successful_payments / 10.0) * 20.0)
        if customer_successful_payments >= 5:
            factors.append(f"High-value loyal customer ({customer_successful_payments} past successful payments)")
        elif customer_successful_payments >= 1:
            factors.append(f"Returning customer ({customer_successful_payments} past successful payment)")

        # 4. Case Type & Urgency Adjustments (Max 10 points)
        type_bonus = 0.0
        if case_type == "SUBSCRIPTION_FAILURE":
            type_bonus = 10.0
            factors.append("Recurring subscription payment - immediate churn risk")
        elif case_type == "CHECKOUT_DROPOFF":
            type_bonus = 5.0
            factors.append("Active checkout abandonment - high intent window")

        # 5. Retry Count Penalty (-5 points per retry)
        retry_penalty = min(20.0, retry_count * 5.0)
        if retry_count > 0:
            factors.append(f"{retry_count} previous recovery retries attempted")

        # Final Priority Score Calculation (Bounded 0.0 to 100.0)
        raw_priority = amount_score + rec_score + cust_score + type_bonus - retry_penalty
        priority_score = round(max(0.0, min(100.0, raw_priority)), 2)

        # Priority Level Mapping
        if priority_score >= 75.0:
            priority_level = "CRITICAL"
        elif priority_score >= 55.0:
            priority_level = "HIGH"
        elif priority_score >= 30.0:
            priority_level = "MEDIUM"
        else:
            priority_level = "LOW"

        return PriorityResult(
            priority_score=priority_score,
            priority_level=priority_level,
            priority_factors=factors
        )

priority_engine = PriorityEngine()
