"""JSON-serializable decision provenance (AU1, G1, D4, D6)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import cast

from .models import ApprovalPathStep
from .results import RuleResult, failure, success

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]

ENGINE_VERSION: str = "1.0.0"
_FORBIDDEN_GROUND_TRUTH_KEYS: frozenset[str] = frozenset(
    {
        "ground_truth",
        "ground_truth_id",
        "ground_truth_anomaly_id",
        "ground_truth_decision_id",
        "expected_finding_code",
        "expected_approval_path",
        "expected_status",
        "violation_rule_ids",
        "label",
    }
)


@dataclass(frozen=True, slots=True)
class DecisionTrace:
    """Immutable routing/audit decision inputs, matched rules, reasons, and outputs (AU1)."""

    inputs_snapshot: dict[str, JSONValue]
    matched_rule_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    path: tuple[dict[str, JSONValue], ...]
    engine_version: str
    outputs_snapshot: dict[str, JSONValue]

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a JSON-safe, stable-key representation of this trace (AU1)."""

        return {
            "inputs_snapshot": self.inputs_snapshot,
            "matched_rule_ids": list(self.matched_rule_ids),
            "reason_codes": list(self.reason_codes),
            "path": list(self.path),
            "engine_version": self.engine_version,
            "outputs_snapshot": self.outputs_snapshot,
        }

    def to_json(self) -> str:
        """Serialize this trace with deterministic keys and compact separators (AU1, D6)."""

        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )


def _json_value(value: object) -> JSONValue:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_value(value.value)
    if is_dataclass(value):
        return _json_value(cast(dict[str, object], asdict(value)))
    if isinstance(value, dict):
        pairs = sorted(value.items(), key=lambda pair: str(pair[0]))
        return {str(key): _json_value(item) for key, item in pairs}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable.")


def _contains_ground_truth(value: object) -> bool:
    if is_dataclass(value):
        return _contains_ground_truth(cast(dict[str, object], asdict(value)))
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).casefold()
            if (
                normalized in _FORBIDDEN_GROUND_TRUTH_KEYS
                or "ground_truth" in normalized
                or normalized.startswith("expected_")
            ):
                return True
            if _contains_ground_truth(nested):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_contains_ground_truth(item) for item in value)
    return False


def _plain_path_step(step: ApprovalPathStep | dict[str, object]) -> dict[str, object]:
    if isinstance(step, ApprovalPathStep):
        return {
            "level": step.level,
            "approver_type": step.approver_type.value,
            "approver_id": step.approver_id,
            "approver_name": step.approver_name,
            "reason": step.reason,
            "rule_ids": list(step.rule_ids),
            "reason_codes": list(step.reason_codes),
        }
    return step


def create_decision_trace(
    *,
    inputs_snapshot: dict[str, object],
    matched_rule_ids: tuple[str, ...],
    reason_codes: tuple[str, ...],
    path: tuple[ApprovalPathStep | dict[str, object], ...],
    outputs_snapshot: dict[str, object],
) -> RuleResult[DecisionTrace]:
    """Create AU1 trace data or reject snapshots containing ground-truth material."""

    if (
        _contains_ground_truth(inputs_snapshot)
        or _contains_ground_truth(outputs_snapshot)
        or _contains_ground_truth(path)
    ):
        return failure(
            reason_codes=("GROUND_TRUTH_LEAK_PREVENTED",),
            rule_ids=("G1", "AU1"),
            message="Decision trace snapshots cannot contain ground-truth values or labels.",
        )
    try:
        clean_inputs = cast(dict[str, JSONValue], _json_value(inputs_snapshot))
        clean_outputs = cast(dict[str, JSONValue], _json_value(outputs_snapshot))
        clean_path = tuple(
            cast(dict[str, JSONValue], _json_value(_plain_path_step(step))) for step in path
        )
        json.dumps(
            {
                "inputs_snapshot": clean_inputs,
                "outputs_snapshot": clean_outputs,
                "path": clean_path,
            },
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        return failure(
            reason_codes=("NON_JSON_DECISION_DATA",),
            rule_ids=("AU1",),
            message=f"Decision trace contains non-JSON data: {exc}",
        )
    trace = DecisionTrace(
        inputs_snapshot=clean_inputs,
        matched_rule_ids=tuple(dict.fromkeys(matched_rule_ids)),
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        path=clean_path,
        engine_version=ENGINE_VERSION,
        outputs_snapshot=clean_outputs,
    )
    return success(
        trace,
        reason_codes=trace.reason_codes or ("DECISION_TRACED",),
        rule_ids=tuple(dict.fromkeys((*trace.matched_rule_ids, "AU1"))),
        message="Created deterministic decision provenance snapshot.",
    )
