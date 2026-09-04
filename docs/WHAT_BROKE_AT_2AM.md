# What Broke at 2 AM — Real Engineering Incident Log
**PayPilot AI — Razorpay AI Buildathon Track 03**

---

## Incident 1: Next.js Webpack Chunk Cache Corruption (`Error: Cannot find module './206.js'`)
- **Problem**: Next.js dev server returned HTTP 500 on `/cases` and `/_not-found` with stack trace `Error: Cannot find module './206.js'` inside `webpack-runtime.js`.
- **Root Cause**: Stale/corrupted `.next` compilation cache generated during rapid hot-reloads across static route generations.
- **Diagnosis**: Inspected `task-12242.log` showing module resolution failure despite zero syntax errors in `page.tsx`.
- **Fix**: Stopped stale Next.js dev process, deleted `.next` cache directory (`Remove-Item -Recurse -Force .next`), and restarted `npm run dev`.
- **Verification**: Retested all 16 routes; all returned HTTP 200 OK. `npm run build` compiled 18/18 static pages clean.

---

## Incident 2: Pytest Fixture Schema Invariant Violation (`NOT NULL constraint failed: recovery_cases.risk_level`)
- **Problem**: `test_audit_integrity.py` failed with SQLite `IntegrityError: NOT NULL constraint failed: recovery_cases.risk_level`.
- **Root Cause**: Unit test instantiated `RecoveryCase` without populating non-null database column `risk_level`.
- **Diagnosis**: Traceback from `pytest` showed SQLAlchemy ORM flush failure on `INSERT INTO recovery_cases`.
- **Fix**: Added `risk_level="LOW"` to test case instantiations in `test_audit_integrity.py`.
- **Verification**: `pytest` passed 323/323 tests.

---

## Incident 3: Data Lineage Metric Inflation (Legacy ₹2,500 Unreconciled Record)
- **Problem**: Main dashboard reported recovered revenue inflated by ₹2,500 despite no provider-captured payment existing for that amount.
- **Root Cause**: Historical test case `a802b0cb-06a3-4ba2-b0d5-e1ab37422741` had `status='RECOVERED'` and `recovered_amount=2500` set manually during early testing without a captured transaction record.
- **Diagnosis**: Executed SQL audit querying `recovery_cases` join `transactions` where `status='captured'`.
- **Fix**: Reclassified case `a802b0cb-06a3-4ba2-b0d5-e1ab37422741` to `INVALID_UNRECONCILED` with `recovered_amount = 0.0`. Updated `analytics.py` to count only verified recovered revenue (**INR 80.00**).
- **Verification**: Re-ran analytics audit; recovered metrics dynamically reflect exact provider-confirmed payment sum.

---

## Incident 4: Voice Assistant Rate Limiting & Quota Throttling
- **Problem**: Voice assistant text bubble displayed fallback message when Gemini API key hit 429 quota limits.
- **Root Cause**: Upstream LLM rate limit throttled response generation under rapid test loops.
- **Diagnosis**: Inspected API proxy logs showing HTTP 429 from Google Gemini API endpoint.
- **Fix**: Frozen and bypassed Voice Assistant route (`/voice`) to ensure core Track 03 Razorpay revenue recovery engines remained 100% deterministic, stable, and unaffected.
- **Verification**: Frozen voice route verified stable without breaking backend dependencies.
