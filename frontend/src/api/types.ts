export type ISODate = string;
export type UTCDateTime = string;
export type DecimalString = string;
export type ReportingCurrency = "USD";
export type EmployeeId = `EMP-${string}`;
export type LeaveRequestId = `LVE-2026-${string}`;
export type ExpenseClaimId = `EXP-2026-${string}`;
export type ExpenseLineId = `EXPL-${ExpenseClaimId}-${string}`;
export type ApprovalStepId = `APR-${LeaveRequestId | ExpenseClaimId}-${string}`;
export type ReimbursementId = `RMB-2026-${string}`;
export type LeaveBalanceId = `LBL-${EmployeeId}-${LeavePolicyId}-2026`;
export type CostCenterId = `CC-${string}`;
export type HolidayId = `HOL-2026-${CountryCode}-${string}`;
export type ExpensePolicyId = `XPO-${string}`;
export type ApprovalRuleId = `ARL-${string}`;
export type LeaveLedgerEntryId = `LLE-2026-${string}`;
export type LeaveRequestEventId = `LRE-2026-${string}`;
export type ExpenseClaimEventId = `ECE-2026-${string}`;
export type AuditFindingId = `AFN-2026-${string}`;
export type AuditFindingEventId = `AFE-2026-${string}`;
export type DecisionAuditId = `DAU-2026-${string}`;
export type GroundTruthAnomalyId = `GTA-2026-${string}`;
export type GroundTruthDecisionId = `GTD-2026-${string}`;
export type LeavePolicyId = "LPO-001" | "LPO-002" | "LPO-003" | "LPO-004" | "LPO-005" | "LPO-006";
export type JsonObject = Record<string, unknown>;

export enum FunctionalRole {
  NONE = "NONE",
  DEPT_HEAD = "DEPT_HEAD",
  HR_PARTNER = "HR_PARTNER",
  FINANCE_CONTROLLER = "FINANCE_CONTROLLER",
  CFO = "CFO",
  COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER",
}

export enum SystemRole {
  REQUESTER = "REQUESTER",
  APPROVER = "APPROVER",
  PROCESS_OWNER = "PROCESS_OWNER",
  ANALYST = "ANALYST",
  ADMIN = "ADMIN",
}

export enum ApprovalRole {
  MANAGER = "MANAGER",
  DEPT_HEAD = "DEPT_HEAD",
  HR_PARTNER = "HR_PARTNER",
  FINANCE_CONTROLLER = "FINANCE_CONTROLLER",
  CFO = "CFO",
  COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER",
  SYSTEM = "SYSTEM",
}

export enum RequestType {
  LEAVE = "LEAVE",
  EXPENSE = "EXPENSE",
}

export enum CountryCode {
  IN = "IN",
  US = "US",
  GB = "GB",
  DE = "DE",
  SG = "SG",
}

export enum CurrencyCode {
  INR = "INR",
  USD = "USD",
  GBP = "GBP",
  EUR = "EUR",
  SGD = "SGD",
}

export enum ExpenseCategory {
  MEALS = "MEALS",
  LODGING = "LODGING",
  AIRFARE = "AIRFARE",
  GROUND_TRANSPORT = "GROUND_TRANSPORT",
  SOFTWARE = "SOFTWARE",
  OFFICE_SUPPLIES = "OFFICE_SUPPLIES",
  TRAINING = "TRAINING",
  CLIENT_ENTERTAINMENT = "CLIENT_ENTERTAINMENT",
  GIFTS = "GIFTS",
  COMMUNICATION = "COMMUNICATION",
}

export enum LeaveRequestStatus {
  DRAFT = "DRAFT",
  SUBMITTED = "SUBMITTED",
  PENDING_APPROVAL = "PENDING_APPROVAL",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
  CANCELLED = "CANCELLED",
}

export enum ExpenseClaimStatus {
  DRAFT = "DRAFT",
  SUBMITTED = "SUBMITTED",
  PENDING_APPROVAL = "PENDING_APPROVAL",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
  CANCELLED = "CANCELLED",
  REIMBURSED = "REIMBURSED",
}

export enum ReimbursementStatus {
  SCHEDULED = "SCHEDULED",
  PAID = "PAID",
}

export enum ApprovalStepStatus {
  PENDING = "PENDING",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
}

export enum LeaveLedgerEntryType {
  OPENING = "OPENING",
  ACCRUAL = "ACCRUAL",
  RESERVE = "RESERVE",
  RELEASE = "RELEASE",
  DEBIT = "DEBIT",
  ADJUSTMENT = "ADJUSTMENT",
  REVERSAL = "REVERSAL",
}

export enum LeaveLedgerEffectBucket {
  AVAILABLE = "AVAILABLE",
  RESERVED = "RESERVED",
  USED = "USED",
}

export enum AuditFindingCode {
  INVALID_DATE_RANGE = "INVALID_DATE_RANGE",
  ZERO_BUSINESS_DAYS = "ZERO_BUSINESS_DAYS",
  EMPLOYEE_NOT_ACTIVE = "EMPLOYEE_NOT_ACTIVE",
  TENURE_INELIGIBLE = "TENURE_INELIGIBLE",
  MAX_CONSECUTIVE_DAYS = "MAX_CONSECUTIVE_DAYS",
  OVERLAP = "OVERLAP",
  INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE",
  POLICY_LIMIT_BREACH = "POLICY_LIMIT_BREACH",
  MISSING_RECEIPT = "MISSING_RECEIPT",
  DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT",
  MISSING_COST_CENTER = "MISSING_COST_CENTER",
  DATE_OUTSIDE_EMPLOYMENT = "DATE_OUTSIDE_EMPLOYMENT",
  FUTURE_EXPENSE_DATE = "FUTURE_EXPENSE_DATE",
  SPLIT_CLAIM = "SPLIT_CLAIM",
  SELF_APPROVAL_PREVENTED = "SELF_APPROVAL_PREVENTED",
  UNRESOLVED_APPROVER = "UNRESOLVED_APPROVER",
  DUPLICATE_REIMBURSEMENT = "DUPLICATE_REIMBURSEMENT",
}

export enum IssueType {
  NEGATIVE_LEAVE_BALANCE = "NEGATIVE_LEAVE_BALANCE",
  OVERLAPPING_APPROVED_LEAVE = "OVERLAPPING_APPROVED_LEAVE",
  EXPENSE_OUTSIDE_EMPLOYMENT = "EXPENSE_OUTSIDE_EMPLOYMENT",
  FUTURE_EXPENSE_DATE = "FUTURE_EXPENSE_DATE",
  SPLIT_CLAIM = "SPLIT_CLAIM",
  MISSING_COST_CENTER = "MISSING_COST_CENTER",
  SELF_APPROVAL = "SELF_APPROVAL",
  DUPLICATE_REIMBURSEMENT = "DUPLICATE_REIMBURSEMENT",
  MISSING_RECEIPT = "MISSING_RECEIPT",
  DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT",
  POLICY_LIMIT_BREACH = "POLICY_LIMIT_BREACH",
  INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE",
  ZERO_BUSINESS_DAY_SPAN = "ZERO_BUSINESS_DAY_SPAN",
}

export enum Severity {
  INFO = "INFO",
  WARNING = "WARNING",
  ERROR = "ERROR",
}

export enum FindingStatus {
  OPEN = "OPEN",
  RESOLVED = "RESOLVED",
  DISMISSED = "DISMISSED",
}

export enum ReceiptFileType {
  PDF = "PDF",
  JPG = "JPG",
  JPEG = "JPEG",
  PNG = "PNG",
  HEIC = "HEIC",
}

export enum ExcludedDateReason {
  WEEKEND = "WEEKEND",
  HOLIDAY = "HOLIDAY",
}

export enum ReasonCode {
  INVALID_DATE_RANGE = "INVALID_DATE_RANGE",
  ZERO_BUSINESS_DAYS = "ZERO_BUSINESS_DAYS",
  EMPLOYEE_NOT_ACTIVE = "EMPLOYEE_NOT_ACTIVE",
  TENURE_INELIGIBLE = "TENURE_INELIGIBLE",
  MAX_CONSECUTIVE_DAYS = "MAX_CONSECUTIVE_DAYS",
  OVERLAP = "OVERLAP",
  INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE",
  LEAVE_UNPAID = "LEAVE_UNPAID",
  LEAVE_DAYS_1_3 = "LEAVE_DAYS_1_3",
  LEAVE_DAYS_4_10 = "LEAVE_DAYS_4_10",
  LEAVE_DAYS_GT_10 = "LEAVE_DAYS_GT_10",
  PARENTAL_LEAVE = "PARENTAL_LEAVE",
  EXPENSE_LT_50_AUTO = "EXPENSE_LT_50_AUTO",
  EXPENSE_LT_50_FLAGGED = "EXPENSE_LT_50_FLAGGED",
  EXPENSE_50_1000 = "EXPENSE_50_1000",
  EXPENSE_1000_5000 = "EXPENSE_1000_5000",
  EXPENSE_5000_20000 = "EXPENSE_5000_20000",
  EXPENSE_GTE_20000 = "EXPENSE_GTE_20000",
  AIRFARE_INTERNATIONAL = "AIRFARE_INTERNATIONAL",
  CLIENT_ENTERTAINMENT_GT_250 = "CLIENT_ENTERTAINMENT_GT_250",
  GIFT_GT_250 = "GIFT_GT_250",
  POLICY_LIMIT_BREACH = "POLICY_LIMIT_BREACH",
  MISSING_RECEIPT = "MISSING_RECEIPT",
  DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT",
  MISSING_COST_CENTER = "MISSING_COST_CENTER",
  DATE_OUTSIDE_EMPLOYMENT = "DATE_OUTSIDE_EMPLOYMENT",
  FUTURE_EXPENSE_DATE = "FUTURE_EXPENSE_DATE",
  SPLIT_CLAIM = "SPLIT_CLAIM",
  SELF_APPROVAL_PREVENTED = "SELF_APPROVAL_PREVENTED",
  UNRESOLVED_APPROVER = "UNRESOLVED_APPROVER",
  CEO_MANAGER_FALLBACK = "CEO_MANAGER_FALLBACK",
  DUPLICATE_REIMBURSEMENT = "DUPLICATE_REIMBURSEMENT",
}

export enum ApiErrorCode {
  SELF_APPROVAL = "SELF_APPROVAL",
  OUT_OF_ORDER = "OUT_OF_ORDER",
  ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION",
  INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE",
  VALIDATION_FAILED = "VALIDATION_FAILED",
  FORBIDDEN = "FORBIDDEN",
  NOT_FOUND = "NOT_FOUND",
  CONFLICT = "CONFLICT",
}

export enum EvaluationMissType {
  MISSED_ANOMALY = "MISSED_ANOMALY",
  FALSE_POSITIVE = "FALSE_POSITIVE",
  DECISION_MISMATCH = "DECISION_MISMATCH",
  PATH_MISMATCH = "PATH_MISMATCH",
  REIMBURSEMENT_MISMATCH = "REIMBURSEMENT_MISMATCH",
}

export type LeavePreviewCheckCode =
  | "DATE_ORDER"
  | "BUSINESS_DAYS_POSITIVE"
  | "EMPLOYEE_ACTIVE"
  | "TENURE_ELIGIBLE"
  | "MAX_CONSECUTIVE"
  | "NO_OVERLAP"
  | "BALANCE_SUFFICIENT";

export type ExpensePreviewCheckCode =
  | "DATE_WITHIN_EMPLOYMENT"
  | "NOT_FUTURE_DATED"
  | "COST_CENTER_PRESENT"
  | "NO_DUPLICATE_RECEIPT"
  | "NO_HARD_LIMIT_BREACH"
  | "RECEIPT_METADATA_VALID";

export type LeaveRequestEventType =
  | "CREATED"
  | "SUBMISSION_ATTEMPT"
  | "SUBMITTED"
  | "APPROVAL_STARTED"
  | "APPROVAL_DECIDED"
  | "CANCELLED";

export type ExpenseClaimEventType =
  | "CREATED"
  | "SUBMISSION_ATTEMPT"
  | "SUBMITTED"
  | "APPROVAL_STARTED"
  | "APPROVAL_DECIDED"
  | "CANCELLED"
  | "REIMBURSEMENT_CREATED"
  | "REIMBURSEMENT_PAID";

export interface PageQuery {
  page?: number;
  page_size?: number;
  sort?: string;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface ListEnvelope<T> {
  data: T[];
  meta: PageMeta;
}

export interface SingleEnvelope<T> {
  data: T;
}

export interface ApiError {
  type: "about:blank";
  title: string;
  status: number;
  detail: string;
  code: ApiErrorCode;
}

export interface DemoLoginRequest {
  employee_id: EmployeeId;
}

export interface AuthPersona {
  employee_id: EmployeeId;
  display_name: string;
  country: CountryCode;
  functional_role: FunctionalRole;
  system_role: SystemRole;
}

export interface DemoLoginResult {
  access_token: string;
  token_type: "Bearer";
  expires_in_seconds: number;
  persona: Pick<AuthPersona, "employee_id" | "display_name" | "functional_role" | "system_role">;
}

export interface Employee {
  employee_id: EmployeeId;
  display_name: string;
  country: CountryCode;
  home_currency: CurrencyCode;
  hire_date: ISODate;
  termination_date: ISODate | null;
  manager_id: EmployeeId | null;
  cost_center_id: CostCenterId | null;
  functional_role: FunctionalRole;
  system_role: SystemRole;
  job_level: number;
  is_ceo: boolean;
}

export interface Me extends Employee {
  permissions: string[];
}

export interface LeaveBalance {
  leave_balance_id: LeaveBalanceId;
  employee_id: EmployeeId;
  leave_policy_id: LeavePolicyId;
  balance_year: 2026;
  as_of_date: ISODate;
  opening_days: number;
  accrued_days: number;
  adjustments_days: number;
  used_days: number;
  pending_days: number;
  available_days: number;
}

export interface CostCenter {
  cost_center_id: CostCenterId;
  name: string;
  country: CountryCode;
  owner_employee_id: EmployeeId;
  owner_name: string;
  budget_year: 2026;
  budget_usd: DecimalString;
  currency: ReportingCurrency;
}

export interface Holiday {
  holiday_id: HolidayId;
  country: CountryCode;
  holiday_date: ISODate;
  holiday_name: string;
  is_illustrative: true;
}

export interface LeavePolicy {
  leave_policy_id: LeavePolicyId;
  name: "Annual" | "Sick" | "Casual" | "Parental" | "Compassionate" | "Unpaid";
  annual_entitlement_days: number | null;
  carry_forward_max_days: number;
  max_consecutive_days: number | null;
  medical_certificate_after_days: number | null;
  tenure_required_months: number;
  lump_sum_days: number | null;
  is_unpaid: boolean;
  effective_from: ISODate;
  effective_to: ISODate | null;
}

export interface ExpensePolicy {
  expense_policy_id: ExpensePolicyId;
  category: ExpenseCategory;
  country: CountryCode;
  per_line_limit_usd: DecimalString;
  receipt_threshold_usd: DecimalString;
  currency: ReportingCurrency;
  effective_from: ISODate;
  effective_to: ISODate | null;
  version: number;
}

export interface ApprovalRule {
  approval_rule_id: ApprovalRuleId;
  rule_code: string;
  request_type: RequestType;
  priority: number;
  required_role: ApprovalRole;
  condition_description: string;
  designated_employee_id: EmployeeId | null;
  effective_from: ISODate;
  effective_to: ISODate | null;
  version: number;
  is_active: boolean;
}

export interface ApprovalPathStep {
  level: number;
  approver_type: ApprovalRole;
  approver_id: EmployeeId | null;
  approver_name: string | null;
  reason: string;
  rule_ids: string[];
}

export interface PreviewCheck<Code extends string = string> {
  code: Code;
  ok: boolean;
  message: string;
  rule_id: string;
}

export interface ExcludedDate {
  date: ISODate;
  reason: ExcludedDateReason;
}

export interface LeaveRequestPreviewRequest {
  employee_id?: EmployeeId;
  leave_policy_id: LeavePolicyId;
  start_date: ISODate;
  end_date: ISODate;
  reason?: string | null;
}

export type LeaveRequestCreateRequest = LeaveRequestPreviewRequest;

export interface LeaveRequestPreview {
  employee_id: EmployeeId;
  leave_policy_id: LeavePolicyId;
  start_date: ISODate;
  end_date: ISODate;
  business_days: number;
  excluded_dates: ExcludedDate[];
  balance_before: number | null;
  balance_after: number | null;
  checks: PreviewCheck<LeavePreviewCheckCode>[];
  valid: boolean;
  blocking_reason: ReasonCode | null;
  path: ApprovalPathStep[];
}

export interface ApprovalStepRecord {
  approval_step_id: ApprovalStepId;
  request_type: RequestType;
  request_id: LeaveRequestId | ExpenseClaimId;
  step_number: number;
  required_role: ApprovalRole;
  approver_employee_id: EmployeeId | null;
  approver_name: string | null;
  status: ApprovalStepStatus;
  assigned_at: UTCDateTime;
  due_date: ISODate;
  decided_at: UTCDateTime | null;
  reason_code: ReasonCode | null;
}

export interface LeaveRequestEvent {
  event_id: LeaveRequestEventId;
  sequence_number: number;
  event_type: LeaveRequestEventType;
  from_status: LeaveRequestStatus | null;
  to_status: LeaveRequestStatus | null;
  occurred_at: UTCDateTime;
  actor_employee_id: EmployeeId | null;
  reason_code: ReasonCode | null;
}

export interface LeaveRequestBase {
  leave_request_id: LeaveRequestId;
  employee_id: EmployeeId;
  employee_name: string;
  leave_policy_id: LeavePolicyId;
  policy_name: string;
  start_date: ISODate;
  end_date: ISODate;
  business_days: number;
  status: LeaveRequestStatus;
  submitted_at: UTCDateTime | null;
  medical_certificate_required: boolean;
  risk_score: number;
  reason: string | null;
}

export interface LeaveRequestSummary extends LeaveRequestBase {
  approval_progress: {
    approved: number;
    required: number;
  };
}

export interface LeaveRequestDetail extends LeaveRequestBase {
  approval_steps: ApprovalStepRecord[];
  events: LeaveRequestEvent[];
  ledger_entry_ids: LeaveLedgerEntryId[];
  decision_audit_ids: DecisionAuditId[];
}

export interface CancelLeaveRequestRequest {
  reason: string;
}

export interface LeaveRequestCancelResult {
  leave_request_id: LeaveRequestId;
  status: LeaveRequestStatus.CANCELLED;
  event_id: LeaveRequestEventId;
  released_ledger_entry_ids: LeaveLedgerEntryId[];
  decision_audit_id: DecisionAuditId;
  cancelled_at: UTCDateTime;
}

export interface ExpenseLineInput {
  line_number: number;
  category: ExpenseCategory;
  description?: string | null;
  amount: DecimalString;
  currency: CurrencyCode;
  receipt_present: boolean;
  receipt_id: string | null;
  receipt_hash: string | null;
  file_type: ReceiptFileType | null;
  size_kb: number | null;
}

export interface ExpenseClaimPreviewRequest {
  employee_id?: EmployeeId;
  merchant_name: string;
  merchant_country: CountryCode;
  expense_date: ISODate;
  cost_center_id: CostCenterId | null;
  lines: ExpenseLineInput[];
}

export type ExpenseClaimCreateRequest = ExpenseClaimPreviewRequest;

export interface ExpensePreviewFlag {
  code: AuditFindingCode;
  message: string;
  pct_over: number | null;
}

export interface ExpensePreviewLine {
  line_id: ExpenseLineId | null;
  line_number: number;
  amount: DecimalString;
  currency: CurrencyCode;
  amount_usd: DecimalString;
  fx_rate: DecimalString;
  reporting_currency: ReportingCurrency;
  flags: ExpensePreviewFlag[];
  limit_usd: DecimalString;
}

export interface ExpenseClaimPreview {
  employee_id: EmployeeId;
  merchant_name: string;
  merchant_country: CountryCode;
  expense_date: ISODate;
  cost_center_id: CostCenterId | null;
  lines: ExpensePreviewLine[];
  total_usd: DecimalString;
  reporting_currency: ReportingCurrency;
  checks: PreviewCheck<ExpensePreviewCheckCode>[];
  path: ApprovalPathStep[];
  exception_banner: string | null;
}

export interface ExpenseLine {
  expense_line_id: ExpenseLineId;
  expense_claim_id: ExpenseClaimId;
  line_number: number;
  category: ExpenseCategory;
  expense_policy_id: ExpensePolicyId;
  description: string | null;
  amount: DecimalString;
  currency: CurrencyCode;
  fx_rate_to_usd: DecimalString;
  amount_usd: DecimalString;
  receipt_present: boolean;
  receipt_id: string | null;
  receipt_hash: string | null;
  file_type: ReceiptFileType | null;
  size_kb: number | null;
}

export interface ExpenseClaimEvent {
  event_id: ExpenseClaimEventId;
  sequence_number: number;
  event_type: ExpenseClaimEventType;
  from_status: ExpenseClaimStatus | null;
  to_status: ExpenseClaimStatus | null;
  occurred_at: UTCDateTime;
  actor_employee_id: EmployeeId | null;
  reason_code: ReasonCode | null;
  event_payload: JsonObject;
}

export interface ExpenseClaimBase {
  expense_claim_id: ExpenseClaimId;
  employee_id: EmployeeId;
  employee_name: string;
  merchant_name: string;
  merchant_country: CountryCode;
  expense_date: ISODate;
  cost_center_id: CostCenterId | null;
  total_usd: DecimalString;
  reporting_currency: ReportingCurrency;
  status: ExpenseClaimStatus;
  submitted_at: UTCDateTime | null;
  risk_score: number;
}

export interface ExpenseClaimSummary extends ExpenseClaimBase {
  line_count: number;
  approval_progress: {
    approved: number;
    required: number;
  };
}

export interface ExpenseClaimDetail extends ExpenseClaimBase {
  lines: ExpenseLine[];
  approval_steps: ApprovalStepRecord[];
  events: ExpenseClaimEvent[];
  finding_codes: AuditFindingCode[];
  decision_audit_ids: DecisionAuditId[];
  reimbursement_ids: ReimbursementId[];
}

export interface ApprovalInboxItem extends ApprovalStepRecord {
  employee_id: EmployeeId;
  employee_name: string;
  amount_usd: DecimalString;
  currency: ReportingCurrency;
}

export interface ApprovalApprovedRequest {
  decision: "APPROVED";
  reason?: string | null;
  reason_code?: ReasonCode | null;
}

export interface ApprovalRejectedRequest {
  decision: "REJECTED";
  reason: string;
  reason_code?: ReasonCode | null;
}

export type ApprovalDecisionRequest = ApprovalApprovedRequest | ApprovalRejectedRequest;
export type ApprovalStepDecisionRequest = ApprovalDecisionRequest;

export interface ApprovalDecisionResult {
  approval_step: ApprovalStepRecord;
  request_status: LeaveRequestStatus | ExpenseClaimStatus;
  next_step: ApprovalStepRecord | null;
  event_id: ExpenseClaimEventId | LeaveRequestEventId;
  decision_audit_id: DecisionAuditId;
}

export interface Reimbursement {
  reimbursement_id: ReimbursementId;
  expense_claim_id: ExpenseClaimId;
  employee_id: EmployeeId;
  amount_home_currency: DecimalString;
  home_currency: CurrencyCode;
  amount_usd: DecimalString;
  reporting_currency: ReportingCurrency;
  payment_date: ISODate;
  status: ReimbursementStatus;
  created_at: UTCDateTime;
  paid_at: UTCDateTime | null;
  payment_reference: string | null;
}

export interface AuditRunRequest {
  scope?: "ALL" | "LEAVE" | "EXPENSE";
  as_of_date?: ISODate;
}

export interface AuditRunResult {
  scope: "ALL" | "LEAVE" | "EXPENSE";
  as_of_date: ISODate;
  status: "COMPLETED";
  scanned_requests: number;
  findings_created: number;
  findings_by_code: Partial<Record<AuditFindingCode, number>>;
  finding_ids: AuditFindingId[];
  decision_audit_ids: DecisionAuditId[];
}

export interface AuditFinding {
  audit_finding_id: AuditFindingId;
  finding_code: AuditFindingCode;
  severity: Severity;
  status: FindingStatus;
  leave_request_id: LeaveRequestId | null;
  expense_claim_id: ExpenseClaimId | null;
  expense_line_id: ExpenseLineId | null;
  approval_step_id: ApprovalStepId | null;
  reimbursement_id: ReimbursementId | null;
  details: JsonObject;
  detected_at: UTCDateTime;
}

export interface AuditFindingEvent {
  finding_event_id: AuditFindingEventId;
  sequence_number: number;
  from_status: FindingStatus.OPEN;
  to_status: FindingStatus.RESOLVED | FindingStatus.DISMISSED;
  occurred_at: UTCDateTime;
  actor_employee_id: EmployeeId | null;
  reason_code: ReasonCode;
}

export interface AuditFindingDetail extends AuditFinding {
  events: AuditFindingEvent[];
}

export interface AccuracyMetric {
  correct: number;
  total: number;
  rate: number;
}

export interface AnomalyPrecisionMetric {
  true_positive: number;
  false_positive: number;
  rate: number;
}

export interface AnomalyRecallMetric {
  true_positive: number;
  false_negative: number;
  rate: number;
}

export interface EvaluationSummary {
  as_of_date: ISODate;
  evaluated_decisions: number;
  decision_accuracy: AccuracyMetric;
  approval_path_accuracy: AccuracyMetric;
  anomaly_precision: AnomalyPrecisionMetric;
  anomaly_recall: AnomalyRecallMetric;
  reimbursement_eligibility_accuracy: AccuracyMetric;
  validation_pass_counts: {
    passed: number;
    failed: number;
    total: number;
  };
}

export type EvaluationTargetType =
  | "LEAVE_REQUEST"
  | "LEAVE_BALANCE"
  | "EXPENSE_CLAIM"
  | "EXPENSE_LINE"
  | "APPROVAL_STEP"
  | "REIMBURSEMENT";

export interface EvaluationMiss {
  ground_truth_id: GroundTruthAnomalyId | GroundTruthDecisionId;
  target_type: EvaluationTargetType;
  target_id: LeaveRequestId | LeaveBalanceId | ExpenseClaimId | ExpenseLineId | ApprovalStepId | ReimbursementId;
  expense_claim_id: ExpenseClaimId | null;
  issue_type: IssueType;
  expected_finding_code: AuditFindingCode | null;
  actual_finding_codes: AuditFindingCode[];
  miss_type: EvaluationMissType;
  expected_status: LeaveRequestStatus | ExpenseClaimStatus | ReimbursementStatus | null;
  actual_status: LeaveRequestStatus | ExpenseClaimStatus | ReimbursementStatus | null;
  expected_approval_path: ApprovalPathStep[];
  actual_approval_path: ApprovalPathStep[];
}

export interface StatusVolumes {
  DRAFT: number;
  SUBMITTED: number;
  PENDING_APPROVAL: number;
  APPROVED: number;
  REJECTED: number;
  CANCELLED: number;
}

export interface ExpenseStatusVolumes extends StatusVolumes {
  REIMBURSED: number;
}

export interface MetricsOverview {
  as_of_date: ISODate;
  reporting_currency: ReportingCurrency;
  volumes_by_status: {
    leave_requests: StatusVolumes;
    expense_claims: ExpenseStatusVolumes;
    approval_steps: Record<ApprovalStepStatus, number>;
    reimbursements: Record<ReimbursementStatus, number>;
  };
  auto_approval_rate: number;
  rejection_reasons: Array<{
    code: ReasonCode;
    count: number;
    share_pct: number;
  }>;
  cycle_time_by_level: Array<{
    level: number;
    avg_hours: number;
    p90_hours: number;
  }>;
  sla_breach_rate: number;
  multi_level_share: number;
  spend_by_cost_center: Array<{
    cost_center_id: CostCenterId;
    name: string;
    spent_usd: DecimalString;
    budget_usd: DecimalString;
    utilization_pct: number;
    currency: ReportingCurrency;
  }>;
  spend_by_category: Array<{
    category: ExpenseCategory;
    spent_usd: DecimalString;
    claim_count: number;
    currency: ReportingCurrency;
  }>;
  spend_by_country: Array<{
    country: CountryCode;
    spent_usd: DecimalString;
    claim_count: number;
    currency: ReportingCurrency;
  }>;
  leave_utilization: Array<{
    leave_policy_id: LeavePolicyId;
    name: LeavePolicy["name"];
    opening_days: number;
    accrued_days: number;
    used_days: number;
    pending_days: number;
    available_days: number;
    utilization_pct: number;
  }>;
  reimbursements: {
    paid_usd: DecimalString;
    scheduled_usd: DecimalString;
    currency: ReportingCurrency;
    paid_count: number;
    scheduled_count: number;
  };
  anomalies_flagged: number;
  recent_activity: Array<{
    event_id: LeaveRequestEventId | ExpenseClaimEventId;
    request_type: RequestType;
    request_id: LeaveRequestId | ExpenseClaimId;
    event_type: LeaveRequestEventType | ExpenseClaimEventType;
    from_status: LeaveRequestStatus | ExpenseClaimStatus | null;
    to_status: LeaveRequestStatus | ExpenseClaimStatus | null;
    occurred_at: UTCDateTime;
    employee_id: EmployeeId;
    employee_name: string;
    summary: string;
  }>;
}

export interface DatasetManifest {
  generator_name: string;
  generator_version: string;
  seed: 20261022;
  as_of_date: "2026-10-22";
  reporting_currency: ReportingCurrency;
  row_counts: Record<string, number>;
  files: Array<{
    path: string;
    format: "csv" | "json" | "sql";
    row_count: number;
    sha256: string;
    contains_ground_truth: boolean;
  }>;
  reference_fixtures: {
    countries: CountryCode[];
    holiday_count_per_country: number;
    expense_policy_count: number;
  };
  validation: {
    status: "PASSED" | "FAILED";
    checks_passed: number;
    checks_failed: number;
  };
}

export type GetAuthPersonasQuery = PageQuery;

export interface EmployeePathParams {
  id: EmployeeId;
}

export interface EmployeeLeaveBalancesPathParams {
  id: EmployeeId;
}

export interface LeaveRequestPathParams {
  id: LeaveRequestId;
}

export interface CancelLeaveRequestPathParams {
  id: LeaveRequestId;
}

export interface ExpenseClaimPathParams {
  id: ExpenseClaimId;
}

export interface ApprovalStepDecisionPathParams {
  id: ApprovalStepId;
}

export interface ReimbursementPathParams {
  id: ReimbursementId;
}

export interface AuditFindingPathParams {
  id: AuditFindingId;
}
export interface GetEmployeesQuery extends PageQuery {
  country?: CountryCode;
  functional_role?: FunctionalRole;
  system_role?: SystemRole;
  active?: boolean;
  q?: string;
}
export interface GetEmployeeLeaveBalancesQuery extends PageQuery {
  as_of_date?: ISODate;
}
export interface GetCostCentersQuery extends PageQuery {
  country?: CountryCode;
  employee_id?: EmployeeId;
}
export interface GetHolidaysQuery extends PageQuery {
  country: CountryCode;
  year?: 2026;
}
export interface GetLeavePoliciesQuery extends PageQuery {
  effective_on?: ISODate;
}
export interface GetExpensePoliciesQuery extends PageQuery {
  country?: CountryCode;
  category?: ExpenseCategory;
  effective_on?: ISODate;
}
export interface GetApprovalRulesQuery extends PageQuery {
  request_type?: RequestType;
  required_role?: ApprovalRole;
  active?: boolean;
  effective_on?: ISODate;
  category?: ExpenseCategory;
}
export interface GetLeaveRequestsQuery extends PageQuery {
  employee_id?: EmployeeId;
  status?: LeaveRequestStatus;
  leave_policy_id?: LeavePolicyId;
  from?: ISODate;
  to?: ISODate;
}
export interface GetExpenseClaimsQuery extends PageQuery {
  employee_id?: EmployeeId;
  status?: ExpenseClaimStatus;
  cost_center_id?: CostCenterId;
  merchant_country?: CountryCode;
  from?: ISODate;
  to?: ISODate;
}
export interface GetApprovalsInboxQuery extends PageQuery {
  status?: ApprovalStepStatus;
  request_type?: RequestType;
  due_before?: ISODate;
  employee_id?: EmployeeId;
}
export interface GetReimbursementsQuery extends PageQuery {
  employee_id?: EmployeeId;
  expense_claim_id?: ExpenseClaimId;
  status?: ReimbursementStatus;
  from?: ISODate;
  to?: ISODate;
}
export interface GetAuditFindingsQuery extends PageQuery {
  finding_code?: AuditFindingCode;
  severity?: Severity;
  status?: FindingStatus;
  request_type?: RequestType;
  request_id?: LeaveRequestId | ExpenseClaimId;
  from?: ISODate;
  to?: ISODate;
}
export interface GetEvaluationMissesQuery extends PageQuery {
  issue_type?: IssueType;
  miss_type?: EvaluationMissType;
  target_type?: EvaluationTargetType;
}
export interface GetMetricsOverviewQuery {
  as_of_date?: "2026-10-22";
}

export interface IdempotencyKeyHeader {
  "Idempotency-Key"?: string;
}

export type GetAuthPersonasResponse = ListEnvelope<AuthPersona>;
export type PostAuthDemoLoginResponse = SingleEnvelope<DemoLoginResult>;
export type GetMeResponse = SingleEnvelope<Me>;
export type GetEmployeesResponse = ListEnvelope<Employee>;
export type GetEmployeeResponse = SingleEnvelope<Employee>;
export type GetEmployeeLeaveBalancesResponse = ListEnvelope<LeaveBalance>;
export type GetCostCentersResponse = ListEnvelope<CostCenter>;
export type GetHolidaysResponse = ListEnvelope<Holiday>;
export type GetLeavePoliciesResponse = ListEnvelope<LeavePolicy>;
export type GetExpensePoliciesResponse = ListEnvelope<ExpensePolicy>;
export type GetApprovalRulesResponse = ListEnvelope<ApprovalRule>;
export type PostLeaveRequestPreviewResponse = SingleEnvelope<LeaveRequestPreview>;
export type PostLeaveRequestResponse = SingleEnvelope<LeaveRequestDetail>;
export type GetLeaveRequestsResponse = ListEnvelope<LeaveRequestSummary>;
export type GetLeaveRequestResponse = SingleEnvelope<LeaveRequestDetail>;
export type PostLeaveRequestCancelResponse = SingleEnvelope<LeaveRequestCancelResult>;
export type PostExpenseClaimPreviewResponse = SingleEnvelope<ExpenseClaimPreview>;
export type PostExpenseClaimResponse = SingleEnvelope<ExpenseClaimDetail>;
export type GetExpenseClaimsResponse = ListEnvelope<ExpenseClaimSummary>;
export type GetExpenseClaimResponse = SingleEnvelope<ExpenseClaimDetail>;
export type GetApprovalsInboxResponse = ListEnvelope<ApprovalInboxItem>;
export type PostApprovalDecisionResponse = SingleEnvelope<ApprovalDecisionResult>;
export type GetReimbursementsResponse = ListEnvelope<Reimbursement>;
export type GetReimbursementResponse = SingleEnvelope<Reimbursement>;
export type PostAuditRunResponse = SingleEnvelope<AuditRunResult>;
export type GetAuditFindingsResponse = ListEnvelope<AuditFinding>;
export type GetAuditFindingResponse = SingleEnvelope<AuditFindingDetail>;
export type GetEvaluationSummaryResponse = SingleEnvelope<EvaluationSummary>;
export type GetEvaluationMissesResponse = ListEnvelope<EvaluationMiss>;
export type GetMetricsOverviewResponse = SingleEnvelope<MetricsOverview>;
export type GetDatasetManifestResponse = SingleEnvelope<DatasetManifest>;
