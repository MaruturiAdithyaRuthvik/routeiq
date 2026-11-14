from datetime import date
from decimal import Decimal

import pytest

from app.engine.calendar import (
    HOLIDAYS_BY_COUNTRY,
    ExcludedDateReason,
    add_business_days,
    business_days_between,
    is_business_day,
)
from app.engine.ids import IdKind, format_id, parse_id, validate_id
from app.engine.models import CountryCode, CurrencyCode
from app.engine.money import currency_for_country, round_half_up, to_home_currency, to_usd


@pytest.mark.parametrize(
    ("kind", "sequence", "expected"),
    [
        (IdKind.EMPLOYEE, 1, "EMP-000001"),
        (IdKind.LEAVE_REQUEST, 1, "LVE-2026-000001"),
        (IdKind.EXPENSE_CLAIM, 1, "EXP-2026-000001"),
        (IdKind.REIMBURSEMENT, 1, "RMB-2026-000001"),
        (IdKind.LEAVE_POLICY, 1, "LPO-001"),
        (IdKind.EXPENSE_POLICY, 1, "XPO-0001"),
        (IdKind.COST_CENTER, 1, "CC-0001"),
        (IdKind.APPROVAL_RULE, 1, "ARL-001"),
        (IdKind.LEAVE_LEDGER_ENTRY, 1, "LLE-2026-000001"),
        (IdKind.LEAVE_REQUEST_EVENT, 1, "LRE-2026-000001"),
        (IdKind.EXPENSE_CLAIM_EVENT, 1, "ECE-2026-000001"),
        (IdKind.DECISION_AUDIT, 1, "DAU-2026-000001"),
        (IdKind.AUDIT_FINDING, 1, "AFN-2026-000001"),
        (IdKind.AUDIT_FINDING_EVENT, 1, "AFE-2026-000001"),
        (IdKind.GROUND_TRUTH_ANOMALY, 1, "GTA-2026-000001"),
        (IdKind.GROUND_TRUTH_DECISION, 1, "GTD-2026-000001"),
    ],
)
def test_format_and_parse_simple_ids(kind: IdKind, sequence: int, expected: str) -> None:
    formatted = format_id(kind, sequence)
    parsed = parse_id(expected)
    assert formatted.ok and formatted.value == expected
    assert parsed.ok and parsed.value is not None and parsed.value.kind == kind
    assert validate_id(expected, kind).ok


@pytest.mark.parametrize(
    ("kind", "kwargs", "expected"),
    [
        (IdKind.EXPENSE_LINE, {"parent_id": "EXP-2026-000001"}, "EXPL-EXP-2026-000001-01"),
        (IdKind.APPROVAL_STEP, {"parent_id": "LVE-2026-000001"}, "APR-LVE-2026-000001-01"),
        (
            IdKind.APPROVAL_STEP,
            {"parent_id": "EXP-2026-000001", "sequence": 12},
            "APR-EXP-2026-000001-12",
        ),
        (
            IdKind.LEAVE_BALANCE,
            {
                "employee_id": "EMP-000001",
                "policy_id": "LPO-001",
                "sequence": 2026,
            },
            "LBL-EMP-000001-LPO-001-2026",
        ),
        (
            IdKind.HOLIDAY,
            {"country": CountryCode.SG, "sequence": 8},
            "HOL-2026-SG-08",
        ),
    ],
)
def test_format_composite_ids(kind: IdKind, kwargs: dict[str, object], expected: str) -> None:
    sequence = int(kwargs.pop("sequence", 1))
    result = format_id(kind, sequence, **kwargs)
    assert result.ok and result.value == expected
    assert parse_id(expected).ok


@pytest.mark.parametrize(
    ("value", "kind", "code"),
    [
        ("bad-id", None, "INVALID_ID_FORMAT"),
        ("EXP-2026-000001", IdKind.EMPLOYEE, "ID_KIND_MISMATCH"),
        ("EMP-1000000", IdKind.EMPLOYEE, "INVALID_ID_FORMAT"),
        ("EMP-000000", IdKind.EMPLOYEE, "INVALID_ID_SEQUENCE"),
        ("APR-LVE-2026-000001-00", IdKind.APPROVAL_STEP, "INVALID_ID_SEQUENCE"),
    ],
)
def test_invalid_ids_are_explained(value: str, kind: IdKind | None, code: str) -> None:
    result = validate_id(value, kind)
    assert not result.ok
    assert code in result.reason_codes


@pytest.mark.parametrize(
    ("kind", "sequence", "kwargs", "code"),
    [
        (IdKind.EMPLOYEE, 0, {}, "INVALID_ID_SEQUENCE"),
        (IdKind.EMPLOYEE, 1_000_000, {}, "INVALID_ID_SEQUENCE"),
        (IdKind.EXPENSE_LINE, 1, {"parent_id": "LVE-2026-000001"}, "INVALID_ID_PARENT"),
        (IdKind.EXPENSE_LINE, 100, {"parent_id": "EXP-2026-000001"}, "INVALID_ID_SEQUENCE"),
        (IdKind.LEAVE_BALANCE, 1, {}, "ID_COMPONENT_REQUIRED"),
        (
            IdKind.LEAVE_BALANCE,
            2025,
            {"employee_id": "EMP-000001", "policy_id": "LPO-001"},
            "INVALID_ID_YEAR",
        ),
        (IdKind.HOLIDAY, 9, {"country": CountryCode.US}, "INVALID_HOLIDAY_ID_COMPONENT"),
    ],
)
def test_invalid_id_components(
    kind: IdKind, sequence: int, kwargs: dict[str, object], code: str
) -> None:
    result = format_id(kind, sequence, **kwargs)
    assert not result.ok and code in result.reason_codes


@pytest.mark.parametrize(
    ("currency", "rate"),
    [
        (CurrencyCode.INR, Decimal("0.012")),
        (CurrencyCode.USD, Decimal("1.0")),
        (CurrencyCode.GBP, Decimal("1.27")),
        (CurrencyCode.EUR, Decimal("1.08")),
        (CurrencyCode.SGD, Decimal("0.74")),
    ],
)
def test_fixed_fx_rates_and_half_up(currency: CurrencyCode, rate: Decimal) -> None:
    result = to_usd(Decimal("100"), currency)
    assert result.ok and result.value == (Decimal("100") * rate).quantize(Decimal("0.01"))


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [
        ("1.005", 2, Decimal("1.01")),
        ("1.004", 2, Decimal("1.00")),
        ("-1.005", 2, Decimal("-1.01")),
        ("0.1234565", 6, Decimal("0.123457")),
    ],
)
def test_decimal_round_half_up(value: str, places: int, expected: Decimal) -> None:
    assert round_half_up(value, places).value == expected


def test_money_rejects_float_nonpositive_and_unknown_currency() -> None:
    assert not to_usd(1.0, "USD").ok
    assert not to_usd("0", "USD").ok
    assert not to_usd("0.001", "USD").ok
    assert not to_usd("1", "CAD").ok
    assert not to_usd(None, "USD").ok
    assert not round_half_up("1", 7).ok
    assert not to_home_currency("-1", "INR").ok
    assert not currency_for_country("CA").ok
    assert currency_for_country(CountryCode.DE).value == CurrencyCode.EUR


def test_synthetic_holiday_fixtures_are_eight_per_country() -> None:
    assert {country: len(days) for country, days in HOLIDAYS_BY_COUNTRY.items()} == {
        country: 8 for country in CountryCode
    }


@pytest.mark.parametrize(
    ("start", "end", "count", "excluded_reason"),
    [
        (date(2026, 10, 24), date(2026, 10, 25), 0, ExcludedDateReason.WEEKEND),
        (date(2026, 11, 6), date(2026, 11, 10), 2, ExcludedDateReason.WEEKEND),
        (date(2026, 11, 7), date(2026, 11, 10), 1, ExcludedDateReason.WEEKEND),
        (date(2026, 11, 9), date(2026, 11, 9), 0, ExcludedDateReason.HOLIDAY),
        (date(2026, 12, 31), date(2027, 1, 4), 3, ExcludedDateReason.WEEKEND),
    ],
)
def test_business_day_ranges(
    start: date, end: date, count: int, excluded_reason: ExcludedDateReason
) -> None:
    result = business_days_between(start, end, CountryCode.US)
    assert result.ok and result.value is not None
    assert result.value.count == count
    assert excluded_reason in {item.reason for item in result.value.excluded_dates}


def test_calendar_invalid_inputs_and_add_business_days() -> None:
    assert not business_days_between(date(2026, 1, 2), date(2026, 1, 1), "US").ok
    assert not business_days_between(date(2026, 1, 1), date(2026, 1, 2), "CA").ok
    assert not is_business_day(date(2026, 1, 1), "CA").ok
    assert is_business_day(date(2026, 1, 13), CountryCode.US).value is True
    assert not is_business_day(date(2026, 1, 12), CountryCode.US).value
    assert add_business_days(date(2026, 11, 6), 1, CountryCode.US).value == date(2026, 11, 10)
    assert add_business_days(date(2026, 11, 6), 0, CountryCode.US).value == date(2026, 11, 6)
    assert not add_business_days(date(2026, 1, 1), -1, CountryCode.US).ok
