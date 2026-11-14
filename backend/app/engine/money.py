"""Decimal-only currency conversion and rounding (G2)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from types import MappingProxyType
from typing import Final

from .models import CountryCode, CurrencyCode
from .results import RuleResult, failure, success

FX_TO_USD: Final = MappingProxyType(
    {
        CurrencyCode.INR: Decimal("0.012"),
        CurrencyCode.USD: Decimal("1.0"),
        CurrencyCode.GBP: Decimal("1.27"),
        CurrencyCode.EUR: Decimal("1.08"),
        CurrencyCode.SGD: Decimal("0.74"),
    }
)

HOME_CURRENCY_BY_COUNTRY: Final = MappingProxyType(
    {
        CountryCode.IN: CurrencyCode.INR,
        CountryCode.US: CurrencyCode.USD,
        CountryCode.GB: CurrencyCode.GBP,
        CountryCode.DE: CurrencyCode.EUR,
        CountryCode.SG: CurrencyCode.SGD,
    }
)


def _decimal(value: Decimal | str | int) -> Decimal | None:
    if isinstance(value, (bool, float)):
        return None
    try:
        converted = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return converted if converted.is_finite() else None


def round_half_up(value: Decimal | str | int, places: int = 2) -> RuleResult[Decimal]:
    """Round a finite exact decimal with ROUND_HALF_UP (G2, L2)."""

    decimal_value = _decimal(value)
    if decimal_value is None:
        return failure(
            reason_codes=("INVALID_DECIMAL",),
            rule_ids=("G2",),
            message="Value must be a finite Decimal, string, or integer; floats are not accepted.",
        )
    if isinstance(places, bool) or not isinstance(places, int) or not 0 <= places <= 6:
        return failure(
            reason_codes=("INVALID_DECIMAL_PLACES",),
            rule_ids=("G2", "L2"),
            message="Rounding places must be an integer from 0 through 6.",
        )
    quantum = Decimal(1).scaleb(-places)
    try:
        rounded = decimal_value.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return failure(
            reason_codes=("DECIMAL_OUT_OF_RANGE",),
            rule_ids=("G2",),
            message="Value exceeds the supported Decimal precision.",
        )
    return success(
        rounded,
        reason_codes=("ROUNDED_HALF_UP",),
        rule_ids=("G2",),
        message=f"Rounded to {places} decimal places using round-half-up.",
    )


def currency_for_country(country: CountryCode) -> RuleResult[CurrencyCode]:
    """Resolve the fixed home currency for an allowed country (G2)."""

    try:
        resolved_country = CountryCode(country)
    except (TypeError, ValueError):
        return failure(
            reason_codes=("UNSUPPORTED_COUNTRY",),
            rule_ids=("G2",),
            message="Country is not one of IN, US, GB, DE, or SG.",
        )
    return success(
        HOME_CURRENCY_BY_COUNTRY[resolved_country],
        reason_codes=("HOME_CURRENCY_RESOLVED",),
        rule_ids=("G2",),
        message=f"Resolved home currency for {resolved_country.value}.",
    )


def _currency(value: CurrencyCode | str) -> CurrencyCode | None:
    try:
        return CurrencyCode(value)
    except (TypeError, ValueError):
        return None


def to_usd(amount: Decimal | str | int, currency: CurrencyCode | str) -> RuleResult[Decimal]:
    """Convert a positive source-currency amount to rounded USD (G2, E2)."""

    decimal_amount = _decimal(amount)
    resolved_currency = _currency(currency)
    if decimal_amount is None:
        return failure(
            reason_codes=("INVALID_DECIMAL",),
            rule_ids=("G2", "E2"),
            message="Amount must be finite exact decimal data; floats are not accepted.",
        )
    if decimal_amount <= 0:
        return failure(
            reason_codes=("AMOUNT_NOT_POSITIVE",),
            rule_ids=("E2",),
            message="Expense amount must be greater than zero.",
        )
    if resolved_currency is None:
        return failure(
            reason_codes=("UNSUPPORTED_CURRENCY",),
            rule_ids=("G2",),
            message="Currency is not one of INR, USD, GBP, EUR, or SGD.",
        )
    try:
        usd_amount = decimal_amount * FX_TO_USD[resolved_currency]
    except InvalidOperation:
        return failure(
            reason_codes=("DECIMAL_OUT_OF_RANGE",),
            rule_ids=("G2", "E2"),
            message="Converted USD amount exceeds the supported Decimal precision.",
        )
    rounded = round_half_up(usd_amount, 2)
    if rounded.value is None:
        return failure(
            reason_codes=rounded.reason_codes,
            rule_ids=rounded.rule_ids,
            message=rounded.messages[0],
        )
    if rounded.value <= 0:
        return failure(
            reason_codes=("AMOUNT_USD_ROUNDS_TO_ZERO",),
            rule_ids=("G2", "E2"),
            message="Positive source amount rounds to zero USD and cannot form an expense line.",
        )
    return success(
        rounded.value,
        reason_codes=("AMOUNT_CONVERTED_TO_USD",),
        rule_ids=("G2", "E2"),
        message=f"Converted {resolved_currency.value} to USD using the fixed G2 rate.",
    )


def to_home_currency(
    amount_usd: Decimal | str | int, home_currency: CurrencyCode | str
) -> RuleResult[Decimal]:
    """Convert approved USD to an employee's home currency (G2, E9)."""

    usd_amount = _decimal(amount_usd)
    resolved_currency = _currency(home_currency)
    if usd_amount is None:
        return failure(
            reason_codes=("INVALID_DECIMAL",),
            rule_ids=("G2", "E9"),
            message="USD amount must be finite exact decimal data; floats are not accepted.",
        )
    if usd_amount <= 0:
        return failure(
            reason_codes=("AMOUNT_NOT_POSITIVE",),
            rule_ids=("E9",),
            message="Approved reimbursement amount must be greater than zero.",
        )
    if resolved_currency is None:
        return failure(
            reason_codes=("UNSUPPORTED_CURRENCY",),
            rule_ids=("G2",),
            message="Home currency is not supported by the fixed FX table.",
        )
    try:
        converted_amount = usd_amount / FX_TO_USD[resolved_currency]
    except (InvalidOperation, ZeroDivisionError):
        return failure(
            reason_codes=("DECIMAL_OUT_OF_RANGE",),
            rule_ids=("G2", "E9"),
            message="Converted home-currency amount exceeds the supported Decimal precision.",
        )
    home_amount = round_half_up(converted_amount, 2)
    if home_amount.value is None:
        return failure(
            reason_codes=home_amount.reason_codes,
            rule_ids=home_amount.rule_ids,
            message=home_amount.messages[0],
        )
    return success(
        home_amount.value,
        reason_codes=("REIMBURSEMENT_HOME_CURRENCY_CONVERTED",),
        rule_ids=("G2", "E9"),
        message=f"Converted approved USD amount to {resolved_currency.value}.",
    )
