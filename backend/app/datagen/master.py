"""Synthetic reference data and organizational hierarchy stages."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from app.engine.calendar import HOLIDAYS_BY_COUNTRY
from app.engine.ids import IdKind, format_id
from app.engine.leave import LEAVE_POLICIES
from app.engine.models import (
    ApprovalRole,
    CostCenter,
    CountryCode,
    CurrencyCode,
    DesignatedApprover,
    Employee,
    EmployeeCostCenterAssignment,
    ExpenseCategory,
    ExpensePolicy,
    FunctionalRole,
    OrganizationSnapshot,
    SystemRole,
)
from app.engine.money import round_half_up

from .context import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    CATEGORY_LIMITS,
    COST_CENTER_DEPARTMENTS,
    COUNTRIES,
    COUNTRY_COST_FACTORS,
    COUNTRY_CURRENCIES,
    COUNTRY_SHARES,
    FIRST_NAMES,
    LAST_NAMES,
    MERCHANT_BY_COUNTRY_CATEGORY,
    GenerationContext,
    Row,
)

_EFFECTIVE_FROM = date(2026, 1, 1)


def _id(kind: IdKind, sequence: int) -> str:
    result = format_id(kind, sequence)
    if result.value is None:
        raise ValueError(result.messages[0])
    return result.value


def _country_counts(total: int) -> dict[str, int]:
    exact = {country: Decimal(total) * COUNTRY_SHARES[country] for country in COUNTRIES}
    counts = {country: int(value) for country, value in exact.items()}
    remainder = total - sum(counts.values())
    order = sorted(
        COUNTRIES,
        key=lambda country: (-(exact[country] - counts[country]), COUNTRIES.index(country)),
    )
    for country in order[:remainder]:
        counts[country] += 1
    return counts


def _center_plan() -> list[tuple[str, str, str]]:
    country_codes = (
        ("IN", 7),
        ("US", 5),
        ("GB", 3),
        ("DE", 3),
        ("SG", 2),
    )
    center_rows: list[tuple[str, str, str]] = []
    department_index = 0
    sequence = 1
    for country, count in country_codes:
        for _ in range(count):
            department = COST_CENTER_DEPARTMENTS[department_index]
            center_rows.append((_id(IdKind.COST_CENTER, sequence), country, department))
            sequence += 1
            department_index += 1
    return center_rows


def generate_master_data(context: GenerationContext) -> None:
    """Create all rule fixtures, employees, centers, and effective-dated assignments."""

    center_plan = _center_plan()
    owner_centers_by_country: dict[str, list[str]] = {country: [] for country in COUNTRIES}
    for center_id, country, _department in center_plan:
        owner_centers_by_country[country].append(center_id)

    employee_specs: list[Row] = []
    owner_employee_by_center: dict[str, str] = {}
    employee_id_by_role: dict[tuple[str, str], str] = {}
    employee_sequence = 1
    for country in COUNTRIES:
        if country == "IN":
            employee_specs.append(_employee_spec(employee_sequence, country, "CEO", None))
            employee_sequence += 1
        employee_specs.append(_employee_spec(employee_sequence, country, "VP", None))
        employee_sequence += 1
        for center_id in owner_centers_by_country[country]:
            employee_specs.append(_employee_spec(employee_sequence, country, "OWNER", center_id))
            owner_employee_by_center[center_id] = f"EMP-{employee_sequence:06d}"
            employee_sequence += 1
        employee_specs.append(_employee_spec(employee_sequence, country, "HR", None))
        employee_id_by_role[(country, "HR")] = f"EMP-{employee_sequence:06d}"
        employee_sequence += 1
        if country == "US":
            for role in ("CFO", "FINANCE_CONTROLLER", "COMPLIANCE_OFFICER"):
                employee_specs.append(_employee_spec(employee_sequence, country, role, None))
                employee_id_by_role[(country, role)] = f"EMP-{employee_sequence:06d}"
                employee_sequence += 1

    country_counts = _country_counts(context.preset.employees)
    for country in COUNTRIES:
        current_count = sum(spec["country"] == country for spec in employee_specs)
        for _ in range(country_counts[country] - current_count):
            employee_specs.append(_employee_spec(employee_sequence, country, "EXTRA", None))
            employee_sequence += 1
    employee_specs.sort(key=lambda spec: spec["employee_id"])

    extras = [spec for spec in employee_specs if spec["kind"] == "EXTRA"]
    for index, spec in enumerate(extras):
        special_roles = ("PROCESS_OWNER", "ANALYST", "ADMIN")
        spec["system_role"] = special_roles[index] if index < len(special_roles) else "REQUESTER"

    rng = context.rng
    midyear_hires = max(3, context.preset.employees // 20)
    midyear_specs = extras[:midyear_hires]
    midyear_ids = {spec["employee_id"] for spec in midyear_specs}
    termination_count = max(1, round(context.preset.employees * 0.04))
    termination_specs = extras[midyear_hires : midyear_hires + termination_count]
    termination_ids = {spec["employee_id"] for spec in termination_specs}
    for spec in employee_specs:
        if midyear_specs and spec["employee_id"] == midyear_specs[0]["employee_id"]:
            hire_date = date(2026, 6, 16)
        else:
            hire_date = _hire_date(rng, spec["employee_id"] in midyear_ids, spec["kind"] == "EXTRA")
        termination_date = None
        if spec["employee_id"] in termination_ids:
            earliest = max(hire_date + timedelta(days=30), date(2026, 3, 1))
            if earliest > context.as_of_date:
                earliest = context.as_of_date
            span = (context.as_of_date - earliest).days
            termination_date = earliest + timedelta(days=rng.randint(0, span))
        spec["hire_date"] = hire_date
        spec["termination_date"] = termination_date

    vp_by_country: dict[str, str] = {}
    for spec in employee_specs:
        if spec["kind"] == "VP":
            vp_by_country[spec["country"]] = spec["employee_id"]
    center_rows: list[Row] = []
    for sequence, (center_id, country, department) in enumerate(center_plan, start=1):
        owner_id = owner_employee_by_center[center_id]
        center_rows.append(
            {
                "cost_center_id": center_id,
                "name": f"{department} - {country} Unit {sequence:02d}",
                "country": country,
                "owner_employee_id": owner_id,
                "budget_year": 2026,
                "budget_usd": _budget_for_center(department, sequence),
            }
        )

    owner_ids = set(owner_employee_by_center.values())
    country_centers = {
        country: [
            center_id for center_id, center_country, _ in center_plan if center_country == country
        ]
        for country in COUNTRIES
    }
    split_count = max(1, round(context.preset.employees * 0.08))
    split_candidates = [
        spec["employee_id"] for spec in employee_specs if spec["employee_id"] not in owner_ids
    ]
    split_ids = set(rng.sample(split_candidates, min(split_count, len(split_candidates))))
    assignment_rows: list[Row] = []
    for spec in employee_specs:
        employee_id = spec["employee_id"]
        country = spec["country"]
        if spec["kind"] == "OWNER":
            primary_center = str(spec["cost_center_id"])
        else:
            primary_center = rng.choice(country_centers[country])
        selected_centers = [primary_center]
        if employee_id in split_ids:
            alternatives = [
                center for center in country_centers[country] if center != primary_center
            ]
            if alternatives:
                selected_centers.append(rng.choice(alternatives))
        effective_from = max(_EFFECTIVE_FROM, spec["hire_date"])
        effective_to = (
            spec["termination_date"] + timedelta(days=1)
            if spec["termination_date"] is not None
            else None
        )
        allocations = (
            (Decimal("60.00"), Decimal("40.00"))
            if len(selected_centers) == 2
            else (Decimal("100.00"),)
        )
        for center_id, allocation in zip(selected_centers, allocations, strict=True):
            assignment_rows.append(
                {
                    "employee_id": employee_id,
                    "cost_center_id": center_id,
                    "effective_from": effective_from,
                    "effective_to": effective_to,
                    "allocation_pct": allocation,
                }
            )
        spec["cost_center_id"] = primary_center

    for spec in employee_specs:
        kind = str(spec["kind"])
        country = str(spec["country"])
        if kind == "CEO":
            spec["manager_id"] = None
        elif kind == "VP":
            spec["manager_id"] = next(
                item["employee_id"] for item in employee_specs if item["kind"] == "CEO"
            )
        else:
            manager_center = next(
                center for center in country_centers[country] if center in owner_employee_by_center
            )
            manager_id = owner_employee_by_center[manager_center]
            if spec["employee_id"] == manager_id:
                manager_id = vp_by_country[country]
            spec["manager_id"] = manager_id

    employee_rows: list[Row] = []
    employee_models: list[Employee] = []
    for spec in employee_specs:
        country = str(spec["country"])
        employee_id = str(spec["employee_id"])
        name_index = sum(
            item["country"] == country for item in employee_specs[: employee_specs.index(spec)]
        )
        first_name = FIRST_NAMES[country][name_index % len(FIRST_NAMES[country])]
        last_name_index = (name_index // len(FIRST_NAMES[country])) % len(LAST_NAMES[country])
        name = f"{first_name} {LAST_NAMES[country][last_name_index]}"
        spec["display_name"] = name
        employee_rows.append(
            {
                "employee_id": employee_id,
                "display_name": name,
                "country": country,
                "home_currency": COUNTRY_CURRENCIES[country],
                "hire_date": spec["hire_date"],
                "termination_date": spec["termination_date"],
                "manager_id": spec["manager_id"],
                "functional_role": spec["functional_role"],
                "system_role": spec["system_role"],
                "job_level": spec["job_level"],
                "is_ceo": spec["kind"] == "CEO",
                "cost_center_id": spec["cost_center_id"],
            }
        )
        employee_models.append(
            Employee(
                employee_id=employee_id,
                display_name=name,
                country=CountryCode(country),
                home_currency=CurrencyCode(COUNTRY_CURRENCIES[country]),
                hire_date=spec["hire_date"],
                termination_date=spec["termination_date"],
                manager_id=spec["manager_id"],
                functional_role=FunctionalRole(spec["functional_role"]),
                system_role=SystemRole(spec["system_role"]),
                job_level=spec["job_level"],
                is_ceo=spec["kind"] == "CEO",
            )
        )

    leave_policy_rows = [
        {
            "leave_policy_id": policy.leave_policy_id,
            "name": policy.name,
            "annual_entitlement_days": policy.annual_entitlement_days,
            "carry_forward_max_days": policy.carry_forward_max_days,
            "max_consecutive_days": policy.max_consecutive_days,
            "medical_certificate_after_days": policy.medical_certificate_after_days,
            "tenure_required_months": policy.tenure_required_months,
            "lump_sum_days": policy.lump_sum_days,
            "is_unpaid": policy.is_unpaid,
            "effective_from": _EFFECTIVE_FROM,
            "effective_to": None,
        }
        for policy in LEAVE_POLICIES.values()
    ]
    category_rows = [
        {"category": category, "description": CATEGORY_DESCRIPTIONS[category]}
        for category in CATEGORIES
    ]
    policy_rows: list[Row] = []
    policy_models: list[ExpensePolicy] = []
    policy_id_by_category_country: dict[tuple[str, str], str] = {}
    for country in COUNTRIES:
        factor = COUNTRY_COST_FACTORS[country]
        for category in CATEGORIES:
            policy_id = f"XPO-{len(policy_rows) + 1:04d}"
            base_limit, base_threshold = CATEGORY_LIMITS[category]
            limit_result = round_half_up(base_limit * factor, 2)
            threshold_result = round_half_up(base_threshold * factor, 2)
            if limit_result.value is None or threshold_result.value is None:
                raise ValueError("expense policy fixture exceeded Decimal precision")
            model = ExpensePolicy(
                expense_policy_id=policy_id,
                category=ExpenseCategory(category),
                country=CountryCode(country),
                per_line_limit_usd=limit_result.value,
                receipt_threshold_usd=threshold_result.value,
                effective_from=_EFFECTIVE_FROM,
                version=1,
            )
            policy_rows.append(
                {
                    "expense_policy_id": policy_id,
                    "category": category,
                    "country": country,
                    "per_line_limit_usd": limit_result.value,
                    "receipt_threshold_usd": threshold_result.value,
                    "effective_from": _EFFECTIVE_FROM,
                    "effective_to": None,
                    "version": 1,
                }
            )
            policy_models.append(model)
            policy_id_by_category_country[(country, category)] = policy_id

    context.set_rows(
        "holiday",
        _holiday_rows(),
        ("holiday_id", "country", "holiday_date", "holiday_name", "is_illustrative"),
    )
    context.set_rows(
        "leave_policy",
        leave_policy_rows,
        (
            "leave_policy_id",
            "name",
            "annual_entitlement_days",
            "carry_forward_max_days",
            "max_consecutive_days",
            "medical_certificate_after_days",
            "tenure_required_months",
            "lump_sum_days",
            "is_unpaid",
            "effective_from",
            "effective_to",
        ),
    )
    context.set_rows("expense_category", category_rows, ("category", "description"))
    context.set_rows(
        "expense_policy",
        policy_rows,
        (
            "expense_policy_id",
            "category",
            "country",
            "per_line_limit_usd",
            "receipt_threshold_usd",
            "effective_from",
            "effective_to",
            "version",
        ),
    )
    context.set_rows(
        "cost_center",
        center_rows,
        ("cost_center_id", "name", "country", "owner_employee_id", "budget_year", "budget_usd"),
    )
    context.set_rows(
        "employee",
        employee_rows,
        (
            "employee_id",
            "display_name",
            "country",
            "home_currency",
            "hire_date",
            "termination_date",
            "manager_id",
            "functional_role",
            "system_role",
            "job_level",
            "is_ceo",
            "cost_center_id",
        ),
    )
    context.set_rows(
        "employee_cost_center_assignment",
        assignment_rows,
        ("employee_id", "cost_center_id", "effective_from", "effective_to", "allocation_pct"),
    )

    rule_rows, category_link_rows, designated = _approval_rules(
        employee_id_by_role, policy_id_by_category_country
    )
    context.set_rows(
        "approval_rule",
        rule_rows,
        (
            "approval_rule_id",
            "rule_code",
            "request_type",
            "priority",
            "required_role",
            "condition_description",
            "designated_employee_id",
            "effective_from",
            "effective_to",
            "version",
            "is_active",
        ),
    )
    context.set_rows(
        "approval_rule_category",
        category_link_rows,
        ("approval_rule_id", "category", "effective_from", "effective_to"),
    )

    assignment_models = tuple(
        EmployeeCostCenterAssignment(
            employee_id=row["employee_id"],
            cost_center_id=row["cost_center_id"],
            allocation_pct=row["allocation_pct"],
            effective_from=row["effective_from"],
            effective_to=row["effective_to"],
        )
        for row in assignment_rows
    )
    center_models = tuple(
        CostCenter(row["cost_center_id"], row["owner_employee_id"]) for row in center_rows
    )
    chro_id = employee_id_by_role[("IN", "HR")]
    organization = OrganizationSnapshot(
        employees=tuple(employee_models),
        cost_centers=center_models,
        cost_center_assignments=assignment_models,
        designated_approvers=tuple(designated),
        chro_employee_id=chro_id,
    )
    context.references.update(
        {
            "employees": {employee.employee_id: employee for employee in employee_models},
            "leave_policies": dict(LEAVE_POLICIES),
            "expense_policies": tuple(policy_models),
            "policy_id_by_category_country": policy_id_by_category_country,
            "organization": organization,
            "cost_centers": {row["cost_center_id"]: row for row in center_rows},
            "assignments": assignment_rows,
            "terminated_employee_ids": tuple(
                sorted(
                    spec["employee_id"]
                    for spec in employee_specs
                    if spec["termination_date"] is not None
                )
            ),
            "owner_employee_by_center": owner_employee_by_center,
            "country_centers": country_centers,
            "cost_factors": COUNTRY_COST_FACTORS.copy(),
            "merchants": MERCHANT_BY_COUNTRY_CATEGORY.copy(),
            "policy_cost_factors": COUNTRY_COST_FACTORS.copy(),
        }
    )


def _employee_spec(sequence: int, country: str, kind: str, cost_center_id: str | None) -> Row:
    roles = {
        "CEO": ("NONE", "APPROVER", 10),
        "VP": ("NONE", "APPROVER", 9),
        "OWNER": ("DEPT_HEAD", "APPROVER", 7),
        "HR": ("HR_PARTNER", "APPROVER", 5),
        "CFO": ("CFO", "APPROVER", 10),
        "FINANCE_CONTROLLER": ("FINANCE_CONTROLLER", "APPROVER", 9),
        "COMPLIANCE_OFFICER": ("COMPLIANCE_OFFICER", "APPROVER", 8),
        "EXTRA": ("NONE", "APPROVER", 3),
    }
    functional_role, system_role, level = roles[kind]
    return {
        "employee_id": f"EMP-{sequence:06d}",
        "country": country,
        "kind": kind,
        "cost_center_id": cost_center_id,
        "functional_role": functional_role,
        "system_role": system_role,
        "job_level": level,
    }


def _hire_date(rng: random.Random, midyear: bool, is_extra: bool) -> date:
    if midyear:
        start = date(2026, 6, 1)
        return start + timedelta(days=rng.randint(0, (date(2026, 8, 31) - start).days))
    years = tuple(range(2015, 2027 if is_extra else 2026))
    weights = (
        (1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 5, 10) if is_extra else (1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 5)
    )
    year = rng.choices(years, weights=weights, k=1)[0]
    start = date(year, 1, 1)
    end = min(date(year, 12, 31), date(2026, 10, 22))
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _budget_for_center(department: str, sequence: int) -> Decimal:
    base = {
        "Engineering": Decimal("1800000"),
        "Sales": Decimal("1250000"),
        "Marketing": Decimal("850000"),
        "Finance": Decimal("700000"),
        "HR": Decimal("550000"),
        "Operations": Decimal("1100000"),
        "Legal": Decimal("500000"),
        "Support": Decimal("650000"),
    }[department]
    return base + Decimal(sequence % 5) * Decimal("25000")


def _holiday_rows() -> list[Row]:
    rows: list[Row] = []
    for country in COUNTRIES:
        for sequence, holiday_date in enumerate(
            sorted(HOLIDAYS_BY_COUNTRY[CountryCode(country)]), start=1
        ):
            rows.append(
                {
                    "holiday_id": f"HOL-2026-{country}-{sequence:02d}",
                    "country": country,
                    "holiday_date": holiday_date,
                    "holiday_name": f"Illustrative holiday {sequence:02d}",
                    "is_illustrative": True,
                }
            )
    return rows


def _approval_rules(
    designated_ids: dict[tuple[str, str], str],
    _policy_ids: dict[tuple[str, str], str],
) -> tuple[list[Row], list[Row], list[DesignatedApprover]]:
    rule_specs: list[tuple[str, str, str, str, str | None, tuple[str, ...]]] = []
    leave_rules = (
        (
            "LEAVE_UNPAID_MANAGER",
            "LEAVE",
            "MANAGER",
            "Unpaid leave requires manager approval.",
            None,
        ),
        ("LEAVE_UNPAID_HR", "LEAVE", "HR_PARTNER", "Unpaid leave requires HR approval.", None),
        (
            "LEAVE_1_3_MANAGER",
            "LEAVE",
            "MANAGER",
            "Leave of 1-3 business days requires manager approval.",
            None,
        ),
        (
            "LEAVE_4_10_MANAGER",
            "LEAVE",
            "MANAGER",
            "Leave of 4-10 business days requires manager approval.",
            None,
        ),
        (
            "LEAVE_4_10_HR",
            "LEAVE",
            "HR_PARTNER",
            "Leave of 4-10 business days requires HR approval.",
            None,
        ),
        (
            "LEAVE_GT10_MANAGER",
            "LEAVE",
            "MANAGER",
            "Leave over 10 business days requires manager approval.",
            None,
        ),
        (
            "LEAVE_GT10_HR",
            "LEAVE",
            "HR_PARTNER",
            "Leave over 10 business days requires HR approval.",
            None,
        ),
        (
            "LEAVE_GT10_DEPT",
            "LEAVE",
            "DEPT_HEAD",
            "Leave over 10 business days requires department-head approval.",
            None,
        ),
        (
            "LEAVE_PARENTAL_MANAGER",
            "LEAVE",
            "MANAGER",
            "Parental leave requires manager approval.",
            None,
        ),
        ("LEAVE_PARENTAL_HR", "LEAVE", "HR_PARTNER", "Parental leave requires HR approval.", None),
        (
            "LEAVE_PARENTAL_DEPT",
            "LEAVE",
            "DEPT_HEAD",
            "Parental leave requires department-head approval.",
            None,
        ),
    )
    for code, request_type, role, condition, _ in leave_rules:
        rule_specs.append((code, request_type, role, condition, None, ()))

    expense_rules = (
        ("EXPENSE_AUTO_LT50", "SYSTEM", "Total below USD 50 and no open flags.", None),
        ("EXPENSE_FLAGGED_LT50", "MANAGER", "Total below USD 50 with one or more E3 flags.", None),
        ("EXPENSE_50_1000", "MANAGER", "Total from USD 50 to below USD 1,000.", None),
        ("EXPENSE_1000_5000_MANAGER", "MANAGER", "Total from USD 1,000 to below USD 5,000.", None),
        ("EXPENSE_1000_5000_DEPT", "DEPT_HEAD", "Total from USD 1,000 to below USD 5,000.", None),
        (
            "EXPENSE_5000_20000_MANAGER",
            "MANAGER",
            "Total from USD 5,000 to below USD 20,000.",
            None,
        ),
        ("EXPENSE_5000_20000_DEPT", "DEPT_HEAD", "Total from USD 5,000 to below USD 20,000.", None),
        (
            "EXPENSE_5000_20000_FINANCE",
            "FINANCE_CONTROLLER",
            "Total from USD 5,000 to below USD 20,000.",
            "FINANCE_CONTROLLER",
        ),
        ("EXPENSE_GTE20000_MANAGER", "MANAGER", "Total of USD 20,000 or more.", None),
        ("EXPENSE_GTE20000_DEPT", "DEPT_HEAD", "Total of USD 20,000 or more.", None),
        (
            "EXPENSE_GTE20000_FINANCE",
            "FINANCE_CONTROLLER",
            "Total of USD 20,000 or more.",
            "FINANCE_CONTROLLER",
        ),
        ("EXPENSE_GTE20000_CFO", "CFO", "Total of USD 20,000 or more.", "CFO"),
        (
            "EXPENSE_INTERNATIONAL_AIRFARE",
            "FINANCE_CONTROLLER",
            "International airfare requires exception review.",
            "FINANCE_CONTROLLER",
        ),
        (
            "EXPENSE_CLIENT_ENTERTAINMENT",
            "COMPLIANCE_OFFICER",
            "Client entertainment line exceeds USD 250.",
            "COMPLIANCE_OFFICER",
        ),
        ("EXPENSE_GIFTS", "COMPLIANCE_OFFICER", "Gift line exceeds USD 250.", "COMPLIANCE_OFFICER"),
        (
            "EXPENSE_LIMIT_EXCEPTION",
            "FINANCE_CONTROLLER",
            "Policy-limit breach not exceeding 150% requires exception review.",
            "FINANCE_CONTROLLER",
        ),
        (
            "EXPENSE_MISSING_RECEIPT",
            "FINANCE_CONTROLLER",
            "Missing receipt requires exception review.",
            "FINANCE_CONTROLLER",
        ),
    )
    for code, role, condition, designated_role in expense_rules:
        category_codes: tuple[str, ...] = ()
        if code == "EXPENSE_INTERNATIONAL_AIRFARE":
            category_codes = ("AIRFARE",)
        elif code == "EXPENSE_CLIENT_ENTERTAINMENT":
            category_codes = ("CLIENT_ENTERTAINMENT",)
        elif code == "EXPENSE_GIFTS":
            category_codes = ("GIFTS",)
        elif code in ("EXPENSE_LIMIT_EXCEPTION", "EXPENSE_MISSING_RECEIPT"):
            category_codes = CATEGORIES
        designated = (
            designated_ids[("US", designated_role)] if designated_role is not None else None
        )
        rule_specs.append((code, "EXPENSE", role, condition, designated, category_codes))

    rows: list[Row] = []
    links: list[Row] = []
    designated: list[DesignatedApprover] = []
    priorities = {"LEAVE": 0, "EXPENSE": 0}
    for sequence, (
        code,
        request_type,
        role,
        condition,
        explicit_designated,
        category_codes,
    ) in enumerate(rule_specs, start=1):
        priorities[request_type] += 1
        designated_id = explicit_designated
        if designated_id is None and role in ("FINANCE_CONTROLLER", "CFO", "COMPLIANCE_OFFICER"):
            designated_id = designated_ids[("US", role)]
        rule_id = _id(IdKind.APPROVAL_RULE, sequence)
        rows.append(
            {
                "approval_rule_id": rule_id,
                "rule_code": code,
                "request_type": request_type,
                "priority": priorities[request_type],
                "required_role": role,
                "condition_description": condition,
                "designated_employee_id": designated_id,
                "effective_from": _EFFECTIVE_FROM,
                "effective_to": None,
                "version": 1,
                "is_active": True,
            }
        )
        if designated_id is not None and role in (
            "FINANCE_CONTROLLER",
            "CFO",
            "COMPLIANCE_OFFICER",
        ):
            designated.append(
                DesignatedApprover(
                    approval_rule_id=rule_id,
                    role=ApprovalRole(role),
                    employee_id=designated_id,
                    priority=priorities[request_type],
                    effective_from=_EFFECTIVE_FROM,
                )
            )
        for category in category_codes:
            links.append(
                {
                    "approval_rule_id": rule_id,
                    "category": category,
                    "effective_from": _EFFECTIVE_FROM,
                    "effective_to": None,
                }
            )
    return rows, links, designated
