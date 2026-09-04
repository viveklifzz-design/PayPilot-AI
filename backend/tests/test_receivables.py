import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.base import utc_now
from app.services.revenue_risk.receivables_service import receivables_chaser_service

@pytest.mark.asyncio
async def test_receivables_overdue_and_promise_tracker(db_session: AsyncSession):
    # 1. Create merchant and customer
    m = Merchant(name="B2B Merchant", email="b2b@merchant.com")
    db_session.add(m)
    await db_session.commit()

    c = Customer(merchant_id=m.id, name="Corporate Client", email="corp@client.com")
    db_session.add(c)
    await db_session.commit()

    # 2. Create overdue invoice (due 5 days ago)
    past_due = utc_now() - timedelta(days=5)
    inv = await receivables_chaser_service.create_invoice(
        db=db_session,
        merchant_id=m.id,
        invoice_number="INV-2026-001",
        amount=150000.0,
        due_date=past_due,
        customer_id=c.id
    )
    assert inv.status == "DUE"

    # 3. Process overdue invoices -> creates B2B_RECEIVABLE RecoveryCase
    cases = await receivables_chaser_service.process_overdue_invoices(db_session)
    assert len(cases) == 1
    case = cases[0]
    assert case.case_type == "B2B_RECEIVABLE"
    assert float(case.amount) == 150000.0

    # 4. Register Promise-to-Pay for future date
    future_promise = utc_now() + timedelta(days=3)
    updated_inv = await receivables_chaser_service.register_promise_to_pay(
        db=db_session,
        invoice_id=inv.id,
        promise_date=future_promise
    )
    assert updated_inv.status == "PROMISE_TO_PAY"
    assert updated_inv.promise_date.strftime("%Y-%m-%d") == future_promise.strftime("%Y-%m-%d")
