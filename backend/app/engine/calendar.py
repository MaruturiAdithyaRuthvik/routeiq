"""Synthetic 2026 business-day calculations (G3, G4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from .models import CountryCode
from .results import RuleResult, failure, success

AS_OF_DATE: Final = date(2026, 10, 22)

HOLIDAYS_BY_COUNTRY: Final = MappingProxyType(
    {
        CountryCode.IN: frozenset(
            date.fromisoformat(day)
            for day in (
                "2026-01-05",
                "2026-02-09",
                "2026-03-16",
                "2026-04-20",
                "2026-06-08",
                "2026-08-17",
                "2026-10-12",
                "2026-12-14",
            )
        ),
        CountryCode.US: frozenset(
            date.fromisoformat(day)
            for day in (
                "2026-01-12",
                "2026-02-23",
                "2026-04-06",
                "2026-05-18",
                "2026-07-13",
                "2026-09-14",
                "2026-11-09",
                "2026-12-21",
            )
        ),
        CountryCode.GB: frozenset(
            date.fromisoformat(day)
            for day in (
                "2026-01-19",
                "2026-03-02",
                "2026-04-13",
                "2026-06-01",
                "2026-07-20",
                "2026-09-21",
                "2026-11-16",
                "2026-12-07",
            )
        ),
        CountryCode.DE: frozenset(
            date.fromisoformat(day)
            for day in (
                "2026-01-26",
                "2026-03-09",
                "2026-04-27",
                "2026-06-15",
                "2026-08-03",
                "2026-09-28",
                "2026-11-23",
                "2026-12-28",
            )
        ),
        CountryCode.SG: frozenset(
            date.fromisoformat(day)
            for day in (
                "2026-02-02",
                "2026-03-23",
                "2026-05-11",
                "2026-06-22",
                "2026-08-10",
                "2026-09-07",
                "2026-10-26",
                "2026-12-14",
            )
        ),
    }
)


class ExcludedDateReason(StrEnum):
    WEEKEND = "WEEKEND"
    HOLIDAY = "HOLIDAY"


@dataclass(frozen=True, slots=True)
class ExcludedDate:
    value: date
    reason: ExcludedDateReason


@dataclass(frozen=True, slots=True)
class BusinessDayCount:
    count: int
    excluded_dates: tuple[ExcludedDate, ...]


def _country(country: CountryCode | str) -> CountryCode | None:
    try:
        return CountryCode(country)
    except (TypeError, ValueError):
        return None


def is_business_day(value: date, country: CountryCode | str) -> RuleResult[bool]:
    """Return whether a date is a weekday outside its country's synthetic holidays (G3, G4)."""

    resolved_country = _country(country)
    if resolved_country is None:
        return failure(
            reason_codes=("UNSUPPORTED_COUNTRY",),
            rule_ids=("G2", "G4"),
            message="Business-day country is not supported.",
        )
    if value.weekday() >= 5:
        return success(
            False,
            reason_codes=("WEEKEND",),
            rule_ids=("G4",),
            message="Date is a Saturday or Sunday.",
        )
    if value in HOLIDAYS_BY_COUNTRY[resolved_country]:
        return success(
            False,
            reason_codes=("HOLIDAY",),
            rule_ids=("G3", "G4"),
            message="Date is a synthetic holiday in the employee's country.",
        )
    return success(
        True,
        reason_codes=("BUSINESS_DAY",),
        rule_ids=("G4",),
        message="Date is Monday through Friday and is not a country holiday.",
    )


def business_days_between(
    start_date: date, end_date: date, country: CountryCode | str
) -> RuleResult[BusinessDayCount]:
    """Count inclusive business days and report every excluded date (G3, G4)."""

    if end_date < start_date:
        return failure(
            reason_codes=("INVALID_DATE_RANGE",),
            rule_ids=("L4", "G4"),
            message="End date must be on or after start date.",
        )
    resolved_country = _country(country)
    if resolved_country is None:
        return failure(
            reason_codes=("UNSUPPORTED_COUNTRY",),
            rule_ids=("G2", "G4"),
            message="Business-day country is not supported.",
        )
    excluded: list[ExcludedDate] = []
    count = 0
    current = start_date
    while current <= end_date:
        if current.weekday() >= 5:
            excluded.append(ExcludedDate(current, ExcludedDateReason.WEEKEND))
        elif current in HOLIDAYS_BY_COUNTRY[resolved_country]:
            excluded.append(ExcludedDate(current, ExcludedDateReason.HOLIDAY))
        else:
            count += 1
        current += timedelta(days=1)
    result = BusinessDayCount(count, tuple(excluded))
    code = "ZERO_BUSINESS_DAYS" if count == 0 else "BUSINESS_DAYS_COUNTED"
    return success(
        result,
        reason_codes=(code,),
        rule_ids=("G3", "G4"),
        message=f"Counted {count} inclusive business day(s).",
    )


def add_business_days(
    start_date: date, number_of_days: int, country: CountryCode | str
) -> RuleResult[date]:
    """Add business days after the start date; the start date is not counted (G4, E7, E9)."""

    if (
        isinstance(number_of_days, bool)
        or not isinstance(number_of_days, int)
        or number_of_days < 0
    ):
        return failure(
            reason_codes=("INVALID_BUSINESS_DAY_OFFSET",),
            rule_ids=("G4", "E7", "E9"),
            message="Business-day offset must be a non-negative integer.",
        )
    resolved_country = _country(country)
    if resolved_country is None:
        return failure(
            reason_codes=("UNSUPPORTED_COUNTRY",),
            rule_ids=("G2", "G4"),
            message="Business-day country is not supported.",
        )
    current = start_date
    remaining = number_of_days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in HOLIDAYS_BY_COUNTRY[resolved_country]:
            remaining -= 1
    return success(
        current,
        reason_codes=("BUSINESS_DAYS_ADDED",),
        rule_ids=("G3", "G4"),
        message=f"Added {number_of_days} business day(s) after {start_date.isoformat()}.",
    )
