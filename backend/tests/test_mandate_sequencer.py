import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.receivables_and_mandates import Mandate, MandateRetryAttempt
from app.models.audit_log import AuditLog
from app.services.revenue_risk.mandate_service import mandate_retry_sequencer_service, MAX_MANDATE_RETRIES

@pytest.mark.asyncio
async def test_mandate_retry_sequencing_and_stopping_rules(db_session: AsyncSession):
    """TEST 1 & 4: Mandate failure -> RETRYING -> Max attempts (3) -> ESCALATED."""
    m = Merchant(name="Mandate Merchant", email="mandate@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session,
        merchant_id=m.id,
        mandate_number="MND-9901",
        amount=12500.0,
        billing_interval="monthly"
    )
    assert mandate.status == "ACTIVE"

    # Attempt 1 -> RETRYING
    m1, c1 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db_session, mandate.id)
    assert m1.attempt_count == 1
    assert m1.status == "RETRYING"
    assert c1.case_type == "MANDATE_RETRY"

    # Attempt 2 -> RETRYING
    m2, c2 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db_session, mandate.id)
    assert m2.attempt_count == 2
    assert m2.status == "RETRYING"

    # Attempt 3 -> Exceeds MAX_MANDATE_RETRIES (3) -> ESCALATED
    m3, c3 = await mandate_retry_sequencer_service.process_failed_mandate_attempt(db_session, mandate.id)
    assert m3.attempt_count == 3
    assert m3.status == "ESCALATED"
    assert c3.status == "ESCALATED"


@pytest.mark.asyncio
async def test_mandate_retry_succeeds(db_session: AsyncSession):
    """TEST 2: Retry executes -> Razorpay payment succeeds -> RECOVERED sequence stops."""
    m = Merchant(name="Mandate Merchant 2", email="m2@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9902", amount=5000.0
    )
    await mandate_retry_sequencer_service.process_failed_mandate_attempt(db_session, mandate.id)

    m_exec, attempt, res = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db_session, mandate_id=mandate.id, simulate_success=True
    )
    assert m_exec.status == "RECOVERED"
    assert attempt.status == "SUCCEEDED"
    assert attempt.provider_payment_id is not None
    assert res["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_mandate_retry_fails_next_scheduled(db_session: AsyncSession):
    """TEST 3: Retry fails -> provider error logged -> next retry scheduled."""
    m = Merchant(name="Mandate Merchant 3", email="m3@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9903", amount=3000.0
    )
    await mandate_retry_sequencer_service.process_failed_mandate_attempt(db_session, mandate.id)

    m_exec, attempt, res = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db_session, mandate_id=mandate.id, simulate_success=False
    )
    assert attempt.status == "FAILED"
    assert res["status"] == "FAILED"
    assert m_exec.attempt_count == 2
    assert m_exec.status == "RETRYING"


@pytest.mark.asyncio
async def test_mandate_non_retryable_failure(db_session: AsyncSession):
    """TEST 5: Non-retryable failure (ACCOUNT_CLOSED) -> STOPPED/CANCELLED immediately."""
    m = Merchant(name="Mandate Merchant 5", email="m5@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9905", amount=7500.0
    )
    m_proc, case = await mandate_retry_sequencer_service.process_failed_mandate_attempt(
        db=db_session, mandate_id=mandate.id, failure_reason="Bank error: ACCOUNT_CLOSED by user"
    )
    assert m_proc.status == "CANCELLED"
    assert m_proc.next_retry_date is None


@pytest.mark.asyncio
async def test_mandate_policy_gate_blocks(db_session: AsyncSession):
    """TEST 6: Policy Gate blocks retry on terminal mandate state."""
    m = Merchant(name="Mandate Merchant 6", email="m6@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9906", amount=4000.0
    )
    mandate.status = "RECOVERED"
    db_session.add(mandate)
    await db_session.commit()

    m_exec, attempt, res = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db_session, mandate_id=mandate.id, simulate_success=True
    )
    assert attempt.status == "BLOCKED"
    assert res["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_mandate_human_escalation(db_session: AsyncSession):
    """TEST 7: Human escalation -> ESCALATED -> no further automatic retry."""
    m = Merchant(name="Mandate Merchant 7", email="m7@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9907", amount=15000.0
    )
    m_esc = await mandate_retry_sequencer_service.escalate_mandate(
        db=db_session, mandate_id=mandate.id, reason="Customer requested dispute review"
    )
    assert m_esc.status == "ESCALATED"
    assert m_esc.escalation_reason == "Customer requested dispute review"

    # Execution attempt while escalated should be blocked
    m_exec, attempt, res = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db_session, mandate_id=mandate.id, simulate_success=True
    )
    assert attempt.status == "BLOCKED"


@pytest.mark.asyncio
async def test_mandate_idempotency_duplicate_request(db_session: AsyncSession):
    """TEST 8: Duplicate retry request with same idempotency key -> returns existing attempt."""
    m = Merchant(name="Mandate Merchant 8", email="m8@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9908", amount=2500.0
    )
    key = "idem_key_unique_test_888"

    m1, att1, res1 = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db_session, mandate_id=mandate.id, idempotency_key=key, simulate_success=True
    )
    assert res1["status"] == "SUCCEEDED"

    m2, att2, res2 = await mandate_retry_sequencer_service.execute_mandate_retry(
        db=db_session, mandate_id=mandate.id, idempotency_key=key, simulate_success=True
    )
    assert res2["status"] == "IDEMPOTENT_SKIPPED"
    assert att2.id == att1.id


@pytest.mark.asyncio
async def test_mandate_audit_trail(db_session: AsyncSession):
    """TEST 12: Audit trail created for state-changing actions."""
    m = Merchant(name="Mandate Merchant 12", email="m12@merchant.com")
    db_session.add(m)
    await db_session.commit()

    mandate = await mandate_retry_sequencer_service.create_mandate(
        db=db_session, merchant_id=m.id, mandate_number="MND-9912", amount=6000.0
    )
    await mandate_retry_sequencer_service.process_failed_mandate_attempt(db_session, mandate.id)

    audits = (await db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "MANDATE_RETRY_SCHEDULED")
    )).scalars().all()
    assert len(audits) >= 1
    assert audits[0].event_type == "MANDATE_RETRY_SCHEDULED"

