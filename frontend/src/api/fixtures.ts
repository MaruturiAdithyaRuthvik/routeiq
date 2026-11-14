import {
    ApprovalRole,
    ApprovalStepStatus,
    AuditFindingCode,
    CountryCode,
    CurrencyCode,
    EvaluationMissType,
    ExpenseCategory,
    ExpenseClaimStatus,
    ExcludedDateReason,
    FindingStatus,
    FunctionalRole,
    IssueType,
    LeaveRequestStatus,
    ReimbursementStatus,
    ReceiptFileType,
    RequestType,
    ReasonCode,
    Severity,
    SystemRole,
    type ApprovalInboxItem,
    type ApprovalDecisionResult,
    type ApprovalRule,
    type AuditFinding,
    type AuditFindingDetail,
    type AuditRunResult,
    type AuthPersona,
    type CostCenter,
    type DatasetManifest,
    type DemoLoginRequest,
    type DemoLoginResult,
    type Employee,
    type ExpenseClaimDetail,
    type ExpenseClaimPreview,
    type EvaluationMiss,
    type EvaluationSummary,
    type ExpenseClaimSummary,
    type ExpensePolicy,
    type GetEmployeesQuery,
    type Holiday,
    type LeaveBalance,
    type LeavePolicy,
    type LeaveRequestCancelResult,
    type LeaveRequestDetail,
    type LeaveRequestPreview,
    type LeaveRequestSummary,
    type Me,
    type MetricsOverview,
    type Reimbursement,
} from "@/api/types"

export class FixtureNotFoundError extends Error {
    constructor(path: string, method: string) {
        super(`No deterministic fixture is defined for ${method} ${path}.`)
        this.name = "FixtureNotFoundError"
    }
}

const personas: AuthPersona[] = [
    {
        employee_id: "EMP-000001",
        display_name: "Avery Chen",
        country: CountryCode.US,
        functional_role: FunctionalRole.NONE,
        system_role: SystemRole.REQUESTER,
    },
    {
        employee_id: "EMP-000002",
        display_name: "Jordan Patel",
        country: CountryCode.US,
        functional_role: FunctionalRole.DEPT_HEAD,
        system_role: SystemRole.APPROVER,
    },
    {
        employee_id: "EMP-000004",
        display_name: "Taylor Brooks",
        country: CountryCode.GB,
        functional_role: FunctionalRole.FINANCE_CONTROLLER,
        system_role: SystemRole.PROCESS_OWNER,
    },
    {
        employee_id: "EMP-000005",
        display_name: "Morgan Lee",
        country: CountryCode.SG,
        functional_role: FunctionalRole.COMPLIANCE_OFFICER,
        system_role: SystemRole.ANALYST,
    },
    {
        employee_id: "EMP-000006",
        display_name: "Casey Nguyen",
        country: CountryCode.DE,
        functional_role: FunctionalRole.CFO,
        system_role: SystemRole.ADMIN,
    },
]

const employees: Employee[] = [
    {
        employee_id: "EMP-000001",
        display_name: "Avery Chen",
        country: CountryCode.US,
        home_currency: CurrencyCode.USD,
        hire_date: "2020-04-15",
        termination_date: null,
        manager_id: "EMP-000002",
        cost_center_id: "CC-0001",
        functional_role: FunctionalRole.NONE,
        system_role: SystemRole.REQUESTER,
        job_level: 4,
        is_ceo: false,
    },
    {
        employee_id: "EMP-000002",
        display_name: "Jordan Patel",
        country: CountryCode.US,
        home_currency: CurrencyCode.USD,
        hire_date: "2016-09-01",
        termination_date: null,
        manager_id: null,
        cost_center_id: "CC-0001",
        functional_role: FunctionalRole.DEPT_HEAD,
        system_role: SystemRole.APPROVER,
        job_level: 8,
        is_ceo: false,
    },
    {
        employee_id: "EMP-000004",
        display_name: "Taylor Brooks",
        country: CountryCode.GB,
        home_currency: CurrencyCode.GBP,
        hire_date: "2018-02-12",
        termination_date: null,
        manager_id: null,
        cost_center_id: "CC-0002",
        functional_role: FunctionalRole.FINANCE_CONTROLLER,
        system_role: SystemRole.PROCESS_OWNER,
        job_level: 9,
        is_ceo: false,
    },
    {
        employee_id: "EMP-000005",
        display_name: "Morgan Lee",
        country: CountryCode.SG,
        home_currency: CurrencyCode.SGD,
        hire_date: "2019-08-20",
        termination_date: null,
        manager_id: null,
        cost_center_id: "CC-0003",
        functional_role: FunctionalRole.COMPLIANCE_OFFICER,
        system_role: SystemRole.ANALYST,
        job_level: 7,
        is_ceo: false,
    },
    {
        employee_id: "EMP-000006",
        display_name: "Casey Nguyen",
        country: CountryCode.DE,
        home_currency: CurrencyCode.EUR,
        hire_date: "2015-03-03",
        termination_date: null,
        manager_id: null,
        cost_center_id: "CC-0004",
        functional_role: FunctionalRole.CFO,
        system_role: SystemRole.ADMIN,
        job_level: 10,
        is_ceo: false,
    },
]

const permissionsByRole: Record<SystemRole, string[]> = {
    [SystemRole.REQUESTER]: [
        "read:reference",
        "read:own_requests",
        "create:leave_request",
        "create:expense_claim",
        "cancel:own_request",
    ],
    [SystemRole.APPROVER]: ["read:reference", "read:assigned_approvals"],
    [SystemRole.PROCESS_OWNER]: ["read:reference", "read:all_requests"],
    [SystemRole.ANALYST]: ["read:reference", "read:operational_data"],
    [SystemRole.ADMIN]: ["read:reference", "read:all_requests", "admin:all"],
}

const balances: LeaveBalance[] = [
    {
        leave_balance_id: "LBL-EMP-000001-LPO-001-2026",
        employee_id: "EMP-000001",
        leave_policy_id: "LPO-001",
        balance_year: 2026,
        as_of_date: "2026-10-22",
        opening_days: 6,
        accrued_days: 18,
        adjustments_days: 0,
        used_days: 4,
        pending_days: 2,
        available_days: 18,
    },
]

const costCenters: CostCenter[] = [
    {
        cost_center_id: "CC-0001",
        name: "North America Operations",
        country: CountryCode.US,
        owner_employee_id: "EMP-000002",
        owner_name: "Jordan Patel",
        budget_year: 2026,
        budget_usd: "250000.00",
        currency: "USD",
    },
    {
        cost_center_id: "CC-0002",
        name: "UK Customer Experience",
        country: CountryCode.GB,
        owner_employee_id: "EMP-000004",
        owner_name: "Taylor Brooks",
        budget_year: 2026,
        budget_usd: "185000.00",
        currency: "USD",
    },
]

const holidays: Holiday[] = [
    {
        holiday_id: "HOL-2026-US-01",
        country: CountryCode.US,
        holiday_date: "2026-01-12",
        holiday_name: "Illustrative holiday 01",
        is_illustrative: true,
    },
]

const leavePolicies: LeavePolicy[] = [
    {
        leave_policy_id: "LPO-001",
        name: "Annual",
        annual_entitlement_days: 24,
        carry_forward_max_days: 10,
        max_consecutive_days: 20,
        medical_certificate_after_days: null,
        tenure_required_months: 0,
        lump_sum_days: null,
        is_unpaid: false,
        effective_from: "2026-01-01",
        effective_to: null,
    },
]

const expensePolicies: ExpensePolicy[] = [
    {
        expense_policy_id: "XPO-0011",
        category: ExpenseCategory.MEALS,
        country: CountryCode.US,
        per_line_limit_usd: "150.00",
        receipt_threshold_usd: "25.00",
        currency: "USD",
        effective_from: "2026-01-01",
        effective_to: null,
        version: 1,
    },
]

const approvalRules: ApprovalRule[] = [
    {
        approval_rule_id: "ARL-001",
        rule_code: "EXPENSE_50_1000",
        request_type: RequestType.EXPENSE,
        priority: 1,
        required_role: ApprovalRole.MANAGER,
        condition_description:
            "Claim total is at least USD 50 and below USD 1,000.",
        designated_employee_id: null,
        effective_from: "2026-01-01",
        effective_to: null,
        version: 1,
        is_active: true,
    },
]

const leaveRequests: LeaveRequestSummary[] = [
    {
        leave_request_id: "LVE-2026-000001",
        employee_id: "EMP-000001",
        employee_name: "Avery Chen",
        leave_policy_id: "LPO-001",
        policy_name: "Annual",
        start_date: "2026-11-23",
        end_date: "2026-11-28",
        business_days: 5,
        status: LeaveRequestStatus.PENDING_APPROVAL,
        submitted_at: "2026-10-22T09:00:00Z",
        medical_certificate_required: false,
        risk_score: 0,
        reason: "Family visit",
        approval_progress: { approved: 0, required: 2 },
    },
]

const expenseClaims: ExpenseClaimSummary[] = [
    {
        expense_claim_id: "EXP-2026-000001",
        employee_id: "EMP-000001",
        employee_name: "Avery Chen",
        merchant_name: "Northstar Cafe",
        merchant_country: CountryCode.US,
        expense_date: "2026-10-15",
        cost_center_id: "CC-0001",
        total_usd: "120.00",
        reporting_currency: "USD",
        status: ExpenseClaimStatus.PENDING_APPROVAL,
        submitted_at: "2026-10-22T09:00:00Z",
        risk_score: 0,
        line_count: 1,
        approval_progress: { approved: 0, required: 1 },
    },
]

const approvalInbox: ApprovalInboxItem[] = [
    {
        approval_step_id: "APR-EXP-2026-000001-01",
        request_type: RequestType.EXPENSE,
        request_id: "EXP-2026-000001",
        step_number: 1,
        required_role: ApprovalRole.MANAGER,
        approver_employee_id: "EMP-000002",
        approver_name: "Jordan Patel",
        status: ApprovalStepStatus.PENDING,
        assigned_at: "2026-10-22T09:00:00Z",
        due_date: "2026-10-27",
        decided_at: null,
        reason_code: null,
        employee_id: "EMP-000001",
        employee_name: "Avery Chen",
        amount_usd: "120.00",
        currency: "USD",
    },
]

const leaveDetail: LeaveRequestDetail = {
    ...leaveRequests[0]!,
    approval_steps: [
        {
            approval_step_id: "APR-LVE-2026-000001-01",
            request_type: RequestType.LEAVE,
            request_id: "LVE-2026-000001",
            step_number: 1,
            required_role: ApprovalRole.MANAGER,
            approver_employee_id: "EMP-000002",
            approver_name: "Jordan Patel",
            status: ApprovalStepStatus.PENDING,
            assigned_at: "2026-10-22T09:00:00Z",
            due_date: "2026-10-27",
            decided_at: null,
            reason_code: null,
        },
        {
            approval_step_id: "APR-LVE-2026-000001-02",
            request_type: RequestType.LEAVE,
            request_id: "LVE-2026-000001",
            step_number: 2,
            required_role: ApprovalRole.HR_PARTNER,
            approver_employee_id: "EMP-000003",
            approver_name: "Riley Morgan",
            status: ApprovalStepStatus.PENDING,
            assigned_at: "2026-10-22T09:00:00Z",
            due_date: "2026-10-27",
            decided_at: null,
            reason_code: null,
        },
    ],
    events: [
        {
            event_id: "LRE-2026-000001",
            sequence_number: 1,
            event_type: "CREATED",
            from_status: null,
            to_status: LeaveRequestStatus.DRAFT,
            occurred_at: "2026-10-22T08:59:00Z",
            actor_employee_id: "EMP-000001",
            reason_code: null,
        },
        {
            event_id: "LRE-2026-000002",
            sequence_number: 2,
            event_type: "SUBMITTED",
            from_status: LeaveRequestStatus.DRAFT,
            to_status: LeaveRequestStatus.SUBMITTED,
            occurred_at: "2026-10-22T09:00:00Z",
            actor_employee_id: "EMP-000001",
            reason_code: null,
        },
        {
            event_id: "LRE-2026-000003",
            sequence_number: 3,
            event_type: "APPROVAL_STARTED",
            from_status: LeaveRequestStatus.SUBMITTED,
            to_status: LeaveRequestStatus.PENDING_APPROVAL,
            occurred_at: "2026-10-22T09:00:00Z",
            actor_employee_id: null,
            reason_code: null,
        },
    ],
    ledger_entry_ids: ["LLE-2026-000001"],
    decision_audit_ids: ["DAU-2026-000001"],
}

const expenseDetail: ExpenseClaimDetail = {
    ...expenseClaims[0]!,
    lines: [
        {
            expense_line_id: "EXPL-EXP-2026-000001-01",
            expense_claim_id: "EXP-2026-000001",
            line_number: 1,
            category: ExpenseCategory.MEALS,
            expense_policy_id: "XPO-0011",
            description: "Team lunch",
            amount: "120.00",
            currency: CurrencyCode.USD,
            fx_rate_to_usd: "1.00000",
            amount_usd: "120.00",
            receipt_present: true,
            receipt_id: "RCT-2026-000001",
            receipt_hash:
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            file_type: ReceiptFileType.PDF,
            size_kb: 250,
        },
    ],
    approval_steps: [
        {
            approval_step_id: "APR-EXP-2026-000001-01",
            request_type: RequestType.EXPENSE,
            request_id: "EXP-2026-000001",
            step_number: 1,
            required_role: ApprovalRole.MANAGER,
            approver_employee_id: "EMP-000002",
            approver_name: "Jordan Patel",
            status: ApprovalStepStatus.PENDING,
            assigned_at: "2026-10-22T09:00:00Z",
            due_date: "2026-10-27",
            decided_at: null,
            reason_code: null,
        },
    ],
    events: [
        {
            event_id: "ECE-2026-000001",
            sequence_number: 1,
            event_type: "CREATED",
            from_status: null,
            to_status: ExpenseClaimStatus.DRAFT,
            occurred_at: "2026-10-22T08:59:00Z",
            actor_employee_id: "EMP-000001",
            reason_code: null,
            event_payload: {},
        },
        {
            event_id: "ECE-2026-000002",
            sequence_number: 2,
            event_type: "SUBMITTED",
            from_status: ExpenseClaimStatus.DRAFT,
            to_status: ExpenseClaimStatus.SUBMITTED,
            occurred_at: "2026-10-22T09:00:00Z",
            actor_employee_id: "EMP-000001",
            reason_code: null,
            event_payload: {},
        },
        {
            event_id: "ECE-2026-000003",
            sequence_number: 3,
            event_type: "APPROVAL_STARTED",
            from_status: ExpenseClaimStatus.SUBMITTED,
            to_status: ExpenseClaimStatus.PENDING_APPROVAL,
            occurred_at: "2026-10-22T09:00:00Z",
            actor_employee_id: null,
            reason_code: null,
            event_payload: {},
        },
    ],
    finding_codes: [],
    decision_audit_ids: ["DAU-2026-000002"],
    reimbursement_ids: [],
}

const expensePreview: ExpenseClaimPreview = {
    employee_id: "EMP-000001",
    merchant_name: "Northstar Cafe",
    merchant_country: CountryCode.US,
    expense_date: "2026-10-15",
    cost_center_id: "CC-0001",
    lines: [
        {
            line_id: null,
            line_number: 1,
            amount: "120.00",
            currency: CurrencyCode.USD,
            amount_usd: "120.00",
            fx_rate: "1.00000",
            reporting_currency: "USD",
            flags: [],
            limit_usd: "150.00",
        },
    ],
    total_usd: "120.00",
    reporting_currency: "USD",
    checks: [
        {
            code: "DATE_WITHIN_EMPLOYMENT",
            ok: true,
            message: "Expense date is within employment.",
            rule_id: "E3",
        },
        {
            code: "NOT_FUTURE_DATED",
            ok: true,
            message: "Expense date is not after AS_OF_DATE.",
            rule_id: "E4",
        },
        {
            code: "COST_CENTER_PRESENT",
            ok: true,
            message: "A cost center is assigned.",
            rule_id: "E4",
        },
        {
            code: "NO_DUPLICATE_RECEIPT",
            ok: true,
            message: "Receipt hash is not duplicated.",
            rule_id: "E4",
        },
        {
            code: "NO_HARD_LIMIT_BREACH",
            ok: true,
            message: "No line exceeds 150% of its policy limit.",
            rule_id: "E4",
        },
        {
            code: "RECEIPT_METADATA_VALID",
            ok: true,
            message: "Receipt metadata is complete.",
            rule_id: "E2",
        },
    ],
    path: [
        {
            level: 1,
            approver_type: ApprovalRole.MANAGER,
            approver_id: "EMP-000002",
            approver_name: "Jordan Patel",
            reason: "USD total is in the 50-to-under-1,000 band.",
            rule_ids: ["E5", "E7"],
        },
    ],
    exception_banner: null,
}

const approvalDecision: ApprovalDecisionResult = {
    approval_step: {
        ...approvalInbox[0]!,
        status: ApprovalStepStatus.APPROVED,
        decided_at: "2026-10-22T10:00:00Z",
    },
    request_status: ExpenseClaimStatus.APPROVED,
    next_step: null,
    event_id: "ECE-2026-000004",
    decision_audit_id: "DAU-2026-000003",
}

const reimbursements: Reimbursement[] = [
    {
        reimbursement_id: "RMB-2026-000001",
        expense_claim_id: "EXP-2026-000001",
        employee_id: "EMP-000001",
        amount_home_currency: "120.00",
        home_currency: CurrencyCode.USD,
        amount_usd: "120.00",
        reporting_currency: "USD",
        payment_date: "2026-10-29",
        status: ReimbursementStatus.SCHEDULED,
        created_at: "2026-10-22T10:00:00Z",
        paid_at: null,
        payment_reference: "PAY-2026-000001",
    },
]

const auditFinding: AuditFinding = {
    audit_finding_id: "AFN-2026-000001",
    finding_code: AuditFindingCode.DUPLICATE_RECEIPT,
    severity: Severity.ERROR,
    status: FindingStatus.OPEN,
    leave_request_id: null,
    expense_claim_id: "EXP-2026-000001",
    expense_line_id: "EXPL-EXP-2026-000001-01",
    approval_step_id: null,
    reimbursement_id: null,
    details: {
        receipt_hash:
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    },
    detected_at: "2026-10-22T11:00:00Z",
}

const auditFindingDetail: AuditFindingDetail = {
    ...auditFinding,
    events: [],
}

const leaveCancel: LeaveRequestCancelResult = {
    leave_request_id: "LVE-2026-000001",
    status: LeaveRequestStatus.CANCELLED,
    event_id: "LRE-2026-000004",
    released_ledger_entry_ids: ["LLE-2026-000002"],
    decision_audit_id: "DAU-2026-000002",
    cancelled_at: "2026-10-22T10:00:00Z",
}

const auditRun: AuditRunResult = {
    scope: "ALL",
    as_of_date: "2026-10-22",
    status: "COMPLETED",
    scanned_requests: 1800,
    findings_created: 1,
    findings_by_code: { [AuditFindingCode.DUPLICATE_RECEIPT]: 1 },
    finding_ids: ["AFN-2026-000001"],
    decision_audit_ids: ["DAU-2026-000004"],
}

const metrics: MetricsOverview = {
    as_of_date: "2026-10-22",
    reporting_currency: "USD",
    volumes_by_status: {
        leave_requests: {
            DRAFT: 20,
            SUBMITTED: 0,
            PENDING_APPROVAL: 18,
            APPROVED: 620,
            REJECTED: 120,
            CANCELLED: 22,
        },
        expense_claims: {
            DRAFT: 25,
            SUBMITTED: 0,
            PENDING_APPROVAL: 30,
            APPROVED: 700,
            REJECTED: 180,
            CANCELLED: 20,
            REIMBURSED: 45,
        },
        approval_steps: {
            PENDING: 33,
            APPROVED: 2450,
            REJECTED: 142,
        },
        reimbursements: { SCHEDULED: 12, PAID: 33 },
    },
    auto_approval_rate: 12,
    rejection_reasons: [
        { code: ReasonCode.INSUFFICIENT_BALANCE, count: 42, share_pct: 14 },
    ],
    cycle_time_by_level: [
        { level: 1, avg_hours: 11.2, p90_hours: 30.5 },
        { level: 2, avg_hours: 18.75, p90_hours: 46 },
    ],
    sla_breach_rate: 4.25,
    multi_level_share: 41,
    spend_by_cost_center: [
        {
            cost_center_id: "CC-0001",
            name: "North America Operations",
            spent_usd: "182500.00",
            budget_usd: "250000.00",
            utilization_pct: 73,
            currency: "USD",
        },
    ],
    spend_by_category: [
        {
            category: ExpenseCategory.MEALS,
            spent_usd: "12500.00",
            claim_count: 210,
            currency: "USD",
        },
        {
            category: ExpenseCategory.AIRFARE,
            spent_usd: "44900.00",
            claim_count: 87,
            currency: "USD",
        },
        {
            category: ExpenseCategory.LODGING,
            spent_usd: "22800.00",
            claim_count: 134,
            currency: "USD",
        },
    ],
    spend_by_country: [
        {
            country: CountryCode.US,
            spent_usd: "220000.00",
            claim_count: 310,
            currency: "USD",
        },
    ],
    leave_utilization: [
        {
            leave_policy_id: "LPO-001",
            name: "Annual",
            opening_days: 1800,
            accrued_days: 6000,
            used_days: 1420,
            pending_days: 90,
            available_days: 6290,
            utilization_pct: 18.21,
        },
    ],
    reimbursements: {
        paid_usd: "42000.00",
        scheduled_usd: "15800.00",
        currency: "USD",
        paid_count: 33,
        scheduled_count: 12,
    },
    anomalies_flagged: 72,
    recent_activity: [
        {
            event_id: "ECE-2026-000003",
            request_type: RequestType.EXPENSE,
            request_id: "EXP-2026-000001",
            event_type: "APPROVAL_STARTED",
            from_status: ExpenseClaimStatus.SUBMITTED,
            to_status: ExpenseClaimStatus.PENDING_APPROVAL,
            occurred_at: "2026-10-22T09:00:00Z",
            employee_id: "EMP-000001",
            employee_name: "Avery Chen",
            summary: "Expense claim submitted for approval.",
        },
    ],
}

const evaluationSummary: EvaluationSummary = {
    as_of_date: "2026-10-22",
    evaluated_decisions: 1800,
    decision_accuracy: { correct: 1710, total: 1800, rate: 0.95 },
    approval_path_accuracy: { correct: 1656, total: 1800, rate: 0.92 },
    anomaly_precision: { true_positive: 72, false_positive: 8, rate: 0.9 },
    anomaly_recall: { true_positive: 72, false_negative: 8, rate: 0.9 },
    reimbursement_eligibility_accuracy: {
        correct: 990,
        total: 1000,
        rate: 0.99,
    },
    validation_pass_counts: { passed: 1792, failed: 8, total: 1800 },
}

const evaluationMisses: EvaluationMiss[] = [
    {
        ground_truth_id: "GTA-2026-000001",
        target_type: "EXPENSE_LINE",
        target_id: "EXPL-EXP-2026-000001-01",
        expense_claim_id: "EXP-2026-000001",
        issue_type: IssueType.DUPLICATE_RECEIPT,
        expected_finding_code: AuditFindingCode.DUPLICATE_RECEIPT,
        actual_finding_codes: [],
        miss_type: EvaluationMissType.MISSED_ANOMALY,
        expected_status: null,
        actual_status: null,
        expected_approval_path: [],
        actual_approval_path: [],
    },
]

const datasetManifest: DatasetManifest = {
    generator_name: "RouteIQ synthetic generator",
    generator_version: "1.0.0",
    seed: 20261022,
    as_of_date: "2026-10-22",
    reporting_currency: "USD",
    row_counts: {
        employee: 400,
        leave_policy: 6,
        leave_balance: 2400,
        leave_request: 800,
        expense_policy: 50,
        expense_claim: 1000,
        expense_line: 5500,
        cost_center: 20,
        approval_rule: 24,
        holiday: 40,
        audit_finding: 80,
        ground_truth_anomaly: 80,
        ground_truth_decision: 1800,
    },
    files: [
        {
            path: "data/employees.csv",
            format: "csv",
            row_count: 400,
            sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            contains_ground_truth: false,
        },
        {
            path: "data/ground_truth.json",
            format: "json",
            row_count: 80,
            sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            contains_ground_truth: true,
        },
    ],
    reference_fixtures: {
        countries: [
            CountryCode.IN,
            CountryCode.US,
            CountryCode.GB,
            CountryCode.DE,
            CountryCode.SG,
        ],
        holiday_count_per_country: 8,
        expense_policy_count: 50,
    },
    validation: { status: "PASSED", checks_passed: 12, checks_failed: 0 },
}

const leavePreview: LeaveRequestPreview = {
    employee_id: "EMP-000001",
    leave_policy_id: "LPO-001",
    start_date: "2026-11-23",
    end_date: "2026-11-28",
    business_days: 5,
    excluded_dates: [
        { date: "2026-11-28", reason: ExcludedDateReason.WEEKEND },
    ],
    balance_before: 18,
    balance_after: 13,
    checks: [
        {
            code: "DATE_ORDER",
            ok: true,
            message: "End date is on or after start date.",
            rule_id: "L4",
        },
        {
            code: "BUSINESS_DAYS_POSITIVE",
            ok: true,
            message: "The range contains 5 business days.",
            rule_id: "G4",
        },
        {
            code: "EMPLOYEE_ACTIVE",
            ok: true,
            message: "The employee is active for the requested dates.",
            rule_id: "L4",
        },
        {
            code: "TENURE_ELIGIBLE",
            ok: true,
            message: "The employee meets the policy tenure requirement.",
            rule_id: "L4",
        },
        {
            code: "MAX_CONSECUTIVE",
            ok: true,
            message: "The request is within the consecutive-day limit.",
            rule_id: "L4",
        },
        {
            code: "NO_OVERLAP",
            ok: true,
            message: "No active overlapping leave request exists.",
            rule_id: "L4",
        },
        {
            code: "BALANCE_SUFFICIENT",
            ok: true,
            message: "Available balance covers the request.",
            rule_id: "L4",
        },
    ],
    valid: true,
    blocking_reason: null,
    path: [
        {
            level: 1,
            approver_type: ApprovalRole.MANAGER,
            approver_id: "EMP-000002",
            approver_name: "Jordan Patel",
            reason: "Direct manager per G5.",
            rule_ids: ["L5", "G5"],
        },
    ],
}

function list<T>(
    values: T[],
    query?: Record<string, string | number | boolean | null | undefined>,
): { data: T[]; meta: { page: number; page_size: number; total: number } } {
    const page = Math.max(1, Number(query?.page ?? 1))
    const pageSize = Math.min(100, Math.max(1, Number(query?.page_size ?? 25)))
    const start = (page - 1) * pageSize
    return {
        data: values.slice(start, start + pageSize),
        meta: { page, page_size: pageSize, total: values.length },
    }
}

function single<T>(data: T): { data: T } {
    return { data }
}

function normalizePath(path: string): string {
    return path.startsWith("/api/v1/") ? path.slice("/api/v1".length) : path
}

function getMe(token?: string): Me {
    const employee =
        employees.find((item) => item.employee_id === token?.split(".")[1]) ??
        employees[0]!
    return {
        ...employee,
        permissions: permissionsByRole[employee.system_role],
    }
}

export function getFixture(
    rawPath: string,
    method: string,
    body?: unknown,
    query?: Record<string, string | number | boolean | null | undefined>,
    token?: string | null,
): unknown {
    const path = normalizePath(rawPath)
    const verb = method.toUpperCase()

    if (path === "/auth/personas" && verb === "GET")
        return list(personas, query)
    if (path === "/auth/demo-login" && verb === "POST") {
        const request = body as DemoLoginRequest | undefined
        const selected =
            personas.find(
                (persona) => persona.employee_id === request?.employee_id,
            ) ?? personas[0]!
        const result: DemoLoginResult = {
            access_token: `fixture.${selected.employee_id}.20261022`,
            token_type: "Bearer",
            expires_in_seconds: 3600,
            persona: {
                employee_id: selected.employee_id,
                display_name: selected.display_name,
                functional_role: selected.functional_role,
                system_role: selected.system_role,
            },
        }
        return single(result)
    }
    if (path === "/me" && verb === "GET")
        return single(getMe(token ?? undefined))
    if (path === "/metrics/overview" && verb === "GET") return single(metrics)
    if (path === "/employees" && verb === "GET") {
        const filters = query as GetEmployeesQuery | undefined
        const matches = employees.filter((employee) => {
            const search = filters?.q?.toLowerCase()
            return (
                (!filters?.country || employee.country === filters.country) &&
                (!filters?.system_role ||
                    employee.system_role === filters.system_role) &&
                (!search ||
                    `${employee.employee_id} ${employee.display_name}`
                        .toLowerCase()
                        .includes(search))
            )
        })
        return list(matches, query)
    }
    if (path === "/cost-centers" && verb === "GET")
        return list(costCenters, query)
    if (path === "/holidays" && verb === "GET") return list(holidays, query)
    if (path === "/leave-policies" && verb === "GET")
        return list(leavePolicies, query)
    if (path === "/expense-policies" && verb === "GET")
        return list(expensePolicies, query)
    if (path === "/approval-rules" && verb === "GET")
        return list(approvalRules, query)
    if (/^\/employees\/[^/]+\/leave-balances$/.test(path) && verb === "GET")
        return list(
            balances.map((item) => {
                const employeeId = path.split("/")[2] ?? item.employee_id
                return {
                    ...item,
                    employee_id: employeeId,
                    leave_balance_id: `LBL-${employeeId}-LPO-001-2026`,
                }
            }),
            query,
        )
    if (/^\/employees\/[^/]+$/.test(path) && verb === "GET")
        return single(
            employees.find((item) => item.employee_id === path.split("/")[2]) ??
                employees[0]!,
        )
    if (path === "/leave-requests/preview" && verb === "POST")
        return single(leavePreview)
    if (path === "/leave-requests" && verb === "GET")
        return list(leaveRequests, query)
    if (path === "/leave-requests" && verb === "POST")
        return single(leaveDetail)
    if (/^\/leave-requests\/[^/]+\/cancel$/.test(path) && verb === "POST")
        return single(leaveCancel)
    if (/^\/leave-requests\/[^/]+$/.test(path) && verb === "GET")
        return single(leaveDetail)
    if (path === "/expense-claims/preview" && verb === "POST")
        return single(expensePreview)
    if (path === "/expense-claims" && verb === "GET")
        return list(expenseClaims, query)
    if (path === "/expense-claims" && verb === "POST")
        return single(expenseDetail)
    if (/^\/expense-claims\/[^/]+$/.test(path) && verb === "GET")
        return single(expenseDetail)
    if (path === "/approvals/inbox" && verb === "GET")
        return list(approvalInbox, query)
    if (/^\/approval-steps\/[^/]+\/decision$/.test(path) && verb === "POST")
        return single(approvalDecision)
    if (path === "/reimbursements" && verb === "GET")
        return list(reimbursements, query)
    if (/^\/reimbursements\/[^/]+$/.test(path) && verb === "GET")
        return single(reimbursements[0]!)
    if (path === "/audit/run" && verb === "POST") return single(auditRun)
    if (path === "/audit/findings" && verb === "GET")
        return list([auditFinding], query)
    if (/^\/audit\/findings\/[^/]+$/.test(path) && verb === "GET")
        return single(auditFindingDetail)
    if (path === "/evaluation/summary" && verb === "GET")
        return single(evaluationSummary)
    if (path === "/evaluation/misses" && verb === "GET")
        return list(evaluationMisses, query)
    if (path === "/dataset/manifest" && verb === "GET")
        return single(datasetManifest)

    throw new FixtureNotFoundError(path, verb)
}

export const fixturePersonaIds = personas.map((persona) => persona.employee_id)
