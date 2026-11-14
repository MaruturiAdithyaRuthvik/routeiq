# RouteIQ Project Constitution

PRODUCT: Route leave and expense requests using policy, balances, budgets and approval authority. Expose key decisions and exceptions, preserve traceability, produce measurable outputs.

ARCHITECTURE: Three independent tiers. (1) Frontend: React 18 + Vite + TypeScript + Tailwind + shadcn/ui in /frontend. (2) Backend: Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2 in /backend, managed with uv. (3) Database: PostgreSQL 16 in Docker, DDL in /db/schema.sql. Frontend talks only to the backend REST API (/api/v1). Backend is the only thing that touches the DB.

PURE ENGINE: all business rules live in backend/app/engine as pure, deterministic, side-effect-free functions. The data generator AND the API both import this engine, so outcomes are derived from documented rules and never from independent random assignment.

IDs (immutable, zero-padded, referenced identically everywhere): EMP-000001; LVE-2026-000001; EXP-2026-000001; EXPL-<claim-id>-01 (e.g. EXPL-EXP-2026-000001-01); APR-<request-id>-01 (e.g. APR-LVE-2026-000001-01); RMB-2026-000001. Other entities: LPO-001 (leave policy), XPO-0001 (expense policy), CC-0001 (cost center), ARL-001 (approval rule), LBL-<emp>-<policy>-2026 (balance).

HISTORY: never overwrite history. State changes are appended to event tables (leave_request_event, expense_claim_event, leave_ledger_entry, decision_audit).

GROUND TRUTH: lives in a separate Postgres schema `ground_truth` and separate files. Only the evaluation service may read it. Audit detectors, routing engine and feature code must never import or query it. A test must enforce this.

DETERMINISM: fixed seed 20261022, fixed AS_OF_DATE 2026-10-22, no wall-clock, no uuid4, no unseeded randomness, sorted outputs. All data is 100% synthetic; no external data.

ENGINEERING RULES: type hints everywhere; ruff + pytest on backend; eslint + tsc strict + vitest on frontend; no secrets in git (.env.example only); small focused modules; docstrings that cite the rule IDs from docs/BUSINESS_RULES.md; every rule has unit tests including boundaries; conventional commits.

WORKFLOW AFTER EVERY TASK: run the relevant tests/linters, fix until green, commit with a conventional commit message, then print a 5-line summary of what changed and what is next. If a requirement is ambiguous, choose the simplest reasonable interpretation and record it in docs/ASSUMPTIONS.md instead of asking me.
