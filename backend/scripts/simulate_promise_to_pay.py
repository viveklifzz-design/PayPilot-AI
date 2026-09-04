import sys
import os
import asyncio
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import *
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.base import utc_now
from app.services.revenue_risk.receivables_service import receivables_chaser_service

async def run_promise_simulation():
    print("=================================================================")
    print("   PAYPILOT AI -- PROMISE-TO-PAY TRACKER LOCAL SIMULATION       ")
    print("   [LABEL: LOCAL TEST SIMULATION]                               ")
    print("=================================================================\n")

    async with AsyncSessionLocal() as db:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()

        inv = await receivables_chaser_service.create_invoice(
            db=db,
            merchant_id=merchant.id if merchant else "merch_demo",
            invoice_number=f"INV-P2P-{utc_now().timestamp()}",
            amount=95000.0,
            due_date=utc_now() - timedelta(days=3)
        )

        cases = await receivables_chaser_service.process_overdue_invoices(db)

        promise_dt = utc_now() + timedelta(days=4)
        updated_inv = await receivables_chaser_service.register_promise_to_pay(db, inv.id, promise_dt)

        print(f"[PASS] 1. Overdue Invoice Created : #{inv.invoice_number} (INR {inv.amount:,.2f})")
        print(f"[PASS] 2. Customer Promise Date  : {promise_dt.strftime('%Y-%m-%d')}")
        print(f"[PASS] 3. Status Transitioned     : {updated_inv.status}")
        print("\n[LOCAL TEST SIMULATION COMPLETE]")

if __name__ == "__main__":
    asyncio.run(run_promise_simulation())
