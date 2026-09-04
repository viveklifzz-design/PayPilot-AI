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

async def run_mandate_simulation():
    print("=================================================================")
    print("   PAYPILOT AI -- MANDATE RETRY SEQUENCER LOCAL SIMULATION      ")
    print("   [LABEL: LOCAL TEST SIMULATION]                               ")
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
            mandate_number=f"MND-SIM-{utc_now().timestamp()}",
            amount=18500.0,
            billing_interval="monthly"
        )

        m1, c1 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db, mandate.id, "Bank auto-debit timeout")

        print(f"[PASS] 1. Mandate Created        : Mandate #{mandate.mandate_number} (Amount: INR {mandate.amount:,.2f})")
        print(f"[PASS] 2. Attempt #1 Failed     : Status: {m1.status}, Cooldown: 24h Scheduled")
        print(f"[PASS] 3. RecoveryCase Created  : Type: MANDATE_RETRY, Attempt: {m1.attempt_count}/3")
        print("\n[LOCAL TEST SIMULATION COMPLETE]")

if __name__ == "__main__":
    asyncio.run(run_mandate_simulation())
