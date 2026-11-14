Business Context / Problem
Route leave and expense requests using policy, balances, budgets and approval authority.

Objective and Scope
Build a working solution for this end-to-end workflow: Route leave and expense requests using policy, balances, budgets and approval authority. The solution should expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Medium complexity means multiple related entities, conditional rules, at least one exception path and meaningful evaluation metrics.

Primary Actors / Systems
Business requester, process owner, approver, operations analyst and system administrator

Business Workflow and Rules
1. Generate/reference master data first: Employee, LeavePolicy, LeaveBalance, LeaveRequest, ExpensePolicy.
2. Generate dependent transaction/event records using valid parent IDs.
3. Apply business logic: Seed employee hierarchy and policies; compute leave accrual/balance; create leave requests with date ranges and business-day counts; create expense claims with line items, receipts metadata and cost centers; route by amount, category, country and manager; produce approval steps and reimbursement records only after final approval.
4. Persist state changes as explicit records/events where relevant; do not overwrite history.
5. Generate outcomes and ground-truth labels from documented rules, not independent random assignment.

Entities and Relationships
Core entities: Employee, LeavePolicy, LeaveBalance, LeaveRequest, ExpensePolicy, ExpenseClaim, ExpenseLine, CostCenter, ApprovalRule, ApprovalStep, Reimbursement. Define a primary key for every entity and foreign keys for every relationship. Document cardinality (1:1, 1:N, N:M), optional relationships, effective dates and lifecycle states. Use bridge tables for many-to-many relationships; retain event history for state changes; validate all joins. For deliberate anomaly cases, keep an issue_type/ground_truth label rather than silently corrupting unrelated rows.

ID / Nomenclature Conventions
EMP-000001; LVE-2026-000001; EXP-2026-000001; EXPL-<claim-id>-01; APR-<request-id>-01; RMB-2026-000001.

Synthetic Data Generation Instructions (Granular)
Step 1 — Write a data dictionary for: Employee, LeavePolicy, LeaveBalance, LeaveRequest, ExpensePolicy, ExpenseClaim, ExpenseLine, CostCenter, ApprovalRule, ApprovalStep, Reimbursement. For each field specify type, required/optional, allowed values, units, uniqueness and validation rule.
Step 2 — Create parent/master tables first, then child and event tables. Apply this domain-specific generation logic: Seed employee hierarchy and policies; compute leave accrual/balance; create leave requests with date ranges and business-day counts; create expense claims with line items, receipts metadata and cost centers; route by amount, category, country and manager; produce approval steps and reimbursement records only after final approval.
Step 3 — Apply deterministic IDs and naming: EMP-000001; LVE-2026-000001; EXP-2026-000001; EXPL-<claim-id>-01; APR-<request-id>-01; RMB-2026-000001. Keep counters zero-padded, IDs immutable, and referenced IDs exactly consistent across files.
Step 4 — Generate the baseline volume: Generate 400 employees, 6 leave policies, 800 leave requests and 1,000 expense claims with 1–10 lines each. Include overlapping leave, insufficient balance, weekend/holiday spans, missing receipt, duplicate receipt hash, policy limit breach and multi-level approval. Use a fixed seed (e.g. 20261022) and parameterize scale so starter and full datasets use the same generator.
Step 5 — Generate valid baseline records first, then inject labelled edge cases: Negative leave balance; same employee has overlapping approved leave; expense date outside employment dates; split claims to evade thresholds; missing cost center; approval by requester; duplicate reimbursement.
Step 6 — Calculate derived values (totals, balances, scores, statuses and dates) from source records rather than generating them independently.
Step 7 — Produce a separate ground_truth.csv/json for known anomalies, expected decisions or labels; never leak it into input features.
Step 8 — Run validation: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions and duplicate checks.
Step 9 — Export CSV/JSON/SQL seed data plus README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary.
Step 10 — Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.

Suggested Volume and Coverage
Generate 400 employees, 6 leave policies, 800 leave requests and 1,000 expense claims with 1–10 lines each. Include overlapping leave, insufficient balance, weekend/holiday spans, missing receipt, duplicate receipt hash, policy limit breach and multi-level approval.

Required Edge Cases / Negative Scenarios
Negative leave balance; same employee has overlapping approved leave; expense date outside employment dates; split claims to evade thresholds; missing cost center; approval by requester; duplicate reimbursement.

Validation Rules / Acceptance Criteria
Balance calculations are correct; approval path follows thresholds; duplicate claims are flagged; reimbursements exist only for eligible approved claims; all decision reasons are auditable.

Evaluation Focus for Generated Data
Review: (a) realistic distributions and meaningful variation; (b) consistent IDs and valid joins; (c) dependency/lifecycle consistency across entities; (d) correct derived values and reconciliation; (e) normal, boundary, failure and exception coverage; (f) separate ground truth; (g) fixed-seed reproducibility, documentation and lawful provenance.

Public Data Guidance / Lawful Use
External data is optional. If used, record source URL, dataset/version, retrieval date, license/terms, attribution, transformations and fields discarded. Use only data you are legally permitted to access and redistribute; do not bypass access controls or collect confidential/personal information. If licensing or suitability is unclear, use synthetic data and cite public reference data only for schema inspiration.