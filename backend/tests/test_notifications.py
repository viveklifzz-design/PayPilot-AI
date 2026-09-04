import pytest
from app.models.recovery_case import RecoveryCase
from app.models.notification import Notification
from app.services.notification_service import notification_service

@pytest.mark.asyncio
async def test_create_notification(db_session):
    n = await notification_service.create_notification(
        db_session,
        type="PAYMENT_FAILED",
        severity="WARNING",
        title="Test Failure Notification",
        message="A test payment failure occurred.",
        case_id="c_notif_001"
    )
    assert n.id is not None
    assert n.type == "PAYMENT_FAILED"
    assert n.severity == "WARNING"
    assert n.is_read is False

@pytest.mark.asyncio
async def test_notification_idempotency(db_session):
    n1 = await notification_service.create_notification(
        db_session,
        type="HUMAN_REVIEW_REQUIRED",
        severity="WARNING",
        title="Escalated Case",
        message="Case requires review",
        case_id="c_notif_idem_01"
    )
    n2 = await notification_service.create_notification(
        db_session,
        type="HUMAN_REVIEW_REQUIRED",
        severity="WARNING",
        title="Escalated Case",
        message="Case requires review",
        case_id="c_notif_idem_01"
    )
    assert n1.id == n2.id

@pytest.mark.asyncio
async def test_false_success_protection(db_session):
    # Unrecovered case should block PAYMENT_RECOVERED type and fallback to PAYMENT_VERIFICATION_PENDING
    case = RecoveryCase(id="c_unrec_notif_99", merchant_id="m_test", amount=20.0, risk_level="LOW", status="OPEN")
    db_session.add(case)
    await db_session.commit()

    n = await notification_service.create_notification(
        db_session,
        type="PAYMENT_RECOVERED",
        severity="SUCCESS",
        title="Payment Recovered",
        message="Fake success attempt",
        case_id="c_unrec_notif_99"
    )
    assert n.type == "PAYMENT_VERIFICATION_PENDING"
    assert n.severity == "WARNING"

@pytest.mark.asyncio
async def test_count_unread_and_mark_read(db_session):
    n = await notification_service.create_notification(
        db_session,
        type="RECOVERY_ELIGIBLE",
        severity="INFO",
        title="Eligible for Recovery",
        message="Case is eligible",
        case_id="c_notif_read_01"
    )
    count_before = await notification_service.count_unread(db_session)
    assert count_before >= 1

    ok = await notification_service.mark_as_read(db_session, n.id)
    assert ok is True

    count_after = await notification_service.count_unread(db_session)
    assert count_after == count_before - 1

@pytest.mark.asyncio
async def test_mark_all_read(db_session):
    await notification_service.create_notification(
        db_session, type="AI_DIAGNOSED", severity="INFO", title="T1", message="M1", case_id="c_all_01"
    )
    await notification_service.create_notification(
        db_session, type="RECOVERY_STARTED", severity="INFO", title="T2", message="M2", case_id="c_all_02"
    )
    marked = await notification_service.mark_all_as_read(db_session)
    assert marked >= 2

    unread = await notification_service.count_unread(db_session)
    assert unread == 0

@pytest.mark.asyncio
async def test_authoritative_case_notifications(db_session):
    auth_cid = "d669dce3-b855-4348-b457-f0ef7c34b6b1"
    # Create or update authoritative case as RECOVERED in test DB fixture session
    case = await db_session.get(RecoveryCase, auth_cid)
    if not case:
        case = RecoveryCase(id=auth_cid, merchant_id="m_live_001", amount=10.0, recovered_amount=10.0, risk_level="LOW", status="RECOVERED")
        db_session.add(case)
        await db_session.commit()

    n = await notification_service.create_notification(
        db_session,
        type="PAYMENT_RECOVERED",
        severity="SUCCESS",
        title="Verified Recovery",
        message="Authoritative case recovered",
        case_id=auth_cid
    )
    assert n.type == "PAYMENT_RECOVERED"
    assert n.severity == "SUCCESS"

@pytest.mark.asyncio
async def test_endpoint_get_notifications(async_client, db_session):
    await notification_service.create_notification(
        db_session, type="CHECKOUT_STARTED", severity="INFO", title="Checkout", message="Started", case_id="c_ep_n_01"
    )
    res = await async_client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1

@pytest.mark.asyncio
async def test_endpoint_unread_count(async_client):
    res = await async_client.get("/api/v1/notifications/unread-count")
    assert res.status_code == 200
    data = res.json()
    assert "unread_count" in data

@pytest.mark.asyncio
async def test_endpoint_mark_read(async_client, db_session):
    n = await notification_service.create_notification(
        db_session, type="RETRY_AVAILABLE", severity="INFO", title="Retry", message="Available", case_id="c_ep_n_02"
    )
    res = await async_client.post(f"/api/v1/notifications/{n.id}/read")
    assert res.status_code == 200
    data = res.json()
    assert data["is_read"] is True

@pytest.mark.asyncio
async def test_endpoint_mark_all_read(async_client):
    res = await async_client.post("/api/v1/notifications/read-all")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

@pytest.mark.asyncio
async def test_step_1_ai_decision_regression():
    from app.services.recovery.ai_decision_service import ai_decision_service
    case = RecoveryCase(id="c_reg_s1_n", merchant_id="m_test", amount=10.0, risk_level="LOW", status="OPEN")
    eval_res = ai_decision_service.assess_case(case)
    assert eval_res.case_id == "c_reg_s1_n"

@pytest.mark.asyncio
async def test_step_2_policy_gate_regression():
    from app.services.recovery.policy_gate import policy_gate
    case = RecoveryCase(id="c_reg_s2_n", merchant_id="m_test", amount=10.0, risk_score=10.0, risk_level="LOW", status="OPEN")
    pol = policy_gate.assess_case(case)
    assert pol.decision in ["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]

@pytest.mark.asyncio
async def test_step_3_stopping_rules_regression():
    from app.services.recovery.stopping_rules import stopping_rules
    case = RecoveryCase(id="c_reg_s3_n", merchant_id="m_test", amount=10.0, retry_count=0, risk_level="LOW", status="OPEN")
    stp = stopping_rules.evaluate_case(case)
    assert stp.decision in ["CONTINUE", "STOP"]

@pytest.mark.asyncio
async def test_step_4_human_escalation_regression():
    from app.services.recovery.human_escalation import human_escalation
    case = RecoveryCase(id="c_reg_s4_n", merchant_id="m_test", amount=10.0, risk_level="LOW", status="ESCALATED")
    esc = human_escalation.evaluate_case(case)
    assert esc.should_escalate is True

@pytest.mark.asyncio
async def test_step_7_failure_fallback_regression(db_session):
    from app.services.recovery.failure_fallback import failure_fallback, SimulateFailureRequest
    req = SimulateFailureRequest(scenario_key="RAZORPAY_ORDER_FAILURE")
    f_res = await failure_fallback.simulate_failure(req, db_session)
    assert f_res.case_state_preserved == "OPEN"
