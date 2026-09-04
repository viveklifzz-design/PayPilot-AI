import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_analytics_metrics_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    res = await async_client.get("/api/v1/analytics/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "revenue_at_risk" in data
    assert "recovered_revenue" in data
    assert "recovery_rate" in data

@pytest.mark.asyncio
async def test_analytics_funnel_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    res = await async_client.get("/api/v1/analytics/funnel")
    assert res.status_code == 200
    data = res.json()
    assert "funnel" in data
    assert len(data["funnel"]) == 5

@pytest.mark.asyncio
async def test_analytics_no_evaluation_run_fallback(async_client: AsyncClient, db_session: AsyncSession):
    """Verifies that analytics metrics do NOT fall back to synthetic EvaluationRun when live cases are empty."""
    res = await async_client.get("/api/v1/analytics/metrics")
    assert res.status_code == 200
    data = res.json()
    # Synthetic benchmark values (e.g. 17.95M risk) must NEVER contaminate empty state
    if data["failed_payments_count"] == 0:
        assert data["revenue_at_risk"] == 0.0
        assert data["recovered_revenue"] == 0.0
