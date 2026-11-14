# RouteIQ Assumptions

These are explicit resolutions for details not fixed by `docs/PROBLEM_STATEMENT.md` or `docs/BUSINESS_RULES.md`. They are intentionally deterministic and synthetic.

## Dates, balances, and state

- All operational effective intervals are start-inclusive and end-exclusive. An employee's `termination_date` is inclusive; leave must fall entirely within employment dates. Employment activity for a request is evaluated over the request dates, not by wall-clock time.
- Leave date ranges are inclusive. `business_days` excludes weekends and the employee's country holidays. `max_consecutive_days` uses inclusive calendar days, not business days.
- Monthly accrual applies to Annual, Sick, and Casual. Accrual is earned only for a month in which the employee is employed at month end; a hire-month credit is made only when the hire day is 15 or earlier. There is no partial-month proration beyond this cutoff. Month-end monthly credits are rounded to 6 decimal places; December receives the remainder needed to make the year's credits equal the exact annual entitlement.
- With `AS_OF_DATE = 2026-10-22`, only month-end accruals through September 30, 2026 are included in current balances; October accrual is not credited before October 31.
- For a lump-sum policy, eligibility is the later of January 1 and the eligibility date; Parental eligibility is the date 12 calendar months after hire. If a month has no corresponding day, use that month's last calendar day.
- Opening balance follows L2 exactly: `min(prior_year_closing_days, carry_forward_max_days)`. Baseline prior-year closing balances are nonnegative; negative-balance anomalies are injected in the current-year ledger and do not alter the opening calculation. Unpaid leave has a zero balance and no ledger accrual.
- Since 2025 operational history is outside this dataset, record a deterministic synthetic prior-year closing value on each 2026 OPENING ledger row. For Annual leave, use the numeric suffix of `employee_id` modulo 13 (0–12 days) for employees hired before 2026; use zero for employees hired in 2026. Other policies use zero prior-year closing. This exercises the 10-day Annual carry-forward cap without external data.
- L6 applies to balance-bearing leave policies. For Unpaid, append the required RESERVE/RELEASE/DEBIT ledger markers with `delta_days = 0`; they preserve request history without creating or consuming a balance.
- A reversal is a full, one-time inverse of one non-reversal ledger entry. Partial reversals and reversal chains are not generated. Leave day quantities are stored to 6 decimal places; an injected negative-balance anomaly is permitted by domain validation but remains labeled in ground truth.
- Submit-time hard rejections do not transition a request from DRAFT. The failed attempt and reason are appended to the corresponding event table and `DecisionAudit`; the request remains DRAFT. This reconciles submit-time REJECT rules with the explicitly allowed lifecycle transitions.
- A failed submission may have a `DRAFT` to `DRAFT` event snapshot, which records an attempt rather than a state transition. All actual state changes remain append-only.
- Event and audit timestamps are deterministic UTC values derived from the fixed scenario timeline. The evaluation clock is always `AS_OF_DATE = 2026-10-22`.

## Synthetic reference data

- The eight dates per country listed in G3 are synthetic illustrative holidays. They are not sourced from, or asserted to represent, real public-holiday calendars.
- Expense policies have version 1, `effective_from = 2026-01-01`, and no `effective_to`. Generate one row for each of the 10 E1 categories and each of the five countries. IDs are assigned in country order `IN, US, GB, DE, SG`, then E1 category order, yielding `XPO-0001` through `XPO-0050`.
- E1 does not provide numerical limits. Use the synthetic per-line USD policy matrix below, scaled by the cost-of-living factor for each employee country: IN 0.65, US 1.00, GB 0.95, DE 0.90, SG 1.05. Apply the factor and round half-up to 2 decimals for both the per-line limit and receipt threshold.

  | category | base per_line_limit_usd | base receipt_threshold_usd |
  |---|---:|---:|
  | MEALS | 150.00 | 25.00 |
  | LODGING | 500.00 | 50.00 |
  | AIRFARE | 2000.00 | 0.00 |
  | GROUND_TRANSPORT | 250.00 | 25.00 |
  | SOFTWARE | 3000.00 | 0.00 |
  | OFFICE_SUPPLIES | 500.00 | 25.00 |
  | TRAINING | 2000.00 | 0.00 |
  | CLIENT_ENTERTAINMENT | 1000.00 | 25.00 |
  | GIFTS | 500.00 | 25.00 |
  | COMMUNICATION | 300.00 | 25.00 |

- `ExpensePolicy.country` is the employee's home country; select a policy using that country and the line's category and claim's `expense_date`. `ExpenseLine.category` is the category used for policy evaluation and routing. A claim may contain multiple categories.
- Source line amounts are positive values in the line's `currency`; `fx_rate_to_usd` is the fixed G2 currency rate. Round each line to 2 USD decimals before summing `ExpenseClaim.total_usd`. Reimbursement home currency is obtained by dividing the approved USD total by the employee home-currency rate, then rounding half-up to 2 decimals.
- Receipt file types are limited to `PDF`, `JPG`, `JPEG`, `PNG`, and `HEIC`. Receipt hashes are lowercase SHA-256 hex and are not unique-constrained so duplicates remain loadable for detection.
- Receipt metadata is synthetic. Hash the canonical UTF-8 bytes of a deterministic synthetic receipt descriptor; duplicate-receipt anomalies deliberately reuse an existing hash. No real receipt files are collected.
- Each valid expense claim has 1–10 lines. Line numbers and `EXPL` suffixes are sequential from 01. `APR` step suffixes are sequential from 01 for each request.
- Leave policies have one row per LPO ID, effective from 2026-01-01 with no end date. Parental has no separate `max_consecutive_days` cap; the available 90-day balance remains the limit. The policies are the exact six rows in L1.
- Create one 2026 `LeaveBalance` snapshot per employee and each of the six policies, including an all-zero Unpaid snapshot. Ineligible Parental balances remain zero until the eligibility date; no opening ledger entry is created for Unpaid.
- Cost-center annual budgets are synthetic USD reporting values. The rules define no budget threshold, reservation, or rejection behavior, so budget is recorded for reporting only and must not independently alter routing or eligibility.

## Approval resolution and flags

- Approval roles are evaluated sequentially. Start with the base path, append additive roles in the E6 order (`FINANCE_CONTROLLER`, then `COMPLIANCE_OFFICER`), and retain only the first occurrence of each role.
- All assigned managers, cost-center owners, and designated role holders are active employees with `system_role = APPROVER`; cost-center owners have `functional_role = DEPT_HEAD`, and designated holders' functional roles match the required role. The designated CEO fallback is an HR_PARTNER approver.
- `HR_PARTNER` resolves to the active same-country employee with `functional_role = HR_PARTNER` and `system_role = APPROVER` having the lexicographically smallest `employee_id`, excluding the requester. If no such person exists, record `UNRESOLVED_APPROVER` and leave the request pending; never choose randomly.
- `FINANCE_CONTROLLER`, `CFO`, and `COMPLIANCE_OFFICER` resolve to the active APPROVER employee named by the effective matching `ApprovalRule.designated_employee_id`. An absent or inactive designated holder is an unresolved approver, not a reason to silently skip a step.
- For expense `DEPT_HEAD`, use `CostCenter.owner_employee_id`. For leave `DEPT_HEAD`, use the owner of the requester's active cost-center assignment with the greatest `allocation_pct`; break ties by lexicographically smallest `cost_center_id`. If there is no active assignment, record an unresolved approver.
- `MANAGER` resolves to the direct `manager_id`. The CEO has no manager, so a CEO request's manager step resolves to the designated active CHRO/HR-head holder (an `HR_PARTNER` approver). If the selected approver is the requester, replace that approver with their direct manager; if unavailable, use the CHRO/HR-head holder. Record `SELF_APPROVAL_PREVENTED`. If no distinct approver is available, leave the request pending with `UNRESOLVED_APPROVER`.
- A step's `due_date` is the third business day after the UTC date component of `assigned_at`; the assignment date itself is not counted. Apply the employee's country holiday calendar without timezone conversion. Reimbursement's fifth business day is counted the same way after the final approval event's UTC date.
- E5 "flags" means open findings from E3 only. A claim has an E3 flag if any line or claim-level E3 finding is present. For a claim under USD 50 with such a flag, use MANAGER as the otherwise-unspecified base route, then append E6 additions.
- `DUPLICATE_RECEIPT`, `SPLIT_CLAIM`, and `DUPLICATE_REIMBURSEMENT` are duplicate-related findings for E9. A hard-rejected duplicate receipt cannot proceed to reimbursement. Resolve or dismiss findings only by appending an `AuditFindingEvent`; the original finding is immutable.
- For E10, normalize merchant names by trimming outer whitespace and case-folding. A shared category means at least one `ExpenseLine.category` appears on both claims. Compare each claim's whole `total_usd` with the same boundary; the 90% and 99.99% endpoints are inclusive, and the date distance is absolute calendar days.
- Baseline contains at most one reimbursement per claim, but `Reimbursement.expense_claim_id` is not unique-constrained so a labeled duplicate-reimbursement anomaly can be loaded without breaking a key constraint.
- A negative leave balance, overlap, receipt duplicate, and other deliberate anomalies keep valid IDs, foreign keys, and enum values; the domain-level rule violation is recorded in `GroundTruthAnomaly`. Duplicate receipt hashes and reimbursement claim references are deliberately not unique-constrained.

## Ground truth, provenance, and metrics

- `GroundTruthAnomaly` and `GroundTruthDecision` are stored only in the `ground_truth` schema and both isolated `ground_truth.csv` and `ground_truth.json` evaluation files. Only the evaluation service receives read access. Routing, audit detection, API features, and generated input data cannot query or import them.
- Public external datasets are not incorporated into generated scenario or transaction records; those records remain 100% synthetic. If a lawful public source is consulted only for schema inspiration, record URL, dataset/version, retrieval date, license/terms, attribution, transformations, and discarded fields in the source manifest. Do not access restricted sources or use confidential or personal data.
- Evaluation metrics should include decision accuracy, approval-path accuracy, anomaly precision/recall, reimbursement eligibility accuracy, and validation pass counts. These metrics use ground truth only inside the evaluation service.
- The source manifest records the synthetic generator/version, fixed seed, `AS_OF_DATE`, policy/holiday fixtures, and output checksums. No external data source is used for generated records.

## Existing scaffold decisions

- Non-database root `Makefile` targets remain placeholders until their implementation commands exist.
- `.env.example` contains local development connection settings and reproducibility values only; replace its sample database credentials for non-local deployment.
- Judge-facing `data/csv/` and `data/json/` are operational-only exports; evaluation labels are emitted under `data/ground_truth/`. `data/sql/seed.sql` loads operational rows only.
- Anomaly and decision labels are serialized into the requested compact evaluation columns at export time; source generation frames retain the database-oriented field names.

## Database implementation decisions

- Add nullable `employee.cost_center_id` to support the explicitly requested deferred circular foreign keys between employees and cost centers. It represents the employee's primary cost center; the documented `EmployeeCostCenterAssignment` bridge remains the source for dated, allocated multi-center assignments.
- Keep `approval_step.approver_employee_id` as documented in the dictionary; the requested SQL name `approver_id` maps to this same field. It remains a plain employee foreign key with no requester-difference constraint so labeled self-approval anomalies remain loadable.
- Database access roles `routeiq_app` and `routeiq_evaluator` are non-login groups; initialization creates separate login roles from the development-only passwords in `.env.example` and grants each login its matching group. Only the evaluator group receives privileges on `ground_truth`; the `POSTGRES_USER` account is reserved for local administration.
- The views use the fixed 2026-10-22 evaluation date. Spend reports approved and reimbursed claims by their 2026 cost center; cycle time is measured from the first SUBMITTED event to the terminal approval/rejection/cancellation event.
- `make db-up` and the smoke script copy `.env.example` to the ignored `.env` when it is absent. The local sample credentials are for development only.
