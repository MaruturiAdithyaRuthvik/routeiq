CREATE OR REPLACE VIEW public.v_leave_balance_live AS
WITH ledger_totals AS (
    SELECT
        employee_id,
        leave_policy_id,
        COALESCE(sum(delta_days) FILTER (WHERE entry_type = 'OPENING'), 0)::numeric(12,6) AS opening_days,
        COALESCE(sum(delta_days) FILTER (WHERE entry_type = 'ACCRUAL'), 0)::numeric(12,6) AS accrued_days,
        COALESCE(sum(delta_days) FILTER (
            WHERE entry_type = 'ADJUSTMENT'
               OR (entry_type = 'REVERSAL' AND effect_bucket = 'AVAILABLE')
        ), 0)::numeric(12,6) AS adjustments_days,
        COALESCE(sum(delta_days) FILTER (
            WHERE entry_type = 'DEBIT'
               OR (entry_type = 'REVERSAL' AND effect_bucket = 'USED')
        ), 0)::numeric(12,6) AS used_days,
        COALESCE(sum(delta_days) FILTER (
            WHERE entry_type IN ('RESERVE', 'RELEASE')
               OR (entry_type = 'REVERSAL' AND effect_bucket = 'RESERVED')
        ), 0)::numeric(12,6) AS pending_days
    FROM public.leave_ledger_entry
    WHERE entry_date <= DATE '2026-10-22'
    GROUP BY employee_id, leave_policy_id
)
SELECT
    employee.employee_id,
    leave_policy.leave_policy_id,
    DATE '2026-10-22' AS as_of_date,
    COALESCE(ledger_totals.opening_days, 0)::numeric(12,6) AS opening_days,
    COALESCE(ledger_totals.accrued_days, 0)::numeric(12,6) AS accrued_days,
    COALESCE(ledger_totals.adjustments_days, 0)::numeric(12,6) AS adjustments_days,
    COALESCE(ledger_totals.used_days, 0)::numeric(12,6) AS used_days,
    COALESCE(ledger_totals.pending_days, 0)::numeric(12,6) AS pending_days,
    (
        COALESCE(ledger_totals.opening_days, 0)
        + COALESCE(ledger_totals.accrued_days, 0)
        + COALESCE(ledger_totals.adjustments_days, 0)
        - COALESCE(ledger_totals.used_days, 0)
        - COALESCE(ledger_totals.pending_days, 0)
    )::numeric(12,6) AS available_days
FROM public.employee
CROSS JOIN public.leave_policy
LEFT JOIN ledger_totals
    ON ledger_totals.employee_id = employee.employee_id
   AND ledger_totals.leave_policy_id = leave_policy.leave_policy_id;

CREATE OR REPLACE VIEW public.v_claim_totals AS
SELECT
    claim.expense_claim_id,
    claim.employee_id,
    claim.cost_center_id,
    claim.status,
    claim.total_usd AS stored_total_usd,
    COALESCE(sum(line.amount_usd), 0)::numeric(14,2) AS line_total_usd,
    count(line.expense_line_id)::integer AS line_count,
    claim.total_usd = COALESCE(sum(line.amount_usd), 0)::numeric(14,2) AS totals_match
FROM public.expense_claim AS claim
LEFT JOIN public.expense_line AS line
    ON line.expense_claim_id = claim.expense_claim_id
GROUP BY claim.expense_claim_id;

CREATE OR REPLACE VIEW public.v_approval_queue AS
SELECT
    step.approval_step_id,
    CASE WHEN step.leave_request_id IS NOT NULL THEN 'LEAVE' ELSE 'EXPENSE' END AS request_type,
    COALESCE(step.leave_request_id, step.expense_claim_id) AS request_id,
    COALESCE(leave_request.employee_id, expense_claim.employee_id) AS employee_id,
    step.step_number,
    step.required_role,
    step.approver_employee_id AS approver_id,
    step.status,
    step.assigned_at,
    step.due_date,
    step.reason_code
FROM public.approval_step AS step
LEFT JOIN public.leave_request AS leave_request
    ON leave_request.leave_request_id = step.leave_request_id
LEFT JOIN public.expense_claim AS expense_claim
    ON expense_claim.expense_claim_id = step.expense_claim_id
WHERE step.status = 'PENDING';

CREATE OR REPLACE VIEW public.v_spend_by_cost_center AS
SELECT
    cost_center.cost_center_id,
    cost_center.name AS cost_center_name,
    cost_center.country,
    2026::smallint AS spend_year,
    cost_center.budget_usd,
    COALESCE(sum(claim.total_usd) FILTER (
        WHERE claim.status IN ('APPROVED', 'REIMBURSED')
    ), 0)::numeric(14,2) AS approved_spend_usd,
    (
        cost_center.budget_usd
        - COALESCE(sum(claim.total_usd) FILTER (
            WHERE claim.status IN ('APPROVED', 'REIMBURSED')
        ), 0)
    )::numeric(14,2) AS remaining_budget_usd,
    count(claim.expense_claim_id) FILTER (
        WHERE claim.status IN ('APPROVED', 'REIMBURSED')
    )::integer AS approved_claim_count
FROM public.cost_center
LEFT JOIN public.expense_claim AS claim
    ON claim.cost_center_id = cost_center.cost_center_id
   AND claim.expense_date >= DATE '2026-01-01'
   AND claim.expense_date < DATE '2027-01-01'
GROUP BY cost_center.cost_center_id;

CREATE OR REPLACE VIEW public.v_cycle_time AS
WITH all_events AS (
    SELECT
        'LEAVE'::text AS request_type,
        event.leave_request_id AS request_id,
        event.event_type,
        event.to_status,
        event.occurred_at
    FROM public.leave_request_event AS event
    UNION ALL
    SELECT
        'EXPENSE'::text AS request_type,
        event.expense_claim_id AS request_id,
        event.event_type,
        event.to_status,
        event.occurred_at
    FROM public.expense_claim_event AS event
),
submitted AS (
    SELECT request_type, request_id, min(occurred_at) AS submitted_at
    FROM all_events
    WHERE event_type = 'SUBMITTED'
    GROUP BY request_type, request_id
),
completed AS (
    SELECT DISTINCT ON (request_type, request_id)
        request_type,
        request_id,
        to_status AS terminal_status,
        occurred_at AS completed_at
    FROM all_events
    WHERE to_status IN ('APPROVED', 'REJECTED', 'CANCELLED')
    ORDER BY request_type, request_id, occurred_at
)
SELECT
    submitted.request_type,
    submitted.request_id,
    submitted.submitted_at,
    completed.completed_at,
    completed.terminal_status,
    extract(epoch FROM (completed.completed_at - submitted.submitted_at))::numeric(14,2) AS cycle_seconds,
    (completed.completed_at - submitted.submitted_at) AS cycle_duration
FROM submitted
JOIN completed USING (request_type, request_id)
WHERE completed.completed_at >= submitted.submitted_at;

GRANT SELECT ON
    public.v_leave_balance_live,
    public.v_claim_totals,
    public.v_approval_queue,
    public.v_spend_by_cost_center,
    public.v_cycle_time
TO routeiq_app, routeiq_evaluator;
