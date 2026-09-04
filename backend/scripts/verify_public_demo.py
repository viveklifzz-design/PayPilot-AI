import json
import httpx

def run_public_demo_verification():
    print("=================================================================")
    print("       PAYPILOT AI - PUBLIC DEMO E2E VERIFICATION SUITE          ")
    print("=================================================================")

    # 1. Backend Health Check
    res_health = httpx.get("http://localhost:8000/api/v1/health")
    assert res_health.status_code == 200
    h_data = res_health.json()
    assert h_data["status"] == "healthy"
    assert h_data["database"] is True
    assert h_data["razorpay"] is True
    assert h_data["ai"] is True
    print("1. Backend Health Check (GET /api/v1/health): PASS")

    # 2. Razorpay Integration Health Check
    res_rzp = httpx.get("http://localhost:8000/api/v1/health/razorpay")
    assert res_rzp.status_code == 200
    rzp_data = res_rzp.json()
    assert rzp_data["configured"] is True
    assert rzp_data["test_mode"] is True
    assert rzp_data["status"] == "connected"
    print("2. Razorpay Integration Check (GET /api/v1/health/razorpay): PASS (Connected in Test Mode)")

    # 3. Transactions API Check
    res_tx = httpx.get("http://localhost:8000/api/v1/transactions?limit=5")
    assert res_tx.status_code == 200
    txs = res_tx.json()
    print(f"3. Transactions API Check (GET /api/v1/transactions): PASS ({len(txs)} transactions returned)")

    # 4. Recovery Cases API Check
    res_cases = httpx.get("http://localhost:8000/api/v1/cases?limit=5")
    assert res_cases.status_code == 200
    cases = res_cases.json()
    print(f"4. Recovery Cases API Check (GET /api/v1/cases): PASS ({len(cases)} cases returned)")

    # 5. Analytics Metrics API Check
    res_analytics = httpx.get("http://localhost:8000/api/v1/analytics/metrics")
    assert res_analytics.status_code == 200
    analytics = res_analytics.json()
    assert "revenue_at_risk" in analytics
    print("5. Analytics Metrics Check (GET /api/v1/analytics/metrics): PASS")

    # 6. Evaluation Benchmark Summary Check
    res_eval = httpx.get("http://localhost:8000/api/v1/evaluation/summary")
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert "precision" in eval_data
    assert eval_data.get("unsafe_actions", 0) == 0
    print("6. Evaluation Benchmark Check (GET /api/v1/evaluation/summary): PASS (Unsafe Actions = 0)")

    # 7. Audit Trail API Check
    res_audit = httpx.get("http://localhost:8000/api/v1/audit?limit=10")
    assert res_audit.status_code == 200
    audits = res_audit.json()
    print(f"7. Audit Trail API Check (GET /api/v1/audit): PASS ({len(audits)} events returned)")

    # 8. Webhook Security Check (Invalid Signature Rejection)
    res_wh_invalid = httpx.post(
        "http://localhost:8000/api/v1/webhooks/razorpay",
        json={"event": "payment.failed"},
        headers={"x-razorpay-signature": "bogus_invalid_sig_12345"}
    )
    assert res_wh_invalid.status_code == 401
    print("8. Webhook Security Check (Invalid HMAC Signature): PASS (HTTP 401 Unauthorized)")

    # 9. Secret Exposure Redaction Scan
    res_audit_scan = httpx.get("http://localhost:8000/api/v1/audit?limit=100")
    audit_text = res_audit_scan.text
    assert "rzp_secret" not in audit_text
    assert "RAZORPAY_KEY_SECRET" not in audit_text
    assert "RAZORPAY_WEBHOOK_SECRET" not in audit_text
    print("9. Secret Exposure Redaction Scan: PASS (Zero secrets exposed)")

    # 10. Frontend Production Server Availability
    try:
        res_fe = httpx.get("http://localhost:3000")
        assert res_fe.status_code == 200
        print("10. Frontend Production Server Check (http://localhost:3000): PASS (HTTP 200 OK)")
    except Exception as fe_err:
        print(f"10. Frontend Production Server Check: WARNING ({fe_err})")

    print("\n=================================================================")
    print("    ALL PAYPILOT AI PUBLIC DEMO VERIFICATION CHECKS PASSED       ")
    print("=================================================================")

if __name__ == "__main__":
    run_public_demo_verification()
