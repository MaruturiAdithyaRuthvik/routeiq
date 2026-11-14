CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS ground_truth;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'routeiq_app') THEN
        EXECUTE 'CREATE ROLE routeiq_app NOLOGIN';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'routeiq_evaluator') THEN
        EXECUTE 'CREATE ROLE routeiq_evaluator NOLOGIN';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'routeiq_app_login') THEN
        EXECUTE 'CREATE ROLE routeiq_app_login NOLOGIN';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'routeiq_evaluator_login') THEN
        EXECUTE 'CREATE ROLE routeiq_evaluator_login NOLOGIN';
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION public.is_sorted_unique_text_array(input_values text[])
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT NOT EXISTS (
        SELECT 1
        FROM unnest(input_values) AS values_table(value)
        WHERE value IS NULL
    )
    AND input_values = ARRAY(
            SELECT DISTINCT value
            FROM unnest(input_values) AS values_table(value)
            ORDER BY value
        )
$$;

CREATE OR REPLACE FUNCTION public.is_documented_reason_code(reason_code text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT reason_code IN (
        'INVALID_DATE_RANGE', 'ZERO_BUSINESS_DAYS', 'EMPLOYEE_NOT_ACTIVE',
        'TENURE_INELIGIBLE', 'MAX_CONSECUTIVE_DAYS', 'OVERLAP', 'INSUFFICIENT_BALANCE',
        'LEAVE_UNPAID', 'LEAVE_DAYS_1_3', 'LEAVE_DAYS_4_10', 'LEAVE_DAYS_GT_10',
        'PARENTAL_LEAVE', 'EXPENSE_LT_50_AUTO', 'EXPENSE_LT_50_FLAGGED',
        'EXPENSE_50_1000', 'EXPENSE_1000_5000', 'EXPENSE_5000_20000',
        'EXPENSE_GTE_20000', 'AIRFARE_INTERNATIONAL', 'CLIENT_ENTERTAINMENT_GT_250',
        'GIFT_GT_250', 'POLICY_LIMIT_BREACH', 'MISSING_RECEIPT', 'DUPLICATE_RECEIPT',
        'MISSING_COST_CENTER', 'DATE_OUTSIDE_EMPLOYMENT', 'FUTURE_EXPENSE_DATE',
        'SPLIT_CLAIM', 'SELF_APPROVAL_PREVENTED', 'UNRESOLVED_APPROVER',
        'CEO_MANAGER_FALLBACK', 'DUPLICATE_REIMBURSEMENT'
    )
$$;

CREATE OR REPLACE FUNCTION public.are_documented_reason_codes(input_values text[])
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT NOT EXISTS (
        SELECT 1
        FROM unnest(input_values) AS values_table(value)
        WHERE value IS NULL OR NOT public.is_documented_reason_code(value)
    )
$$;

CREATE TABLE IF NOT EXISTS public.employee (
    employee_id varchar(10) PRIMARY KEY CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    display_name varchar(100) NOT NULL CHECK (length(trim(display_name)) > 0),
    country char(2) NOT NULL CHECK (country IN ('IN', 'US', 'GB', 'DE', 'SG')),
    home_currency char(3) NOT NULL CHECK (home_currency IN ('INR', 'USD', 'GBP', 'EUR', 'SGD')),
    hire_date date NOT NULL,
    termination_date date,
    manager_id varchar(10),
    functional_role varchar(32) NOT NULL CHECK (
        functional_role IN ('NONE', 'DEPT_HEAD', 'HR_PARTNER', 'FINANCE_CONTROLLER', 'CFO', 'COMPLIANCE_OFFICER')
    ),
    system_role varchar(32) NOT NULL CHECK (
        system_role IN ('REQUESTER', 'APPROVER', 'PROCESS_OWNER', 'ANALYST', 'ADMIN')
    ),
    job_level smallint NOT NULL CHECK (job_level BETWEEN 1 AND 10),
    is_ceo boolean NOT NULL DEFAULT false,
    cost_center_id varchar(7),
    CONSTRAINT employee_dates_ordered CHECK (termination_date IS NULL OR termination_date >= hire_date),
    CONSTRAINT employee_currency_matches_country CHECK (
        home_currency = CASE country
            WHEN 'IN' THEN 'INR'
            WHEN 'US' THEN 'USD'
            WHEN 'GB' THEN 'GBP'
            WHEN 'DE' THEN 'EUR'
            WHEN 'SG' THEN 'SGD'
        END
    ),
    CONSTRAINT employee_manager_not_self CHECK (manager_id IS NULL OR manager_id <> employee_id),
    CONSTRAINT employee_ceo_has_no_manager CHECK (NOT is_ceo OR manager_id IS NULL),
    CONSTRAINT employee_non_ceo_has_manager CHECK (is_ceo OR manager_id IS NOT NULL),
    CONSTRAINT employee_manager_fk FOREIGN KEY (manager_id)
        REFERENCES public.employee(employee_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_single_ceo
    ON public.employee (is_ceo) WHERE is_ceo;

CREATE TABLE IF NOT EXISTS public.leave_policy (
    leave_policy_id varchar(7) PRIMARY KEY CHECK (leave_policy_id ~ '^LPO-00[1-6]$'),
    name varchar(32) NOT NULL UNIQUE,
    annual_entitlement_days numeric(6,2),
    carry_forward_max_days numeric(6,2) NOT NULL CHECK (carry_forward_max_days >= 0),
    max_consecutive_days smallint,
    medical_certificate_after_days smallint,
    tenure_required_months smallint NOT NULL CHECK (tenure_required_months >= 0),
    lump_sum_days numeric(6,2),
    is_unpaid boolean NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    CONSTRAINT leave_policy_dates_ordered CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT leave_policy_values_valid CHECK (
        (leave_policy_id = 'LPO-001' AND name = 'Annual' AND annual_entitlement_days = 24
            AND carry_forward_max_days = 10 AND max_consecutive_days = 20
            AND medical_certificate_after_days IS NULL AND tenure_required_months = 0
            AND lump_sum_days IS NULL AND NOT is_unpaid)
        OR (leave_policy_id = 'LPO-002' AND name = 'Sick' AND annual_entitlement_days = 12
            AND carry_forward_max_days = 0 AND max_consecutive_days = 15
            AND medical_certificate_after_days = 2 AND tenure_required_months = 0
            AND lump_sum_days IS NULL AND NOT is_unpaid)
        OR (leave_policy_id = 'LPO-003' AND name = 'Casual' AND annual_entitlement_days = 8
            AND carry_forward_max_days = 0 AND max_consecutive_days = 3
            AND medical_certificate_after_days IS NULL AND tenure_required_months = 0
            AND lump_sum_days IS NULL AND NOT is_unpaid)
        OR (leave_policy_id = 'LPO-004' AND name = 'Parental' AND annual_entitlement_days IS NULL
            AND carry_forward_max_days = 0 AND max_consecutive_days IS NULL
            AND medical_certificate_after_days IS NULL AND tenure_required_months = 12
            AND lump_sum_days = 90 AND NOT is_unpaid)
        OR (leave_policy_id = 'LPO-005' AND name = 'Compassionate' AND annual_entitlement_days IS NULL
            AND carry_forward_max_days = 0 AND max_consecutive_days = 5
            AND medical_certificate_after_days IS NULL AND tenure_required_months = 0
            AND lump_sum_days = 5 AND NOT is_unpaid)
        OR (leave_policy_id = 'LPO-006' AND name = 'Unpaid' AND annual_entitlement_days IS NULL
            AND carry_forward_max_days = 0 AND max_consecutive_days = 30
            AND medical_certificate_after_days IS NULL AND tenure_required_months = 0
            AND lump_sum_days = 0 AND is_unpaid)
    )
);

CREATE TABLE IF NOT EXISTS public.expense_category (
    category varchar(32) PRIMARY KEY CHECK (category IN (
        'MEALS', 'LODGING', 'AIRFARE', 'GROUND_TRANSPORT', 'SOFTWARE',
        'OFFICE_SUPPLIES', 'TRAINING', 'CLIENT_ENTERTAINMENT', 'GIFTS', 'COMMUNICATION'
    )),
    description varchar(120) NOT NULL CHECK (length(trim(description)) > 0)
);

CREATE TABLE IF NOT EXISTS public.cost_center (
    cost_center_id varchar(7) PRIMARY KEY CHECK (cost_center_id ~ '^CC-[0-9]{4}$'),
    name varchar(100) NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    country char(2) NOT NULL CHECK (country IN ('IN', 'US', 'GB', 'DE', 'SG')),
    owner_employee_id varchar(10) NOT NULL,
    budget_year smallint NOT NULL CHECK (budget_year = 2026),
    budget_usd numeric(14,2) NOT NULL CHECK (budget_usd >= 0),
    CONSTRAINT cost_center_owner_fk FOREIGN KEY (owner_employee_id)
        REFERENCES public.employee(employee_id) DEFERRABLE INITIALLY DEFERRED
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'employee_cost_center_fk'
          AND conrelid = 'public.employee'::regclass
    ) THEN
        ALTER TABLE public.employee
            ADD CONSTRAINT employee_cost_center_fk
            FOREIGN KEY (cost_center_id)
            REFERENCES public.cost_center(cost_center_id)
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.leave_balance (
    leave_balance_id varchar(64) PRIMARY KEY CHECK (
        leave_balance_id ~ '^LBL-EMP-[0-9]{6}-LPO-00[1-6]-2026$'
    ),
    employee_id varchar(10) NOT NULL REFERENCES public.employee(employee_id),
    leave_policy_id varchar(7) NOT NULL REFERENCES public.leave_policy(leave_policy_id),
    balance_year smallint NOT NULL CHECK (balance_year = 2026),
    as_of_date date NOT NULL CHECK (as_of_date = DATE '2026-10-22'),
    opening_days numeric(12,6) NOT NULL CHECK (opening_days >= 0),
    accrued_days numeric(12,6) NOT NULL CHECK (accrued_days >= 0),
    adjustments_days numeric(12,6) NOT NULL,
    used_days numeric(12,6) NOT NULL CHECK (used_days >= 0),
    pending_days numeric(12,6) NOT NULL CHECK (pending_days >= 0),
    available_days numeric(12,6) NOT NULL,
    CONSTRAINT leave_balance_id_matches_keys CHECK (
        leave_balance_id = 'LBL-' || employee_id || '-' || leave_policy_id || '-' || balance_year::text
    ),
    CONSTRAINT leave_balance_unique_year UNIQUE (employee_id, leave_policy_id, balance_year)
);

CREATE TABLE IF NOT EXISTS public.leave_request (
    leave_request_id varchar(17) PRIMARY KEY CHECK (leave_request_id ~ '^LVE-2026-[0-9]{6}$'),
    employee_id varchar(10) NOT NULL REFERENCES public.employee(employee_id),
    leave_policy_id varchar(7) NOT NULL REFERENCES public.leave_policy(leave_policy_id),
    start_date date NOT NULL,
    end_date date NOT NULL,
    business_days smallint NOT NULL CHECK (business_days >= 0),
    status varchar(24) NOT NULL CHECK (
        status IN ('DRAFT', 'SUBMITTED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CANCELLED')
    ),
    submitted_at timestamptz,
    medical_certificate_required boolean NOT NULL DEFAULT false,
    risk_score smallint NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    reason varchar(500),
    CONSTRAINT leave_request_dates_ordered CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS public.expense_policy (
    expense_policy_id varchar(8) PRIMARY KEY CHECK (expense_policy_id ~ '^XPO-[0-9]{4}$'),
    category varchar(32) NOT NULL REFERENCES public.expense_category(category),
    country char(2) NOT NULL CHECK (country IN ('IN', 'US', 'GB', 'DE', 'SG')),
    per_line_limit_usd numeric(12,2) NOT NULL CHECK (per_line_limit_usd > 0),
    receipt_threshold_usd numeric(12,2) NOT NULL CHECK (receipt_threshold_usd >= 0),
    effective_from date NOT NULL,
    effective_to date,
    version smallint NOT NULL CHECK (version > 0),
    CONSTRAINT expense_policy_dates_ordered CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT expense_policy_category_pair UNIQUE (expense_policy_id, category),
    CONSTRAINT expense_policy_version_unique UNIQUE (category, country, version)
);

CREATE TABLE IF NOT EXISTS public.expense_claim (
    expense_claim_id varchar(17) PRIMARY KEY CHECK (expense_claim_id ~ '^EXP-2026-[0-9]{6}$'),
    employee_id varchar(10) NOT NULL REFERENCES public.employee(employee_id),
    merchant_name varchar(120) NOT NULL CHECK (length(trim(merchant_name)) > 0),
    merchant_country char(2) NOT NULL CHECK (merchant_country IN ('IN', 'US', 'GB', 'DE', 'SG')),
    expense_date date NOT NULL,
    cost_center_id varchar(7) REFERENCES public.cost_center(cost_center_id),
    total_usd numeric(14,2) NOT NULL CHECK (total_usd > 0),
    status varchar(24) NOT NULL CHECK (
        status IN ('DRAFT', 'SUBMITTED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CANCELLED', 'REIMBURSED')
    ),
    submitted_at timestamptz,
    risk_score smallint NOT NULL CHECK (risk_score BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS public.expense_line (
    expense_line_id varchar(23) PRIMARY KEY CHECK (
        expense_line_id ~ '^EXPL-EXP-2026-[0-9]{6}-[0-9]{2}$'
    ),
    expense_claim_id varchar(17) NOT NULL REFERENCES public.expense_claim(expense_claim_id),
    line_number smallint NOT NULL CHECK (line_number BETWEEN 1 AND 10),
    category varchar(32) NOT NULL REFERENCES public.expense_category(category),
    expense_policy_id varchar(8) NOT NULL,
    description varchar(250),
    amount numeric(12,2) NOT NULL CHECK (amount > 0),
    currency char(3) NOT NULL CHECK (currency IN ('INR', 'USD', 'GBP', 'EUR', 'SGD')),
    fx_rate_to_usd numeric(8,5) NOT NULL CHECK (fx_rate_to_usd > 0),
    amount_usd numeric(12,2) NOT NULL CHECK (amount_usd > 0),
    receipt_present boolean NOT NULL,
    receipt_id varchar(64) UNIQUE,
    receipt_hash char(64),
    file_type varchar(8),
    size_kb numeric(10,2),
    CONSTRAINT expense_line_policy_category_fk FOREIGN KEY (expense_policy_id, category)
        REFERENCES public.expense_policy(expense_policy_id, category),
    CONSTRAINT expense_line_claim_number_unique UNIQUE (expense_claim_id, line_number),
    CONSTRAINT expense_line_id_matches_number CHECK (
        expense_line_id = 'EXPL-' || expense_claim_id || '-' || lpad(line_number::text, 2, '0')
    ),
    CONSTRAINT expense_line_amount_fx CHECK (
        fx_rate_to_usd = CASE currency
            WHEN 'INR' THEN 0.01200
            WHEN 'USD' THEN 1.00000
            WHEN 'GBP' THEN 1.27000
            WHEN 'EUR' THEN 1.08000
            WHEN 'SGD' THEN 0.74000
        END
        AND amount_usd = round(amount * fx_rate_to_usd, 2)
    ),
    CONSTRAINT expense_line_receipt_metadata CHECK (
        (receipt_present
            AND receipt_id IS NOT NULL
            AND receipt_hash IS NOT NULL
            AND receipt_hash ~ '^[0-9a-f]{64}$'
            AND file_type IS NOT NULL
            AND file_type IN ('PDF', 'JPG', 'JPEG', 'PNG', 'HEIC')
            AND size_kb IS NOT NULL
            AND size_kb > 0)
        OR
        (NOT receipt_present
            AND receipt_id IS NULL
            AND receipt_hash IS NULL
            AND file_type IS NULL
            AND size_kb IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.approval_rule (
    approval_rule_id varchar(7) PRIMARY KEY CHECK (approval_rule_id ~ '^ARL-[0-9]{3}$'),
    rule_code varchar(40) NOT NULL UNIQUE CHECK (length(trim(rule_code)) > 0),
    request_type varchar(8) NOT NULL CHECK (request_type IN ('LEAVE', 'EXPENSE')),
    priority smallint NOT NULL CHECK (priority > 0),
    required_role varchar(32) NOT NULL CHECK (
        required_role IN ('DEPT_HEAD', 'HR_PARTNER', 'FINANCE_CONTROLLER', 'CFO',
                          'COMPLIANCE_OFFICER', 'MANAGER', 'SYSTEM')
    ),
    condition_description varchar(500) NOT NULL CHECK (length(trim(condition_description)) > 0),
    designated_employee_id varchar(10) REFERENCES public.employee(employee_id),
    effective_from date NOT NULL,
    effective_to date,
    version smallint NOT NULL CHECK (version > 0),
    is_active boolean NOT NULL,
    CONSTRAINT approval_rule_dates_ordered CHECK (effective_to IS NULL OR effective_to > effective_from),
    CONSTRAINT approval_rule_priority_unique UNIQUE (request_type, version, priority)
);

CREATE TABLE IF NOT EXISTS public.employee_cost_center_assignment (
    employee_id varchar(10) NOT NULL REFERENCES public.employee(employee_id),
    cost_center_id varchar(7) NOT NULL REFERENCES public.cost_center(cost_center_id),
    effective_from date NOT NULL,
    effective_to date,
    allocation_pct numeric(5,2) NOT NULL CHECK (allocation_pct > 0 AND allocation_pct <= 100),
    PRIMARY KEY (employee_id, cost_center_id, effective_from),
    CONSTRAINT employee_cost_center_dates_ordered CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS public.approval_rule_category (
    approval_rule_id varchar(7) NOT NULL REFERENCES public.approval_rule(approval_rule_id),
    category varchar(32) NOT NULL REFERENCES public.expense_category(category),
    effective_from date NOT NULL,
    effective_to date,
    PRIMARY KEY (approval_rule_id, category, effective_from),
    CONSTRAINT approval_rule_category_dates_ordered CHECK (effective_to IS NULL OR effective_to > effective_from)
);

CREATE TABLE IF NOT EXISTS public.approval_step (
    approval_step_id varchar(64) PRIMARY KEY CHECK (
        approval_step_id ~ '^APR-(LVE-2026-[0-9]{6}|EXP-2026-[0-9]{6})-[0-9]{2}$'
    ),
    leave_request_id varchar(17) REFERENCES public.leave_request(leave_request_id),
    expense_claim_id varchar(17) REFERENCES public.expense_claim(expense_claim_id),
    step_number smallint NOT NULL CHECK (step_number > 0),
    required_role varchar(32) NOT NULL CHECK (
        required_role IN ('MANAGER', 'DEPT_HEAD', 'HR_PARTNER', 'FINANCE_CONTROLLER',
                          'CFO', 'COMPLIANCE_OFFICER', 'SYSTEM')
    ),
    approver_employee_id varchar(10) REFERENCES public.employee(employee_id),
    status varchar(16) NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    assigned_at timestamptz NOT NULL,
    due_date date NOT NULL,
    decided_at timestamptz,
    reason_code varchar(64) CHECK (
        reason_code IS NULL OR public.is_documented_reason_code(reason_code)
    ),
    CONSTRAINT approval_step_one_request CHECK (
        (leave_request_id IS NOT NULL)::integer + (expense_claim_id IS NOT NULL)::integer = 1
    ),
    CONSTRAINT approval_step_id_matches_sequence CHECK (
        approval_step_id = 'APR-' || COALESCE(leave_request_id, expense_claim_id)
            || '-' || lpad(step_number::text, 2, '0')
    ),
    CONSTRAINT approval_step_system_approver CHECK (
        (required_role = 'SYSTEM' AND approver_employee_id IS NULL AND status = 'APPROVED')
        OR (required_role <> 'SYSTEM' AND approver_employee_id IS NOT NULL)
    ),
    CONSTRAINT approval_step_decision_time CHECK (
        (status = 'PENDING' AND decided_at IS NULL)
        OR (status IN ('APPROVED', 'REJECTED') AND decided_at IS NOT NULL AND decided_at >= assigned_at)
    ),
    CONSTRAINT approval_step_leave_sequence UNIQUE (leave_request_id, step_number),
    CONSTRAINT approval_step_expense_sequence UNIQUE (expense_claim_id, step_number)
);

CREATE TABLE IF NOT EXISTS public.reimbursement (
    reimbursement_id varchar(15) PRIMARY KEY CHECK (reimbursement_id ~ '^RMB-2026-[0-9]{6}$'),
    expense_claim_id varchar(17) NOT NULL REFERENCES public.expense_claim(expense_claim_id),
    amount_home_currency numeric(14,2) NOT NULL CHECK (amount_home_currency > 0),
    home_currency char(3) NOT NULL CHECK (home_currency IN ('INR', 'USD', 'GBP', 'EUR', 'SGD')),
    payment_date date NOT NULL,
    status varchar(12) NOT NULL CHECK (status IN ('SCHEDULED', 'PAID')),
    created_at timestamptz NOT NULL,
    paid_at timestamptz,
    payment_reference varchar(64) UNIQUE,
    CONSTRAINT reimbursement_paid_at_valid CHECK (
        (status = 'PAID' AND paid_at IS NOT NULL AND paid_at::date >= payment_date)
        OR (status = 'SCHEDULED' AND paid_at IS NULL)
    ),
    CONSTRAINT reimbursement_status_matches_as_of_date CHECK (
        (status = 'PAID' AND payment_date <= DATE '2026-10-22')
        OR (status = 'SCHEDULED' AND payment_date > DATE '2026-10-22')
    )
);

CREATE TABLE IF NOT EXISTS public.holiday (
    holiday_id varchar(16) PRIMARY KEY CHECK (
        holiday_id ~ '^HOL-2026-(IN|US|GB|DE|SG)-[0-9]{2}$'
    ),
    country char(2) NOT NULL CHECK (country IN ('IN', 'US', 'GB', 'DE', 'SG')),
    holiday_date date NOT NULL CHECK (
        holiday_date >= DATE '2026-01-01' AND holiday_date < DATE '2027-01-01'
    ),
    holiday_name varchar(64) NOT NULL CHECK (length(trim(holiday_name)) > 0),
    is_illustrative boolean NOT NULL DEFAULT true CHECK (is_illustrative),
    CONSTRAINT holiday_country_date_unique UNIQUE (country, holiday_date),
    CONSTRAINT holiday_id_matches_country CHECK (
        split_part(holiday_id, '-', 3) = country::text
    )
);

CREATE TABLE IF NOT EXISTS public.leave_request_event (
    event_id varchar(20) PRIMARY KEY CHECK (event_id ~ '^LRE-2026-[0-9]{6}$'),
    leave_request_id varchar(17) NOT NULL REFERENCES public.leave_request(leave_request_id),
    sequence_number integer NOT NULL CHECK (sequence_number > 0),
    event_type varchar(32) NOT NULL CHECK (
        event_type IN ('CREATED', 'SUBMISSION_ATTEMPT', 'SUBMITTED', 'APPROVAL_STARTED',
                       'APPROVAL_DECIDED', 'CANCELLED')
    ),
    from_status varchar(24) CHECK (
        from_status IS NULL OR from_status IN ('DRAFT', 'SUBMITTED', 'PENDING_APPROVAL',
                                               'APPROVED', 'REJECTED', 'CANCELLED')
    ),
    to_status varchar(24) CHECK (
        to_status IS NULL OR to_status IN ('DRAFT', 'SUBMITTED', 'PENDING_APPROVAL',
                                           'APPROVED', 'REJECTED', 'CANCELLED')
    ),
    occurred_at timestamptz NOT NULL,
    actor_employee_id varchar(10) REFERENCES public.employee(employee_id),
    reason_code varchar(64) CHECK (
        reason_code IS NULL OR public.is_documented_reason_code(reason_code)
    ),
    CONSTRAINT leave_request_event_sequence UNIQUE (leave_request_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS public.expense_claim_event (
    event_id varchar(20) PRIMARY KEY CHECK (event_id ~ '^ECE-2026-[0-9]{6}$'),
    expense_claim_id varchar(17) NOT NULL REFERENCES public.expense_claim(expense_claim_id),
    sequence_number integer NOT NULL CHECK (sequence_number > 0),
    event_type varchar(32) NOT NULL CHECK (
        event_type IN ('CREATED', 'SUBMISSION_ATTEMPT', 'SUBMITTED', 'APPROVAL_STARTED',
                       'APPROVAL_DECIDED', 'CANCELLED', 'REIMBURSEMENT_CREATED', 'REIMBURSEMENT_PAID')
    ),
    from_status varchar(24) CHECK (
        from_status IS NULL OR from_status IN ('DRAFT', 'SUBMITTED', 'PENDING_APPROVAL',
                                               'APPROVED', 'REJECTED', 'CANCELLED', 'REIMBURSED')
    ),
    to_status varchar(24) CHECK (
        to_status IS NULL OR to_status IN ('DRAFT', 'SUBMITTED', 'PENDING_APPROVAL',
                                           'APPROVED', 'REJECTED', 'CANCELLED', 'REIMBURSED')
    ),
    occurred_at timestamptz NOT NULL,
    actor_employee_id varchar(10) REFERENCES public.employee(employee_id),
    reason_code varchar(64) CHECK (
        reason_code IS NULL OR public.is_documented_reason_code(reason_code)
    ),
    event_payload jsonb NOT NULL CHECK (jsonb_typeof(event_payload) = 'object'),
    CONSTRAINT expense_claim_event_sequence UNIQUE (expense_claim_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS public.leave_ledger_entry (
    leave_ledger_entry_id varchar(18) PRIMARY KEY CHECK (
        leave_ledger_entry_id ~ '^LLE-2026-[0-9]{6}$'
    ),
    employee_id varchar(10) NOT NULL REFERENCES public.employee(employee_id),
    leave_policy_id varchar(7) NOT NULL REFERENCES public.leave_policy(leave_policy_id),
    leave_request_id varchar(17) REFERENCES public.leave_request(leave_request_id),
    entry_type varchar(16) NOT NULL CHECK (
        entry_type IN ('OPENING', 'ACCRUAL', 'RESERVE', 'RELEASE', 'DEBIT', 'ADJUSTMENT', 'REVERSAL')
    ),
    effect_bucket varchar(16) NOT NULL CHECK (effect_bucket IN ('AVAILABLE', 'RESERVED', 'USED')),
    delta_days numeric(12,6) NOT NULL,
    prior_year_closing_days numeric(12,6),
    entry_date date NOT NULL,
    reversal_of_entry_id varchar(18) UNIQUE REFERENCES public.leave_ledger_entry(leave_ledger_entry_id),
    source_event_id varchar(20) REFERENCES public.leave_request_event(event_id),
    CONSTRAINT leave_ledger_entry_effect_matches_type CHECK (
        (entry_type IN ('OPENING', 'ACCRUAL', 'ADJUSTMENT') AND effect_bucket = 'AVAILABLE')
        OR (entry_type IN ('RESERVE', 'RELEASE') AND effect_bucket = 'RESERVED')
        OR (entry_type = 'DEBIT' AND effect_bucket = 'USED')
        OR (entry_type = 'REVERSAL' AND reversal_of_entry_id IS NOT NULL)
    ),
    CONSTRAINT leave_ledger_opening_values CHECK (
        (entry_type = 'OPENING' AND prior_year_closing_days IS NOT NULL
            AND prior_year_closing_days >= 0 AND delta_days >= 0)
        OR (entry_type <> 'OPENING' AND prior_year_closing_days IS NULL)
    ),
    CONSTRAINT leave_ledger_positive_effects CHECK (
        (entry_type IN ('ACCRUAL', 'RESERVE', 'DEBIT') AND delta_days >= 0)
        OR entry_type NOT IN ('ACCRUAL', 'RESERVE', 'DEBIT')
    ),
    CONSTRAINT leave_ledger_release_negative CHECK (entry_type <> 'RELEASE' OR delta_days <= 0),
    CONSTRAINT leave_ledger_reversal_link CHECK (
        (entry_type = 'REVERSAL' AND reversal_of_entry_id IS NOT NULL)
        OR (entry_type <> 'REVERSAL' AND reversal_of_entry_id IS NULL)
    ),
    CONSTRAINT leave_ledger_request_required CHECK (
        entry_type NOT IN ('RESERVE', 'RELEASE', 'DEBIT') OR leave_request_id IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS public.decision_audit (
    decision_audit_id varchar(20) PRIMARY KEY CHECK (decision_audit_id ~ '^DAU-2026-[0-9]{6}$'),
    leave_request_id varchar(17) REFERENCES public.leave_request(leave_request_id),
    expense_claim_id varchar(17) REFERENCES public.expense_claim(expense_claim_id),
    decision_kind varchar(32) NOT NULL CHECK (
        decision_kind IN ('SUBMIT_VALIDATION', 'ROUTING', 'APPROVAL',
                          'REIMBURSEMENT_ELIGIBILITY', 'RISK_SCORE')
    ),
    inputs_snapshot jsonb NOT NULL CHECK (jsonb_typeof(inputs_snapshot) = 'object'),
    outputs_snapshot jsonb NOT NULL CHECK (jsonb_typeof(outputs_snapshot) = 'object'),
    matched_rule_ids text[] NOT NULL,
    reason_codes text[] NOT NULL,
    computed_path jsonb NOT NULL CHECK (jsonb_typeof(computed_path) = 'array'),
    engine_version varchar(32) NOT NULL CHECK (length(trim(engine_version)) > 0),
    recorded_at timestamptz NOT NULL,
    CONSTRAINT decision_audit_one_request CHECK (
        (leave_request_id IS NOT NULL)::integer + (expense_claim_id IS NOT NULL)::integer = 1
    ),
    CONSTRAINT decision_audit_sorted_rules CHECK (public.is_sorted_unique_text_array(matched_rule_ids)),
    CONSTRAINT decision_audit_sorted_reasons CHECK (public.is_sorted_unique_text_array(reason_codes)),
    CONSTRAINT decision_audit_reason_codes_valid CHECK (public.are_documented_reason_codes(reason_codes))
);

CREATE TABLE IF NOT EXISTS public.audit_finding (
    audit_finding_id varchar(18) PRIMARY KEY CHECK (audit_finding_id ~ '^AFN-2026-[0-9]{6}$'),
    leave_request_id varchar(17) REFERENCES public.leave_request(leave_request_id),
    expense_claim_id varchar(17) REFERENCES public.expense_claim(expense_claim_id),
    expense_line_id varchar(23) REFERENCES public.expense_line(expense_line_id),
    approval_step_id varchar(64) REFERENCES public.approval_step(approval_step_id),
    reimbursement_id varchar(15) REFERENCES public.reimbursement(reimbursement_id),
    finding_code varchar(40) NOT NULL CHECK (finding_code IN (
        'INVALID_DATE_RANGE', 'ZERO_BUSINESS_DAYS', 'EMPLOYEE_NOT_ACTIVE', 'TENURE_INELIGIBLE',
        'MAX_CONSECUTIVE_DAYS', 'OVERLAP', 'INSUFFICIENT_BALANCE', 'POLICY_LIMIT_BREACH',
        'MISSING_RECEIPT', 'DUPLICATE_RECEIPT', 'MISSING_COST_CENTER', 'DATE_OUTSIDE_EMPLOYMENT',
        'FUTURE_EXPENSE_DATE', 'SPLIT_CLAIM', 'SELF_APPROVAL_PREVENTED',
        'UNRESOLVED_APPROVER', 'DUPLICATE_REIMBURSEMENT'
    )),
    severity varchar(12) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
    status varchar(12) NOT NULL DEFAULT 'OPEN' CHECK (status = 'OPEN'),
    details jsonb NOT NULL CHECK (jsonb_typeof(details) = 'object'),
    detected_at timestamptz NOT NULL,
    CONSTRAINT audit_finding_one_target CHECK (
        (leave_request_id IS NOT NULL)::integer
        + (expense_claim_id IS NOT NULL)::integer
        + (expense_line_id IS NOT NULL)::integer
        + (approval_step_id IS NOT NULL)::integer
        + (reimbursement_id IS NOT NULL)::integer = 1
    )
);

CREATE TABLE IF NOT EXISTS public.audit_finding_event (
    finding_event_id varchar(18) PRIMARY KEY CHECK (finding_event_id ~ '^AFE-2026-[0-9]{6}$'),
    audit_finding_id varchar(18) NOT NULL REFERENCES public.audit_finding(audit_finding_id),
    sequence_number integer NOT NULL CHECK (sequence_number > 0),
    from_status varchar(12) NOT NULL CHECK (from_status = 'OPEN'),
    to_status varchar(12) NOT NULL CHECK (to_status IN ('RESOLVED', 'DISMISSED')),
    occurred_at timestamptz NOT NULL,
    actor_employee_id varchar(10) REFERENCES public.employee(employee_id),
    reason_code varchar(64) NOT NULL CHECK (
        length(trim(reason_code)) > 0 AND public.is_documented_reason_code(reason_code)
    ),
    CONSTRAINT audit_finding_event_sequence UNIQUE (audit_finding_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS ground_truth.ground_truth_anomaly (
    ground_truth_anomaly_id varchar(18) PRIMARY KEY CHECK (
        ground_truth_anomaly_id ~ '^GTA-2026-[0-9]{6}$'
    ),
    leave_request_id varchar(17) REFERENCES public.leave_request(leave_request_id),
    leave_balance_id varchar(64) REFERENCES public.leave_balance(leave_balance_id),
    expense_claim_id varchar(17) REFERENCES public.expense_claim(expense_claim_id),
    expense_line_id varchar(23) REFERENCES public.expense_line(expense_line_id),
    approval_step_id varchar(64) REFERENCES public.approval_step(approval_step_id),
    reimbursement_id varchar(15) REFERENCES public.reimbursement(reimbursement_id),
    issue_type varchar(40) NOT NULL CHECK (issue_type IN (
        'NEGATIVE_LEAVE_BALANCE', 'OVERLAPPING_APPROVED_LEAVE', 'EXPENSE_OUTSIDE_EMPLOYMENT',
        'FUTURE_EXPENSE_DATE', 'SPLIT_CLAIM', 'MISSING_COST_CENTER', 'SELF_APPROVAL',
        'DUPLICATE_REIMBURSEMENT', 'MISSING_RECEIPT', 'DUPLICATE_RECEIPT',
        'POLICY_LIMIT_BREACH', 'INSUFFICIENT_BALANCE', 'ZERO_BUSINESS_DAY_SPAN'
    )),
    violation_rule_ids text[] NOT NULL CHECK (cardinality(violation_rule_ids) > 0),
    expected_finding_code varchar(64) CHECK (
        expected_finding_code IS NULL OR expected_finding_code IN (
            'INVALID_DATE_RANGE', 'ZERO_BUSINESS_DAYS', 'EMPLOYEE_NOT_ACTIVE',
            'TENURE_INELIGIBLE', 'MAX_CONSECUTIVE_DAYS', 'OVERLAP', 'INSUFFICIENT_BALANCE',
            'POLICY_LIMIT_BREACH', 'MISSING_RECEIPT', 'DUPLICATE_RECEIPT',
            'MISSING_COST_CENTER', 'DATE_OUTSIDE_EMPLOYMENT', 'FUTURE_EXPENSE_DATE',
            'SPLIT_CLAIM', 'SELF_APPROVAL_PREVENTED', 'UNRESOLVED_APPROVER',
            'DUPLICATE_REIMBURSEMENT'
        )
    ),
    label varchar(32) NOT NULL CHECK (label = 'ANOMALY'),
    details jsonb NOT NULL CHECK (jsonb_typeof(details) = 'object'),
    CONSTRAINT ground_truth_anomaly_one_target CHECK (
        (leave_request_id IS NOT NULL)::integer
        + (leave_balance_id IS NOT NULL)::integer
        + (expense_claim_id IS NOT NULL)::integer
        + (expense_line_id IS NOT NULL)::integer
        + (approval_step_id IS NOT NULL)::integer
        + (reimbursement_id IS NOT NULL)::integer = 1
    ),
    CONSTRAINT ground_truth_anomaly_rules_sorted CHECK (
        public.is_sorted_unique_text_array(violation_rule_ids)
    )
);

CREATE TABLE IF NOT EXISTS ground_truth.ground_truth_decision (
    ground_truth_decision_id varchar(18) PRIMARY KEY CHECK (
        ground_truth_decision_id ~ '^GTD-2026-[0-9]{6}$'
    ),
    leave_request_id varchar(17) UNIQUE REFERENCES public.leave_request(leave_request_id),
    expense_claim_id varchar(17) UNIQUE REFERENCES public.expense_claim(expense_claim_id),
    expected_status varchar(32) NOT NULL CHECK (expected_status IN (
        'DRAFT', 'SUBMITTED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED',
        'CANCELLED', 'REIMBURSED', 'SCHEDULED', 'PAID'
    )),
    expected_approval_path jsonb NOT NULL CHECK (jsonb_typeof(expected_approval_path) = 'array'),
    expected_reason_codes text[] NOT NULL,
    matched_rule_ids text[] NOT NULL,
    expected_reimbursement boolean,
    expected_risk_score smallint CHECK (expected_risk_score BETWEEN 0 AND 100),
    evaluation_metric varchar(64),
    CONSTRAINT ground_truth_decision_one_target CHECK (
        (leave_request_id IS NOT NULL)::integer + (expense_claim_id IS NOT NULL)::integer = 1
    ),
    CONSTRAINT ground_truth_decision_leave_reimbursement CHECK (
        leave_request_id IS NULL OR expected_reimbursement IS NULL
    ),
    CONSTRAINT ground_truth_decision_reasons_sorted CHECK (
        public.is_sorted_unique_text_array(expected_reason_codes)
    ),
    CONSTRAINT ground_truth_decision_reason_codes_valid CHECK (
        public.are_documented_reason_codes(expected_reason_codes)
    ),
    CONSTRAINT ground_truth_decision_rules_sorted CHECK (
        public.is_sorted_unique_text_array(matched_rule_ids)
    )
);

CREATE INDEX IF NOT EXISTS idx_employee_manager_id ON public.employee(manager_id);
CREATE INDEX IF NOT EXISTS idx_employee_cost_center_id ON public.employee(cost_center_id);
CREATE INDEX IF NOT EXISTS idx_cost_center_owner_employee_id ON public.cost_center(owner_employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_employee_id ON public.leave_balance(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_policy_id ON public.leave_balance(leave_policy_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_employee_id ON public.leave_request(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_policy_id ON public.leave_request(leave_policy_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_status ON public.leave_request(status);
CREATE INDEX IF NOT EXISTS idx_leave_request_dates ON public.leave_request(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_leave_request_employee_dates ON public.leave_request(employee_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_expense_policy_category ON public.expense_policy(category);
CREATE INDEX IF NOT EXISTS idx_expense_claim_employee_id ON public.expense_claim(employee_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_cost_center_id ON public.expense_claim(cost_center_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_status ON public.expense_claim(status);
CREATE INDEX IF NOT EXISTS idx_expense_claim_date ON public.expense_claim(expense_date);
CREATE INDEX IF NOT EXISTS idx_expense_claim_employee_date ON public.expense_claim(employee_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_expense_line_claim_id ON public.expense_line(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_expense_line_category ON public.expense_line(category);
CREATE INDEX IF NOT EXISTS idx_expense_line_policy_category ON public.expense_line(expense_policy_id, category);
CREATE INDEX IF NOT EXISTS idx_expense_line_receipt_hash ON public.expense_line(receipt_hash);
CREATE INDEX IF NOT EXISTS idx_approval_rule_designated_employee_id ON public.approval_rule(designated_employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_cost_center_assignment_cost_center ON public.employee_cost_center_assignment(cost_center_id);
CREATE INDEX IF NOT EXISTS idx_approval_rule_category_category ON public.approval_rule_category(category);
CREATE INDEX IF NOT EXISTS idx_approval_step_leave_request_id ON public.approval_step(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_approval_step_expense_claim_id ON public.approval_step(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_approval_step_approver_id ON public.approval_step(approver_employee_id);
CREATE INDEX IF NOT EXISTS idx_approval_step_status_due ON public.approval_step(status, due_date);
CREATE INDEX IF NOT EXISTS idx_reimbursement_claim_id ON public.reimbursement(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_reimbursement_status_payment_date ON public.reimbursement(status, payment_date);
CREATE INDEX IF NOT EXISTS idx_leave_ledger_employee_policy_date
    ON public.leave_ledger_entry(employee_id, leave_policy_id, entry_date);
CREATE INDEX IF NOT EXISTS idx_leave_ledger_request_id ON public.leave_ledger_entry(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_leave_ledger_source_event_id ON public.leave_ledger_entry(source_event_id);
CREATE INDEX IF NOT EXISTS idx_leave_ledger_reversal_of_id ON public.leave_ledger_entry(reversal_of_entry_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_event_request_id ON public.leave_request_event(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_event_actor_id ON public.leave_request_event(actor_employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_event_occurred_at ON public.leave_request_event(occurred_at);
CREATE INDEX IF NOT EXISTS idx_expense_claim_event_claim_id ON public.expense_claim_event(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_event_actor_id ON public.expense_claim_event(actor_employee_id);
CREATE INDEX IF NOT EXISTS idx_expense_claim_event_occurred_at ON public.expense_claim_event(occurred_at);
CREATE INDEX IF NOT EXISTS idx_decision_audit_leave_request_id ON public.decision_audit(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_decision_audit_expense_claim_id ON public.decision_audit(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_decision_audit_recorded_at ON public.decision_audit(recorded_at);
CREATE INDEX IF NOT EXISTS idx_audit_finding_leave_request_id ON public.audit_finding(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_audit_finding_expense_claim_id ON public.audit_finding(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_audit_finding_expense_line_id ON public.audit_finding(expense_line_id);
CREATE INDEX IF NOT EXISTS idx_audit_finding_approval_step_id ON public.audit_finding(approval_step_id);
CREATE INDEX IF NOT EXISTS idx_audit_finding_reimbursement_id ON public.audit_finding(reimbursement_id);
CREATE INDEX IF NOT EXISTS idx_audit_finding_issue_type ON public.audit_finding(finding_code);
CREATE INDEX IF NOT EXISTS idx_audit_finding_status ON public.audit_finding(status);
CREATE INDEX IF NOT EXISTS idx_audit_finding_event_finding_id ON public.audit_finding_event(audit_finding_id);
CREATE INDEX IF NOT EXISTS idx_audit_finding_event_actor_id ON public.audit_finding_event(actor_employee_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_leave_request_id ON ground_truth.ground_truth_anomaly(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_leave_balance_id ON ground_truth.ground_truth_anomaly(leave_balance_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_expense_claim_id ON ground_truth.ground_truth_anomaly(expense_claim_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_expense_line_id ON ground_truth.ground_truth_anomaly(expense_line_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_approval_step_id ON ground_truth.ground_truth_anomaly(approval_step_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_reimbursement_id ON ground_truth.ground_truth_anomaly(reimbursement_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_anomaly_issue_type ON ground_truth.ground_truth_anomaly(issue_type);
CREATE INDEX IF NOT EXISTS idx_ground_truth_decision_leave_request_id ON ground_truth.ground_truth_decision(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_ground_truth_decision_expense_claim_id ON ground_truth.ground_truth_decision(expense_claim_id);

INSERT INTO public.leave_policy (
    leave_policy_id, name, annual_entitlement_days, carry_forward_max_days,
    max_consecutive_days, medical_certificate_after_days, tenure_required_months,
    lump_sum_days, is_unpaid, effective_from
) VALUES
    ('LPO-001', 'Annual', 24, 10, 20, NULL, 0, NULL, false, DATE '2026-01-01'),
    ('LPO-002', 'Sick', 12, 0, 15, 2, 0, NULL, false, DATE '2026-01-01'),
    ('LPO-003', 'Casual', 8, 0, 3, NULL, 0, NULL, false, DATE '2026-01-01'),
    ('LPO-004', 'Parental', NULL, 0, NULL, NULL, 12, 90, false, DATE '2026-01-01'),
    ('LPO-005', 'Compassionate', NULL, 0, 5, NULL, 0, 5, false, DATE '2026-01-01'),
    ('LPO-006', 'Unpaid', NULL, 0, 30, NULL, 0, 0, true, DATE '2026-01-01')
ON CONFLICT (leave_policy_id) DO NOTHING;

INSERT INTO public.expense_category (category, description) VALUES
    ('MEALS', 'Meals and refreshments'),
    ('LODGING', 'Accommodation and lodging'),
    ('AIRFARE', 'Air travel'),
    ('GROUND_TRANSPORT', 'Local ground transportation'),
    ('SOFTWARE', 'Software and digital services'),
    ('OFFICE_SUPPLIES', 'Office supplies and equipment'),
    ('TRAINING', 'Training and professional development'),
    ('CLIENT_ENTERTAINMENT', 'Client entertainment'),
    ('GIFTS', 'Business gifts'),
    ('COMMUNICATION', 'Communication services')
ON CONFLICT (category) DO NOTHING;

WITH countries(country, country_order) AS (
    VALUES ('IN'::char(2), 1), ('US'::char(2), 2), ('GB'::char(2), 3),
           ('DE'::char(2), 4), ('SG'::char(2), 5)
),
category_limits(category, per_line_limit_usd, receipt_threshold_usd, category_order) AS (
    VALUES
        ('MEALS', 150.00::numeric, 25.00::numeric, 1),
        ('LODGING', 500.00::numeric, 50.00::numeric, 2),
        ('AIRFARE', 2000.00::numeric, 0.00::numeric, 3),
        ('GROUND_TRANSPORT', 250.00::numeric, 25.00::numeric, 4),
        ('SOFTWARE', 3000.00::numeric, 0.00::numeric, 5),
        ('OFFICE_SUPPLIES', 500.00::numeric, 25.00::numeric, 6),
        ('TRAINING', 2000.00::numeric, 0.00::numeric, 7),
        ('CLIENT_ENTERTAINMENT', 1000.00::numeric, 25.00::numeric, 8),
        ('GIFTS', 500.00::numeric, 25.00::numeric, 9),
        ('COMMUNICATION', 300.00::numeric, 25.00::numeric, 10)
),
policy_rows AS (
    SELECT row_number() OVER (ORDER BY c.country_order, p.category_order) AS sequence,
           p.category, c.country, p.per_line_limit_usd, p.receipt_threshold_usd
    FROM countries c CROSS JOIN category_limits p
)
INSERT INTO public.expense_policy (
    expense_policy_id, category, country, per_line_limit_usd,
    receipt_threshold_usd, effective_from, version
)
SELECT 'XPO-' || lpad(sequence::text, 4, '0'), category, country,
       per_line_limit_usd, receipt_threshold_usd, DATE '2026-01-01', 1
FROM policy_rows
ORDER BY sequence
ON CONFLICT (expense_policy_id) DO NOTHING;

INSERT INTO public.holiday (holiday_id, country, holiday_date, holiday_name) VALUES
    ('HOL-2026-IN-01', 'IN', '2026-01-05', 'Illustrative holiday 01'),
    ('HOL-2026-IN-02', 'IN', '2026-02-09', 'Illustrative holiday 02'),
    ('HOL-2026-IN-03', 'IN', '2026-03-16', 'Illustrative holiday 03'),
    ('HOL-2026-IN-04', 'IN', '2026-04-20', 'Illustrative holiday 04'),
    ('HOL-2026-IN-05', 'IN', '2026-06-08', 'Illustrative holiday 05'),
    ('HOL-2026-IN-06', 'IN', '2026-08-17', 'Illustrative holiday 06'),
    ('HOL-2026-IN-07', 'IN', '2026-10-12', 'Illustrative holiday 07'),
    ('HOL-2026-IN-08', 'IN', '2026-12-14', 'Illustrative holiday 08'),
    ('HOL-2026-US-01', 'US', '2026-01-12', 'Illustrative holiday 01'),
    ('HOL-2026-US-02', 'US', '2026-02-23', 'Illustrative holiday 02'),
    ('HOL-2026-US-03', 'US', '2026-04-06', 'Illustrative holiday 03'),
    ('HOL-2026-US-04', 'US', '2026-05-18', 'Illustrative holiday 04'),
    ('HOL-2026-US-05', 'US', '2026-07-13', 'Illustrative holiday 05'),
    ('HOL-2026-US-06', 'US', '2026-09-14', 'Illustrative holiday 06'),
    ('HOL-2026-US-07', 'US', '2026-11-09', 'Illustrative holiday 07'),
    ('HOL-2026-US-08', 'US', '2026-12-21', 'Illustrative holiday 08'),
    ('HOL-2026-GB-01', 'GB', '2026-01-19', 'Illustrative holiday 01'),
    ('HOL-2026-GB-02', 'GB', '2026-03-02', 'Illustrative holiday 02'),
    ('HOL-2026-GB-03', 'GB', '2026-04-13', 'Illustrative holiday 03'),
    ('HOL-2026-GB-04', 'GB', '2026-06-01', 'Illustrative holiday 04'),
    ('HOL-2026-GB-05', 'GB', '2026-07-20', 'Illustrative holiday 05'),
    ('HOL-2026-GB-06', 'GB', '2026-09-21', 'Illustrative holiday 06'),
    ('HOL-2026-GB-07', 'GB', '2026-11-16', 'Illustrative holiday 07'),
    ('HOL-2026-GB-08', 'GB', '2026-12-07', 'Illustrative holiday 08'),
    ('HOL-2026-DE-01', 'DE', '2026-01-26', 'Illustrative holiday 01'),
    ('HOL-2026-DE-02', 'DE', '2026-03-09', 'Illustrative holiday 02'),
    ('HOL-2026-DE-03', 'DE', '2026-04-27', 'Illustrative holiday 03'),
    ('HOL-2026-DE-04', 'DE', '2026-06-15', 'Illustrative holiday 04'),
    ('HOL-2026-DE-05', 'DE', '2026-08-03', 'Illustrative holiday 05'),
    ('HOL-2026-DE-06', 'DE', '2026-09-28', 'Illustrative holiday 06'),
    ('HOL-2026-DE-07', 'DE', '2026-11-23', 'Illustrative holiday 07'),
    ('HOL-2026-DE-08', 'DE', '2026-12-28', 'Illustrative holiday 08'),
    ('HOL-2026-SG-01', 'SG', '2026-02-02', 'Illustrative holiday 01'),
    ('HOL-2026-SG-02', 'SG', '2026-03-23', 'Illustrative holiday 02'),
    ('HOL-2026-SG-03', 'SG', '2026-05-11', 'Illustrative holiday 03'),
    ('HOL-2026-SG-04', 'SG', '2026-06-22', 'Illustrative holiday 04'),
    ('HOL-2026-SG-05', 'SG', '2026-08-10', 'Illustrative holiday 05'),
    ('HOL-2026-SG-06', 'SG', '2026-09-07', 'Illustrative holiday 06'),
    ('HOL-2026-SG-07', 'SG', '2026-10-26', 'Illustrative holiday 07'),
    ('HOL-2026-SG-08', 'SG', '2026-12-14', 'Illustrative holiday 08')
ON CONFLICT (holiday_id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.reject_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Rows in %.% are append-only; % is not permitted',
        TG_TABLE_SCHEMA, TG_TABLE_NAME, TG_OP
        USING ERRCODE = '55000';
END
$$;

DROP TRIGGER IF EXISTS leave_ledger_entry_append_only ON public.leave_ledger_entry;
CREATE TRIGGER leave_ledger_entry_append_only
    BEFORE UPDATE OR DELETE ON public.leave_ledger_entry
    FOR EACH ROW EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS leave_request_event_append_only ON public.leave_request_event;
CREATE TRIGGER leave_request_event_append_only
    BEFORE UPDATE OR DELETE ON public.leave_request_event
    FOR EACH ROW EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS expense_claim_event_append_only ON public.expense_claim_event;
CREATE TRIGGER expense_claim_event_append_only
    BEFORE UPDATE OR DELETE ON public.expense_claim_event
    FOR EACH ROW EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS decision_audit_append_only ON public.decision_audit;
CREATE TRIGGER decision_audit_append_only
    BEFORE UPDATE OR DELETE ON public.decision_audit
    FOR EACH ROW EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS audit_finding_append_only ON public.audit_finding;
CREATE TRIGGER audit_finding_append_only
    BEFORE UPDATE OR DELETE ON public.audit_finding
    FOR EACH ROW EXECUTE FUNCTION public.reject_append_only_mutation();

DROP TRIGGER IF EXISTS audit_finding_event_append_only ON public.audit_finding_event;
CREATE TRIGGER audit_finding_event_append_only
    BEFORE UPDATE OR DELETE ON public.audit_finding_event
    FOR EACH ROW EXECUTE FUNCTION public.reject_append_only_mutation();

REVOKE ALL ON SCHEMA ground_truth FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA ground_truth FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO routeiq_app, routeiq_evaluator;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO routeiq_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO routeiq_evaluator;
GRANT USAGE ON SCHEMA ground_truth TO routeiq_evaluator;
GRANT SELECT ON ALL TABLES IN SCHEMA ground_truth TO routeiq_evaluator;
ALTER DEFAULT PRIVILEGES IN SCHEMA ground_truth REVOKE ALL ON TABLES FROM PUBLIC;
