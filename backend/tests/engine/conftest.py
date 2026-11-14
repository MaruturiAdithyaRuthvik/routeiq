"""Reusable fixed-date and synthetic policy fixtures for engine tests."""

from datetime import date
from decimal import Decimal

import pytest

from app.engine.models import (
    CountryCode,
    CurrencyCode,
    Employee,
    ExpenseCategory,
    ExpensePolicy,
    FunctionalRole,
    LeavePolicy,
    SystemRole,
)


@pytest.fixture
def employee() -> Employee:
    return Employee(
        employee_id="EMP-000001",
        display_name="Avery Chen",
        country=CountryCode.US,
        hire_date=date(2020, 4, 15),
        manager_id="EMP-000002",
        home_currency=CurrencyCode.USD,
    )


@pytest.fixture
def annual_policy() -> LeavePolicy:
    return LeavePolicy(
        leave_policy_id="LPO-001",
        name="Annual",
        annual_entitlement_days=Decimal("24"),
        carry_forward_max_days=Decimal("10"),
        max_consecutive_days=20,
        medical_certificate_after_days=None,
        tenure_required_months=0,
        lump_sum_days=None,
    )


@pytest.fixture
def expense_policy() -> ExpensePolicy:
    return ExpensePolicy(
        expense_policy_id="XPO-0001",
        category=ExpenseCategory.MEALS,
        country=CountryCode.US,
        per_line_limit_usd=Decimal("100.00"),
        receipt_threshold_usd=Decimal("25.00"),
        effective_from=date(2026, 1, 1),
    )


@pytest.fixture
def manager() -> Employee:
    return Employee(
        employee_id="EMP-000002",
        display_name="Jordan Patel",
        country=CountryCode.US,
        hire_date=date(2018, 1, 1),
        functional_role=FunctionalRole.DEPT_HEAD,
        system_role=SystemRole.APPROVER,
        job_level=8,
    )
