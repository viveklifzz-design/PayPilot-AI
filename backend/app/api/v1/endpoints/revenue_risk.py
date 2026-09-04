from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.unified_risk import UnifiedRiskSummaryResponse, UnifiedOpportunitiesResponse
from app.services.revenue_risk.unified_risk import unified_risk_service

router = APIRouter()

@router.get("/revenue-risk/summary", response_model=UnifiedRiskSummaryResponse, tags=["Unified Revenue Risk"])
async def get_revenue_risk_summary(db: AsyncSession = Depends(get_db)):
    """
    Fetch canonical summary of revenue at risk deduplicated across 
    Payment Failures, Checkout Drop-offs, and Subscription Failures.
    """
    res = await unified_risk_service.get_unified_opportunities(db)
    return res.summary

@router.get("/revenue-risk/opportunities", response_model=UnifiedOpportunitiesResponse, tags=["Unified Revenue Risk"])
async def get_revenue_risk_opportunities(db: AsyncSession = Depends(get_db)):
    """
    Fetch prioritized active recovery opportunities sorted by priority score descending.
    """
    return await unified_risk_service.get_unified_opportunities(db)
