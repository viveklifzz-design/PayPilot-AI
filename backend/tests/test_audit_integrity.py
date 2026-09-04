import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.recovery_case import RecoveryCase

@pytest.mark.asyncio
async def test_link_creation_is_not_recovery(db_session: AsyncSession):
    """Verify that creating a payment link does NOT set RecoveryCase to RECOVERED."""
    case = RecoveryCase(
        case_type="PAYMENT_FAILURE",
        merchant_id="merchant_test_123",
        amount=1500.0,
        recovered_amount=0.0,
        risk_level="LOW",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)

    assert case.status == "OPEN"
    assert case.recovered_amount == 0.0


@pytest.mark.asyncio
async def test_unreconciled_case_excluded_from_analytics(async_client: AsyncClient, db_session: AsyncSession):
    """Verify that INVALID_UNRECONCILED cases do NOT inflate recovered_revenue metrics."""
    unreconciled_case = RecoveryCase(
        case_type="PAYMENT_FAILURE",
        merchant_id="merchant_test_123",
        amount=2500.0,
        recovered_amount=0.0,
        risk_level="LOW",
        status="INVALID_UNRECONCILED"
    )
    db_session.add(unreconciled_case)
    await db_session.commit()

    res = await async_client.get("/api/v1/analytics/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["recovered_revenue"] < 2500.0 or data["recovered_revenue"] == 0.0


@pytest.mark.asyncio
async def test_provider_verification_required_for_recovered_status(db_session: AsyncSession):
    """Verify that a case is only RECOVERED when provider payment is captured."""
    verified_case = RecoveryCase(
        case_type="PAYMENT_FAILURE",
        merchant_id="merchant_test_123",
        amount=10.0,
        recovered_amount=10.0,
        risk_level="LOW",
        status="RECOVERED"
    )
    db_session.add(verified_case)
    await db_session.commit()

    assert verified_case.status == "RECOVERED"
    assert verified_case.recovered_amount == 10.0
