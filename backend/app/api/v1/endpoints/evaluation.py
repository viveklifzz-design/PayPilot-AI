import csv
import io
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.schemas.evaluation import (
    EvaluationRunRequest,
    EvaluationRunSummaryResponse,
    CaseDetailResponse
)
from app.models.evaluation_run import EvaluationRun
from app.services.evaluation.evaluator import evaluation_engine
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger

router = APIRouter()

def _build_summary_response(run: EvaluationRun) -> EvaluationRunSummaryResponse:
    metrics = run.metrics or {}
    summary = metrics.get("summary", {})
    rev_at_risk = float(run.revenue_at_risk or 0.0)
    rev_rec = float(run.total_recovered or 0.0)
    rec_rev = float(run.recoverable_revenue or (rev_at_risk * 0.70))

    precision_val = summary.get("precision") if "precision" in summary else float(run.precision_rate or 0.0)
    recall_val = summary.get("recall", 0.0)
    intervention_rate_val = summary.get("intervention_rate", 0.0)
    safe_stop_rate_val = summary.get("safe_stop_rate") if "safe_stop_rate" in summary else float(run.safe_stop_rate or 0.0)
    escalation_rate_val = summary.get("escalation_rate") if "escalation_rate" in summary else float(run.escalation_rate or 0.0)
    unsafe_actions = summary.get("unsafe_action_count", 0)

    return EvaluationRunSummaryResponse(
        run_id=run.id,
        run_name=run.run_name,
        seed=run.seed,
        dataset_size=run.batch_size,
        batch_size=run.batch_size,
        mode=run.mode,
        total_cases=run.total_cases,
        revenue_at_risk=rev_at_risk,
        total_failed_amount=rev_at_risk,
        recoverable_revenue=rec_rev,
        total_recovered=rev_rec,
        revenue_recovered=rev_rec,
        remaining_revenue_at_risk=float(run.remaining_revenue_at_risk or (rev_at_risk - rev_rec)),
        diagnosed_count=run.diagnosed_count,
        policy_allowed_count=run.policy_allowed_count,
        policy_blocked_count=run.policy_blocked_count,
        escalated_count=run.escalated_count,
        recovery_attempt_count=run.recovery_attempt_count,
        recovered_count=run.recovered_count,
        failed_recovery_count=run.failed_recovery_count,
        stopped_count=run.stopped_count,
        recovery_rate=float(run.recovery_rate or 0.0),
        recovery_success_rate=float(run.recovery_success_rate or run.recovery_rate or 0.0),
        precision=precision_val,
        precision_rate=precision_val,
        recall=recall_val,
        intervention_rate=intervention_rate_val,
        false_intervention_rate=float(run.false_intervention_rate or 0.0),
        escalation_rate=escalation_rate_val,
        safe_stop_rate=safe_stop_rate_val,
        unsafe_action_count=unsafe_actions,
        created_at=run.created_at,
        completed_at=run.completed_at
    )

@router.post("/evaluation/run", response_model=EvaluationRunSummaryResponse, tags=["Evaluation Engine"])
async def trigger_evaluation_run(
    req: EvaluationRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a reproducible, deterministic synthetic dataset evaluation run.
    Evaluates cases through Risk Engine -> Policy Gate -> Outcome Simulation.
    """
    size = req.effective_size
    mode = req.mode or "deterministic"
    result = await evaluation_engine.run_evaluation(
        db=db,
        dataset_size=size,
        seed=req.seed,
        mode=mode,
        run_name=req.run_name
    )

    res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == result.run_id))
    run = res.scalar_one()
    return _build_summary_response(run)

@router.get("/evaluation/summary", response_model=EvaluationRunSummaryResponse, tags=["Evaluation Engine"])
async def get_evaluation_summary(db: AsyncSession = Depends(get_db)):
    """Fetch latest evaluation run summary, or automatically execute a default 1000-case run if no runs exist."""
    res = await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1))
    run = res.scalar_one_or_none()

    if not run:
        logger.info("No existing evaluation runs found. Generating default 1000-case evaluation run...")
        result = await evaluation_engine.run_evaluation(db=db, dataset_size=1000, seed=42, mode="deterministic")
        res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == result.run_id))
        run = res.scalar_one()

    return _build_summary_response(run)

@router.get("/evaluation/runs/{run_id}", response_model=EvaluationRunSummaryResponse, tags=["Evaluation Engine"])
async def get_evaluation_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch complete summary metrics for a specific evaluation run."""
    res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise ResourceNotFoundException(resource="EvaluationRun", resource_id=run_id)
    return _build_summary_response(run)

@router.get("/evaluation/runs/{run_id}/cases", response_model=List[CaseDetailResponse], tags=["Evaluation Engine"])
async def get_evaluation_run_cases(run_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch case-level breakdown for an evaluation run."""
    res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise ResourceNotFoundException(resource="EvaluationRun", resource_id=run_id)

    metrics = run.metrics or {}
    cases_list = metrics.get("cases_summary", [])
    out: List[CaseDetailResponse] = []
    for idx, c in enumerate(cases_list, 1):
        out.append(CaseDetailResponse(
            case_num=c.get("case_num", idx),
            case_id=c.get("case_id"),
            amount=float(c.get("amount", 0.0)),
            error_code=c.get("error_code") or c.get("failure_reason"),
            failure_reason=c.get("failure_reason") or c.get("error_code"),
            risk_level=c.get("risk_level", "MEDIUM"),
            risk_score=float(c.get("risk_score", 50.0)),
            recoverability_score=float(c.get("recoverability_score", 0.5)),
            ai_root_cause=c.get("ai_root_cause", "N/A"),
            ai_recommended_action=c.get("ai_recommended_action", "RECOVERY_LINK"),
            ai_confidence=float(c.get("ai_confidence", 0.85)),
            policy_allowed=c.get("policy_allowed", True),
            effective_action=c.get("effective_action", "RECOVERY_LINK"),
            policy_violations=c.get("policy_violations", []),
            final_status=c.get("final_status", "OPEN"),
            recovered_amount=float(c.get("recovered_amount", 0.0)),
            simulation_notes=c.get("simulation_notes"),
            ground_truth_category=c.get("ground_truth_category"),
            ground_truth_action=c.get("ground_truth_action"),
            expected_recoverable=c.get("expected_recoverable", False)
        ))
    return out

@router.get("/evaluation/runs/{run_id}/export/csv", tags=["Evaluation Engine"])
async def export_evaluation_run_csv(run_id: str, db: AsyncSession = Depends(get_db)):
    """Export evaluation run case data as a judge-friendly CSV file."""
    res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = res.scalar_one_or_none()
    if not run:
        raise ResourceNotFoundException(resource="EvaluationRun", resource_id=run_id)

    metrics = run.metrics or {}
    cases_list = metrics.get("cases_summary", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Case ID",
        "Amount (INR)",
        "Failure Reason",
        "Risk Level",
        "Ground Truth Category",
        "Ground Truth Action",
        "Agent Decision",
        "Policy Allowed",
        "Effective Action",
        "Final Status",
        "Recovered Amount (INR)",
        "Simulation Notes"
    ])

    for c in cases_list:
        writer.writerow([
            c.get("case_id", f"case_{c.get('case_num', 0)}"),
            c.get("amount", 0.0),
            c.get("failure_reason") or c.get("error_code", "UNKNOWN"),
            c.get("risk_level", "MEDIUM"),
            c.get("ground_truth_category", "N/A"),
            c.get("ground_truth_action", "N/A"),
            c.get("ai_recommended_action", "N/A"),
            "ALLOWED" if c.get("policy_allowed", True) else "BLOCKED",
            c.get("effective_action", "N/A"),
            c.get("final_status", "N/A"),
            c.get("recovered_amount", 0.0),
            c.get("simulation_notes", "")
        ])

    csv_content = output.getvalue()
    filename = f"paypilot_evaluation_{run.seed}_{run.batch_size}cases.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
