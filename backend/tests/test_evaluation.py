import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.evaluation.dataset import dataset_generator, SyntheticDatasetGenerator
from app.services.evaluation.ground_truth import ground_truth_policy
from app.services.evaluation.metrics import metrics_calculator, MetricSummary
from app.services.evaluation.evaluator import evaluation_engine
from app.models.evaluation_run import EvaluationRun
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase

def test_same_seed_produces_same_dataset():
    ds1 = dataset_generator.generate_dataset(dataset_size=100, seed=42)
    ds2 = dataset_generator.generate_dataset(dataset_size=100, seed=42)

    assert len(ds1) == 100
    assert len(ds2) == 100
    assert ds1[0]["case_id"] == ds2[0]["case_id"]
    assert ds1[0]["amount"] == ds2[0]["amount"]
    assert ds1[50]["failure_reason"] == ds2[50]["failure_reason"]

def test_different_seed_produces_different_dataset():
    ds1 = dataset_generator.generate_dataset(dataset_size=100, seed=42)
    ds2 = dataset_generator.generate_dataset(dataset_size=100, seed=99)

    assert ds1[0]["case_id"] != ds2[0]["case_id"]
    assert ds1[0]["amount"] != ds2[0]["amount"] or ds1[1]["amount"] != ds2[1]["amount"]

def test_configurable_dataset_sizes():
    for sz in [100, 500, 1000]:
        ds = dataset_generator.generate_dataset(dataset_size=sz, seed=42)
        assert len(ds) == sz

def test_ground_truth_policy_deterministic():
    case_fraud = {"failure_reason": "SUSPECTED_FRAUD", "amount": 1000.0, "retry_count": 0, "previous_success_count": 5}
    cat, act, prob = ground_truth_policy.evaluate_ground_truth(case_fraud)
    assert cat == "REQUIRES_HUMAN_REVIEW"
    assert act == "ESCALATE"

    case_timeout = {"failure_reason": "BAD_REQUEST_PAYMENT_TIMED_OUT", "amount": 2500.0, "retry_count": 0, "previous_success_count": 3}
    cat2, act2, prob2 = ground_truth_policy.evaluate_ground_truth(case_timeout)
    assert cat2 == "RECOVERABLE"
    assert act2 == "RETRY"
    assert prob2 >= 0.80

def test_metrics_math_and_zero_division_safety():
    empty_summary = metrics_calculator.calculate_metrics([])
    assert empty_summary.total_cases == 0
    assert empty_summary.precision == 0.0
    assert empty_summary.recall == 0.0

    dummy_cases = [
        {
            "amount": 1000.0,
            "expected_recoverable": True,
            "effective_action": "RECOVERY_LINK",
            "policy_allowed": True,
            "final_status": "RECOVERED",
            "recovered_amount": 1000.0,
            "ground_truth_action": "RECOVERY_LINK"
        },
        {
            "amount": 2000.0,
            "expected_recoverable": False,
            "effective_action": "STOP",
            "policy_allowed": True,
            "final_status": "STOPPED",
            "recovered_amount": 0.0,
            "ground_truth_action": "STOP"
        }
    ]
    summary = metrics_calculator.calculate_metrics(dummy_cases)
    assert summary.total_cases == 2
    assert summary.total_revenue_at_risk == 3000.0
    assert summary.recoverable_cases == 1
    assert summary.revenue_recovered == 1000.0
    assert summary.precision == 100.0
    assert summary.recall == 100.0
    assert summary.unsafe_action_count == 0

@pytest.mark.asyncio
async def test_evaluation_run_endpoint_and_db_isolation(async_client: AsyncClient, db_session: AsyncSession):
    # Count real Transactions & RecoveryCases before run
    tx_count_before = (await db_session.execute(select(func.count(Transaction.id)))).scalar()
    case_count_before = (await db_session.execute(select(func.count(RecoveryCase.id)))).scalar()

    # Trigger evaluation run via API
    payload = {"dataset_size": 100, "seed": 42, "mode": "deterministic"}
    res = await async_client.post("/api/v1/evaluation/run", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["dataset_size"] == 100
    assert data["seed"] == 42
    assert data["mode"] == "deterministic"
    assert data["revenue_at_risk"] > 0
    assert data["revenue_recovered"] >= 0
    assert data["unsafe_action_count"] == 0

    run_id = data["run_id"]

    # Verify real DB isolation (no fake production transactions created)
    tx_count_after = (await db_session.execute(select(func.count(Transaction.id)))).scalar()
    case_count_after = (await db_session.execute(select(func.count(RecoveryCase.id)))).scalar()
    assert tx_count_after == tx_count_before
    assert case_count_after == case_count_before

    # Test GET summary endpoint
    res_sum = await async_client.get("/api/v1/evaluation/summary")
    assert res_sum.status_code == 200
    assert res_sum.json()["run_id"] == run_id

    # Test GET run cases endpoint
    res_cases = await async_client.get(f"/api/v1/evaluation/runs/{run_id}/cases")
    assert res_cases.status_code == 200
    cases = res_cases.json()
    assert len(cases) == 100

    # Test CSV export endpoint
    res_csv = await async_client.get(f"/api/v1/evaluation/runs/{run_id}/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Case ID,Amount (INR)" in res_csv.text
