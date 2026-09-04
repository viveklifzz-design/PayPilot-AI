from dataclasses import dataclass
from typing import Optional, List, Literal
from app.core.logging import logger

@dataclass
class RiskAssessmentResult:
    revenue_at_risk: float
    risk_score: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recoverability_score: float
    priority_score: float
    priority_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_factors: List[str]

class RevenueRiskEngine:
    """
    Deterministic Revenue-at-Risk Engine for PayPilot AI.
    Calculates risk score, recoverability, priority score, and risk factors.
    Contains NO LLM calls; purely rules-driven & deterministic.
    """

    HIGH_RECOVERABILITY_CODES = {
        "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "GATEWAY_ERROR",
        "NETWORK_ERROR",
        "BANK_SERVER_DOWN"
    }
    
    MEDIUM_RECOVERABILITY_CODES = {
        "BAD_REQUEST_PAYMENT_CANCELLED",
        "OTP_TIMEOUT",
        "BAD_REQUEST_PAYMENT_DECLINED",
        "INSUFFICIENT_FUNDS"
    }

    LOW_RECOVERABILITY_CODES = {
        "EXPIRED_CARD",
        "INVALID_CARD_DETAILS",
        "INVALID_ACCOUNT"
    }

    FRAUD_SECURITY_CODES = {
        "SUSPECTED_FRAUD",
        "RISK_CHECK_FAILED",
        "BLACKLISTED_CARD"
    }

    def assess_transaction(
        self,
        amount: float,
        error_code: Optional[str] = None,
        error_description: Optional[str] = None,
        customer_successful_payments: int = 0,
        customer_failed_payments: int = 0,
        retry_count: int = 0,
        payment_method: Optional[str] = None,
        previous_recovery_success: bool = False
    ) -> RiskAssessmentResult:
        risk_factors: List[str] = []
        is_fraud = False
        
        # 1. Base Recoverability Score
        err = (error_code or "").upper()
        if err in self.HIGH_RECOVERABILITY_CODES:
            base_recoverability = 0.85
            risk_factors.append(f"Temporary infrastructure/bank outage detected ({err})")
        elif err in self.MEDIUM_RECOVERABILITY_CODES:
            base_recoverability = 0.60
            risk_factors.append(f"Customer authorization or balance issue ({err})")
        elif err in self.LOW_RECOVERABILITY_CODES:
            base_recoverability = 0.20
            risk_factors.append(f"Permanent payment instrument failure ({err})")
        elif err in self.FRAUD_SECURITY_CODES:
            base_recoverability = 0.05
            is_fraud = True
            risk_factors.append(f"Security or suspected fraud alert ({err})")
        else:
            base_recoverability = 0.50
            risk_factors.append(f"Standard/unspecified failure reason ({err or 'UNKNOWN'})")

        # 2. Customer History Adjustments
        history_adj = 0.0
        if customer_successful_payments >= 5:
            history_adj += 0.15
            risk_factors.append(f"High-value loyal customer ({customer_successful_payments} successful payments)")
        elif customer_successful_payments >= 1:
            history_adj += 0.08
            risk_factors.append(f"Returning customer ({customer_successful_payments} past successful payment)")
        elif customer_successful_payments == 0 and customer_failed_payments == 0:
            risk_factors.append("New customer with no prior payment history")

        if customer_failed_payments >= 3:
            history_adj -= 0.15
            risk_factors.append(f"High historical failure rate ({customer_failed_payments} past failures)")

        if previous_recovery_success:
            history_adj += 0.10
            risk_factors.append("Customer previously responded positively to recovery interventions")

        # 3. Retry Count Penalty
        retry_penalty = 0.0
        if retry_count == 1:
            retry_penalty = 0.10
            risk_factors.append("1 previous recovery retry attempt made")
        elif retry_count == 2:
            retry_penalty = 0.25
            risk_factors.append("2 previous recovery retry attempts made")
        elif retry_count >= 3:
            retry_penalty = 0.50
            risk_factors.append(f"Maximum retry attempts reached ({retry_count})")

        # Compute Final Recoverability Score (Bounded 0.0 to 1.0)
        recoverability_score = round(max(0.0, min(1.0, base_recoverability + history_adj - retry_penalty)), 2)

        # 4. Risk Score Calculation (0.0 to 100.0)
        if is_fraud:
            risk_score = 90.0
            risk_level = "CRITICAL"
        else:
            amount_exposure = min(1.0, amount / 100000.0)
            raw_risk_score = ((1.0 - recoverability_score) * 70.0) + (amount_exposure * 30.0)
            risk_score = round(max(0.0, min(100.0, raw_risk_score)), 2)

            # 5. Risk Level Mapping
            if risk_score < 25.0:
                risk_level = "LOW"
            elif risk_score < 50.0:
                risk_level = "MEDIUM"
            elif risk_score < 75.0:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"

        # 6. Revenue at Risk Calculation
        revenue_at_risk = round(amount * (0.5 + 0.5 * recoverability_score), 2)

        # 7. Priority Score & Priority Level Calculation
        amount_score = min(1.0, amount / 50000.0) * 50.0
        rec_score_component = recoverability_score * 30.0
        cust_val_component = min(1.0, customer_successful_payments / 10.0) * 20.0
        priority_score = round(max(0.0, min(100.0, amount_score + rec_score_component + cust_val_component)), 2)

        if priority_score >= 80.0:
            priority_level = "CRITICAL"
        elif priority_score >= 60.0:
            priority_level = "HIGH"
        elif priority_score >= 35.0:
            priority_level = "MEDIUM"
        else:
            priority_level = "LOW"

        logger.debug(
            f"Risk Assessment: amount={amount}, score={risk_score}, level={risk_level}, "
            f"rec={recoverability_score}, priority={priority_score}"
        )

        return RiskAssessmentResult(
            revenue_at_risk=revenue_at_risk,
            risk_score=risk_score,
            risk_level=risk_level,
            recoverability_score=recoverability_score,
            priority_score=priority_score,
            priority_level=priority_level,
            risk_factors=risk_factors
        )

risk_engine = RevenueRiskEngine()
