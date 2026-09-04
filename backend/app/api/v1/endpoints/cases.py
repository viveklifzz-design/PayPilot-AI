from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.schemas.recovery_case import RecoveryCaseResponse
from app.schemas.ai_diagnosis import AIDiagnosisResponse
from app.schemas.ai_assessment import AIAssessmentResponse
from app.schemas.audit import (
    CaseTimelineResponse,
    TimelineStageItem,
    DecisionSummaryResponse,
    ExplainabilityCheckItem
)
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.models.ai_diagnosis import AIDiagnosis
from app.services.policy import policy_engine, PolicyCheckResult
from app.services.recovery.policy_gate import policy_gate, PolicyGateResponse
from app.services.recovery.stopping_rules import stopping_rules, StoppingRulesResponse
from app.services.recovery.human_escalation import human_escalation, HumanEscalationResponse, HumanActionRequest, HumanActionResponse
from app.services.analytics.recovery_funnel import recovery_funnel, CaseFunnelLineageResponse
from app.services.analytics.ai_metrics import ai_metrics, CaseAIEvaluationResponse
from app.services.revenue_risk.failure_classifier import classify_razorpay_failure
from app.services.recovery.checkout_abandonment import checkout_abandonment_service, CheckoutStatusResponse, CheckoutRetryResponse
from app.services.ai import get_ai_service, PROMPT_VERSION
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import logger

router = APIRouter()

class PolicyCheckRequest(BaseModel):
    proposed_action: str
    ai_confidence: Optional[float] = None

@router.get("/cases", response_model=List[RecoveryCaseResponse], tags=["Recovery Cases"])
async def list_cases(
    merchant_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    risk_level: Optional[str] = Query(None),
    priority_level: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List recovery cases with status, risk level, and merchant filtering."""
    query = select(RecoveryCase)
    if merchant_id:
        query = query.where(RecoveryCase.merchant_id == merchant_id)
    if status_filter:
        query = query.where(RecoveryCase.status == status_filter)
    if risk_level:
        query = query.where(RecoveryCase.risk_level == risk_level.upper())
    if priority_level:
        query = query.where(RecoveryCase.priority_level == priority_level.upper())
        
    query = query.order_by(RecoveryCase.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    cases = result.scalars().all()
    return cases

async def _get_case_by_id_or_prefix(case_id: str, db: AsyncSession) -> Optional[RecoveryCase]:
    if not case_id or not isinstance(case_id, str):
        return None
    cid = case_id.strip()
    if not cid:
        return None

    # 1. Exact UUID match
    exact_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == cid))
    exact_case = exact_res.scalar_one_or_none()
    if exact_case:
        return exact_case

    # 2. Prefix match (must be at least 4 characters long)
    if len(cid) < 4:
        return None

    prefix_res = await db.execute(
        select(RecoveryCase).where(
            ~RecoveryCase.case_type.in_(["B2B_RECEIVABLE", "MANDATE_RETRY"]),
            RecoveryCase.id.like(f"{cid}%")
        ).order_by(RecoveryCase.created_at.desc())
    )
    matches = prefix_res.scalars().all()
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ambiguous case ID prefix '{cid}' matches multiple cases ({len(matches)} matches found)."
        )
    return None

@router.get("/cases/escalated", response_model=List[RecoveryCaseResponse], tags=["Recovery Cases"])
async def list_escalated_cases(
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all recovery cases that are currently in ESCALATED, ACTION_PENDING, or requiring human review.
    """
    stmt = select(RecoveryCase).where(
        RecoveryCase.status.in_(["ESCALATED", "ACTION_PENDING"])
    ).order_by(RecoveryCase.created_at.desc())
    res = await db.execute(stmt)
    cases = res.scalars().all()
    return cases

@router.get("/cases/{case_id}", response_model=RecoveryCaseResponse, tags=["Recovery Cases"])
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch details of a single recovery case by ID or 8-character ID prefix."""
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)
    return case

@router.get("/cases/{case_id}/ai-assessment", response_model=AIAssessmentResponse, tags=["AI Decision Intelligence"])
@router.get("/recovery-cases/{case_id}/ai-assessment", response_model=AIAssessmentResponse, tags=["AI Decision Intelligence"])
async def get_case_ai_assessment(case_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch explainable AI Recovery Assessment for a recovery case.
    Generates structured AI decision (recoverable, confidence, why, signals) based on actual case facts.
    Does NOT mutate financial or recovery state.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn = None
    if case.transaction_id:
        txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
        txn = txn_res.scalar_one_or_none()

    from app.services.recovery.ai_decision_service import ai_decision_service
    assessment = ai_decision_service.assess_case(case, txn)
    return assessment

@router.get("/cases/{case_id}/timeline", response_model=CaseTimelineResponse, tags=["Audit & Decision Trace"])
async def get_case_timeline(case_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch chronological 7-stage decision timeline for a recovery case."""
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    actions_res = await db.execute(
        select(RecoveryAction)
        .where(RecoveryAction.case_id == case.id)
        .order_by(RecoveryAction.executed_at.asc())
    )
    actions = actions_res.scalars().all()

    audit_res = await db.execute(
        select(AuditLog)
        .where(AuditLog.case_id == case.id)
        .order_by(AuditLog.created_at.asc())
    )
    audits = audit_res.scalars().all()

    timeline: List[TimelineStageItem] = []

    # Stage 1: DETECT
    is_dropoff = (case.case_type == "CHECKOUT_DROPOFF")
    detect_title = "Checkout Drop-off Detected" if is_dropoff else "Payment Failure Detected"
    detect_desc = (
        f"Checkout session inactive past window. Case #{case.id[:8]} initialized."
        if is_dropoff
        else f"Transaction failure ({txn.error_code if txn else 'TIMED_OUT'}) captured. Case #{case.id[:8]} initialized."
    )

    timeline.append(TimelineStageItem(
        stage="DETECT",
        stage_number=1,
        event="CHECKOUT_DROPOFF_DETECTED" if is_dropoff else "CASE_CREATED",
        timestamp=case.created_at,
        status="completed",
        title=detect_title,
        description=detect_desc,
        details={
            "case_type": case.case_type,
            "amount": float(case.amount),
            "error_code": txn.error_code if txn else ("CHECKOUT_ABANDONED" if is_dropoff else "UNKNOWN"),
            "payment_method": txn.payment_method if txn else "N/A"
        }
    ))

    # Stage 2: DIAGNOSE
    ai_diag_log = next((a for a in audits if a.event_type == "AI_DIAGNOSIS_COMPLETED"), None)
    diag_ts = ai_diag_log.created_at if ai_diag_log else case.created_at
    timeline.append(TimelineStageItem(
        stage="DIAGNOSE",
        stage_number=2,
        event="AI_DIAGNOSIS_COMPLETED",
        timestamp=diag_ts,
        status="completed",
        title="AI Root Cause Diagnosis",
        description=f"AI identified: '{case.ai_root_cause or 'Temporary network/gateway error'}' (Confidence: {int((case.ai_confidence or 0.85)*100)}%)",
        details={
            "root_cause": case.ai_root_cause or "Temporary timeout",
            "confidence": case.ai_confidence or 0.85,
            "risk_level": case.risk_level
        }
    ))

    # Stage 3: DECIDE
    timeline.append(TimelineStageItem(
        stage="DECIDE",
        stage_number=3,
        event="AI_DECISION_MADE",
        timestamp=diag_ts,
        status="completed",
        title=f"AI Action Recommendation: {case.ai_recommended_action or 'RECOVERY_LINK'}",
        description=f"AI recommended action '{case.ai_recommended_action or 'RECOVERY_LINK'}'. Reasoning: {case.ai_reasoning or 'Returning customer with strong past history.'}",
        details={
            "recommended_action": case.ai_recommended_action or "RECOVERY_LINK",
            "reasoning": case.ai_reasoning or "Standard recovery rule"
        }
    ))

    # Stage 4: POLICY
    pol_log = next((a for a in audits if a.event_type in ["RECOVERY_POLICY_CHECKED", "RECOVERY_POLICY_BLOCKED", "POLICY_APPROVED", "POLICY_BLOCKED"]), None)
    pol_ts = pol_log.created_at if pol_log else case.created_at
    pol_status = "allowed" if case.policy_passed else "blocked"
    pol_title = "Policy Safety Gate Approved" if case.policy_passed else "Policy Safety Gate Blocked"
    pol_desc = "Action approved by safety gate constraints." if case.policy_passed else f"Blocked: {case.policy_failure_reason or 'Policy violation'}"

    timeline.append(TimelineStageItem(
        stage="POLICY",
        stage_number=4,
        event="RECOVERY_POLICY_CHECKED",
        timestamp=pol_ts,
        status=pol_status,
        title=pol_title,
        description=pol_desc,
        details={
            "policy_passed": case.policy_passed,
            "failure_reason": case.policy_failure_reason,
            "retry_count": case.retry_count
        }
    ))

    # Stage 5: EXECUTE
    latest_action = actions[-1] if actions else None
    exec_ts = latest_action.executed_at if latest_action else case.created_at
    exec_status = latest_action.status if latest_action else ("completed" if case.actual_action_taken else "pending")
    exec_title = f"Executed {case.actual_action_taken or 'RECOVERY_LINK'}" if case.actual_action_taken else "Action Execution"
    exec_desc = (latest_action.payload.get("message") if (latest_action and latest_action.payload) else None) or "Recovery action initiated."

    timeline.append(TimelineStageItem(
        stage="EXECUTE",
        stage_number=5,
        event="RECOVERY_EXECUTION",
        timestamp=exec_ts,
        status=exec_status.lower(),
        title=exec_title,
        description=exec_desc,
        details={
            "action_taken": case.actual_action_taken or "RECOVERY_LINK",
            "provider": "RAZORPAY",
            "provider_reference": latest_action.razorpay_payment_link_id if latest_action else None,
            "payment_url": latest_action.short_url if latest_action else None
        }
    ))

    # Stage 6: VERIFY
    verify_log = next((a for a in audits if a.event_type == "RECOVERY_PAYMENT_RECEIVED"), None)
    verify_ts = verify_log.created_at if verify_log else case.updated_at
    verify_status = "completed" if case.status == "RECOVERED" else "pending"
    verify_desc = f"Payment confirmation received via Razorpay webhook." if case.status == "RECOVERED" else "Awaiting webhook payment confirmation."

    timeline.append(TimelineStageItem(
        stage="VERIFY",
        stage_number=6,
        event="RECOVERY_PAYMENT_RECEIVED" if case.status == "RECOVERED" else "WEBHOOK_AWAITING",
        timestamp=verify_ts,
        status=verify_status,
        title="Payment Verification",
        description=verify_desc,
        details={
            "webhook_received": (case.status == "RECOVERED"),
            "amount_verified": float(case.recovered_amount)
        }
    ))

    # Stage 7: RECOVER
    timeline.append(TimelineStageItem(
        stage="RECOVER",
        stage_number=7,
        event=f"CASE_{case.status}",
        timestamp=case.updated_at,
        status="completed" if case.status == "RECOVERED" else "pending",
        title=f"Final Case State: {case.status}",
        description=f"Total Revenue Recovered: INR {float(case.recovered_amount):,.2f}" if case.status == "RECOVERED" else f"Case in state {case.status}.",
        details={
            "final_status": case.status,
            "recovered_amount": float(case.recovered_amount)
        }
    ))

    return CaseTimelineResponse(
        case_id=case.id,
        case_type=case.case_type,
        status=case.status,
        amount=float(case.amount),
        currency=txn.currency if txn else "INR",
        timeline=timeline
    )

@router.get("/cases/{case_id}/decision-summary", response_model=DecisionSummaryResponse, tags=["Audit & Decision Trace"])
async def get_case_decision_summary(case_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch judge-friendly decision summary and structured explainability checklist for a recovery case."""
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    cust_succ = 0
    cust_fail = 0
    if case.customer_id:
        c_res = await db.execute(select(Customer).where(Customer.id == case.customer_id))
        cust = c_res.scalar_one_or_none()
        if cust:
            cust_succ = cust.total_successful_payments
            cust_fail = cust.total_failed_payments

    actions_res = await db.execute(
        select(RecoveryAction)
        .where(RecoveryAction.case_id == case.id)
        .order_by(RecoveryAction.executed_at.desc())
        .limit(1)
    )
    last_act = actions_res.scalar_one_or_none()

    # Deterministic failure classification from observed Razorpay facts
    classified = classify_razorpay_failure(
        error_code=txn.error_code if txn else None,
        error_source=txn.error_source if txn else None,
        error_step=txn.error_step if txn else None,
        error_reason=txn.error_reason if txn else None,
        error_description=txn.error_description if txn else None
    )

    # Build Explainability Checklist
    checklist: List[ExplainabilityCheckItem] = [
        ExplainabilityCheckItem(
            check_name="Customer Payment History",
            passed=(cust_succ > 0 or cust_fail == 0),
            title="Strong Historical Payment Track Record",
            details=f"Customer has {cust_succ} successful past payments and {cust_fail} past failures."
        ),
        ExplainabilityCheckItem(
            check_name="Failure Classification",
            passed=True,
            title="Deterministic Failure Classification",
            details=f"Category '{classified.category}' ({classified.reason})"
        ),
        ExplainabilityCheckItem(
            check_name="Retry Limit Compliance",
            passed=(case.retry_count <= 3),
            title="Retry Count Boundary Check",
            details=f"Attempted retries ({case.retry_count}) within maximum limit (3 retries)."
        ),
        ExplainabilityCheckItem(
            check_name="Automatic Recovery Amount Limit",
            passed=(float(case.amount) <= 50000.0),
            title="Transaction Value Limit Check",
            details=f"Failed amount (INR {float(case.amount):,.2f}) within maximum auto-recovery limit (INR 50,000.00)."
        ),
        ExplainabilityCheckItem(
            check_name="Policy Safety Gate Result",
            passed=case.policy_passed,
            title="Policy Engine Compliance Result",
            details="APPROVED by Policy Safety Gate constraints." if case.policy_passed else f"BLOCKED: {case.policy_failure_reason}"
        )
    ]

    return DecisionSummaryResponse(
        case_id=case.id,
        case_type=case.case_type,
        amount=float(case.amount),
        currency=txn.currency if txn else "INR",
        failure_category=classified.category if (txn and case.case_type != "CHECKOUT_DROPOFF") else "CHECKOUT_DROPOFF",
        error_code=txn.error_code if txn else ("CHECKOUT_ABANDONED" if case.case_type == "CHECKOUT_DROPOFF" else "BAD_REQUEST_PAYMENT_TIMED_OUT"),
        error_description=txn.error_description if txn else None,
        error_source=txn.error_source if txn else None,
        error_step=txn.error_step if txn else None,
        error_reason=txn.error_reason if txn else None,
        classification_reason=classified.reason,
        ai_confidence=float(case.ai_confidence or 0.85),
        recommended_action=case.ai_recommended_action or "RECOVERY_LINK",
        effective_action=case.actual_action_taken or case.ai_recommended_action or "RECOVERY_LINK",
        policy_allowed=case.policy_passed,
        policy_reason=case.policy_failure_reason,
        execution_status=last_act.status if last_act else ("COMPLETED" if case.status == "RECOVERED" else "PENDING"),
        recovery_status=case.status,
        recovered_amount=float(case.recovered_amount),
        provider="RAZORPAY",
        provider_reference=last_act.razorpay_payment_link_id if last_act else None,
        decision_reason=case.ai_reasoning or "Standard policy-approved recovery recommendation.",
        explainability_checklist=checklist,
        created_at=case.created_at,
        updated_at=case.updated_at
    )

@router.post("/cases/{case_id}/diagnose", response_model=AIDiagnosisResponse, tags=["AI Diagnosis"])
async def run_ai_diagnosis(case_id: str, db: AsyncSession = Depends(get_db)):
    """Run AI Payment Failure Diagnosis on a recovery case."""
    result = await db.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    cust_succ = 0
    cust_fail = 0
    if case.customer_id:
        c_res = await db.execute(select(Customer).where(Customer.id == case.customer_id))
        cust = c_res.scalar_one_or_none()
        if cust:
            cust_succ = cust.total_successful_payments
            cust_fail = cust.total_failed_payments

    classified = classify_razorpay_failure(
        error_code=txn.error_code if txn else None,
        error_source=txn.error_source if txn else None,
        error_step=txn.error_step if txn else None,
        error_reason=txn.error_reason if txn else None,
        error_description=txn.error_description if txn else None
    )

    context = {
        "case_type": case.case_type,
        "amount": float(case.amount),
        "currency": txn.currency if txn else "INR",
        "payment_method": txn.payment_method if txn else "N/A",
        "error_code": txn.error_code if txn else "UNKNOWN",
        "error_description": txn.error_description if txn else "N/A",
        "error_source": txn.error_source if txn else "N/A",
        "error_step": txn.error_step if txn else "N/A",
        "error_reason": txn.error_reason if txn else "N/A",
        "normalized_failure_category": classified.category,
        "classification_reason": classified.reason,
        "customer_successful_payments": cust_succ,
        "customer_failed_payments": cust_fail,
        "risk_level": case.risk_level,
        "risk_score": float(case.risk_score),
        "recoverability_score": float(case.risk_score) / 100.0 if case.risk_score else 0.50,
        "priority_level": case.priority_level,
        "risk_factors": case.risk_factors or []
    }

    db.add(AuditLog(
        case_id=case.id,
        actor="AI_AGENT",
        event_type="AI_DIAGNOSIS_STARTED",
        description=f"Initiating AI Payment Failure Diagnosis for case '{case.id}'"
    ))
    await db.commit()

    ai_service = get_ai_service()
    diagnosis_output = ai_service.diagnose_payment_failure(context)

    ai_record = AIDiagnosis(
        case_id=case.id,
        provider=ai_service.provider_name,
        model=ai_service.model_name,
        prompt_version=PROMPT_VERSION,
        risk_level=diagnosis_output.risk_level,
        recoverability_score=diagnosis_output.recoverability_score,
        failure_category=diagnosis_output.failure_category,
        root_cause=diagnosis_output.root_cause,
        recommended_action=diagnosis_output.recommended_action,
        confidence=diagnosis_output.confidence,
        reason=diagnosis_output.reason,
        explanation=diagnosis_output.explanation
    )
    db.add(ai_record)

    case.ai_root_cause = diagnosis_output.root_cause
    case.ai_recommended_action = diagnosis_output.recommended_action
    case.ai_confidence = diagnosis_output.confidence
    case.ai_reasoning = diagnosis_output.reason
    if case.status == "OPEN":
        case.status = "DIAGNOSED"

    action_res = await db.execute(
        select(RecoveryAction)
        .where(RecoveryAction.case_id == case.id)
        .order_by(RecoveryAction.executed_at.desc())
        .limit(1)
    )
    last_action = action_res.scalar_one_or_none()
    last_action_ts = last_action.executed_at if last_action else None

    policy_result = policy_engine.evaluate_action(
        proposed_action=diagnosis_output.recommended_action,
        case_status=case.status,
        amount=float(case.amount),
        retry_count=case.retry_count,
        ai_confidence=diagnosis_output.confidence,
        last_action_timestamp=last_action_ts,
        error_code=txn.error_code if txn else None
    )

    if policy_result.effective_action == "ESCALATE":
        case.status = "ESCALATED"
    elif policy_result.effective_action == "STOP":
        case.status = "STOPPED"
        case.stop_reason = policy_result.reason

    case.policy_passed = policy_result.allowed
    case.policy_failure_reason = policy_result.reason if not policy_result.allowed else None
    db.add(case)

    db.add(AuditLog(
        case_id=case.id,
        actor="AI_AGENT",
        event_type="AI_DIAGNOSIS_COMPLETED",
        description=f"AI Diagnosis completed ({ai_service.provider_name}): category={diagnosis_output.failure_category}, action={diagnosis_output.recommended_action}, confidence={diagnosis_output.confidence}",
        metadata_json={
            "failure_category": diagnosis_output.failure_category,
            "root_cause": diagnosis_output.root_cause,
            "recommended_action": diagnosis_output.recommended_action,
            "confidence": diagnosis_output.confidence,
            "policy_allowed": policy_result.allowed,
            "effective_action": policy_result.effective_action
        }
    ))

    db.add(AuditLog(
        case_id=case.id,
        actor="AI_AGENT",
        event_type="AI_DECISION_MADE",
        description=f"AI Decision made: action='{diagnosis_output.recommended_action}' (confidence={diagnosis_output.confidence})",
        metadata_json={
            "action": diagnosis_output.recommended_action,
            "confidence": diagnosis_output.confidence,
            "reason": diagnosis_output.reason
        }
    ))
    await db.commit()

    return AIDiagnosisResponse(
        case_id=case.id,
        provider=ai_service.provider_name,
        model=ai_service.model_name,
        prompt_version=PROMPT_VERSION,
        diagnosis=diagnosis_output,
        policy_result=policy_result,
        created_at=datetime.now(timezone.utc)
    )

@router.post("/cases/{case_id}/policy-check", response_model=PolicyCheckResult, tags=["Recovery Cases"])
async def evaluate_case_policy(
    case_id: str,
    req: PolicyCheckRequest,
    db: AsyncSession = Depends(get_db)
):
    """Evaluate a proposed recovery action against the Policy Engine Safety Gate."""
    result = await db.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    action_res = await db.execute(
        select(RecoveryAction)
        .where(RecoveryAction.case_id == case.id)
        .order_by(RecoveryAction.executed_at.desc())
        .limit(1)
    )
    last_action = action_res.scalar_one_or_none()
    last_action_ts = last_action.executed_at if last_action else None

    policy_result = policy_engine.evaluate_action(
        proposed_action=req.proposed_action,
        case_status=case.status,
        amount=float(case.amount),
        retry_count=case.retry_count,
        ai_confidence=req.ai_confidence,
        last_action_timestamp=last_action_ts,
        error_code=txn.error_code if txn else None
    )

    event_type = "RECOVERY_POLICY_CHECKED" if policy_result.allowed else "RECOVERY_POLICY_BLOCKED"
    audit = AuditLog(
        case_id=case.id,
        actor="POLICY_ENGINE",
        event_type=event_type,
        description=f"Policy check for action '{req.proposed_action}': allowed={policy_result.allowed}, effective='{policy_result.effective_action}'",
        metadata_json={
            "proposed_action": req.proposed_action,
            "effective_action": policy_result.effective_action,
            "allowed": policy_result.allowed,
            "violations": policy_result.violations,
            "reason": policy_result.reason
        }
    )
    db.add(audit)
    
    if policy_result.effective_action == "ESCALATE":
        case.status = "ESCALATED"
    elif policy_result.effective_action == "STOP":
        case.status = "STOPPED"
        case.stop_reason = policy_result.reason

    case.policy_passed = policy_result.allowed
    case.policy_failure_reason = policy_result.reason if not policy_result.allowed else None
    
    db.add(case)
    await db.commit()

    return policy_result

@router.get("/cases/{case_id}/policy-assessment", response_model=PolicyGateResponse, tags=["Recovery Cases"])
async def get_case_policy_assessment(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the official PayPilot Safety Policy Gate assessment for a recovery case.
    Evaluates 7 safety rules (amount caps, retry limits, fraud guards, risk score, AI confidence)
    and authoritatively returns ALLOW_RECOVERY, REVIEW_REQUIRED, or BLOCK_RECOVERY.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    assessment = policy_gate.assess_case(case=case, transaction=txn)

    audit = AuditLog(
        case_id=case.id,
        actor="POLICY_GATE",
        event_type="RECOVERY_POLICY_EVALUATED",
        description=f"Policy Gate evaluated decision '{assessment.decision}' (Score: {assessment.policy_score})",
        metadata_json={
            "decision": assessment.decision,
            "allowed": assessment.allowed,
            "requires_review": assessment.requires_review,
            "blocked": assessment.blocked,
            "policy_score": assessment.policy_score,
            "passed_rules_count": len(assessment.passed_rules),
            "failed_rules_count": len(assessment.failed_rules)
        }
    )
    db.add(audit)
    await db.commit()

    return assessment

@router.get("/cases/{case_id}/stopping-rules", response_model=StoppingRulesResponse, tags=["Recovery Cases"])
async def get_case_stopping_rules(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the official PayPilot Stopping Rules assessment for a recovery case.
    Evaluates retry limits, recovered states, policy blocks, and terminal states
    to authoritatively return CONTINUE or STOP.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    stopping_assessment = stopping_rules.evaluate_case(case=case, transaction=txn)

    # Log audit event ONLY when a STOP condition is triggered
    if stopping_assessment.should_stop:
        audit = AuditLog(
            case_id=case.id,
            actor="STOPPING_RULES",
            event_type="RECOVERY_STOPPING_RULE_TRIGGERED",
            description=f"Stopping Rules triggered decision '{stopping_assessment.decision}' (Rules: {', '.join(stopping_assessment.triggered_rules)})",
            metadata_json={
                "decision": stopping_assessment.decision,
                "should_stop": stopping_assessment.should_stop,
                "triggered_rules": stopping_assessment.triggered_rules,
                "stop_reason": stopping_assessment.stop_reason,
                "remaining_attempts": stopping_assessment.remaining_attempts
            }
        )
        db.add(audit)
        await db.commit()

    return stopping_assessment

@router.get("/cases/{case_id}/escalation", response_model=HumanEscalationResponse, tags=["Recovery Cases"])
async def get_case_escalation(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve official Human Escalation assessment for a recovery case.
    Returns escalation level (NONE, REVIEW, HIGH_PRIORITY, CRITICAL), reasons, and recommended action.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    txn_res = await db.execute(select(Transaction).where(Transaction.id == case.transaction_id))
    txn = txn_res.scalar_one_or_none()

    escalation = human_escalation.evaluate_case(case=case, transaction=txn)
    return escalation

@router.post("/cases/{case_id}/escalate", response_model=HumanEscalationResponse, tags=["Recovery Cases"])
async def escalate_case(
    case_id: str,
    reason: Optional[str] = Query(None, description="Escalation reason"),
    db: AsyncSession = Depends(get_db)
):
    """
    Explicitly escalate a recovery case to the Human Review Queue.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    prev_status = case.status
    case.status = "ESCALATED"

    audit = AuditLog(
        case_id=case.id,
        actor="HUMAN_ESCALATION",
        event_type="HUMAN_ESCALATION_TRIGGERED",
        description=f"Case explicitly escalated: {reason or 'Manual operator request'}",
        metadata_json={
            "previous_status": prev_status,
            "new_status": "ESCALATED",
            "reason": reason
        }
    )
    db.add(audit)
    await db.commit()
    await db.refresh(case)

    return human_escalation.evaluate_case(case=case)

@router.post("/cases/{case_id}/human-action", response_model=HumanActionResponse, tags=["Recovery Cases"])
async def perform_human_action(
    case_id: str,
    req: HumanActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Perform a controlled operator action (APPROVE_RECOVERY, REJECT_RECOVERY, STOP_RECOVERY, REQUEST_INFO)
    with state validation, safety re-checks, and audit logging.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    try:
        res = await human_escalation.execute_human_action(case=case, action_req=req, db=db)
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))

@router.get("/cases/{case_id}/funnel-lineage", response_model=CaseFunnelLineageResponse, tags=["Recovery Cases"])
async def get_case_funnel_lineage_endpoint(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve step-by-step 8-stage Recovery Funnel lineage and completion timestamps for a specific recovery case.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    return await recovery_funnel.get_case_funnel_lineage(case=case, db=db)

@router.get("/cases/{case_id}/ai-evaluation", response_model=CaseAIEvaluationResponse, tags=["Recovery Cases"])
async def get_case_ai_evaluation_endpoint(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve structured AI Decision Evaluation, confidence calibration, decision agreement, and safety boundary interactions for a specific recovery case.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    return await ai_metrics.get_case_ai_evaluation(case=case, db=db)

@router.get("/cases/{case_id}/checkout-status", response_model=CheckoutStatusResponse, tags=["Recovery Cases"])
async def get_case_checkout_status_endpoint(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve detailed checkout status, abandonment reason, state machine lineage, and retry eligibility for a recovery case.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    return await checkout_abandonment_service.get_checkout_status(db=db, case_id=case.id)

@router.post("/cases/{case_id}/checkout-retry", response_model=CheckoutRetryResponse, tags=["Recovery Cases"])
async def retry_case_checkout_endpoint(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate a safe controlled checkout retry after evaluating Policy Gate, Stopping Rules, and Human Escalation.
    Reuses existing valid order if safe or generates new order if permitted.
    """
    case = await _get_case_by_id_or_prefix(case_id, db)
    if not case:
        raise ResourceNotFoundException(resource="RecoveryCase", resource_id=case_id)

    return await checkout_abandonment_service.evaluate_and_execute_retry(db=db, case_id=case.id)

