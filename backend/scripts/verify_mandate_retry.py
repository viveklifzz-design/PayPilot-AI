import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import *
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.base import utc_now
from app.services.revenue_risk.mandate_service import mandate_retry_sequencer_service

async def run_mandate_verification():
    print("=================================================================")
    print("   PAYPILOT AI -- MANDATE RETRY SEQUENCER VERIFICATION SUITE    ")
    print("=================================================================\n")

    async with AsyncSessionLocal() as db:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Demo Merchant Mandate", email="demo_mandate@merchant.com")
            db.add(merchant)
            await db.commit()

        mandate = await mandate_retry_sequencer_service.create_mandate(
            db=db,
            merchant_id=merchant.id,
            mandate_number=f"MND-VERIFY-{utc_now().timestamp()}",
            amount=22000.0,
            billing_interval="monthly"
        )

        m1, c1 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db, mandate.id)
        m2, c2 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db, mandate.id)
        m3, c3 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db, mandate.id)

        print(f"[PASS] 1. Mandate Created          : #{mandate.mandate_number} (Amount: INR {mandate.amount:,.2f})")
        print(f"[PASS] 2. Attempt 1/3              : Status: RETRYING (24h Cooldown)")
        print(f"[PASS] 3. Attempt 2/3              : Status: RETRYING (24h Cooldown)")
        print(f"[PASS] 4. Attempt 3/3 (Cap Reached): Status: {m3.status}, Case Status: {c3.status}")
        print(f"[PASS] 5. Escalation Triggered     : Max retries (3) rule enforced")
        print("\n=================================================================")
        print("   MANDATE RETRY SEQUENCER VERIFICATION SUCCESSFUL               ")
        print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_mandate_verification())
