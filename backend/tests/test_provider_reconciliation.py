import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import select, func

from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.merchant import Merchant
from app.services.recovery.reconciliation_service import reconciliation_service
from app.core.exceptions import ValidationException, PaymentGatewayException

@pytest.mark.asyncio
async def test_successful_provider_reconciliation(db_session):
    # Setup test merchant & failed transaction & recovery case
    merchant = Merchant(name="Recon Test Merchant", email="merchant1@test.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_test_failed_rec_01",
        razorpay_order_id="order_test_rec_01",
        amount=10.0,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_ERROR"
    )
    db_session.add(txn)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=10.0,
        risk_level="MEDIUM",
        status="RECOVERING",
        recovered_amount=0.0
    )
    db_session.add(case)
    await db_session.commit()

    mock_payment = {
        "id": "pay_test_success_rec_01",
        "entity": "payment",
        "amount": 1000,
        "currency": "INR",
        "status": "captured",
        "captured": True,
        "order_id": "order_test_rec_01",
        "method": "netbanking",
        "notes": {"original_payment_id": "pay_test_failed_rec_01"}
    }

    mock_order_res = MagicMock()
    mock_order_res.status_code = 200
    mock_order_res.json.return_value = {
        "id": "order_test_rec_01",
        "amount": 1000,
        "amount_paid": 1000,
        "amount_due": 0,
        "currency": "INR",
        "status": "paid"
    }

    with patch("app.services.razorpay.razorpay_service.fetch_payment", return_value=mock_payment), \
         patch("requests.get", return_value=mock_order_res):

        # First Reconciliation Pass
        res1 = await reconciliation_service.reconcile_provider_recovery(
            payment_id="pay_test_success_rec_01",
            order_id="order_test_rec_01",
            db=db_session,
            verification_source="TEST_SUITE"
        )
        assert res1["reconciled"] is True
        assert res1["already_recovered"] is False
        assert res1["recovered_amount"] == 10.0

        # Reload case
        await db_session.refresh(case)
        assert case.status == "RECOVERED"
        assert float(case.recovered_amount) == 10.0

        # Idempotent Second Pass
        res2 = await reconciliation_service.reconcile_provider_recovery(
            payment_id="pay_test_success_rec_01",
            order_id="order_test_rec_01",
            db=db_session,
            verification_source="TEST_SUITE"
        )
        assert res2["reconciled"] is True
        assert res2["already_recovered"] is True
        assert res2["recovered_amount"] == 10.0

@pytest.mark.asyncio
async def test_reconciliation_amount_mismatch_rejection(db_session):
    merchant = Merchant(name="Recon Mismatch Merchant", email="mismatch@test.com")
    db_session.add(merchant)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        amount=10.0,
        risk_level="MEDIUM",
        status="RECOVERING",
        recovered_amount=0.0
    )
    db_session.add(case)
    await db_session.commit()

    # Mismatched payment amount (500 paise != 1000 paise)
    mock_payment = {
        "id": "pay_mismatch_amt",
        "amount": 500,
        "currency": "INR",
        "status": "captured",
        "captured": True,
        "order_id": "order_mismatch_amt"
    }
    mock_order_res = MagicMock()
    mock_order_res.status_code = 200
    mock_order_res.json.return_value = {
        "id": "order_mismatch_amt",
        "amount": 500,
        "amount_paid": 500,
        "amount_due": 0,
        "status": "paid"
    }

    with patch("app.services.razorpay.razorpay_service.fetch_payment", return_value=mock_payment), \
         patch("requests.get", return_value=mock_order_res):

        with pytest.raises(ValidationException) as exc_info:
            await reconciliation_service.reconcile_provider_recovery(
                payment_id="pay_mismatch_amt",
                order_id="order_mismatch_amt",
                db=db_session
            )
        assert "payment.amount is 500" in str(exc_info.value)
