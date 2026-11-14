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
    type ExpenseClaimPreviewRequest,
    type ExpensePreviewFlag,
    type ExpensePreviewLine,
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
    type LeaveRequestPreviewRequest,
    type LeaveRequestSummary,
    type ApprovalPathStep,
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

const holidays: Holiday[] = (
    [
        [
            CountryCode.IN,
            [
                "2026-01-05",
                "2026-02-09",
                "2026-03-16",
                "2026-04-20",
                "2026-06-08",
                "2026-08-17",
                "2026-10-12",
                "2026-12-14",
            ],
        ],
        [
            CountryCode.US,
            [
                "2026-01-12",
                "2026-02-23",
                "2026-04-06",
                "2026-05-18",
                "2026-07-13",
                "2026-09-14",
                "2026-11-09",
                "2026-12-21",
            ],
        ],
        [
            CountryCode.GB,
            [
                "2026-01-19",
                "2026-03-02",
                "2026-04-13",
                "2026-06-01",
                "2026-07-20",
                "2026-09-21",
                "2026-11-16",
                "2026-12-07",
            ],
        ],
        [
            CountryCode.DE,
            [
                "2026-01-26",
                "2026-03-09",
                "2026-04-27",
                "2026-06-15",
                "2026-08-03",
                "2026-09-28",
                "2026-11-23",
                "2026-12-28",
            ],
        ],
        [
            CountryCode.SG,
            [
                "2026-02-02",
                "2026-03-23",
                "2026-05-11",
                "2026-06-22",
                "2026-08-10",
                "2026-09-07",
                "2026-10-26",
                "2026-12-14",
            ],
        ],
    ] satisfies Array<[CountryCode, string[]]>
).flatMap(([country, dates]) =>
    dates.map((holiday_date, index) => ({
        holiday_id:
            `HOL-2026-${country}-${String(index + 1).padStart(2, "0")}` as Holiday["holiday_id"],
        country,
        holiday_date,
        holiday_name: `Illustrative holiday ${String(index + 1).padStart(2, "0")}`,
        is_illustrative: true as const,
    })),
)

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
    {
        leave_policy_id: "LPO-002",
        name: "Sick",
        annual_entitlement_days: 12,
        carry_forward_max_days: 0,
        max_consecutive_days: 15,
        medical_certificate_after_days: 2,
        tenure_required_months: 0,
        lump_sum_days: null,
        is_unpaid: false,
        effective_from: "2026-01-01",
        effective_to: null,
    },
    {
        leave_policy_id: "LPO-003",
        name: "Casual",
        annual_entitlement_days: 8,
        carry_forward_max_days: 0,
        max_consecutive_days: 3,
        medical_certificate_after_days: null,
        tenure_required_months: 0,
        lump_sum_days: null,
        is_unpaid: false,
        effective_from: "2026-01-01",
        effective_to: null,
    },
    {
        leave_policy_id: "LPO-004",
        name: "Parental",
        annual_entitlement_days: null,
        carry_forward_max_days: 0,
        max_consecutive_days: null,
        medical_certificate_after_days: null,
        tenure_required_months: 12,
        lump_sum_days: 90,
        is_unpaid: false,
        effective_from: "2026-01-01",
        effective_to: null,
    },
    {
        leave_policy_id: "LPO-005",
        name: "Compassionate",
        annual_entitlement_days: null,
        carry_forward_max_days: 0,
        max_consecutive_days: 5,
        medical_certificate_after_days: null,
        tenure_required_months: 0,
        lump_sum_days: 5,
        is_unpaid: false,
        effective_from: "2026-01-01",
        effective_to: null,
    },
    {
        leave_policy_id: "LPO-006",
        name: "Unpaid",
        annual_entitlement_days: null,
        carry_forward_max_days: 0,
        max_consecutive_days: 30,
        medical_certificate_after_days: null,
        tenure_required_months: 0,
        lump_sum_days: 0,
        is_unpaid: true,
        effective_from: "2026-01-01",
        effective_to: null,
    },
]

const usExpensePolicyValues: Record<
    ExpenseCategory,
    { per_line_limit_usd: number; receipt_threshold_usd: number }
> = {
    [ExpenseCategory.MEALS]: {
        per_line_limit_usd: 150,
        receipt_threshold_usd: 25,
    },
    [ExpenseCategory.LODGING]: {
        per_line_limit_usd: 500,
        receipt_threshold_usd: 50,
    },
    [ExpenseCategory.AIRFARE]: {
        per_line_limit_usd: 2000,
        receipt_threshold_usd: 0,
    },
    [ExpenseCategory.GROUND_TRANSPORT]: {
        per_line_limit_usd: 250,
        receipt_threshold_usd: 25,
    },
    [ExpenseCategory.SOFTWARE]: {
        per_line_limit_usd: 3000,
        receipt_threshold_usd: 0,
    },
    [ExpenseCategory.OFFICE_SUPPLIES]: {
        per_line_limit_usd: 500,
        receipt_threshold_usd: 25,
    },
    [ExpenseCategory.TRAINING]: {
        per_line_limit_usd: 2000,
        receipt_threshold_usd: 0,
    },
    [ExpenseCategory.CLIENT_ENTERTAINMENT]: {
        per_line_limit_usd: 1000,
        receipt_threshold_usd: 25,
    },
    [ExpenseCategory.GIFTS]: {
        per_line_limit_usd: 500,
        receipt_threshold_usd: 25,
    },
    [ExpenseCategory.COMMUNICATION]: {
        per_line_limit_usd: 300,
        receipt_threshold_usd: 25,
    },
}
const expensePolicyScales: Record<CountryCode, number> = {
    [CountryCode.IN]: 0.65,
    [CountryCode.US]: 1,
    [CountryCode.GB]: 0.95,
    [CountryCode.DE]: 0.9,
    [CountryCode.SG]: 1.05,
}
const expensePolicies: ExpensePolicy[] = Object.values(CountryCode).flatMap(
    (country, countryIndex) =>
        Object.values(ExpenseCategory).map((category, categoryIndex) => {
            const base = usExpensePolicyValues[category]
            const scale = expensePolicyScales[country]
            const id =
                countryIndex * Object.values(ExpenseCategory).length +
                categoryIndex +
                1
            return {
                expense_policy_id:
                    `XPO-${String(id).padStart(4, "0")}` as ExpensePolicy["expense_policy_id"],
                category,
                country,
                per_line_limit_usd: (base.per_line_limit_usd * scale).toFixed(
                    2,
                ),
                receipt_threshold_usd: (
                    base.receipt_threshold_usd * scale
                ).toFixed(2),
                currency: "USD",
                effective_from: "2026-01-01",
                effective_to: null,
                version: 1,
            }
        }),
)

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

function getLeaveRequestPreview(
    request: LeaveRequestPreviewRequest,
    token?: string | null,
): LeaveRequestPreview {
    const employeeId =
        request.employee_id ?? token?.split(".")[1] ?? "EMP-000001"
    const employee =
        employees.find((item) => item.employee_id === employeeId) ??
        employees[0]!
    const policy = leavePolicies.find(
        (item) => item.leave_policy_id === request.leave_policy_id,
    )
    const from = new Date(`${request.start_date}T00:00:00Z`)
    const to = new Date(`${request.end_date}T00:00:00Z`)
    const dateOrderOk =
        !Number.isNaN(from.valueOf()) &&
        !Number.isNaN(to.valueOf()) &&
        from <= to
    const excludedDates: LeaveRequestPreview["excluded_dates"] = []
    let businessDays = 0

    if (dateOrderOk) {
        for (
            const date = new Date(from);
            date <= to;
            date.setUTCDate(date.getUTCDate() + 1)
        ) {
            const isoDate = date.toISOString().slice(0, 10)
            const weekday = date.getUTCDay()
            const holiday = holidays.find(
                (item) =>
                    item.country === employee.country &&
                    item.holiday_date === isoDate,
            )
            if (weekday === 0 || weekday === 6) {
                excludedDates.push({
                    date: isoDate,
                    reason: ExcludedDateReason.WEEKEND,
                })
            } else if (holiday) {
                excludedDates.push({
                    date: isoDate,
                    reason: ExcludedDateReason.HOLIDAY,
                })
            } else {
                businessDays += 1
            }
        }
    }

    const balance = balances.find(
        (item) =>
            item.employee_id === employee.employee_id &&
            item.leave_policy_id === request.leave_policy_id,
    )
    const availableDays =
        balance?.available_days ??
        policy?.annual_entitlement_days ??
        policy?.lump_sum_days ??
        0
    const tenureMonths =
        (from.getUTCFullYear() - Number(employee.hire_date.slice(0, 4))) * 12 +
        from.getUTCMonth() -
        Number(employee.hire_date.slice(5, 7)) +
        (from.getUTCDate() >= Number(employee.hire_date.slice(8, 10)) ? 0 : -1)
    const tenureEligible =
        Boolean(policy) && tenureMonths >= (policy?.tenure_required_months ?? 0)
    const overlapping = leaveRequests.some(
        (item) =>
            item.employee_id === employee.employee_id &&
            item.status !== LeaveRequestStatus.CANCELLED &&
            item.status !== LeaveRequestStatus.REJECTED &&
            item.start_date <= request.end_date &&
            item.end_date >= request.start_date,
    )
    const checks: LeaveRequestPreview["checks"] = leavePreview.checks.map(
        (check) => {
            const okByCode: Record<string, boolean> = {
                DATE_ORDER: dateOrderOk,
                BUSINESS_DAYS_POSITIVE: businessDays > 0,
                EMPLOYEE_ACTIVE:
                    employee.termination_date === null ||
                    employee.termination_date >= request.end_date,
                TENURE_ELIGIBLE: tenureEligible,
                MAX_CONSECUTIVE:
                    Boolean(policy) &&
                    (policy?.max_consecutive_days === null ||
                        businessDays <= (policy?.max_consecutive_days ?? 0)),
                NO_OVERLAP: !overlapping,
                BALANCE_SUFFICIENT:
                    Boolean(policy?.is_unpaid) || availableDays >= businessDays,
            }
            const ok = okByCode[check.code] ?? false
            return {
                ...check,
                ok,
                message:
                    check.code === "BUSINESS_DAYS_POSITIVE"
                        ? ok
                            ? `The range contains ${businessDays} business days.`
                            : "The range contains no business days."
                        : check.code === "BALANCE_SUFFICIENT"
                          ? ok
                              ? "Available balance covers the request."
                              : "Available balance does not cover the request."
                          : check.message,
            }
        },
    )
    const firstFailed = checks.find((check) => !check.ok)
    const blockingReason =
        firstFailed?.code === "DATE_ORDER"
            ? ReasonCode.INVALID_DATE_RANGE
            : firstFailed?.code === "BUSINESS_DAYS_POSITIVE"
              ? ReasonCode.ZERO_BUSINESS_DAYS
              : firstFailed?.code === "EMPLOYEE_ACTIVE"
                ? ReasonCode.EMPLOYEE_NOT_ACTIVE
                : firstFailed?.code === "TENURE_ELIGIBLE"
                  ? ReasonCode.TENURE_INELIGIBLE
                  : firstFailed?.code === "MAX_CONSECUTIVE"
                    ? ReasonCode.MAX_CONSECUTIVE_DAYS
                    : firstFailed?.code === "NO_OVERLAP"
                      ? ReasonCode.OVERLAP
                      : firstFailed
                        ? ReasonCode.INSUFFICIENT_BALANCE
                        : null
    const path: ApprovalPathStep[] = checks.every((check) => check.ok)
        ? [
              {
                  ...leavePreview.path[0]!,
                  approver_id: employee.manager_id,
                  approver_name:
                      employees.find(
                          (item) => item.employee_id === employee.manager_id,
                      )?.display_name ?? leavePreview.path[0]!.approver_name,
                  reason:
                      businessDays <= 3
                          ? "Direct manager per G5."
                          : "Direct manager per G5; HR review is required for this duration.",
              },
              ...(businessDays >= 4
                  ? [
                        {
                            level: 2,
                            approver_type: ApprovalRole.HR_PARTNER,
                            approver_id: "EMP-000003" as const,
                            approver_name: "Riley Morgan",
                            reason: "HR review is added for leave requests of 4 or more business days.",
                            rule_ids: ["L5", "G5"],
                        },
                    ]
                  : []),
          ]
        : []

    return {
        employee_id: employee.employee_id,
        leave_policy_id: request.leave_policy_id,
        start_date: request.start_date,
        end_date: request.end_date,
        business_days: businessDays,
        excluded_dates: excludedDates,
        balance_before: policy?.is_unpaid ? null : availableDays,
        balance_after: policy?.is_unpaid ? null : availableDays - businessDays,
        checks,
        valid: checks.every((check) => check.ok),
        blocking_reason: blockingReason,
        path,
    }
}

function getExpenseClaimPreview(
    request: ExpenseClaimPreviewRequest,
    token?: string | null,
): ExpenseClaimPreview {
    const employeeId =
        request.employee_id ?? token?.split(".")[1] ?? "EMP-000001"
    const employee =
        employees.find((item) => item.employee_id === employeeId) ??
        employees[0]!
    const fxRates: Record<CurrencyCode, number> = {
        [CurrencyCode.INR]: 0.012,
        [CurrencyCode.USD]: 1,
        [CurrencyCode.GBP]: 1.27,
        [CurrencyCode.EUR]: 1.08,
        [CurrencyCode.SGD]: 0.74,
    }
    const knownHashes = new Set(
        expenseDetail.lines
            .map((line) => line.receipt_hash)
            .filter((hash): hash is string => hash !== null),
    )
    const seenHashes = new Set(knownHashes)
    let duplicateReceipt = false
    let hardLimitBreach = false
    let receiptMetadataValid = true
    const allFlags: ExpensePreviewFlag[] = []
    const lines: ExpensePreviewLine[] = request.lines.map((line) => {
        const fxRate = fxRates[line.currency]
        const amountUsd = Math.round(Number(line.amount) * fxRate * 100) / 100
        const policy =
            expensePolicies.find(
                (item) =>
                    item.country === employee.country &&
                    item.category === line.category,
            ) ?? expensePolicies[0]!
        const limit = Number(policy.per_line_limit_usd)
        const threshold = Number(policy.receipt_threshold_usd)
        const flags: ExpensePreviewFlag[] = []
        if (amountUsd > limit) {
            flags.push({
                code: AuditFindingCode.POLICY_LIMIT_BREACH,
                message: "Line is over the per-line policy limit.",
                pct_over: Math.round((amountUsd / limit - 1) * 100),
            })
        }
        if (amountUsd > threshold && !line.receipt_present) {
            flags.push({
                code: AuditFindingCode.MISSING_RECEIPT,
                message: "A receipt is required for this amount.",
                pct_over: null,
            })
        }
        if (line.receipt_hash && seenHashes.has(line.receipt_hash)) {
            duplicateReceipt = true
            flags.push({
                code: AuditFindingCode.DUPLICATE_RECEIPT,
                message: "Receipt hash has already been used.",
                pct_over: null,
            })
        }
        if (line.receipt_hash) seenHashes.add(line.receipt_hash)
        if (
            line.receipt_present &&
            (!line.receipt_id ||
                !line.receipt_hash ||
                !line.file_type ||
                !line.size_kb ||
                line.size_kb <= 0)
        ) {
            receiptMetadataValid = false
        }
        if (amountUsd > limit * 1.5) hardLimitBreach = true
        allFlags.push(...flags)
        return {
            line_id: null,
            line_number: line.line_number,
            amount: line.amount,
            currency: line.currency,
            amount_usd: amountUsd.toFixed(2),
            fx_rate: fxRate.toFixed(5),
            reporting_currency: "USD",
            flags,
            limit_usd: policy.per_line_limit_usd,
        }
    })
    const dateWithinEmployment =
        request.expense_date >= employee.hire_date &&
        (employee.termination_date === null ||
            request.expense_date <= employee.termination_date)
    const notFutureDated = request.expense_date <= "2026-10-22"
    const costCenterPresent = request.cost_center_id !== null
    const total = lines.reduce((sum, line) => sum + Number(line.amount_usd), 0)
    const checks: ExpenseClaimPreview["checks"] = expensePreview.checks.map(
        (check) => {
            const okByCode: Record<string, boolean> = {
                DATE_WITHIN_EMPLOYMENT: dateWithinEmployment,
                NOT_FUTURE_DATED: notFutureDated,
                COST_CENTER_PRESENT: costCenterPresent,
                NO_DUPLICATE_RECEIPT: !duplicateReceipt,
                NO_HARD_LIMIT_BREACH: !hardLimitBreach,
                RECEIPT_METADATA_VALID: receiptMetadataValid,
            }
            return {
                ...check,
                ok: okByCode[check.code] ?? false,
                message:
                    check.code === "COST_CENTER_PRESENT" && !costCenterPresent
                        ? "Choose a cost center before submitting."
                        : check.message,
            }
        },
    )

    const baseRoles =
        total < 50
            ? allFlags.length === 0
                ? [ApprovalRole.SYSTEM]
                : [ApprovalRole.MANAGER]
            : total < 1000
              ? [ApprovalRole.MANAGER]
              : total < 5000
                ? [ApprovalRole.MANAGER, ApprovalRole.DEPT_HEAD]
                : total < 20000
                  ? [
                        ApprovalRole.MANAGER,
                        ApprovalRole.DEPT_HEAD,
                        ApprovalRole.FINANCE_CONTROLLER,
                    ]
                  : [
                        ApprovalRole.MANAGER,
                        ApprovalRole.DEPT_HEAD,
                        ApprovalRole.FINANCE_CONTROLLER,
                        ApprovalRole.CFO,
                    ]
    const addRole = (role: ApprovalRole) => {
        if (!baseRoles.includes(role)) baseRoles.push(role)
    }
    const internationalAirfare = request.lines.some(
        (line) =>
            line.category === ExpenseCategory.AIRFARE &&
            employee.country !== request.merchant_country,
    )
    const highRiskCategory = request.lines.some(
        (line) =>
            (line.category === ExpenseCategory.CLIENT_ENTERTAINMENT ||
                line.category === ExpenseCategory.GIFTS) &&
            Number(
                lines.find((item) => item.line_number === line.line_number)
                    ?.amount_usd ?? 0,
            ) > 250,
    )
    if (internationalAirfare) addRole(ApprovalRole.FINANCE_CONTROLLER)
    if (highRiskCategory) addRole(ApprovalRole.COMPLIANCE_OFFICER)
    if (
        allFlags.some(
            (flag) =>
                flag.code === AuditFindingCode.POLICY_LIMIT_BREACH ||
                flag.code === AuditFindingCode.MISSING_RECEIPT,
        )
    ) {
        addRole(ApprovalRole.FINANCE_CONTROLLER)
    }

    const approverDetails: Record<
        ApprovalRole,
        {
            id: string | null
            name: string | null
            reason: string
            rules: string[]
        }
    > = {
        [ApprovalRole.MANAGER]: {
            id: employee.manager_id,
            name:
                employees.find(
                    (item) => item.employee_id === employee.manager_id,
                )?.display_name ?? "Manager",
            reason: "Claim total is routed to the employee's manager.",
            rules: ["E5", "E7"],
        },
        [ApprovalRole.DEPT_HEAD]: {
            id: request.cost_center_id,
            name:
                costCenters.find(
                    (center) =>
                        center.cost_center_id === request.cost_center_id,
                )?.owner_name ?? "Department head",
            reason: "Claim total requires department-head review.",
            rules: ["E5", "E7"],
        },
        [ApprovalRole.FINANCE_CONTROLLER]: {
            id: "EMP-000004",
            name: "Taylor Brooks",
            reason: "An exception requires finance review.",
            rules: ["E6", "AU3"],
        },
        [ApprovalRole.CFO]: {
            id: "EMP-000006",
            name: "Casey Nguyen",
            reason: "Claim total requires CFO review.",
            rules: ["E5", "E7"],
        },
        [ApprovalRole.COMPLIANCE_OFFICER]: {
            id: "EMP-000005",
            name: "Morgan Lee",
            reason: "A high-risk category requires compliance review.",
            rules: ["E6", "AU3"],
        },
        [ApprovalRole.HR_PARTNER]: {
            id: "EMP-000003",
            name: "Riley Morgan",
            reason: "HR review is required.",
            rules: ["E6"],
        },
        [ApprovalRole.SYSTEM]: {
            id: null,
            name: "RouteIQ",
            reason: "Claim is within the automatic approval band.",
            rules: ["E5"],
        },
    }
    const path = baseRoles.map((role, index) => {
        const detail = approverDetails[role]
        return {
            level: index + 1,
            approver_type: role,
            approver_id: detail.id as ApprovalPathStep["approver_id"],
            approver_name: detail.name,
            reason: detail.reason,
            rule_ids: detail.rules,
        }
    })
    const exception = allFlags.length > 0 || checks.some((check) => !check.ok)

    return {
        employee_id: employee.employee_id,
        merchant_name: request.merchant_name,
        merchant_country: request.merchant_country,
        expense_date: request.expense_date,
        cost_center_id: request.cost_center_id,
        lines,
        total_usd: total.toFixed(2),
        reporting_currency: "USD",
        checks,
        path,
        exception_banner: exception
            ? "One or more lines need additional attention. This claim will route to finance for review."
            : null,
    }
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
    if (path === "/holidays" && verb === "GET") {
        const matches = holidays.filter(
            (holiday) =>
                (!query?.country || holiday.country === query.country) &&
                (!query?.year ||
                    holiday.holiday_date.startsWith(String(query.year))),
        )
        return list(matches, query)
    }
    if (path === "/leave-policies" && verb === "GET")
        return list(leavePolicies, query)
    if (path === "/expense-policies" && verb === "GET") {
        const matches = expensePolicies.filter(
            (policy) =>
                (!query?.country || policy.country === query.country) &&
                (!query?.category || policy.category === query.category),
        )
        return list(matches, query)
    }
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
    if (path === "/leave-requests/preview" && verb === "POST") {
        const request = body as LeaveRequestPreviewRequest | undefined
        if (!request) throw new Error("Leave preview requires a request body.")
        return single(getLeaveRequestPreview(request, token))
    }
    if (path === "/leave-requests" && verb === "GET")
        return list(leaveRequests, query)
    if (path === "/leave-requests" && verb === "POST")
        return single(leaveDetail)
    if (/^\/leave-requests\/[^/]+\/cancel$/.test(path) && verb === "POST")
        return single(leaveCancel)
    if (/^\/leave-requests\/[^/]+$/.test(path) && verb === "GET")
        return single(leaveDetail)
    if (path === "/expense-claims/preview" && verb === "POST") {
        const request = body as ExpenseClaimPreviewRequest | undefined
        if (!request)
            throw new Error("Expense preview requires a request body.")
        return single(getExpenseClaimPreview(request, token))
    }
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
