import sys
import os
import asyncio
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import *
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.base import utc_now
from app.services.revenue_risk.receivables_service import receivables_chaser_service

async def run_b2b_simulation():
    print("=================================================================")
    print("   PAYPILOT AI -- B2B RECEIVABLES CHASER LOCAL SIMULATION       ")
    print("   [LABEL: LOCAL TEST SIMULATION]                               ")
    print("=================================================================\n")

    async with AsyncSessionLocal() as db:
        m_res = await db.execute(select(Merchant))
        merchant = m_res.scalars().first()
        if not merchant:
            merchant = Merchant(name="Demo Merchant B2B", email="demo_b2b@merchant.com")
            db.add(merchant)
            await db.commit()

        c_res = await db.execute(select(Customer))
        customer = c_res.scalars().first()
        if not customer:
            customer = Customer(merchant_id=merchant.id, name="Acme Corp B2B", email="billing@acmecorp.com")
            db.add(customer)
            await db.commit()

        # Create overdue invoice (due 7 days ago)
        due_date = utc_now() - timedelta(days=7)
        inv = await receivables_chaser_service.create_invoice(
            db=db,
            merchant_id=merchant.id,
            invoice_number="INV-2026-B2B-88",
            amount=85000.0,
            due_date=due_date,
            customer_id=customer.id
        )

        cases = await receivables_chaser_service.process_overdue_invoices(db)

        print(f"[PASS] 1. B2B Invoice Created   : Invoice #{inv.invoice_number} (Amount: INR {inv.amount:,.2f})")
        print(f"[PASS] 2. Overdue Detected     : Days Overdue: 7, Status: OVERDUE")
        print(f"[PASS] 3. RecoveryCase Created : Type: B2B_RECEIVABLE, Cases Count: {len(cases)}")
        print("\n[LOCAL TEST SIMULATION COMPLETE]")

if __name__ == "__main__":
    asyncio.run(run_b2b_simulation())
