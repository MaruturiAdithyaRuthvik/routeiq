#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
    cp .env.example .env
fi

docker compose up -d --wait db

docker compose exec -T db sh -c \
    'PGPASSWORD="$ROUTEIQ_APP_PASSWORD" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U routeiq_app_login -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM public.v_leave_balance_live"' \
    >/dev/null

if docker compose exec -T db sh -c \
    'PGPASSWORD="$ROUTEIQ_APP_PASSWORD" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U routeiq_app_login -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM ground_truth.ground_truth_anomaly"' \
    >/dev/null 2>&1; then
    printf 'Application database role can read ground_truth unexpectedly\n' >&2
    exit 1
fi

docker compose exec -T db sh -c \
    'PGPASSWORD="$ROUTEIQ_EVALUATOR_PASSWORD" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U routeiq_evaluator_login -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM ground_truth.ground_truth_anomaly"' \
    >/dev/null

db_psql() {
    docker compose exec -T db sh -c \
        'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' \
        sh "$@"
}

db_psql -f /opt/routeiq/db/schema.sql
db_psql -f /opt/routeiq/db/views.sql

missing_tables="$(db_psql -Atqc "
WITH expected(schema_name, table_name) AS (
    VALUES
        ('public', 'employee'),
        ('public', 'leave_policy'),
        ('public', 'leave_balance'),
        ('public', 'leave_request'),
        ('public', 'expense_category'),
        ('public', 'expense_policy'),
        ('public', 'expense_claim'),
        ('public', 'expense_line'),
        ('public', 'cost_center'),
        ('public', 'approval_rule'),
        ('public', 'approval_step'),
        ('public', 'reimbursement'),
        ('public', 'holiday'),
        ('public', 'leave_ledger_entry'),
        ('public', 'leave_request_event'),
        ('public', 'expense_claim_event'),
        ('public', 'decision_audit'),
        ('public', 'employee_cost_center_assignment'),
        ('public', 'approval_rule_category'),
        ('public', 'audit_finding'),
        ('public', 'audit_finding_event'),
        ('ground_truth', 'ground_truth_anomaly'),
        ('ground_truth', 'ground_truth_decision')
)
SELECT string_agg(expected.schema_name || '.' || expected.table_name, ', ' ORDER BY expected.schema_name, expected.table_name)
FROM expected
WHERE NOT EXISTS (
    SELECT 1
    FROM information_schema.tables AS actual
    WHERE actual.table_schema = expected.schema_name
      AND actual.table_name = expected.table_name
      AND actual.table_type = 'BASE TABLE'
);
")"

if [[ -n "$missing_tables" ]]; then
    printf 'Missing database tables: %s\n' "$missing_tables" >&2
    exit 1
fi

missing_views="$(db_psql -Atqc "
SELECT string_agg(required.view_name, ', ' ORDER BY required.view_name)
FROM (VALUES
    ('v_leave_balance_live'),
    ('v_claim_totals'),
    ('v_approval_queue'),
    ('v_spend_by_cost_center'),
    ('v_cycle_time')
) AS required(view_name)
WHERE NOT EXISTS (
    SELECT 1
    FROM information_schema.views AS actual
    WHERE actual.table_schema = 'public'
      AND actual.table_name = required.view_name
);
")"

if [[ -n "$missing_views" ]]; then
    printf 'Missing database views: %s\n' "$missing_views" >&2
    exit 1
fi

reference_counts="$(db_psql -Atqc "
SELECT
    (SELECT count(*) FROM public.holiday) || ',' ||
    (SELECT count(*) FROM public.expense_policy) || ',' ||
    (SELECT count(*) FROM public.leave_policy);
")"
if [[ "$reference_counts" != "40,50,6" ]]; then
    printf 'Unexpected reference fixture counts: %s (expected 40,50,6)\n' "$reference_counts" >&2
    exit 1
fi

db_psql -f - <<'SQL'
BEGIN;

DO $$
DECLARE
    manager_id varchar(10);
BEGIN
    SELECT employee_id
    INTO manager_id
    FROM public.employee
    WHERE is_ceo
    ORDER BY employee_id
    LIMIT 1;

    IF manager_id IS NULL THEN
        INSERT INTO public.employee (
            employee_id, display_name, country, home_currency, hire_date,
            functional_role, system_role, job_level, is_ceo
        ) VALUES (
            'EMP-999998', 'Database smoke CEO', 'US', 'USD', DATE '2020-01-01',
            'HR_PARTNER', 'APPROVER', 10, true
        );
        manager_id := 'EMP-999998';
    END IF;

    INSERT INTO public.employee (
        employee_id, display_name, country, home_currency, hire_date,
        manager_id, functional_role, system_role, job_level, is_ceo, cost_center_id
    ) VALUES (
        'EMP-999999', 'Database smoke employee', 'US', 'USD', DATE '2020-01-01',
        manager_id, 'NONE', 'REQUESTER', 1, false, 'CC-9999'
    );

    INSERT INTO public.cost_center (
        cost_center_id, name, country, owner_employee_id, budget_year, budget_usd
    ) VALUES (
        'CC-9999', 'Database smoke cost center', 'US', 'EMP-999999', 2026, 1000.00
    );
END
$$;

SET CONSTRAINTS ALL IMMEDIATE;

INSERT INTO public.leave_request (
    leave_request_id, employee_id, leave_policy_id, start_date, end_date,
    business_days, status, medical_certificate_required, risk_score
) VALUES (
    'LVE-2026-999999', 'EMP-999999', 'LPO-001', DATE '2026-12-01', DATE '2026-12-01',
    1, 'DRAFT', false, 0
);

INSERT INTO public.leave_request_event (
    event_id, leave_request_id, sequence_number, event_type, to_status, occurred_at
) VALUES (
    'LRE-2026-999999', 'LVE-2026-999999', 1, 'CREATED', 'DRAFT', TIMESTAMPTZ '2026-10-22 12:00:00+00'
);

DO $$
BEGIN
    BEGIN
        UPDATE public.leave_request_event
        SET reason_code = 'smoke-test'
        WHERE event_id = 'LRE-2026-999999';
        RAISE EXCEPTION 'append-only trigger did not reject UPDATE';
    EXCEPTION
        WHEN SQLSTATE '55000' THEN
            RAISE NOTICE 'Append-only trigger rejected UPDATE as expected';
    END;
END
$$;

DO $$
BEGIN
    BEGIN
        DELETE FROM public.leave_request_event
        WHERE event_id = 'LRE-2026-999999';
        RAISE EXCEPTION 'append-only trigger did not reject DELETE';
    EXCEPTION
        WHEN SQLSTATE '55000' THEN
            RAISE NOTICE 'Append-only trigger rejected DELETE as expected';
    END;
END
$$;

DO $$
DECLARE
    manager_id varchar(10);
BEGIN
    SELECT employee_id
    INTO manager_id
    FROM public.employee
    WHERE is_ceo
    ORDER BY employee_id
    LIMIT 1;

    BEGIN
        INSERT INTO public.employee (
            employee_id, display_name, country, home_currency, hire_date,
            manager_id, functional_role, system_role, job_level, is_ceo
        ) VALUES (
            'EMP-999997', 'Invalid smoke employee', 'ZZ', 'USD', DATE '2020-01-01',
            manager_id, 'NONE', 'REQUESTER', 1, false
        );
        RAISE EXCEPTION 'country CHECK constraint did not reject invalid country';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Country CHECK constraint rejected invalid country as expected';
    END;
END
$$;

ROLLBACK;
SQL

remaining_rows="$(db_psql -Atqc "
SELECT
    (SELECT count(*) FROM public.employee WHERE employee_id IN ('EMP-999998', 'EMP-999999')) +
    (SELECT count(*) FROM public.cost_center WHERE cost_center_id = 'CC-9999') +
    (SELECT count(*) FROM public.leave_request WHERE leave_request_id = 'LVE-2026-999999') +
    (SELECT count(*) FROM public.leave_request_event WHERE event_id = 'LRE-2026-999999');
")"

if [[ "$remaining_rows" != "0" ]]; then
    printf 'Smoke-test transaction left %s sample rows behind\n' "$remaining_rows" >&2
    exit 1
fi

printf 'Database smoke test passed: schema, views, fixtures, constraints, append-only trigger, and rollback verified.\n'
