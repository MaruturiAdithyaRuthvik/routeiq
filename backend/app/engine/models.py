"""Immutable value objects shared by engine rules (G1-G5, L1-L7, E1-E10, AU1-AU3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class CountryCode(StrEnum):
    IN = "IN"
    US = "US"
    GB = "GB"
    DE = "DE"
    SG = "SG"


class CurrencyCode(StrEnum):
    INR = "INR"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    SGD = "SGD"


class FunctionalRole(StrEnum):
    NONE = "NONE"
    DEPT_HEAD = "DEPT_HEAD"
    HR_PARTNER = "HR_PARTNER"
    FINANCE_CONTROLLER = "FINANCE_CONTROLLER"
    CFO = "CFO"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"


class SystemRole(StrEnum):
    REQUESTER = "REQUESTER"
    APPROVER = "APPROVER"
    PROCESS_OWNER = "PROCESS_OWNER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class ApprovalRole(StrEnum):
    MANAGER = "MANAGER"
    DEPT_HEAD = "DEPT_HEAD"
    HR_PARTNER = "HR_PARTNER"
    FINANCE_CONTROLLER = "FINANCE_CONTROLLER"
    CFO = "CFO"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    SYSTEM = "SYSTEM"


class RequestType(StrEnum):
    LEAVE = "LEAVE"
    EXPENSE = "EXPENSE"


class LeaveStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ExpenseStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    REIMBURSED = "REIMBURSED"


class ReimbursementStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    PAID = "PAID"


class ApprovalStepStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LeaveLedgerEntryType(StrEnum):
    OPENING = "OPENING"
    ACCRUAL = "ACCRUAL"
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"
    DEBIT = "DEBIT"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class LeaveEffectBucket(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    USED = "USED"


class ExpenseCategory(StrEnum):
    MEALS = "MEALS"
    LODGING = "LODGING"
    AIRFARE = "AIRFARE"
    GROUND_TRANSPORT = "GROUND_TRANSPORT"
    SOFTWARE = "SOFTWARE"
    OFFICE_SUPPLIES = "OFFICE_SUPPLIES"
    TRAINING = "TRAINING"
    CLIENT_ENTERTAINMENT = "CLIENT_ENTERTAINMENT"
    GIFTS = "GIFTS"
    COMMUNICATION = "COMMUNICATION"


class ReceiptFileType(StrEnum):
    PDF = "PDF"
    JPG = "JPG"
    JPEG = "JPEG"
    PNG = "PNG"
    HEIC = "HEIC"


class FindingCode(StrEnum):
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    ZERO_BUSINESS_DAYS = "ZERO_BUSINESS_DAYS"
    EMPLOYEE_NOT_ACTIVE = "EMPLOYEE_NOT_ACTIVE"
    TENURE_INELIGIBLE = "TENURE_INELIGIBLE"
    MAX_CONSECUTIVE_DAYS = "MAX_CONSECUTIVE_DAYS"
    OVERLAP = "OVERLAP"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    POLICY_LIMIT_BREACH = "POLICY_LIMIT_BREACH"
    MISSING_RECEIPT = "MISSING_RECEIPT"
    DUPLICATE_RECEIPT = "DUPLICATE_RECEIPT"
    MISSING_COST_CENTER = "MISSING_COST_CENTER"
    DATE_OUTSIDE_EMPLOYMENT = "DATE_OUTSIDE_EMPLOYMENT"
    FUTURE_EXPENSE_DATE = "FUTURE_EXPENSE_DATE"
    SPLIT_CLAIM = "SPLIT_CLAIM"
    SELF_APPROVAL_PREVENTED = "SELF_APPROVAL_PREVENTED"
    UNRESOLVED_APPROVER = "UNRESOLVED_APPROVER"
    DUPLICATE_REIMBURSEMENT = "DUPLICATE_REIMBURSEMENT"


class AuditFindingStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


@dataclass(frozen=True, slots=True)
class Employee:
    employee_id: str
    country: CountryCode
    hire_date: date
    display_name: str = ""
    termination_date: date | None = None
    manager_id: str | None = None
    functional_role: FunctionalRole = FunctionalRole.NONE
    system_role: SystemRole = SystemRole.REQUESTER
    job_level: int = 1
    is_ceo: bool = False
    home_currency: CurrencyCode | None = None


@dataclass(frozen=True, slots=True)
class LeavePolicy:
    leave_policy_id: str
    name: str
    annual_entitlement_days: Decimal | None
    carry_forward_max_days: Decimal
    max_consecutive_days: int | None
    medical_certificate_after_days: int | None
    tenure_required_months: int
    lump_sum_days: Decimal | None
    is_unpaid: bool = False


@dataclass(frozen=True, slots=True)
class LeaveLedgerEntry:
    leave_ledger_entry_id: str
    employee_id: str
    leave_policy_id: str
    entry_type: LeaveLedgerEntryType
    effect_bucket: LeaveEffectBucket
    delta_days: Decimal
    entry_date: date
    leave_request_id: str | None = None
    prior_year_closing_days: Decimal | None = None
    reversal_of_entry_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExistingLeaveRequest:
    employee_id: str
    start_date: date
    end_date: date
    status: LeaveStatus


@dataclass(frozen=True, slots=True)
class ExpensePolicy:
    expense_policy_id: str
    category: ExpenseCategory
    country: CountryCode
    per_line_limit_usd: Decimal
    receipt_threshold_usd: Decimal
    effective_from: date
    effective_to: date | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ExpenseLine:
    line_number: int
    category: ExpenseCategory
    amount: Decimal
    currency: CurrencyCode
    receipt_present: bool
    receipt_id: str | None = None
    receipt_hash: str | None = None
    file_type: ReceiptFileType | None = None
    size_kb: Decimal | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ExpenseClaim:
    expense_claim_id: str
    employee: Employee
    merchant_name: str
    merchant_country: CountryCode
    expense_date: date
    cost_center_id: str | None
    lines: tuple[ExpenseLine, ...]
    status: ExpenseStatus = ExpenseStatus.DRAFT


@dataclass(frozen=True, slots=True)
class CostCenter:
    cost_center_id: str
    owner_employee_id: str


@dataclass(frozen=True, slots=True)
class EmployeeCostCenterAssignment:
    employee_id: str
    cost_center_id: str
    allocation_pct: Decimal
    effective_from: date
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class DesignatedApprover:
    approval_rule_id: str
    role: ApprovalRole
    employee_id: str
    priority: int
    effective_from: date
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class OrganizationSnapshot:
    employees: tuple[Employee, ...]
    cost_centers: tuple[CostCenter, ...] = ()
    cost_center_assignments: tuple[EmployeeCostCenterAssignment, ...] = ()
    designated_approvers: tuple[DesignatedApprover, ...] = ()
    chro_employee_id: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalPathStep:
    level: int
    approver_type: ApprovalRole
    reason: str
    rule_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    approver_id: str | None = None
    approver_name: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalStep:
    approver_type: ApprovalRole
    status: ApprovalStepStatus


@dataclass(frozen=True, slots=True)
class OpenFinding:
    finding_code: FindingCode
    status: AuditFindingStatus


@dataclass(frozen=True, slots=True)
class ReimbursementEligibilityInput:
    expense_claim_id: str
    employee: Employee
    expense_total_usd: Decimal
    claim_status: ExpenseStatus
    approval_steps: tuple[ApprovalStep, ...]
    findings: tuple[OpenFinding, ...]
    cost_center_id: str | None
    existing_reimbursement_ids: tuple[str, ...]
    final_approval_date: date
