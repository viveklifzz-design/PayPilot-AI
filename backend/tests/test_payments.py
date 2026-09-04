import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_order_endpoint(async_client: AsyncClient):
    payload = {
        "merchant_id": "m_test_99",
        "amount": 1500.0,
        "currency": "INR",
        "receipt": "rcpt_99"
    }
    response = await async_client.post("/api/v1/payments/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 1500.0
    assert data["status"] == "created"
    assert data["razorpay_order_id"] is not None

@pytest.mark.asyncio
async def test_list_and_get_transactions_endpoint(async_client: AsyncClient):
    # First create an order
    order_res = await async_client.post("/api/v1/payments/orders", json={"merchant_id": "m_test_99", "amount": 2000.0})
    txn_id = order_res.json()["id"]

    # Fetch list
    list_res = await async_client.get("/api/v1/transactions")
    assert list_res.status_code == 200
    txns = list_res.json()
    assert len(txns) >= 1

    # Fetch by ID
    get_res = await async_client.get(f"/api/v1/transactions/{txn_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == txn_id
