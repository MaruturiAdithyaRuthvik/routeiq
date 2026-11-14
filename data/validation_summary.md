# Validation summary

**PASS** — seed `20261022`, scale `full`.

Rows: `{"approval_rule": 28, "approval_rule_category": 23, "approval_step": 2224, "audit_finding": 203, "audit_finding_event": 0, "cost_center": 20, "decision_audit": 7507, "employee": 400, "employee_cost_center_assignment": 432, "expense_category": 10, "expense_claim": 1000, "expense_claim_event": 5814, "expense_line": 2009, "expense_policy": 50, "ground_truth_anomaly": 15, "ground_truth_decision": 14, "holiday": 40, "leave_balance": 2400, "leave_ledger_entry": 12937, "leave_policy": 6, "leave_request": 800, "leave_request_event": 3057, "reimbursement": 834}`

- PASS: primary keys and ID formats
- PASS: foreign keys and enums
- PASS: date ordering and lifecycle
- PASS: line totals, FX conversion, ledger/balance reconciliation
- PASS: approval steps and reimbursement eligibility
- PASS: ground-truth targets exist
