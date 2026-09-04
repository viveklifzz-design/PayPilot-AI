import sys
import os
import asyncio
import requests
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import *
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.services.revenue_risk.failure_classifier import classify_razorpay_failure
from app.services.revenue_risk.failure_explanation import explain_razorpay_failure
from app.services.revenue_risk.risk_engine import risk_engine
from app.services.policy.policy_engine import policy_engine
from app.services.ai.gemini_service import gemini_ai_service
from app.services.recovery.executor import recovery_executor
from app.core.config import settings

async def run_ten_rupee_recovery_pipeline():
    print("=================================================================")
    print("   PAYPILOT AI -- REAL INR 10 RECOVERY PIPELINE EXECUTION        ")
    print("=================================================================\n")

    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    async with AsyncSessionLocal() as db:
        # 1. Fetch Real Failed Transaction (pay_TTXlSqxyg5hAiT)
        t_res = await db.execute(select(Transaction).where(Transaction.razorpay_payment_id == "pay_TTXlSqxyg5hAiT"))
        txn = t_res.scalar_one_or_none()
        
        if not txn:
            print("[FAIL] Real failed payment 'pay_TTXlSqxyg5hAiT' not found in database.")
            return False

        print(f"1. AUTHORITATIVE RAZORPAY FAILURE FACTS:")
        print(f"   - Payment ID       : {txn.razorpay_payment_id}")
        print(f"   - Amount           : INR {txn.amount:.2f}")
        print(f"   - Status           : {txn.status}")
        print(f"   - Error Code       : {txn.error_code}")
        print(f"   - Error Source     : {txn.error_source}")
        print(f"   - Error Step       : {txn.error_step}")
        print(f"   - Error Reason     : {txn.error_reason}")
        print(f"   - Description      : {txn.error_description}")

        # 2. Failure Classification & Explanation
        classified = classify_razorpay_failure(
            error_code=txn.error_code,
            error_source=txn.error_source,
            error_step=txn.error_step,
            error_reason=txn.error_reason,
            error_description=txn.error_description
        )
        explanation = explain_razorpay_failure(
            error_code=txn.error_code,
            error_source=txn.error_source,
            error_step=txn.error_step,
            error_reason=txn.error_reason,
            error_description=txn.error_description
        )
        print(f"\n2. FAILURE CLASSIFICATION & EXPLANATION:")
        print(f"   - Category         : {classified.category}")
        print(f"   - Classified Reason: {classified.reason}")
        print(f"   - User Explanation : {explanation}")

        # 3. Fetch/Create RecoveryCase for pay_TTXlSqxyg5hAiT
        rc_res = await db.execute(select(RecoveryCase).where(RecoveryCase.transaction_id == txn.id))
        case = rc_res.scalar_one_or_none()
        if not case:
            risk_res = risk_engine.assess_transaction(amount=float(txn.amount), error_code=txn.error_code)
            case = RecoveryCase(
                case_type="PAYMENT_FAILURE",
                merchant_id=txn.merchant_id,
                transaction_id=txn.id,
                customer_id=txn.customer_id,
                amount=float(txn.amount),
                risk_score=risk_res.risk_score,
                risk_level=risk_res.risk_level,
                priority_score=risk_res.priority_score,
                priority_level=risk_res.priority_level,
                risk_factors=risk_res.risk_factors,
                status="OPEN",
                policy_passed=True
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)

        # 4. Run AI Diagnosis Layer
        diag_context = {
            "error_code": txn.error_code,
            "error_source": txn.error_source,
            "error_step": txn.error_step,
            "error_reason": txn.error_reason,
            "error_description": txn.error_description,
            "amount": float(txn.amount),
            "payment_method": txn.payment_method
        }
        ai_diag = gemini_ai_service.diagnose_payment_failure(diag_context)
        case.ai_root_cause = ai_diag.root_cause
        case.ai_recommended_action = ai_diag.recommended_action
        case.ai_confidence = ai_diag.confidence
        case.status = "DIAGNOSED"
        db.add(case)
        await db.commit()
        await db.refresh(case)

        print(f"\n3. AI DIAGNOSIS RESULTS:")
        print(f"   - Case ID          : #{case.id[:8]}")
        print(f"   - Root Cause       : {case.ai_root_cause}")
        print(f"   - Recommendation   : {case.ai_recommended_action}")
        print(f"   - AI Confidence    : {case.ai_confidence:.2f}")

        # 5. Policy Safety Gate Evaluation
        pol_eval = policy_engine.evaluate_action(
            proposed_action=case.ai_recommended_action or "RECOVERY_LINK",
            case_status=case.status,
            amount=float(case.amount),
            retry_count=case.retry_count,
            ai_confidence=case.ai_confidence,
            error_code=txn.error_code
        )
        case.policy_passed = pol_eval.allowed
        db.add(case)
        await db.commit()

        print(f"\n4. POLICY SAFETY GATE EVALUATION:")
        print(f"   - Policy Allowed   : {pol_eval.allowed}")
        print(f"   - Effective Action : {pol_eval.effective_action}")
        print(f"   - Reason           : {pol_eval.reason}")
        if not pol_eval.allowed:
            print(f"   - Violations       : {pol_eval.violations}")
            print("[FAIL] Policy Safety Gate rejected recovery.")
            return False

        # 6. Execute Recovery Action (Create Real Razorpay Payment Link for INR 10.00)
        exec_res = await recovery_executor.execute_recovery(case=case, db=db, proposed_action="RECOVERY_LINK")
        await db.refresh(case)

        print(f"\n5. REAL RAZORPAY PAYMENT LINK CREATION:")
        print(f"   - Execution Status : {exec_res['status']}")
        print(f"   - Provider Ref     : {exec_res.get('provider_reference')}")
        print(f"   - Payment Link URL : {exec_res.get('payment_link_url')}")
        print(f"   - Link Amount      : INR {exec_res.get('amount'):.2f}")
        print(f"   - Case Status      : {case.status}")

        # 7. Query Razorpay API for the Payment Link directly
        plink_id = exec_res.get('provider_reference')
        if plink_id:
            res_pl = requests.get(f"https://api.razorpay.com/v1/payment_links/{plink_id}", auth=(key_id, key_secret))
            if res_pl.status_code == 200:
                pl_data = res_pl.json()
                print(f"\n6. PROVIDER PAYMENT LINK VERIFICATION:")
                print(f"   - Link ID          : {pl_data['id']}")
                print(f"   - Link Amount      : INR {pl_data['amount']/100:.2f}")
                print(f"   - Amount Paid      : INR {pl_data['amount_paid']/100:.2f}")
                print(f"   - Link Status      : {pl_data['status']}")
                print(f"   - Short URL        : {pl_data['short_url']}")
                print(f"   - Associated Pyts  : {len(pl_data.get('payments', []))}")

    print("\n=================================================================")
    print("   RECOVERY PIPELINE STEP COMPLETE                               ")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    asyncio.run(run_ten_rupee_recovery_pipeline())
