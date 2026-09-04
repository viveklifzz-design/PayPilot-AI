from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.health import RazorpayHealthResponse
from app.services.recovery.failure_fallback import (
    failure_fallback,
    FailureScenarioDetail,
    SimulateFailureRequest,
    SimulateFailureResponse
)
from app.core.config import settings

router = APIRouter()

@router.get("/health/razorpay", response_model=RazorpayHealthResponse, tags=["Health"])
async def check_razorpay_health():
    """Check safe Razorpay integration configuration status."""
    key_id_set = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_ID.strip())
    key_secret_set = bool(settings.RAZORPAY_KEY_SECRET and settings.RAZORPAY_KEY_SECRET.strip())
    webhook_secret_set = bool(settings.RAZORPAY_WEBHOOK_SECRET and settings.RAZORPAY_WEBHOOK_SECRET.strip())

    is_configured = key_id_set and key_secret_set and webhook_secret_set
    is_test_mode = settings.RAZORPAY_KEY_ID.startswith("rzp_test_") if key_id_set else True

    return RazorpayHealthResponse(
        configured=is_configured,
        test_mode=is_test_mode,
        webhook_configured=webhook_secret_set,
        status="connected" if is_configured else "configuration_pending"
    )

@router.get("/health/failure-scenarios", response_model=List[FailureScenarioDetail], tags=["Health"])
async def get_failure_scenarios():
    """List supportable system failure scenarios and fallback behaviors."""
    return failure_fallback.list_scenarios()

@router.post("/health/simulate-failure", response_model=SimulateFailureResponse, tags=["Health"])
async def simulate_failure_endpoint(
    req: SimulateFailureRequest,
    db: AsyncSession = Depends(get_db)
):
    """Safely execute a controlled failure simulation on an isolated test case."""
    return await failure_fallback.simulate_failure(req, db)
