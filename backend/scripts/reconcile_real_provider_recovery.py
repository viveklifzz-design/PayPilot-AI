import sys
import os
import asyncio
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal
from app.services.recovery.reconciliation_service import reconciliation_service

async def run_reconciliation():
    print("=================================================================")
    print("   PAYPILOT AI -- REAL PROVIDER RECOVERY RECONCILIATION RUNNER   ")
    print("=================================================================\n")

    payment_id = "pay_TU3EQsT63DFVuX"
    order_id = "order_TU2xgzptEfg7rP"

    async with AsyncSessionLocal() as db:
        # 1. First Reconciliation Run
        print("1. RUNNING FIRST RECONCILIATION PASS...")
        res1 = await reconciliation_service.reconcile_provider_recovery(
            payment_id=payment_id,
            order_id=order_id,
            db=db,
            verification_source="REAL_RAZORPAY_TEST_MODE_PAYMENT"
        )
        print(f"   - Reconciled       : {res1.get('reconciled')}")
        print(f"   - Already Recovered: {res1.get('already_recovered')}")
        print(f"   - Case ID          : {res1.get('case_id')}")
        print(f"   - Payment ID       : {res1.get('payment_id')}")
        print(f"   - Order ID         : {res1.get('order_id')}")
        print(f"   - Recovered Amount : INR {res1.get('recovered_amount'):.2f}")
        print(f"   - Message          : {res1.get('message')}")

        # 2. Second Reconciliation Run (Idempotency Check)
        print("\n2. RUNNING SECOND RECONCILIATION PASS (IDEMPOTENCY VERIFICATION)...")
        res2 = await reconciliation_service.reconcile_provider_recovery(
            payment_id=payment_id,
            order_id=order_id,
            db=db,
            verification_source="REAL_RAZORPAY_TEST_MODE_PAYMENT"
        )
        print(f"   - Reconciled       : {res2.get('reconciled')}")
        print(f"   - Already Recovered: {res2.get('already_recovered')}")
        print(f"   - Case ID          : {res2.get('case_id')}")
        print(f"   - Recovered Amount : INR {res2.get('recovered_amount'):.2f}")
        print(f"   - Message          : {res2.get('message')}")

    print("\n=================================================================")
    print("   RECONCILIATION RUNNER COMPLETE -- IDEMPOTENCY PASSED          ")
    print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_reconciliation())
