# RouteIQ Data Dictionary

This dictionary defines persisted fields, derived projections, and field-level constraints. `PK` means primary key; `FK` identifies the referenced primary key. Unless otherwise noted, IDs are immutable text values, timestamps are deterministic UTC values (never wall-clock generated), monetary fields use decimal arithmetic, and rows are append-only where they record events or findings. Baseline data must satisfy the validation rules. Ground-truth rows are isolated in the `ground_truth` schema and must not be joined into feature inputs.

## Employee

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| employee_id | varchar(10) | required, PK | `EMP-` followed by 6 digits | identifier | global | Immutable; match `^EMP-[0-9]{6}$`. |
| display_name | varchar(100) | required | Synthetic name | text | none | Non-empty; do not use real personal data. |
| country | char(2) | required | `IN`, `US`, `GB`, `DE`, `SG` | country code | none | Must map to `home_currency` per G2. |
| home_currency | char(3) | required | `INR`, `USD`, `GBP`, `EUR`, `SGD` | ISO-like code | none | Must equal the G2 mapping for `country`. |
| hire_date | date | required | ISO date | date | none | Must be on or before `AS_OF_DATE` for an active employee. |
| termination_date | date | optional | ISO date or null | date | none | If set, must be on or after `hire_date`. |
| manager_id | varchar(10) | optional, FK -> Employee.employee_id | Existing employee ID or null | identifier | none | Cannot equal `employee_id`; hierarchy must be acyclic. CEO has no manager. |
| functional_role | enum | required | `NONE`, `DEPT_HEAD`, `HR_PARTNER`, `FINANCE_CONTROLLER`, `CFO`, `COMPLIANCE_OFFICER` | role | none | Must be a G5 role. |
| system_role | enum | required | `REQUESTER`, `APPROVER`, `PROCESS_OWNER`, `ANALYST`, `ADMIN` | role | none | Exactly one system role per employee. |
| job_level | smallint | required | 1–10 | level | none | Integer in inclusive range 1..10. |
| is_ceo | boolean | required | true, false | boolean | exactly one true per dataset | If true, `manager_id` must be null; if false, the employee cannot be the hierarchy root. |

## LeavePolicy

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| leave_policy_id | varchar(7) | required, PK | `LPO-001`..`LPO-006` | identifier | global | Must match one of the six policies in L1. |
| name | varchar(32) | required | `Annual`, `Sick`, `Casual`, `Parental`, `Compassionate`, `Unpaid` | text | unique | Must match the name paired with the ID in L1. |
| annual_entitlement_days | decimal(6,2) | optional | 24, 12, 8, or null | days/year | none | Required for Annual, Sick, Casual; null for lump-sum and Unpaid policies. |
| carry_forward_max_days | decimal(6,2) | required | 0 or 10 | days | none | Exactly the value in L1; never negative. |
| max_consecutive_days | smallint | optional | 3, 5, 15, 20, 30, or null | calendar days | none | Exactly the value in L1; null only for Parental. |
| medical_certificate_after_days | smallint | optional | 2 or null | consecutive calendar days | none | 2 only for Sick; otherwise null. |
| tenure_required_months | smallint | required | 0 or 12 | months | none | Exactly the value in L1. |
| lump_sum_days | decimal(6,2) | required | 0, 5, 90, or null | days | none | Exactly the value in L1; null for Annual, Sick, Casual. |
| is_unpaid | boolean | required | true, false | boolean | none | True only for Unpaid; Unpaid has no balance. |
| effective_from | date | required | ISO date | date | part of policy interval | Must be earlier than `effective_to` when an end date exists. |
| effective_to | date | optional | ISO date or null | date | part of policy interval | Exclusive end date; must be later than `effective_from`. |

## LeaveBalance

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| leave_balance_id | varchar(64) | required, PK | `LBL-<employee_id>-<leave_policy_id>-2026` | identifier | global | Must encode the related employee, policy, and `balance_year`. |
| employee_id | varchar(10) | required, FK -> Employee.employee_id | Existing employee ID | identifier | with policy/year | Must reference an employee. |
| leave_policy_id | varchar(7) | required, FK -> LeavePolicy.leave_policy_id | Existing policy ID | identifier | with employee/year | Unpaid policy balance is zero. |
| balance_year | smallint | required | 2026 | year | with employee/policy | This dataset uses 2026; must match ID suffix. |
| as_of_date | date | required | 2026-10-22 | date | with employee/policy/year | Fixed evaluation date. |
| opening_days | decimal(12,6) | required | >= 0 | days | none | Equals opening ledger entries, subject to carry-forward cap. |
| accrued_days | decimal(12,6) | required | >= 0 | days | none | Equals accrual ledger entries through `as_of_date`. |
| adjustments_days | decimal(12,6) | required | signed | days | none | Equals adjustment and available-bucket reversal entries through `as_of_date`. |
| used_days | decimal(12,6) | required | >= 0 | days | none | Equals approved debit ledger entries net of reversals. |
| pending_days | decimal(12,6) | required | >= 0 | days | none | Equals active reservations net of releases and reversals. |
| available_days | decimal(12,6) | required | derived | days | none | Equals opening + accrued + adjustments - used - pending. Baseline must be >= 0; a labeled negative-balance anomaly may be below zero. |

## LeaveRequest

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| leave_request_id | varchar(17) | required, PK | `LVE-2026-` followed by 6 digits | identifier | global | Immutable; match `^LVE-2026-[0-9]{6}$`. |
| employee_id | varchar(10) | required, FK -> Employee.employee_id | Existing employee ID | identifier | none | Employee must exist; active status is evaluated from employment dates. |
| leave_policy_id | varchar(7) | required, FK -> LeavePolicy.leave_policy_id | Existing policy ID | identifier | none | Policy must be effective for the leave dates. |
| start_date | date | required | ISO date | date | none | Must be on or before `end_date`. |
| end_date | date | required | ISO date | date | none | Must be on or after `start_date`. |
| business_days | smallint | required | >= 0 | business days | none | Derived inclusively under G4 using employee country; zero causes `ZERO_BUSINESS_DAYS`. |
| status | enum | required | `DRAFT`, `SUBMITTED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `CANCELLED` | state | none | Only L7 transitions are legal. |
| submitted_at | timestamp with time zone | optional | Deterministic UTC timestamp or null | timestamp | none | Required on successful submission; not generated from wall-clock time. |
| medical_certificate_required | boolean | required | true, false | boolean | none | Derived true only for Sick leave with inclusive calendar span > 2 days. |
| risk_score | smallint | required, derived projection | 0–100 | points | none | Derived by D8 from distinct open findings on the request and its approval steps; historical values are preserved in DecisionAudit.outputs_snapshot. |
| reason | varchar(500) | optional | Synthetic text or null | text | none | Must not contain personal or confidential data. |

## ExpensePolicy

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| expense_policy_id | varchar(8) | required, PK | `XPO-` followed by 4 digits | identifier | global | Immutable; match `^XPO-[0-9]{4}$`. |
| category | varchar(32) | required, FK -> ExpenseCategory.category | E1 category values | category | with country/version | Must reference an E1 category. |
| country | char(2) | required | `IN`, `US`, `GB`, `DE`, `SG` | country code | with category/version | Policy jurisdiction is the employee's country. |
| per_line_limit_usd | decimal(12,2) | required | > 0 | USD per line | none | USD reporting limit; the effective policy is selected by expense date. |
| receipt_threshold_usd | decimal(12,2) | required | >= 0 | USD per line | none | A receipt is required only when a line is strictly greater than this threshold. |
| effective_from | date | required | ISO date | date | part of version | Inclusive start date. |
| effective_to | date | optional | ISO date or null | date | part of version | Exclusive end date; must be later than `effective_from`; active intervals for the same category/country cannot overlap. |
| version | smallint | required | positive integer | version | with category/country | Versions increase for successive policy revisions. |

## ExpenseCategory

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| category | varchar(32) | required, PK | `MEALS`, `LODGING`, `AIRFARE`, `GROUND_TRANSPORT`, `SOFTWARE`, `OFFICE_SUPPLIES`, `TRAINING`, `CLIENT_ENTERTAINMENT`, `GIFTS`, `COMMUNICATION` | category | global | Exactly one lookup row per E1 category. |
| description | varchar(120) | required | Synthetic concise description | text | none | Non-empty; no additional categories may be introduced. |

## ExpenseClaim

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| expense_claim_id | varchar(17) | required, PK | `EXP-2026-` followed by 6 digits | identifier | global | Immutable; match `^EXP-2026-[0-9]{6}$`. |
| employee_id | varchar(10) | required, FK -> Employee.employee_id | Existing employee ID | identifier | none | Must reference the claimant. |
| merchant_name | varchar(120) | required | Synthetic merchant name | text | none | Non-empty; no real personal data. |
| merchant_country | char(2) | required | `IN`, `US`, `GB`, `DE`, `SG` | country code | none | Must be a G2 country. |
| expense_date | date | required | ISO date | date | none | E4 rejects future or out-of-employment dates at submit. |
| cost_center_id | varchar(7) | optional, FK -> CostCenter.cost_center_id | Existing cost-center ID or null | identifier | none | Null is a detectable E3 finding and E4 hard reject for baseline submissions; labeled anomalies may retain null. |
| total_usd | decimal(14,2) | required | > 0 | USD | none | Derived as exact sum of the claim's rounded `ExpenseLine.amount_usd` values; claim has 1–10 lines. |
| status | enum | required | `DRAFT`, `SUBMITTED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `CANCELLED`, `REIMBURSED` | state | none | Only E8 transitions are legal. |
| submitted_at | timestamp with time zone | optional | Deterministic UTC timestamp or null | timestamp | none | Required on successful submission; not generated from wall-clock time. |
| risk_score | smallint | required, derived projection | 0–100 | points | none | Derived by D8 from distinct open findings on the claim, its lines, approval steps, and reimbursements; historical values are preserved in DecisionAudit.outputs_snapshot. |

## ExpenseLine

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| expense_line_id | varchar(23) | required, PK | `EXPL-<expense_claim_id>-NN` | identifier | global | Immutable; line suffix is sequential and zero-padded. |
| expense_claim_id | varchar(17) | required, FK -> ExpenseClaim.expense_claim_id | Existing claim ID | identifier | with line_number | Parent claim must exist. |
| line_number | smallint | required | 1–10 | ordinal | with claim | Sequential without gaps within a claim. |
| category | varchar(32) | required, FK -> ExpenseCategory.category | E1 category values | category | none | Must have one effective ExpensePolicy for employee country and expense date. |
| expense_policy_id | varchar(8) | required, FK -> ExpensePolicy.expense_policy_id | Existing policy ID | identifier | none | Policy category must equal line category and policy country must equal claimant country. |
| description | varchar(250) | optional | Synthetic text or null | text | none | No personal or confidential data. |
| amount | decimal(12,2) | required | > 0 | source currency | none | Must be a positive finite decimal. |
| currency | char(3) | required | `INR`, `USD`, `GBP`, `EUR`, `SGD` | currency | none | Must have the G2 static FX rate. |
| fx_rate_to_usd | decimal(8,5) | required | G2 rates | USD per source currency unit | none | Must exactly match the rate for `currency`. |
| amount_usd | decimal(12,2) | required | derived, > 0 | USD | none | Equals G2 round-half-up of `amount * fx_rate_to_usd`. |
| receipt_present | boolean | required | true, false | boolean | none | If false, all receipt metadata fields are null. |
| receipt_id | varchar(64) | optional | Synthetic identifier or null | identifier | unique when non-null | Required when a receipt is present. |
| receipt_hash | char(64) | optional | Lowercase hexadecimal SHA-256 or null | digest | deliberately non-unique | Required when a receipt is present; duplicate hashes remain loadable for detection/anomalies. |
| file_type | enum | optional | `PDF`, `JPG`, `JPEG`, `PNG`, `HEIC`, or null | file type | none | Required when a receipt is present. |
| size_kb | decimal(10,2) | optional | > 0 or null | kilobytes | none | Required when a receipt is present. |

## CostCenter

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| cost_center_id | varchar(7) | required, PK | `CC-` followed by 4 digits | identifier | global | Immutable; match `^CC-[0-9]{4}$`. |
| name | varchar(100) | required | Synthetic name | text | unique | Non-empty. |
| country | char(2) | required | G2 countries | country code | none | Must match the operating country for its assigned employees. |
| owner_employee_id | varchar(10) | required, FK -> Employee.employee_id | Existing employee ID | identifier | none | Employee is the cost-center owner and DEPT_HEAD approver for expense routing. |
| budget_year | smallint | required | 2026 | year | with cost center | Fixed dataset year. |
| budget_usd | decimal(14,2) | required | >= 0 | USD | none | Informational annual budget; no unprovided budget rejection threshold is inferred. |

## ApprovalRule

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| approval_rule_id | varchar(7) | required, PK | `ARL-` followed by 3 digits | identifier | global | Immutable; match `^ARL-[0-9]{3}$`. |
| rule_code | varchar(40) | required | Stable business rule code | text | unique | Must reference a rule ID or named branch in BUSINESS_RULES.md. |
| request_type | enum | required | `LEAVE`, `EXPENSE` | type | none | Must match the rule's scope. |
| priority | smallint | required | positive integer | order | unique within scope/version | Lower number is evaluated first; ties are invalid. |
| required_role | enum | required | G5 functional roles plus `MANAGER`, `SYSTEM` | role | none | `SYSTEM` is only valid for auto-approval. |
| condition_description | varchar(500) | required | Documented human-readable condition | text | none | Must describe the matching condition without executable or opaque code. |
| designated_employee_id | varchar(10) | optional, FK -> Employee.employee_id | Existing employee ID or null | identifier | none | Required for designated holders where applicable; null for dynamically resolved roles. |
| effective_from | date | required | ISO date | date | part of version | Inclusive start date. |
| effective_to | date | optional | ISO date or null | date | part of version | Exclusive end date; must be later than `effective_from`; active intervals for the same rule_code/request_type cannot overlap. |
| version | smallint | required | positive integer | version | with rule_code | Increases when the rule definition changes. |
| is_active | boolean | required | true, false | boolean | none | Only active and effective rules are eligible. |

## ApprovalStep

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| approval_step_id | varchar(64) | required, PK | `APR-<request_id>-NN` | identifier | global | Immutable; suffix is sequential and zero-padded per request. |
| leave_request_id | varchar(17) | optional, FK -> LeaveRequest.leave_request_id | Existing request ID or null | identifier | with step_number | Exactly one of `leave_request_id` and `expense_claim_id` is set. |
| expense_claim_id | varchar(17) | optional, FK -> ExpenseClaim.expense_claim_id | Existing claim ID or null | identifier | with step_number | Exactly one of `leave_request_id` and `expense_claim_id` is set. |
| step_number | smallint | required | positive integer | sequence | with request | Sequential in computed approval path. |
| required_role | enum | required | `MANAGER`, `DEPT_HEAD`, `HR_PARTNER`, `FINANCE_CONTROLLER`, `CFO`, `COMPLIANCE_OFFICER`, `SYSTEM` | role | none | Must match the computed path; SYSTEM is only for auto-approval. |
| approver_employee_id | varchar(10) | optional, FK -> Employee.employee_id | Existing employee ID or null | identifier | none | Required for non-SYSTEM steps; null for SYSTEM. Baseline human approver must have `system_role = APPROVER` and differ from requester; a labeled SELF_APPROVAL anomaly may reference the requester while preserving the FK. |
| status | enum | required | `PENDING`, `APPROVED`, `REJECTED` | state | none | SYSTEM auto-approval is stored as APPROVED. |
| assigned_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Derived from deterministic workflow time. |
| due_date | date | required | ISO date | date | none | Three business days after assignment per E7. |
| decided_at | timestamp with time zone | optional | Deterministic UTC timestamp or null | timestamp | none | Required for terminal step status; not earlier than `assigned_at`. |
| reason_code | varchar(64) | optional | Documented reason code or null | code | none | Required when decision or escalation has a reason. |

## Reimbursement

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| reimbursement_id | varchar(15) | required, PK | `RMB-2026-` followed by 6 digits | identifier | global | Immutable; match `^RMB-2026-[0-9]{6}$`. |
| expense_claim_id | varchar(17) | required, FK -> ExpenseClaim.expense_claim_id | Existing claim ID | identifier | deliberately not unique | Baseline permits at most one per claim by E9; duplicate reimbursements are loadable labeled anomalies. |
| amount_home_currency | decimal(14,2) | required | >= 0 | employee home currency | none | Equals approved USD total converted using G2 FX and round-half-up. |
| home_currency | char(3) | required | G2 currencies | currency | none | Must equal claimant's home currency. |
| payment_date | date | required | ISO date | date | none | Exactly five employee-country business days after final approval. |
| status | enum | required | `SCHEDULED`, `PAID` | state | none | PAID iff `payment_date <= AS_OF_DATE`; SCHEDULED otherwise. |
| created_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Set from final approval event; no wall-clock time. |
| paid_at | timestamp with time zone | optional | Deterministic UTC timestamp or null | timestamp | none | Required only when status is PAID; must be on/after `payment_date`. |
| payment_reference | varchar(64) | optional | Synthetic reference or null | identifier | unique when non-null | Must not contain real banking information. |

## Holiday

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| holiday_id | varchar(16) | required, PK | `HOL-2026-<country>-NN` | identifier | global | Must identify one G3 illustrative holiday. |
| country | char(2) | required | G2 countries | country code | with holiday_date | Must be a supported country. |
| holiday_date | date | required | Dates listed in G3 | date | with country | Must fall in calendar year 2026. |
| holiday_name | varchar(64) | required | `Illustrative holiday NN` | text | none | Marked synthetic/illustrative; not legal holiday advice. |
| is_illustrative | boolean | required | true | boolean | none | Always true for this dataset. |

## LeaveLedgerEntry

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| leave_ledger_entry_id | varchar(18) | required, PK | `LLE-2026-` followed by 6 digits | identifier | global | Immutable and sequentially allocated. |
| employee_id | varchar(10) | required, FK -> Employee.employee_id | Existing employee ID | identifier | none | Must match the balance owner. |
| leave_policy_id | varchar(7) | required, FK -> LeavePolicy.leave_policy_id | Existing policy ID | identifier | none | Must match the affected balance. |
| leave_request_id | varchar(17) | optional, FK -> LeaveRequest.leave_request_id | Existing request ID or null | identifier | none | Required for RESERVE, RELEASE, and DEBIT linked to a request. |
| entry_type | enum | required | `OPENING`, `ACCRUAL`, `RESERVE`, `RELEASE`, `DEBIT`, `ADJUSTMENT`, `REVERSAL` | type | none | Must have the matching effect bucket and sign per L3. |
| effect_bucket | enum | required | `AVAILABLE`, `RESERVED`, `USED` | balance component | none | OPENING/ACCRUAL/ADJUSTMENT affect AVAILABLE; RESERVE/RELEASE affect RESERVED; DEBIT affects USED; REVERSAL mirrors its source. |
| delta_days | decimal(12,6) | required | Signed decimal | days | none | OPENING/ACCRUAL/RESERVE/DEBIT positive for balance-bearing policies; Unpaid RESERVE/RELEASE/DEBIT markers are zero; RELEASE is negative otherwise; ADJUSTMENT is signed; REVERSAL exactly negates source delta. |
| prior_year_closing_days | decimal(12,6) | optional | >= 0 or null | days | none | Required for OPENING entries; null for all other types. `delta_days` equals the lesser of this value and the policy carry-forward cap. |
| entry_date | date | required | ISO date | date | none | Not after `AS_OF_DATE` for evaluated snapshots. |
| reversal_of_entry_id | varchar(18) | optional, FK -> LeaveLedgerEntry.leave_ledger_entry_id | Existing entry ID or null | identifier | unique when non-null | Required only for REVERSAL; reversal must reference one unreversed non-REVERSAL entry. |
| source_event_id | varchar(20) | optional, FK -> LeaveRequestEvent.event_id | Existing event ID or null | identifier | none | When present, event belongs to the same leave request. |

## LeaveRequestEvent

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| event_id | varchar(20) | required, PK | `LRE-2026-` followed by 6 digits | identifier | global | Immutable and sequentially allocated. |
| leave_request_id | varchar(17) | required, FK -> LeaveRequest.leave_request_id | Existing request ID | identifier | with sequence_number | Parent request must exist. |
| sequence_number | integer | required | Positive integer | sequence | with request | Strictly increasing; events are never updated or deleted. |
| event_type | enum | required | `CREATED`, `SUBMISSION_ATTEMPT`, `SUBMITTED`, `APPROVAL_STARTED`, `APPROVAL_DECIDED`, `CANCELLED` | type | none | Must describe the recorded state change or failed attempt. |
| from_status | enum | optional | LeaveRequest statuses or null | state | none | Must match immediately prior state when a transition occurs. |
| to_status | enum | optional | LeaveRequest statuses or null | state | none | Must be a legal L7 transition; failed submit attempt may have DRAFT -> DRAFT. |
| occurred_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Nondecreasing by request sequence; no wall-clock generation. |
| actor_employee_id | varchar(10) | optional, FK -> Employee.employee_id | Existing employee ID or null | identifier | none | Null only for system-generated events. |
| reason_code | varchar(64) | optional | Documented reason code or null | code | none | Set for rejected attempts, decisions, and escalations. |

## ExpenseClaimEvent

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| event_id | varchar(20) | required, PK | `ECE-2026-` followed by 6 digits | identifier | global | Immutable and sequentially allocated. |
| expense_claim_id | varchar(17) | required, FK -> ExpenseClaim.expense_claim_id | Existing claim ID | identifier | with sequence_number | Parent claim must exist. |
| sequence_number | integer | required | Positive integer | sequence | with claim | Strictly increasing; events are never updated or deleted. |
| event_type | enum | required | `CREATED`, `SUBMISSION_ATTEMPT`, `SUBMITTED`, `APPROVAL_STARTED`, `APPROVAL_DECIDED`, `CANCELLED`, `REIMBURSEMENT_CREATED`, `REIMBURSEMENT_PAID` | type | none | Must describe the recorded state change or failed attempt. |
| from_status | enum | optional | ExpenseClaim statuses or null | state | none | Must match immediately prior state when a transition occurs. |
| to_status | enum | optional | ExpenseClaim statuses or null | state | none | Must be a legal E8 transition; failed submit attempt may have DRAFT -> DRAFT, and REIMBURSEMENT_PAID records REIMBURSED -> REIMBURSED while the payload records reimbursement status. |
| occurred_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Nondecreasing by claim sequence; no wall-clock generation. |
| actor_employee_id | varchar(10) | optional, FK -> Employee.employee_id | Existing employee ID or null | identifier | none | Null only for system-generated events. |
| reason_code | varchar(64) | optional | Documented reason code or null | code | none | Set for rejected attempts, decisions, and escalations. |
| event_payload | jsonb | required | JSON object | structured data | none | REIMBURSEMENT_PAID records the reimbursement ID and prior/new reimbursement status; no ground-truth values. |

## DecisionAudit

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| decision_audit_id | varchar(20) | required, PK | `DAU-2026-` followed by 6 digits | identifier | global | Immutable and sequentially allocated. |
| leave_request_id | varchar(17) | optional, FK -> LeaveRequest.leave_request_id | Existing request ID or null | identifier | none | Exactly one request FK is set. |
| expense_claim_id | varchar(17) | optional, FK -> ExpenseClaim.expense_claim_id | Existing claim ID or null | identifier | none | Exactly one request FK is set. |
| decision_kind | enum | required | `SUBMIT_VALIDATION`, `ROUTING`, `APPROVAL`, `REIMBURSEMENT_ELIGIBILITY`, `RISK_SCORE` | type | none | Must identify the decision being audited. |
| inputs_snapshot | jsonb | required | JSON object | structured data | none | Contains decision inputs only; must exclude all ground-truth fields and labels. |
| outputs_snapshot | jsonb | required | JSON object | structured data | none | Contains the decision outputs, including `risk_score` when calculated; must exclude ground truth. |
| matched_rule_ids | text[] | required | Stable IDs from BUSINESS_RULES.md | rule IDs | none | Sorted, unique, and all IDs must exist in the rules document. |
| reason_codes | text[] | required | Documented codes | codes | none | Sorted and unique; empty only when no reason applies. |
| computed_path | jsonb | required | Ordered role/step array | structured data | none | Must equal the path resolved by the engine. |
| engine_version | varchar(32) | required | Semantic or commit version | version | none | Non-empty and immutable for this decision. |
| recorded_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Append-only; no wall-clock generation. |

## EmployeeCostCenterAssignment

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| employee_id | varchar(10) | required, PK part, FK -> Employee.employee_id | Existing employee ID | identifier | with cost center/effective_from | Employee must exist. |
| cost_center_id | varchar(7) | required, PK part, FK -> CostCenter.cost_center_id | Existing cost-center ID | identifier | with employee/effective_from | Cost center must exist. |
| effective_from | date | required, PK part | ISO date | date | with employee/cost center | Inclusive start; intervals for the same pair cannot overlap. |
| effective_to | date | optional | ISO date or null | date | none | Exclusive end; must be later than `effective_from`; intervals for the same rule/category cannot overlap. |
| allocation_pct | decimal(5,2) | required | > 0 and <= 100 | percent | none | For an employee, overlapping active assignments' allocations must sum to at most 100%. |

## ApprovalRuleCategory

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| approval_rule_id | varchar(7) | required, PK part, FK -> ApprovalRule.approval_rule_id | Existing rule ID | identifier | with category/effective_from | Rule must exist. |
| category | varchar(32) | required, PK part, FK -> ExpenseCategory.category | E1 categories | category | with rule/effective_from | Must reference a supported expense category. |
| effective_from | date | required, PK part | ISO date | date | with rule/category | Inclusive start date. |
| effective_to | date | optional | ISO date or null | date | none | Exclusive end; must be later than `effective_from`. |

## AuditFinding

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| audit_finding_id | varchar(18) | required, PK | `AFN-2026-` followed by 6 digits | identifier | global | Immutable and sequentially allocated. |
| leave_request_id | varchar(17) | optional, FK -> LeaveRequest.leave_request_id | Existing request ID or null | identifier | none | Exactly one target FK is set across all target fields. |
| expense_claim_id | varchar(17) | optional, FK -> ExpenseClaim.expense_claim_id | Existing claim ID or null | identifier | none | Exactly one target FK is set across all target fields. |
| expense_line_id | varchar(23) | optional, FK -> ExpenseLine.expense_line_id | Existing line ID or null | identifier | none | Exactly one target FK is set across all target fields. |
| approval_step_id | varchar(64) | optional, FK -> ApprovalStep.approval_step_id | Existing step ID or null | identifier | none | Exactly one target FK is set across all target fields. |
| reimbursement_id | varchar(15) | optional, FK -> Reimbursement.reimbursement_id | Existing reimbursement ID or null | identifier | none | Exactly one target FK is set across all target fields. |
| finding_code | enum | required | `INVALID_DATE_RANGE`, `ZERO_BUSINESS_DAYS`, `EMPLOYEE_NOT_ACTIVE`, `TENURE_INELIGIBLE`, `MAX_CONSECUTIVE_DAYS`, `OVERLAP`, `INSUFFICIENT_BALANCE`, `POLICY_LIMIT_BREACH`, `MISSING_RECEIPT`, `DUPLICATE_RECEIPT`, `MISSING_COST_CENTER`, `DATE_OUTSIDE_EMPLOYMENT`, `FUTURE_EXPENSE_DATE`, `SPLIT_CLAIM`, `SELF_APPROVAL_PREVENTED`, `UNRESOLVED_APPROVER`, `DUPLICATE_REIMBURSEMENT` | code | none | Must map to a documented rule, E3/E10 finding, or routing exception. |
| severity | enum | required | `INFO`, `WARNING`, `ERROR` | severity | none | Must reflect operational impact. |
| status | enum | required | `OPEN` | initial state | none | Immutable creation state. Current state is derived from the latest AuditFindingEvent, or OPEN if none exists. |
| details | jsonb | required | JSON object | structured data | none | Synthetic evidence only; must not contain ground truth. |
| detected_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Append-only detection time. |

## AuditFindingEvent

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| finding_event_id | varchar(18) | required, PK | `AFE-2026-` followed by 6 digits | identifier | global | Immutable and sequentially allocated. |
| audit_finding_id | varchar(18) | required, FK -> AuditFinding.audit_finding_id | Existing finding ID | identifier | with sequence_number | Parent finding must exist. |
| sequence_number | integer | required | Positive integer | sequence | with finding | Strictly increasing; events are never updated or deleted. |
| from_status | enum | required | `OPEN` | state | none | Must match the latest status of the finding. |
| to_status | enum | required | `RESOLVED`, `DISMISSED` | state | none | A finding may be closed once; closed findings cannot be reopened. |
| occurred_at | timestamp with time zone | required | Deterministic UTC timestamp | timestamp | none | Nondecreasing by finding sequence; no wall-clock generation. |
| actor_employee_id | varchar(10) | optional, FK -> Employee.employee_id | Existing employee ID or null | identifier | none | Null only for system-generated resolution. |
| reason_code | varchar(64) | required | Documented reason code | code | none | Non-empty explanation for closure. |

## GroundTruthAnomaly (ground_truth schema only)

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| ground_truth_anomaly_id | varchar(18) | required, PK | `GTA-2026-` followed by 6 digits | identifier | global | Immutable and allocated independently from input data. |
| leave_request_id | varchar(17) | optional, FK -> public.LeaveRequest.leave_request_id | Existing request ID or null | identifier | none | Exactly one target FK among anomaly target fields is set. |
| leave_balance_id | varchar(64) | optional, FK -> public.LeaveBalance.leave_balance_id | Existing balance ID or null | identifier | none | Exactly one target FK among anomaly target fields is set. |
| expense_claim_id | varchar(17) | optional, FK -> public.ExpenseClaim.expense_claim_id | Existing claim ID or null | identifier | none | Exactly one target FK among anomaly target fields is set. |
| expense_line_id | varchar(23) | optional, FK -> public.ExpenseLine.expense_line_id | Existing line ID or null | identifier | none | Exactly one target FK among anomaly target fields is set. |
| approval_step_id | varchar(64) | optional, FK -> public.ApprovalStep.approval_step_id | Existing step ID or null | identifier | none | Exactly one target FK among anomaly target fields is set. |
| reimbursement_id | varchar(15) | optional, FK -> public.Reimbursement.reimbursement_id | Existing reimbursement ID or null | identifier | none | Exactly one target FK among anomaly target fields is set. |
| issue_type | enum | required | `NEGATIVE_LEAVE_BALANCE`, `OVERLAPPING_APPROVED_LEAVE`, `EXPENSE_OUTSIDE_EMPLOYMENT`, `FUTURE_EXPENSE_DATE`, `SPLIT_CLAIM`, `MISSING_COST_CENTER`, `SELF_APPROVAL`, `DUPLICATE_REIMBURSEMENT`, `MISSING_RECEIPT`, `DUPLICATE_RECEIPT`, `POLICY_LIMIT_BREACH`, `INSUFFICIENT_BALANCE`, `ZERO_BUSINESS_DAY_SPAN` | label | none | Must describe a deliberately injected, loadable anomaly. |
| violation_rule_ids | text[] | required | Stable rule IDs | rule IDs | none | Sorted, unique and all references must exist in BUSINESS_RULES.md. |
| expected_finding_code | varchar(64) | optional | AuditFinding code or null | code | none | Describes the expected detector output; not an input feature. |
| label | varchar(32) | required | `ANOMALY` | label | none | Ground truth only. |
| details | jsonb | required | JSON object | structured data | none | Evaluation-only explanatory data; never exposed as a feature. |

## GroundTruthDecision (ground_truth schema only)

| field | type | required/optional | allowed values | units | uniqueness | validation rule |
|---|---|---|---|---|---|---|
| ground_truth_decision_id | varchar(18) | required, PK | `GTD-2026-` followed by 6 digits | identifier | global | Immutable and allocated independently from input data. |
| leave_request_id | varchar(17) | optional, FK -> public.LeaveRequest.leave_request_id | Existing request ID or null | identifier | one decision per target | Exactly one target request FK is set. |
| expense_claim_id | varchar(17) | optional, FK -> public.ExpenseClaim.expense_claim_id | Existing claim ID or null | identifier | one decision per target | Exactly one target request FK is set. |
| expected_status | varchar(32) | required | Status valid for target request type | state | none | Must be a valid expected outcome, not a feature. |
| expected_approval_path | jsonb | required | Ordered role/step array | structured data | none | Represents the documented expected route. |
| expected_reason_codes | text[] | required | Documented reason codes | codes | none | Sorted and unique. |
| matched_rule_ids | text[] | required | Stable rule IDs | rule IDs | none | Sorted, unique and all IDs must exist in BUSINESS_RULES.md. |
| expected_reimbursement | boolean | optional | true, false, or null | boolean | none | Null for leave; derived from E9 for expense. |
| expected_risk_score | smallint | optional | 0–100 or null | points | none | Evaluation-only expected value computed by D8; never included in input features. |
| evaluation_metric | varchar(64) | optional | Documented metric key or null | metric | none | Evaluation-only; never included in input features. |
