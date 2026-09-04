# PayPilot AI — Repository Structure & File Sitemap

## Overview
This sitemap documents the directory hierarchy, purpose, key files, and system participation of every folder in the PayPilot AI repository.

```text
paypilot-ai/
├── .env.example                     # Environment variables template with placeholders
├── .gitignore                        # Git exclusion rules for secrets, DBs, and builds
├── README.md                        # Master project documentation & quickstart guide
├── PRODUCTION_READINESS_AUDIT.md    # Production readiness audit findings (Point #13)
├── backend/                         # FastAPI application backend (Python 3.10+)
│   ├── app/                         # Core application package
│   │   ├── api/                     # API routers and endpoints
│   │   │   ├── deps.py              # Dependency injection (AsyncSession DB context)
│   │   │   └── v1/                  # Version 1 API endpoints
│   │   │       ├── router.py        # Master API router aggregator
│   │   │       └── endpoints/       # Specific domain endpoints
│   │   │           ├── analytics.py   # Revenue metrics & funnel analytics
│   │   │           ├── audit.py       # Audit trail query & secret redaction API
│   │   │           ├── cases.py       # Recovery cases, timeline, & decision summary
│   │   │           ├── evaluation.py  # Synthetic benchmark evaluation runner
│   │   │           ├── health.py      # Health & Razorpay status checks
│   │   │           ├── payments.py    # Transaction registry API
│   │   │           ├── recovery.py    # Recovery case execution API
│   │   │           └── webhooks.py    # HMAC-verified Razorpay webhook ingestion
│   │   ├── core/                    # System configuration, logging, & exception handling
│   │   │   ├── config.py            # Pydantic BaseSettings & CORS origin parsing
│   │   │   ├── exceptions.py        # Production JSON exception handlers
│   │   │   └── logging.py           # Structured logging configuration
│   │   ├── db/                      # Database connection and session management
│   │   │   ├── base.py              # Declarative SQLAlchemy Base
│   │   │   ├── init_db.py           # Automated schema creation on startup
│   │   │   └── session.py           # Async SQLAlchemy engine & session maker
│   │   ├── models/                  # SQLAlchemy ORM database models
│   │   │   ├── ai_diagnosis.py      # AIDiagnosis model
│   │   │   ├── audit_log.py         # AuditLog model
│   │   │   ├── customer.py          # Customer model
│   │   │   ├── evaluation_run.py    # EvaluationRun model
│   │   │   ├── merchant.py          # Merchant model
│   │   │   ├── recovery_action.py   # RecoveryAction model
│   │   │   ├── recovery_case.py     # RecoveryCase model
│   │   │   ├── transaction.py       # Transaction model
│   │   │   └── webhook_event.py     # WebhookEvent model
│   │   ├── schemas/                 # Pydantic data validation & response schemas
│   │   └── services/                # Core domain business logic engines
│   │       ├── ai/                  # Gemini AI failure diagnosis service
│   │       ├── evaluation/          # Batch evaluation & metrics calculation engine
│   │       ├── policy/              # Deterministic Policy Safety Gate rules
│   │       ├── razorpay/            # Razorpay Payment Links API integration service
│   │       ├── recovery/            # Recovery action execution engine
│   │       └── risk/                # Revenue Risk Engine scoring service
│   ├── docs/                        # Backend specific technical documentation
│   │   ├── audit-trail.md           # Audit trail architecture & 7-stage timeline spec
│   │   ├── evaluation.md            # Synthetic evaluation benchmark specification
│   │   └── resilience-testing.md    # Hard failure injection & matrix results
│   ├── scripts/                     # Operational runner scripts
│   │   ├── run_evaluation.py        # CLI runner for 1,000 synthetic case benchmark
│   │   └── verify_public_demo.py    # E2E public demo verification suite
│   ├── tests/                       # Pytest automated test suite (96 tests)
│   │   ├── test_ai_service.py       # AI Service unit/integration tests
│   │   ├── test_analytics.py        # Analytics API tests
│   │   ├── test_audit_trail.py      # Audit trail & decision summary tests
│   │   ├── test_case_pipeline.py    # End-to-end case creation pipeline tests
│   │   ├── test_evaluation.py       # Evaluation engine unit tests
│   │   ├── test_health.py           # Health endpoint tests
│   │   ├── test_models.py           # Database model unit tests
│   │   ├── test_payments.py         # Payments endpoint tests
│   │   ├── test_policy_engine.py    # Policy Engine safety constraint tests
│   │   ├── test_razorpay.py         # Razorpay service unit tests
│   │   ├── test_recovery.py         # Recovery engine unit tests
│   │   ├── test_recovery_execution.py# Recovery link execution tests
│   │   ├── test_resilience.py       # Hard failure injection & safety invariant tests
│   │   ├── test_risk_engine.py      # Risk engine unit tests
│   │   ├── test_schemas.py          # Pydantic schema validation tests
│   │   └── test_webhooks.py         # Webhook signature verification tests
│   ├── .env.example                 # Backend environment variable template
│   ├── paypilot_dev.db              # SQLite development database (auto-generated)
│   └── requirements.txt             # Pinned Python package dependencies
├── docs/                            # Project-wide documentation & guides
│   ├── ARCHITECTURE.md              # System architecture specification
│   ├── DEMO_CHECKLIST.md            # Judge demonstration script & checklist
│   ├── JUDGE_QUICKSTART.md          # 5-minute judge quickstart guide
│   ├── PUBLIC_WEBHOOK_SETUP.md      # Cloudflare Quick Tunnel & Webhook guide
│   ├── RAZORPAY_TEST_MODE.md        # Razorpay Test Mode integration setup
│   ├── REPRODUCIBILITY_REPORT.md    # Reproducibility verification report (Point #14)
│   └── ...                          # Additional specification documents
└── frontend/                        # Next.js 14 Web UI Dashboard (TypeScript + Tailwind)
    ├── src/
    │   ├── app/                     # Next.js App Router pages
    │   │   ├── benchmark/page.tsx   # Synthetic Evaluation Benchmark page
    │   │   ├── cases/page.tsx       # Recovery Cases management page
    │   │   ├── safety/page.tsx      # Safety Policy Engine rules page
    │   │   ├── layout.tsx           # Main application layout with Navbar
    │   │   └── page.tsx             # Master Dashboard overview page
    │   ├── components/              # React UI components
    │   │   ├── CaseDetailDrawer.tsx # 7-Stage Decision Timeline & Trace Drawer
    │   │   └── Navbar.tsx           # Navigation bar with connection badges
    │   └── lib/                     # Frontend utility libraries
    │       └── api.ts               # API client, IST timestamp formatter, & types
    ├── package.json                 # Node package configuration
    ├── package-lock.json            # Pinned npm dependency lockfile
    ├── tailwind.config.js           # Tailwind CSS configuration
    └── tsconfig.json                # TypeScript compiler configuration
```

---

## Disposable Artifacts Cleaned Up
All temporary scratch files or duplicate test artifacts have been cleaned. Key automated verification scripts (`backend/scripts/run_evaluation.py` and `backend/scripts/verify_public_demo.py`) are maintained in the repository for fresh-machine evaluation.
