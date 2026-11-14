"""Explainable return values shared by the pure engine (G1, AU1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleResult[T]:
    """A rule outcome with its machine reasons, governing rules, and explanation."""

    ok: bool
    value: T | None
    reason_codes: tuple[str, ...]
    rule_ids: tuple[str, ...]
    messages: tuple[str, ...]


def success[T](
    value: T,
    *,
    reason_codes: tuple[str, ...],
    rule_ids: tuple[str, ...],
    message: str,
) -> RuleResult[T]:
    """Build a successful explainable result."""

    return RuleResult(True, value, reason_codes, rule_ids, (message,))


def failure[T](
    *,
    reason_codes: tuple[str, ...],
    rule_ids: tuple[str, ...],
    message: str,
    value: T | None = None,
) -> RuleResult[T]:
    """Build a rejected or unresolved explainable result."""

    return RuleResult(False, value, reason_codes, rule_ids, (message,))
