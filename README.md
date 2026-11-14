# RouteIQ — work, with more clarity

RouteIQ is a synthetic leave-and-expense routing dataset and rules-engine demo. It makes policy checks, approval paths, exceptions, and reimbursement outcomes traceable and measurable.

## Run it

Requires Python 3.12, `uv`, Docker Compose, and PostgreSQL 16.

```sh
make setup
make db-up
make generate                 # full, seed 20261022
make validate
make repro
make load
```

Starter data uses the identical pipeline:

```sh
cd backend
uv run python -m app.datagen --seed 20261022 --scale starter --out ../data
```

Use `--scale full` for 400 employees, 800 leave requests, and 1,000 expense claims.

## Repository map

- `backend/app/engine/` — pure, deterministic policy/routing engine
- `backend/app/datagen/` — synthetic master and transaction generation
- `backend/app/db/load.py` — CSV-to-PostgreSQL loader
- `data/csv/`, `data/json/`, `data/sql/` — operational exports and SQL seed
- `data/ground_truth/` — evaluation labels, isolated from operational exports
- `data/schema/` — copied entity dictionary and ERD
- `db/` — PostgreSQL schema, views, and initialization
- [`docs/ERD.md`](docs/ERD.md) · [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) · [`docs/BUSINESS_RULES.md`](docs/BUSINESS_RULES.md)

## Entities and identifiers

Core entities: Employee, LeavePolicy, LeaveBalance, LeaveRequest, ExpensePolicy, ExpenseClaim, ExpenseLine, CostCenter, ApprovalRule, ApprovalStep, Reimbursement; supporting entities include holidays, assignments, events, ledger entries, findings, and decision audits. IDs use immutable zero-padded forms: `EMP-000001`, `LVE-2026-000001`, `EXP-2026-000001`, `EXPL-EXP-2026-000001-01`, `APR-LVE-2026-000001-01`, and `RMB-2026-000001`.

## Rules and anomaly catalog

Leave validation covers dates, business days, eligibility, overlap, and balance; routing depends on policy and duration. Expense validation covers receipt and policy limits, employment dates, duplicates, cost centers, amount bands, and category exceptions. All derived outcomes come from the shared engine; the fixed evaluation date is 2026-10-22.

The generated full-scale ground-truth file currently contains: negative balance 1; overlapping approved leave 1; expense outside employment 1; split-claim group 1 (2 claims); missing cost center 1; requester approval 1; duplicate reimbursement 1; duplicate receipt hash 1. Baseline labels additionally cover missing receipt 1, policy-limit breach 2, insufficient balance 1, and weekend/holiday/zero-business-day span 1. These are actual generated counts; they do not yet meet the larger anomaly-count targets in the submission brief. See `data/ground_truth/ground_truth_anomalies.csv`.

## Validation and reproducibility

| Check | Command/report |
|---|---|
| Key/ID, joins, dates, enums | `make validate` |
| FX, line totals, ledger/balance reconciliation | `make validate` |
| Lifecycle, approvals, reimbursements | `make validate` |
| Two-run SHA-256 comparison | `make repro`; see `data/reproducibility_report.md` |

`data/SOURCE_MANIFEST.json` records the fixed seed, synthetic provenance, and row counts. `data/GENERATOR_COMMAND.txt` records the invocation. No external records or personal data are used. Ground truth is exported separately; operational CSV/JSON and SQL seed do not contain evaluation labels.

## Limitations

This is a hackathon-scale synthetic fixture, not legal, payroll, tax, or accounting advice. Holiday calendars, policy limits, employee identities, merchants, and budgets are illustrative. Reimbursement payment dates are deterministic projections, not payment instructions. The loader expects a fresh compatible schema and is intended for local demonstration.

## Web app
<img width="1440" height="900" alt="Image 1" src="https://github.com/user-attachments/assets/2b1ab4fb-f3d8-4da3-b7b6-2c77b54ee9f7" />

<img width="1440" height="900" alt="Image 3" src="https://github.com/user-attachments/assets/4064a6b8-ab6e-486c-9b98-bf1df53252d3" />
<img width="390" height="844" alt="Image 4" src="https://github.com/user-attachments/assets/8d59eb84-ee88-4915-93b5-62c67b01fabe" />
<img width="1440" height="900" alt="Image 2" src="https://github.com/user-attachments/assets/9f07a1e3-80b6-491c-bc20-be1c80db1434" />



Run `make up` and open [http://localhost:8080](http://localhost:8080); use `make down` to stop the stack. The first run builds both images, waits for PostgreSQL, and loads `data/csv` only when `public.employee` is empty. The persona switcher offers Requester, Approver, Process owner, Analyst, and Admin.

Pages include Overview, My requests, New leave request, New expense claim, Approval inbox, Reimbursements, Analytics, Audit findings/run, Evaluation summary/misses, People, Employee profile/balances, Cost centers, Holidays, Leave policies, Expense policies, Approval rules, Demo personas, and Dataset manifest.

The UI calls `/api/v1/auth/personas`, `/auth/demo-login`, `/me`, reference endpoints, `/leave-requests/preview`, `/leave-requests`, `/expense-claims/preview`, `/expense-claims`, `/approvals/inbox`, `/approval-steps/{id}/decision`, `/audit/run`, `/evaluation/summary`, `/evaluation/misses`, and `/metrics/overview`. API mode is the default; fixture mode must be explicitly enabled for local UI development and is not included in production builds.

### Five-minute judge demo

1. **Requester (1 min):** open Overview, create a leave preview, review business-day exclusions and checks, then preview an expense with receipt metadata.
2. **Approver (1 min):** switch persona, open Approval inbox, inspect a pending item and decide it.
3. **Process owner (1 min):** review people, cost centers, policies, and approval rules; inspect reimbursements and run the operational audit.
4. **Analyst (1 min):** review metrics, audit findings, evaluation summary, and misses; explain the precision/recall values.
5. **Admin (1 min):** switch persona, inspect the dataset manifest and full workflow pages; point out that all records and identities are synthetic.
