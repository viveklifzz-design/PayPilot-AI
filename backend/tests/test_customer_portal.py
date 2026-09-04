import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction

@pytest.mark.asyncio
async def test_customer_login_and_unauthorized_access(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Create two customers and transactions
    m = Merchant(name="Test Merchant Portal", email="portal@merchant.com")
    db_session.add(m)
    await db_session.commit()

    cust_a = Customer(merchant_id=m.id, name="Customer A", email="a@customer.com")
    cust_b = Customer(merchant_id=m.id, name="Customer B", email="b@customer.com")
    db_session.add_all([cust_a, cust_b])
    await db_session.commit()

    txn_a = Transaction(
        merchant_id=m.id,
        customer_id=cust_a.id,
        amount=1500.0,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_ERROR",
        error_reason="insufficient_funds"
    )
    db_session.add(txn_a)
    await db_session.commit()

    # 2. Login as Customer A
    login_resp = await async_client.post("/api/v1/customer/login", json={"email": "a@customer.com"})
    assert login_resp.status_code == 200
    assert login_resp.json()["customer_id"] == cust_a.id

    # 3. Customer A accesses own transaction -> 200 OK
    own_resp = await async_client.get(
        f"/api/v1/customer/transactions/{txn_a.id}",
        headers={"x-customer-id": cust_a.id}
    )
    assert own_resp.status_code == 200
    assert own_resp.json()["transaction_id"] == txn_a.id

    # 4. SECURITY CHECK: Customer B attempts unauthorized access to Customer A's transaction -> 403 Forbidden
    unauth_resp = await async_client.get(
        f"/api/v1/customer/transactions/{txn_a.id}",
        headers={"x-customer-id": cust_b.id}
    )
    assert unauth_resp.status_code == 403
    assert "Access Denied" in unauth_resp.json()["detail"]
