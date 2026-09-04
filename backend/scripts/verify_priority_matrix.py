import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.revenue_risk.priority_engine import priority_engine

def run_matrix():
    test_cases = [
        {
            "name": "High-Value Subscription Failure (VIP Customer)",
            "amount": 49999.0,
            "recoverability_score": 0.85,
            "customer_successful_payments": 10,
            "retry_count": 0,
            "case_type": "SUBSCRIPTION_FAILURE"
        },
        {
            "name": "Moderate Checkout Drop-off (Returning Customer)",
            "amount": 15000.0,
            "recoverability_score": 0.70,
            "customer_successful_payments": 2,
            "retry_count": 1,
            "case_type": "CHECKOUT_DROPOFF"
        },
        {
            "name": "Low-Value Payment Failure (New Customer, Max Retries)",
            "amount": 499.0,
            "recoverability_score": 0.20,
            "customer_successful_payments": 0,
            "retry_count": 3,
            "case_type": "PAYMENT_FAILURE"
        }
    ]

    print("=======================================================")
    print("    DETERMINISTIC PRIORITY ENGINE TEST MATRIX         ")
    print("=======================================================")

    for tc in test_cases:
        res1 = priority_engine.calculate_priority(
            amount=tc["amount"],
            recoverability_score=tc["recoverability_score"],
            customer_successful_payments=tc["customer_successful_payments"],
            retry_count=tc["retry_count"],
            case_type=tc["case_type"]
        )
        res2 = priority_engine.calculate_priority(
            amount=tc["amount"],
            recoverability_score=tc["recoverability_score"],
            customer_successful_payments=tc["customer_successful_payments"],
            retry_count=tc["retry_count"],
            case_type=tc["case_type"]
        )

        print(f"\nScenario           : {tc['name']}")
        print(f"Amount             : INR {tc['amount']:,.2f}")
        print(f"Case Type          : {tc['case_type']}")
        print(f"Priority Score     : {res1.priority_score} / 100")
        print(f"Priority Level     : {res1.priority_level}")
        print(f"Priority Factors   : {[f.replace('₹', 'INR ') for f in res1.priority_factors]}")
        print(f"Determinism Check  : {'PASS (Run 1 == Run 2)' if res1.priority_score == res2.priority_score else 'FAIL'}")

if __name__ == "__main__":
    run_matrix()
