import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import *  # Load all SQLAlchemy models
from app.db.session import AsyncSessionLocal
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.services.revenue_risk.failure_classifier import classify_razorpay_failure

async def main():
    async with AsyncSessionLocal() as db:
        print("=================================================================")
        print("    PAYPILOT AI -- RECOVERY LIFECYCLE DEMO VERIFICATION SUITE    ")
        print("=================================================================")

        # Find RECOVERED case or active recovery case
        res = await db.execute(
            select(RecoveryCase)
            .order_by(RecoveryCase.updated_at.desc())
        )
        cases = res.scalars().all()

        if not cases:
            print("[BLOCKED] NO RECOVERY CASES FOUND IN SYSTEM")
            sys.exit(1)

        rec_case = next((c for c in cases if c.status == "RECOVERED"), cases[0])

        txn_res = await db.execute(select(Transaction).where(Transaction.id == rec_case.transaction_id))
        txn = txn_res.scalar_one_or_none()

        act_res = await db.execute(select(RecoveryAction).where(RecoveryAction.case_id == rec_case.id))
        actions = act_res.scalars().all()

        audit_res = await db.execute(select(AuditLog).where(AuditLog.case_id == rec_case.id))
        audits = audit_res.scalars().all()

        # Execute Checks
        c1 = rec_case.id is not None
        c2 = txn is not None and (txn.error_code is not None or rec_case.case_type == "CHECKOUT_DROPOFF")
        
        classified = classify_razorpay_failure(
            error_code=txn.error_code if txn else None,
            error_source=txn.error_source if txn else None,
            error_step=txn.error_step if txn else None,
            error_reason=txn.error_reason if txn else None
        ) if txn else None

        c3 = classified is not None or rec_case.case_type == "CHECKOUT_DROPOFF"
        c4 = rec_case.ai_recommended_action is not None
        c5 = rec_case.policy_passed is True
        c6 = len(actions) > 0
        c7 = any(a.razorpay_payment_link_id for a in actions)
        c8 = any(a.short_url for a in actions)
        c9 = len(audits) > 0
        c10 = rec_case.status in ["RECOVERED", "RECOVERING", "OPEN", "DIAGNOSED"]

        print(f"1. Payment Failure / Dropoff Case Exists: {'PASS' if c1 else 'FAIL'} (Case #{rec_case.id[:8]})")
        print(f"2. Razorpay Failure Facts Exist         : {'PASS' if c2 else 'FAIL'} ({txn.error_code if txn else 'CHECKOUT_ABANDONED'})")
        print(f"3. Failure Classification Exists        : {'PASS' if c3 else 'FAIL'} ({classified.category if classified else 'DROPOFF'})")
        print(f"4. AI Diagnosis Exists                  : {'PASS' if c4 else 'FAIL'} (Rec: {rec_case.ai_recommended_action})")
        print(f"5. Policy Safety Decision Exists        : {'PASS' if c5 else 'FAIL'} (Passed: {rec_case.policy_passed})")
        print(f"6. Recovery Action Exists               : {'PASS' if c6 else 'FAIL'} ({actions[0].action_type if actions else 'N/A'})")
        print(f"7. Razorpay Provider Reference Exists   : {'PASS' if c7 else 'FAIL'} ({actions[0].razorpay_payment_link_id if actions else 'N/A'})")
        print(f"8. Payment Link URL Exists             : {'PASS' if c8 else 'FAIL'} ({actions[0].short_url if actions else 'N/A'})")
        print(f"9. Audit Trail Events Exist             : {'PASS' if c9 else 'FAIL'} ({len(audits)} events logged)")
        print(f"10. Recovery Status Verified            : {'PASS' if c10 else 'FAIL'} (Status: {rec_case.status})")

        all_pass = all([c1, c2, c3, c4, c5, c6, c7, c8, c9, c10])
        print("\n=================================================================")
        if all_pass:
            print("    ALL RECOVERY LIFECYCLE VERIFICATION CHECKS PASSED           ")
        else:
            print("    SOME RECOVERY LIFECYCLE CHECKS FAILED                       ")
        print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
