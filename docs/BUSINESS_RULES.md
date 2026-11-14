# RouteIQ Business Rules

These rule IDs are stable references for implementation, tests, audit records, and documentation. Unless a rule explicitly describes an injected anomaly, it applies to baseline records. Dates and derived values use `AS_OF_DATE = 2026-10-22`; business-day calculations use the holiday calendar below.

## General

### G1 — Valid baseline and labeled anomalies

Baseline data obeys every business rule. Injected anomalies are deliberate business-rule violations that slipped through controls and each is labeled in the separate ground-truth dataset. An anomaly must remain loadable: it may violate a business rule but must not violate primary-key, foreign-key, or enum constraints. Do not silently corrupt unrelated records.

### G2 — Countries, currencies, and reporting amounts

Allowed `country` values are `IN`, `US`, `GB`, `DE`, and `SG`. The corresponding home currencies are `INR`, `USD`, `GBP`, `EUR`, and `SGD`. Static `fx_rate_to_usd` values are:

| currency | fx_rate_to_usd |
|---|---:|
| INR | 0.012 |
| USD | 1.0 |
| GBP | 1.27 |
| EUR | 1.08 |
| SGD | 0.74 |

Reporting currency is USD. Convert with decimal arithmetic and round monetary values to 2 decimal places using round-half-up. For an expense line, `amount_usd = round_half_up(amount * fx_rate_to_usd, 2)`.

### G3 — Illustrative 2026 public-holiday calendar

The following are synthetic, illustrative holiday records, not authoritative public-holiday guidance. They are the complete 2026 calendar used for this dataset: eight holidays per country.

| holiday_id | country | holiday_date | holiday_name |
|---|---|---|---|
| HOL-2026-IN-01 | IN | 2026-01-05 | Illustrative holiday 01 |
| HOL-2026-IN-02 | IN | 2026-02-09 | Illustrative holiday 02 |
| HOL-2026-IN-03 | IN | 2026-03-16 | Illustrative holiday 03 |
| HOL-2026-IN-04 | IN | 2026-04-20 | Illustrative holiday 04 |
| HOL-2026-IN-05 | IN | 2026-06-08 | Illustrative holiday 05 |
| HOL-2026-IN-06 | IN | 2026-08-17 | Illustrative holiday 06 |
| HOL-2026-IN-07 | IN | 2026-10-12 | Illustrative holiday 07 |
| HOL-2026-IN-08 | IN | 2026-12-14 | Illustrative holiday 08 |
| HOL-2026-US-01 | US | 2026-01-12 | Illustrative holiday 01 |
| HOL-2026-US-02 | US | 2026-02-23 | Illustrative holiday 02 |
| HOL-2026-US-03 | US | 2026-04-06 | Illustrative holiday 03 |
| HOL-2026-US-04 | US | 2026-05-18 | Illustrative holiday 04 |
| HOL-2026-US-05 | US | 2026-07-13 | Illustrative holiday 05 |
| HOL-2026-US-06 | US | 2026-09-14 | Illustrative holiday 06 |
| HOL-2026-US-07 | US | 2026-11-09 | Illustrative holiday 07 |
| HOL-2026-US-08 | US | 2026-12-21 | Illustrative holiday 08 |
| HOL-2026-GB-01 | GB | 2026-01-19 | Illustrative holiday 01 |
| HOL-2026-GB-02 | GB | 2026-03-02 | Illustrative holiday 02 |
| HOL-2026-GB-03 | GB | 2026-04-13 | Illustrative holiday 03 |
| HOL-2026-GB-04 | GB | 2026-06-01 | Illustrative holiday 04 |
| HOL-2026-GB-05 | GB | 2026-07-20 | Illustrative holiday 05 |
| HOL-2026-GB-06 | GB | 2026-09-21 | Illustrative holiday 06 |
| HOL-2026-GB-07 | GB | 2026-11-16 | Illustrative holiday 07 |
| HOL-2026-GB-08 | GB | 2026-12-07 | Illustrative holiday 08 |
| HOL-2026-DE-01 | DE | 2026-01-26 | Illustrative holiday 01 |
| HOL-2026-DE-02 | DE | 2026-03-09 | Illustrative holiday 02 |
| HOL-2026-DE-03 | DE | 2026-04-27 | Illustrative holiday 03 |
| HOL-2026-DE-04 | DE | 2026-06-15 | Illustrative holiday 04 |
| HOL-2026-DE-05 | DE | 2026-08-03 | Illustrative holiday 05 |
| HOL-2026-DE-06 | DE | 2026-09-28 | Illustrative holiday 06 |
| HOL-2026-DE-07 | DE | 2026-11-23 | Illustrative holiday 07 |
| HOL-2026-DE-08 | DE | 2026-12-28 | Illustrative holiday 08 |
| HOL-2026-SG-01 | SG | 2026-02-02 | Illustrative holiday 01 |
| HOL-2026-SG-02 | SG | 2026-03-23 | Illustrative holiday 02 |
| HOL-2026-SG-03 | SG | 2026-05-11 | Illustrative holiday 03 |
| HOL-2026-SG-04 | SG | 2026-06-22 | Illustrative holiday 04 |
| HOL-2026-SG-05 | SG | 2026-08-10 | Illustrative holiday 05 |
| HOL-2026-SG-06 | SG | 2026-09-07 | Illustrative holiday 06 |
| HOL-2026-SG-07 | SG | 2026-10-26 | Illustrative holiday 07 |
| HOL-2026-SG-08 | SG | 2026-12-14 | Illustrative holiday 08 |

### G4 — Business day

A business day is Monday through Friday and is not a `Holiday` for the employee's `country`. Date ranges for leave are inclusive. Use the employee's country calendar for leave and approval SLAs.

### G5 — Roles and approval authority

`functional_role` is one of `NONE`, `DEPT_HEAD`, `HR_PARTNER`, `FINANCE_CONTROLLER`, `CFO`, or `COMPLIANCE_OFFICER`. `system_role` is one of `REQUESTER`, `APPROVER`, `PROCESS_OWNER`, `ANALYST`, or `ADMIN`. `job_level` is an integer from 1 through 10.

The CEO has no `manager_id`. A request by the CEO that routes to `MANAGER` instead routes to the designated CHRO/HR head. No person may approve their own request. If resolution selects the requester, escalate that step one level up, preserve its original required role, and record an `AuditFinding` and reason code `SELF_APPROVAL_PREVENTED`. If no valid approver can be resolved after escalation, do not silently assign a fallback: leave the request pending and record an unresolved-approver finding.

## Leave

### L1 — Leave policies

The six policies and their fields are:

| leave_policy_id | name | annual_entitlement_days | carry_forward_max_days | max_consecutive_days | medical_certificate_after_days | tenure_required_months | lump_sum_days | is_unpaid |
|---|---|---:|---:|---:|---:|---:|---:|---|
| LPO-001 | Annual | 24 | 10 | 20 | — | 0 | — | false |
| LPO-002 | Sick | 12 | 0 | 15 | 2 | 0 | — | false |
| LPO-003 | Casual | 8 | 0 | 3 | — | 0 | — | false |
| LPO-004 | Parental | — | 0 | — | — | 12 | 90 | false |
| LPO-005 | Compassionate | — | 0 | 5 | — | 0 | 5 | false |
| LPO-006 | Unpaid | — | 0 | 30 | — | 0 | 0 | true |

An em dash means not applicable. A medical certificate is required for Sick leave when the inclusive calendar-day span is greater than 2. The available balance floor is zero for all policies; Unpaid has no balance and is exempt from balance sufficiency validation.

### L2 — Accrual and opening balance

For Annual, Sick, and Casual policies, credit `annual_entitlement_days / 12` at each month end. Credit the hire month only when the employee's `hire_date` day-of-month is 15 or earlier. For a lump-sum policy, credit the full `lump_sum_days` on January 1 or on the date the employee becomes eligible, whichever is later. Parental eligibility is the date the employee completes 12 months of tenure.

At the start of a balance year, `opening_days = min(prior_year_closing_days, carry_forward_max_days)`. Write each opening amount as an `OPENING` `LeaveLedgerEntry`. No accrual is generated beyond employment dates.

### L3 — Leave balance snapshot

`available_days = opening_days + accrued_days + adjustments_days - used_days - pending_days`. `LeaveBalance` is a snapshot derived only from `LeaveLedgerEntry`: `opening_days` is the sum of OPENING deltas; `accrued_days` is the sum of ACCRUAL deltas; `adjustments_days` is the signed sum of ADJUSTMENT and AVAILABLE-bucket REVERSAL deltas; `used_days` is the sum of DEBIT and USED-bucket REVERSAL deltas; `pending_days` is the signed sum of RESERVE, RELEASE, and RESERVED-bucket REVERSAL deltas. OPENING, ACCRUAL, RESERVE, and DEBIT deltas are positive; RELEASE deltas are negative; ADJUSTMENT deltas may be positive or negative. A `REVERSAL` exactly negates its referenced entry's delta and uses the same effect bucket. Only approved leave is debited as used.

### L4 — Leave submit-time validation

Apply checks in this order; stop at the first rejection:

1. `end_date >= start_date`, otherwise reject `INVALID_DATE_RANGE`.
2. Compute inclusive `business_days`; if it is zero, reject `ZERO_BUSINESS_DAYS`.
3. Employee must be active on the leave dates, otherwise reject `EMPLOYEE_NOT_ACTIVE`.
4. Enforce `tenure_required_months`, otherwise reject `TENURE_INELIGIBLE`.
5. Enforce `max_consecutive_days` using inclusive calendar days, otherwise reject `MAX_CONSECUTIVE_DAYS`.
6. Reject if this employee has an overlapping `SUBMITTED`, `PENDING_APPROVAL`, or `APPROVED` leave request (`OVERLAP`).
7. Require sufficient available balance, otherwise reject `INSUFFICIENT_BALANCE`; skip this check for Unpaid leave.

A rejected submission attempt does not create an illegal lifecycle transition: the request remains `DRAFT`, and an event and audit record capture the rejection.
Create an `AuditFinding` using the rejection reason code for each failed validation attempt. The request's risk score is derived from its current open findings under D8.

### L5 — Leave approval routing

Create approval steps sequentially in this order:

| condition | required roles |
|---|---|
| Unpaid policy | MANAGER, HR_PARTNER |
| 1–3 `business_days` | MANAGER |
| 4–10 `business_days` | MANAGER, HR_PARTNER |
| More than 10 `business_days`, or Parental policy | MANAGER, HR_PARTNER, DEPT_HEAD |

Resolve each role as defined in G5 and the approval-resolution assumptions in `docs/ASSUMPTIONS.md`.

### L6 — Leave ledger events

On successful submission, append a `RESERVE` for the requested `business_days`. On final approval, append `RELEASE` for the reservation and `DEBIT` for the same days. On rejection or cancellation, append `RELEASE` only. Never update or delete prior ledger entries.

### L7 — Leave lifecycle

The only legal `LeaveRequest.status` transitions are:

`DRAFT -> SUBMITTED -> PENDING_APPROVAL -> APPROVED | REJECTED | CANCELLED`

Submission validation failures remain `DRAFT` as specified by L4. No terminal state has an outgoing transition.

## Expense

### E1 — Categories and policies

Allowed categories are `MEALS`, `LODGING`, `AIRFARE`, `GROUND_TRANSPORT`, `SOFTWARE`, `OFFICE_SUPPLIES`, `TRAINING`, `CLIENT_ENTERTAINMENT`, `GIFTS`, and `COMMUNICATION`.

Each `ExpensePolicy` is keyed by `(category, country, version)` and contains `per_line_limit_usd`, `receipt_threshold_usd`, `effective_from`, and `effective_to`. Use the policy for the employee's country that is effective on `expense_date`.

### E2 — Expense line amounts and receipts

Each `ExpenseLine` has `amount`, `currency`, `fx_rate_to_usd`, and derived `amount_usd = round_half_up(amount * fx_rate_to_usd, 2)`. `ExpenseClaim.total_usd` is the sum of its `amount_usd` lines. Each line stores `receipt_present`, `receipt_id`, `receipt_hash`, `file_type`, and `size_kb`. A present receipt requires metadata; an absent receipt has null receipt metadata.

### E3 — Expense flags

Create an `AuditFinding` with the corresponding code when any condition holds:

| code | condition |
|---|---|
| `POLICY_LIMIT_BREACH` | A line's `amount_usd` is greater than its policy's `per_line_limit_usd`. |
| `MISSING_RECEIPT` | A line's `amount_usd` is greater than its policy's `receipt_threshold_usd` and `receipt_present` is false. |
| `DUPLICATE_RECEIPT` | A non-null `receipt_hash` appears on any other expense line. |
| `MISSING_COST_CENTER` | `ExpenseClaim.cost_center_id` is null. |
| `DATE_OUTSIDE_EMPLOYMENT` | `expense_date` is before `hire_date` or after `termination_date`. |

### E4 — Expense hard rejects at submit

Reject submission if a line breaches its per-line limit by more than 150% (`amount_usd > 1.5 * per_line_limit_usd`), a receipt hash is duplicated, the cost center is missing, the expense date is outside employment, or `expense_date > AS_OF_DATE`. A hard-rejected attempt remains `DRAFT`; append an event, matching `AuditFinding`, and audit record with its reason code. A limit breach of exactly 150% is not a hard reject.

### E5 — Base approval bands

Use `ExpenseClaim.total_usd` after line-level rounding:

| total_usd | base required path |
|---|---|
| `< 50` and zero open E3 flags | `AUTO_APPROVE` using a `SYSTEM` step |
| `50 <= total_usd < 1000` | `MANAGER` |
| `1000 <= total_usd < 5000` | `MANAGER`, `DEPT_HEAD` (cost-center owner) |
| `5000 <= total_usd < 20000` | `MANAGER`, `DEPT_HEAD`, `FINANCE_CONTROLLER` |
| `>= 20000` | `MANAGER`, `DEPT_HEAD`, `FINANCE_CONTROLLER`, `CFO` |

For a claim below USD 50 with one or more open E3 flags, use `MANAGER` as the base path; apply E6 additions.

### E6 — Additive expense approvals

Add `FINANCE_CONTROLLER` when a claim has an `AIRFARE` line and `employee.country != merchant_country`. Add `COMPLIANCE_OFFICER` for each `CLIENT_ENTERTAINMENT` or `GIFTS` line over USD 250. Add `FINANCE_CONTROLLER` for any policy-limit breach that is not hard-rejected under E4, or for any missing receipt. Record the corresponding AU3 reason code for each addition. Append added roles after the base path in deterministic order; a role already in the path is not duplicated.

### E7 — Expense approver resolution and SLA

Resolve `MANAGER` to `Employee.manager_id`; resolve `DEPT_HEAD` to `CostCenter.owner_employee_id`; resolve `HR_PARTNER` to the deterministic active HR partner in the employee's country; resolve `FINANCE_CONTROLLER`, `CFO`, and `COMPLIANCE_OFFICER` to their designated holders. Resolve CEO manager steps using G5. Each step has an SLA of 3 business days starting on `assigned_at`, calculated using the employee's country holiday calendar.

### E8 — Expense lifecycle

The only legal `ExpenseClaim.status` transitions are:

`DRAFT -> SUBMITTED -> PENDING_APPROVAL -> APPROVED | REJECTED | CANCELLED`

After reimbursement creation, `APPROVED -> REIMBURSED`. Submission validation failures remain `DRAFT` as specified by E4. No other transitions are legal.

### E9 — Reimbursement eligibility and payment

Create a reimbursement only when all conditions hold: claim status is `APPROVED`; every approval step is `APPROVED` (including the `SYSTEM` auto-approval step); there is no duplicate-related `AuditFinding` whose latest status is `OPEN`; cost center is present; and no reimbursement already exists for the claim. If a duplicate reimbursement is detected, block further reimbursement and create a `DUPLICATE_REIMBURSEMENT` finding. The reimbursement amount is the approved total converted to the employee's home currency using G2's static FX rate and round-half-up.

`payment_date` is the date five business days after final approval, using the employee's country calendar. Set reimbursement status to `PAID` if `payment_date <= AS_OF_DATE`; otherwise set it to `SCHEDULED`. Once the payment date is reached, a scheduled reimbursement may transition to `PAID`; append an `ExpenseClaimEvent` and audit record for that transition.

### E10 — Split-claim detection

Flag a split-claim pair when claims have the same employee and normalized merchant name and share at least one `ExpenseLine.category`; their `expense_date` values are no more than 3 calendar days apart; each claim's `total_usd` is between 90% (inclusive) and 99.99% (inclusive) of the same approval-band boundary; and their combined total is at least that boundary. Boundaries are USD 50, 1,000, 5,000, and 20,000. Record `SPLIT_CLAIM` findings on both claims.

## Audit

### AU1 — Routing decision audit

Every routing decision, including system auto-approval, stores an append-only `DecisionAudit` with an inputs snapshot, matched rule IDs, reason codes, computed path, `engine_version`, and outputs snapshot. Every risk-score recalculation also appends a `DecisionAudit` with decision kind `RISK_SCORE`. Inputs, outputs, and features must not contain ground-truth values. Record `SELF_APPROVAL_PREVENTED` when G5 escalation is applied.

### AU2 — Finding history

An `AuditFinding` is immutable after creation. Its initial status is `OPEN`; any resolution or dismissal is recorded as an append-only `AuditFindingEvent`. The current status is the latest event state, or `OPEN` if no status event exists.

### AU3 — Stable reason codes

Use these exact reason codes in events, findings, and `DecisionAudit.reason_codes`:

| condition | reason code |
|---|---|
| Invalid leave date order | `INVALID_DATE_RANGE` |
| Leave span has zero business days | `ZERO_BUSINESS_DAYS` |
| Employee inactive during requested leave | `EMPLOYEE_NOT_ACTIVE` |
| Leave tenure requirement unmet | `TENURE_INELIGIBLE` |
| Leave exceeds consecutive-day maximum | `MAX_CONSECUTIVE_DAYS` |
| Leave overlaps an active request | `OVERLAP` |
| Leave balance insufficient | `INSUFFICIENT_BALANCE` |
| Unpaid leave routing | `LEAVE_UNPAID` |
| Leave route of 1–3 days | `LEAVE_DAYS_1_3` |
| Leave route of 4–10 days | `LEAVE_DAYS_4_10` |
| Leave route over 10 days | `LEAVE_DAYS_GT_10` |
| Parental leave route | `PARENTAL_LEAVE` |
| Expense total below USD 50 with no E3 flags | `EXPENSE_LT_50_AUTO` |
| Expense total below USD 50 with E3 flags | `EXPENSE_LT_50_FLAGGED` |
| Expense total USD 50 to below USD 1,000 | `EXPENSE_50_1000` |
| Expense total USD 1,000 to below USD 5,000 | `EXPENSE_1000_5000` |
| Expense total USD 5,000 to below USD 20,000 | `EXPENSE_5000_20000` |
| Expense total USD 20,000 or more | `EXPENSE_GTE_20000` |
| International airfare | `AIRFARE_INTERNATIONAL` |
| Client-entertainment line over USD 250 | `CLIENT_ENTERTAINMENT_GT_250` |
| Gifts line over USD 250 | `GIFT_GT_250` |
| Per-line limit breached | `POLICY_LIMIT_BREACH` |
| Missing required receipt | `MISSING_RECEIPT` |
| Duplicate receipt hash | `DUPLICATE_RECEIPT` |
| Missing cost center | `MISSING_COST_CENTER` |
| Expense date outside employment | `DATE_OUTSIDE_EMPLOYMENT` |
| Expense date after AS_OF_DATE | `FUTURE_EXPENSE_DATE` |
| Detected split claim | `SPLIT_CLAIM` |
| Self-approval prevented | `SELF_APPROVAL_PREVENTED` |
| No approver resolved | `UNRESOLVED_APPROVER` |
| CEO manager step resolved to CHRO/HR head | `CEO_MANAGER_FALLBACK` |
| Duplicate reimbursement detected | `DUPLICATE_REIMBURSEMENT` |

If multiple E4 checks fail, record all applicable reason codes in this table's order and reject the submission once. L4 retains its explicit first-failure order.

## Dataset generation and evaluation

### D1 — Parent-first generation

Generate or reference employees, leave and expense policies, expense categories, cost centers, approval rules and category bridges, employee/cost-center assignments, and holidays first. Seed opening and accrual `LeaveLedgerEntry` rows, then derive the initial `LeaveBalance` snapshot. Create `LeaveRequest` and `ExpenseClaim` parent transactions before their event, line, approval-step, and audit children. Append request/claim events before any linked ledger entries; refresh leave-balance snapshots from the complete ledger. Create reimbursement rows only after E9 eligibility passes. Every child uses an existing valid parent ID.

### D2 — Baseline volume and scale

The full baseline contains exactly 400 employees, 6 leave policies, 800 leave requests, and 1,000 expense claims. Each expense claim has 1–10 lines. Starter and full datasets use the same generator with a scale parameter; changing scale must not change rule semantics or ID formats.

### D3 — Coverage and anomaly injection

Generate valid baseline rows first. Include valid leave spans that cross weekends/holidays, insufficient-balance rejection cases, missing-receipt exception paths, policy-limit exception cases, and multi-level approvals. Then inject and label rule-violation cases in `GroundTruthAnomaly`: negative leave balance; overlapping approved leave for one employee; expense date outside employment; split claims; missing cost center; approval by requester; duplicate reimbursement; duplicate receipt hash; missing receipt; policy-limit breach. Deliberate anomaly rows preserve valid primary keys, foreign keys, and enums per G1.

### D4 — Derived outcomes

Compute totals, balances, scores, statuses, dates, flags, and routing outcomes from source records and the documented rules. Never assign outcomes or ground-truth labels independently at random. The API and generator use the same deterministic rule engine.

### D5 — Data validation

Validate primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions, receipt and claim duplicate checks, policy selection, approval-path consistency, and reimbursement eligibility. Report failures explicitly; do not silently repair invalid rows. Business-rule anomalies are checked against their ground-truth labels and remain valid at the database-key and enum level.

### D6 — Exports and reproducibility

Export CSV, JSON, and SQL seed data plus a README, schema, data dictionary, generator command, fixed seed `20261022`, source manifest, and validation summary. Export known anomalies and expected decisions separately as both `ground_truth.csv` and `ground_truth.json`; never include them in input-feature files. Use `AS_OF_DATE = 2026-10-22`, sorted outputs, no wall-clock values, no UUID4, and no unseeded randomness. Run generation twice with the same seed and `AS_OF_DATE`; compare per-file row counts and checksums and require exact equality.

### D7 — Evaluation and provenance

Evaluate realistic distributions and meaningful variation; ID/join consistency; dependency and lifecycle consistency; derived-value reconciliation; normal, boundary, failure, and exception coverage; ground-truth separation; fixed-seed reproducibility; and lawful provenance. External data is optional, but generated scenario and transaction records remain synthetic under the project constitution. If a public source is consulted, record its URL, dataset/version, retrieval date, license/terms, attribution, transformations, and discarded fields. Never bypass access controls or use confidential or personal data; if suitability or license is unclear, use synthetic data and cite public data only for schema inspiration.

### D8 — Deterministic exception risk score

`LeaveRequest.risk_score` and `ExpenseClaim.risk_score` are the integer sum of weights for distinct currently open `AuditFinding.finding_code` values associated with that request or claim, capped at 100. Leave scores include findings on the request and its approval steps; expense scores include findings on the claim, its lines, approval steps, and reimbursements. Use these fixed weights:

| finding_code | weight |
|---|---:|
| `INVALID_DATE_RANGE` | 25 |
| `ZERO_BUSINESS_DAYS` | 20 |
| `EMPLOYEE_NOT_ACTIVE` | 40 |
| `TENURE_INELIGIBLE` | 25 |
| `MAX_CONSECUTIVE_DAYS` | 20 |
| `OVERLAP` | 35 |
| `INSUFFICIENT_BALANCE` | 30 |
| `POLICY_LIMIT_BREACH` | 20 |
| `MISSING_RECEIPT` | 15 |
| `DUPLICATE_RECEIPT` | 50 |
| `MISSING_COST_CENTER` | 30 |
| `DATE_OUTSIDE_EMPLOYMENT` | 50 |
| `FUTURE_EXPENSE_DATE` | 40 |
| `SPLIT_CLAIM` | 40 |
| `SELF_APPROVAL_PREVENTED` | 10 |
| `UNRESOLVED_APPROVER` | 25 |
| `DUPLICATE_REIMBURSEMENT` | 50 |

Repeated findings with the same code contribute once. Closing the last open finding of a code removes that code's weight from the next derived score. The score is a derived operational feature, never a ground-truth label.
