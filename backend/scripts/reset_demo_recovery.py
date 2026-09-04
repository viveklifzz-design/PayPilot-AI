import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import *  # Load all SQLAlchemy models
from app.db.session import AsyncSessionLocal
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.services.revenue_risk.risk_engine import risk_engine
from app.services.recovery.executor import recovery_executor

async def main():
    async with AsyncSessionLocal() as db:
        print("=======================================================")
        print("     PAYPILOT AI -- DEMO RECOVERY RESET SIMULATOR      ")
        print("=======================================================")

        # Find or create demo merchant
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Demo Merchant", email="demo@merchant.com")
            db.add(merchant)
            await db.commit()
            await db.refresh(merchant)

        # 1. Create fresh demo payment failure transaction
        txn = Transaction(
            merchant_id=merchant.id,
            amount=2500.0,
            currency="INR",
            status="failed",
            error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
            error_description="Customer authorization timed out during payment confirmation",
            error_source="bank",
            error_step="payment_authorization",
            error_reason="payment_verification_failed",
            payment_method="upi"
        )
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        # 2. Risk assessment & case creation
        risk_res = risk_engine.assess_transaction(amount=2500.0, error_code="BAD_REQUEST_PAYMENT_TIMED_OUT")
        case = RecoveryCase(
            case_type="PAYMENT_FAILURE",
            merchant_id=merchant.id,
            transaction_id=txn.id,
            amount=2500.0,
            risk_score=risk_res.risk_score,
            risk_level=risk_res.risk_level,
            priority_score=risk_res.priority_score,
            priority_level=risk_res.priority_level,
            risk_factors=risk_res.risk_factors,
            status="DIAGNOSED",
            ai_root_cause="Temporary bank network timeout during OTP verification",
            ai_recommended_action="RECOVERY_LINK",
            ai_confidence=0.92,
            policy_passed=True
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)

        # 3. Execute recovery link in Test Mode
        exec_res = await recovery_executor.execute_recovery(case=case, db=db, proposed_action="RECOVERY_LINK")

        print("\n[SUCCESS] Fresh Demo Payment Failure & Recovery Action Initialized!")
        print(f"Transaction ID      : {txn.id}")
        print(f"Recovery Case ID    : {case.id}")
        print(f"Case Status         : {case.status}")
        print(f"Execution Status    : {exec_res.get('execution_status')}")
        print(f"Provider Reference  : {exec_res.get('provider_reference')}")
        print(f"Payment Link URL    : {exec_res.get('payment_url') or exec_res.get('payment_link_url')}")

if __name__ == "__main__":
    asyncio.run(main())
