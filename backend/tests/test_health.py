import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PayPilot AI"
    assert "timestamp" in data

@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_root_db_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

@pytest.mark.asyncio
async def test_api_v1_db_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_api_v1_razorpay_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/razorpay")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "status" in data
    assert "RAZORPAY_KEY_SECRET" not in data
    assert "RAZORPAY_WEBHOOK_SECRET" not in data
