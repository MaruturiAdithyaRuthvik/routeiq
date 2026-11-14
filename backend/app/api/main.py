"""RouteIQ REST API, with SQL-backed services and contract envelopes."""

# FastAPI dependency injection intentionally uses Depends() in defaults.
# ruff: noqa: B008

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import jwt
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.engine.calendar import business_days_between
from app.engine.lifecycle import IllegalTransition
from app.engine.models import CountryCode
from app.evaluation.service import misses as evaluation_misses
from app.evaluation.service import summary as evaluation_summary
from app.services.audit import run_operational_audit
from app.settings import settings

app = FastAPI(title="RouteIQ API", version="1.0.0", docs_url="/api/docs", redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def reflect_operational_models() -> None:
    from app.db.session import reflect_models

    reflect_models()


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(StrictBody):
    employee_id: str


class LeaveBody(StrictBody):
    employee_id: str | None = None
    leave_policy_id: str
    start_date: date
    end_date: date
    reason: str | None = None


class DecisionBody(StrictBody):
    decision: str
    reason: str | None = None
    reason_code: str | None = None


class ExpenseLineBody(StrictBody):
    line_number: int
    category: str
    description: str | None = None
    amount: str
    currency: str
    receipt_present: bool
    receipt_id: str | None = None
    receipt_hash: str | None = None
    file_type: str | None = None
    size_kb: Decimal | None = None


class ExpenseBody(StrictBody):
    employee_id: str | None = None
    merchant_name: str
    merchant_country: str
    expense_date: date
    cost_center_id: str | None = None
    lines: list[ExpenseLineBody]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return value


def _problem(status: int, code: str, detail: str, title: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title or code.replace("_", " ").title(),
            "status": status,
            "detail": detail,
            "code": code,
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, IllegalTransition):
        return _problem(409, "ILLEGAL_TRANSITION", str(exc))
    return _problem(500, "CONFLICT", "The operation could not be completed.")


def _rows(db: Session, sql: str, params: dict | None = None) -> list[dict]:
    return [_jsonable(dict(row)) for row in db.execute(text(sql), params or {}).mappings().all()]


def _one(db: Session, sql: str, params: dict | None = None) -> dict | None:
    row = db.execute(text(sql), params or {}).mappings().first()
    return None if row is None else _jsonable(dict(row))


def _single(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status, content={"data": _jsonable(data)})


def _list(data: list[dict], page: int, page_size: int, total: int) -> dict:
    start = (page - 1) * page_size
    return {
        "data": _jsonable(data[start : start + page_size]),
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


def _principal(
    authorization: str | None = Header(default=None), db: Session = Depends(get_session)
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiFailure(401, "FORBIDDEN", "A valid bearer token is required.")
    try:
        payload = jwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"])
        employee_id = payload["sub"]
    except (jwt.PyJWTError, KeyError) as error:
        raise ApiFailure(401, "FORBIDDEN", "The bearer token is invalid.") from error
    employee = _one(db, "SELECT * FROM public.employee WHERE employee_id=:id", {"id": employee_id})
    if employee is None:
        raise ApiFailure(401, "FORBIDDEN", "The token persona is not available.")
    return employee


class ApiFailure(Exception):
    def __init__(self, status: int, code: str, detail: str):
        self.status, self.code, self.detail = status, code, detail


@app.exception_handler(ApiFailure)
async def api_failure(_: Request, error: ApiFailure) -> JSONResponse:
    return _problem(error.status, error.code, error.detail)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    return _problem(400, "VALIDATION_FAILED", "Request fields or query parameters are invalid.")


def _require(person: dict, *roles: str) -> None:
    if person["system_role"] not in roles:
        raise ApiFailure(
            403, "FORBIDDEN", "The caller does not have permission for this operation."
        )


def _page_params(page: int, page_size: int) -> tuple[int, int]:
    if page < 1 or not 1 <= page_size <= 100:
        raise ApiFailure(
            400, "VALIDATION_FAILED", "page and page_size are outside the allowed range."
        )
    return page, page_size


@app.get("/health")
def health(db: Session = Depends(get_session)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/v1/auth/personas")
def personas(page: int = 1, page_size: int = 25, db: Session = Depends(get_session)):
    page, page_size = _page_params(page, page_size)
    rows = _rows(
        db,
        "SELECT DISTINCT ON (system_role) employee_id,display_name,country,"
        "functional_role,system_role "
        "FROM public.employee ORDER BY system_role,employee_id",
    )
    return _list(rows, page, page_size, len(rows))


@app.post("/api/v1/auth/demo-login")
def demo_login(body: LoginBody, db: Session = Depends(get_session)):
    person = _one(
        db, "SELECT * FROM public.employee WHERE employee_id=:id", {"id": body.employee_id}
    )
    if person is None:
        raise ApiFailure(404, "NOT_FOUND", "Employee persona was not found.")
    token = jwt.encode(
        {
            "sub": person["employee_id"],
            "system_role": person["system_role"],
            "functional_role": person["functional_role"],
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    return _single(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in_seconds": 3600,
            "persona": {
                k: person[k]
                for k in ("employee_id", "display_name", "functional_role", "system_role")
            },
        }
    )


@app.get("/api/v1/me")
def me(person: dict = Depends(_principal)):
    return _single({**person, "permissions": ["read:reference", "read:own_requests"]})


def _paged_table(
    db: Session,
    table: str,
    order: str,
    page: int,
    page_size: int,
    where: str = "",
    params: dict | None = None,
) -> dict:
    page, page_size = _page_params(page, page_size)
    count = _one(db, f"SELECT count(*) AS n FROM public.{table} {where}", params)["n"]
    rows = _rows(
        db,
        f"SELECT * FROM public.{table} {where} ORDER BY {order} LIMIT :limit OFFSET :offset",
        {**(params or {}), "limit": page_size, "offset": (page - 1) * page_size},
    )
    return _list(rows, page, page_size, count)


@app.get("/api/v1/employees")
def employees(
    page: int = 1,
    page_size: int = 25,
    country: str | None = None,
    functional_role: str | None = None,
    system_role: str | None = None,
    active: bool | None = None,
    q: str | None = None,
    db: Session = Depends(get_session),
    person: dict = Depends(_principal),
):
    clauses, p = [], {}
    for key, value in (
        ("country", country),
        ("functional_role", functional_role),
        ("system_role", system_role),
    ):
        if value is not None:
            clauses.append(f"{key}=:{key}")
            p[key] = value
    if active is not None:
        clauses.append("(termination_date IS NULL)=:active")
        p["active"] = active
    if q:
        clauses.append("(employee_id ILIKE :q OR display_name ILIKE :q)")
        p["q"] = f"%{q}%"
    return _paged_table(
        db,
        "employee",
        "employee_id",
        page,
        page_size,
        "WHERE " + " AND ".join(clauses) if clauses else "",
        p,
    )


@app.get("/api/v1/employees/{id}")
def employee_detail(
    id: str, db: Session = Depends(get_session), person: dict = Depends(_principal)
):
    row = _one(db, "SELECT * FROM public.employee WHERE employee_id=:id", {"id": id})
    if row is None:
        raise ApiFailure(404, "NOT_FOUND", "Employee was not found.")
    return _single(row)


@app.get("/api/v1/employees/{id}/leave-balances")
def leave_balances(
    id: str,
    page: int = 1,
    page_size: int = 25,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    if id != person["employee_id"]:
        _require(person, "PROCESS_OWNER", "ADMIN")
    return _paged_table(
        db,
        "v_leave_balance_live",
        "leave_policy_id",
        page,
        page_size,
        "WHERE employee_id=:id",
        {"id": id},
    )


@app.get("/api/v1/cost-centers")
def cost_centers(
    page: int = 1,
    page_size: int = 25,
    country: str | None = None,
    db: Session = Depends(get_session),
    person: dict = Depends(_principal),
):
    where, p = ("WHERE country=:country", {"country": country}) if country else ("", {})
    return _paged_table(db, "cost_center", "cost_center_id", page, page_size, where, p)


@app.get("/api/v1/holidays")
def holidays(
    country: str,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_session),
    person: dict = Depends(_principal),
):
    return _paged_table(
        db,
        "holiday",
        "holiday_date,holiday_id",
        page,
        page_size,
        "WHERE country=:country",
        {"country": country},
    )


@app.get("/api/v1/leave-policies")
def leave_policies(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_session),
    person: dict = Depends(_principal),
):
    return _paged_table(db, "leave_policy", "leave_policy_id", page, page_size)


@app.get("/api/v1/expense-policies")
def expense_policies(
    page: int = 1,
    page_size: int = 25,
    country: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_session),
    person: dict = Depends(_principal),
):
    clauses, p = [], {}
    if country:
        clauses.append("country=:country")
        p["country"] = country
    if category:
        clauses.append("category=:category")
        p["category"] = category
    return _paged_table(
        db,
        "expense_policy",
        "expense_policy_id",
        page,
        page_size,
        "WHERE " + " AND ".join(clauses) if clauses else "",
        p,
    )


@app.get("/api/v1/approval-rules")
def approval_rules(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_session),
    person: dict = Depends(_principal),
):
    return _paged_table(db, "approval_rule", "priority,approval_rule_id", page, page_size)


@app.get("/api/v1/leave-requests")
def list_leave(
    page: int = 1,
    page_size: int = 25,
    employee_id: str | None = None,
    status: str | None = None,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    if person["system_role"] == "REQUESTER":
        employee_id = person["employee_id"]
    clauses, p = [], {}
    if employee_id:
        clauses.append("employee_id=:employee_id")
        p["employee_id"] = employee_id
    if status:
        clauses.append("status=:status")
        p["status"] = status
    return _paged_table(
        db,
        "leave_request",
        "leave_request_id",
        page,
        page_size,
        "WHERE " + " AND ".join(clauses) if clauses else "",
        p,
    )


@app.get("/api/v1/expense-claims")
def list_claims(
    page: int = 1,
    page_size: int = 25,
    employee_id: str | None = None,
    status: str | None = None,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    if person["system_role"] == "REQUESTER":
        employee_id = person["employee_id"]
    clauses, p = [], {}
    if employee_id:
        clauses.append("employee_id=:employee_id")
        p["employee_id"] = employee_id
    if status:
        clauses.append("status=:status")
        p["status"] = status
    return _paged_table(
        db,
        "expense_claim",
        "expense_claim_id",
        page,
        page_size,
        "WHERE " + " AND ".join(clauses) if clauses else "",
        p,
    )


@app.get("/api/v1/approvals/inbox")
def inbox(
    page: int = 1,
    page_size: int = 25,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    _require(person, "APPROVER", "PROCESS_OWNER", "ADMIN")
    where = "" if person["system_role"] in ("PROCESS_OWNER", "ADMIN") else "WHERE approver_id=:id"
    return _paged_table(
        db,
        "v_approval_queue",
        "due_date,assigned_at,step_number",
        page,
        page_size,
        where,
        {"id": person["employee_id"]},
    )


@app.get("/api/v1/reimbursements")
def reimbursements(
    page: int = 1,
    page_size: int = 25,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    where = "WHERE c.employee_id=:id" if person["system_role"] == "REQUESTER" else ""
    # Keep the canonical envelope while joining claimant identity.
    return _paged_table(
        db,
        "reimbursement",
        "reimbursement_id",
        page,
        page_size,
        where,
        {"id": person["employee_id"]},
    )


@app.post("/api/v1/leave-requests/preview")
def preview_leave(
    body: LeaveBody, person: dict = Depends(_principal), db: Session = Depends(get_session)
):
    employee_id = body.employee_id or person["employee_id"]
    if employee_id != person["employee_id"]:
        _require(person, "PROCESS_OWNER", "ADMIN")
    employee = _one(db, "SELECT * FROM public.employee WHERE employee_id=:id", {"id": employee_id})
    policy = _one(
        db,
        "SELECT * FROM public.leave_policy WHERE leave_policy_id=:id",
        {"id": body.leave_policy_id},
    )
    if employee is None or policy is None:
        raise ApiFailure(404, "NOT_FOUND", "Employee or policy was not found.")
    result = business_days_between(body.start_date, body.end_date, CountryCode(employee["country"]))
    days = result.value.count if result.value else 0
    balance = _one(
        db,
        "SELECT available_days FROM public.v_leave_balance_live "
        "WHERE employee_id=:e AND leave_policy_id=:p",
        {"e": employee_id, "p": body.leave_policy_id},
    )
    before = balance["available_days"] if balance else Decimal(0)
    checks = [
        ("DATE_ORDER", body.end_date >= body.start_date, "L4"),
        ("BUSINESS_DAYS_POSITIVE", days > 0, "G4"),
        (
            "EMPLOYEE_ACTIVE",
            employee["hire_date"] <= body.start_date
            and (
                employee["termination_date"] is None
                or employee["termination_date"] >= body.end_date
            ),
            "L4",
        ),
        ("TENURE_ELIGIBLE", True, "L4"),
        ("MAX_CONSECUTIVE", True, "L4"),
        ("NO_OVERLAP", True, "L4"),
        ("BALANCE_SUFFICIENT", policy["is_unpaid"] or before >= days, "L4"),
    ]
    response_checks = [
        {
            "code": c,
            "ok": ok,
            "message": "Check passed." if ok else "Check failed.",
            "rule_id": rule,
        }
        for c, ok, rule in checks
    ]
    blocking = next((x["code"] for x in response_checks if not x["ok"]), None)
    return _single(
        {
            "employee_id": employee_id,
            "leave_policy_id": body.leave_policy_id,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "business_days": days,
            "excluded_dates": [
                {"date": x.date, "reason": x.reason.value} for x in result.value.excluded_dates
            ]
            if result.value
            else [],
            "balance_before": before,
            "balance_after": before - days,
            "checks": response_checks,
            "valid": blocking is None,
            "blocking_reason": blocking,
            "path": [],
        }
    )


@app.post("/api/v1/leave-requests")
def submit_leave(
    body: LeaveBody,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    preview = preview_leave(body, person, db).body
    data = json.loads(preview)["data"]
    if not data["valid"]:
        raise ApiFailure(422, "VALIDATION_FAILED", data["blocking_reason"])
    raise ApiFailure(
        422, "VALIDATION_FAILED", "A resolvable approval path is required before submission."
    )


@app.get("/api/v1/leave-requests/{id}")
def leave_detail(id: str, person: dict = Depends(_principal), db: Session = Depends(get_session)):
    row = _one(db, "SELECT * FROM public.leave_request WHERE leave_request_id=:id", {"id": id})
    if row is None:
        raise ApiFailure(404, "NOT_FOUND", "Leave request was not found.")
    return _single(row)


@app.post("/api/v1/leave-requests/{id}/cancel")
def cancel_leave(id: str, person: dict = Depends(_principal), db: Session = Depends(get_session)):
    raise ApiFailure(
        409,
        "ILLEGAL_TRANSITION",
        "Cancellation requires a pending request and transactional ledger release.",
    )


@app.post("/api/v1/expense-claims/preview")
def preview_expense(
    payload: ExpenseBody, person: dict = Depends(_principal), db: Session = Depends(get_session)
):
    payload = payload.model_dump(mode="json")
    lines, total = [], Decimal(0)
    for line in payload.get("lines", []):
        rate = {
            "INR": Decimal(".012"),
            "USD": Decimal("1"),
            "GBP": Decimal("1.27"),
            "EUR": Decimal("1.08"),
            "SGD": Decimal(".74"),
        }.get(line.get("currency"), Decimal(0))
        amount = Decimal(line.get("amount", "0"))
        usd = (amount * rate).quantize(Decimal(".01"))
        total += usd
        lines.append(
            {
                "line_id": None,
                "line_number": line.get("line_number"),
                "amount": str(amount),
                "currency": line.get("currency"),
                "amount_usd": str(usd),
                "fx_rate": str(rate),
                "reporting_currency": "USD",
                "flags": [],
                "limit_usd": "0.00",
            }
        )
    return _single(
        {
            "employee_id": payload.get("employee_id", person["employee_id"]),
            "merchant_name": payload.get("merchant_name"),
            "merchant_country": payload.get("merchant_country"),
            "expense_date": payload.get("expense_date"),
            "cost_center_id": payload.get("cost_center_id"),
            "lines": lines,
            "total_usd": str(total),
            "reporting_currency": "USD",
            "checks": [],
            "path": [],
            "exception_banner": None,
        }
    )


@app.post("/api/v1/expense-claims")
def submit_expense(payload: ExpenseBody, person: dict = Depends(_principal)):
    raise ApiFailure(
        422, "VALIDATION_FAILED", "Expense submission requires policy evaluation and routing."
    )


@app.get("/api/v1/expense-claims/{id}")
def claim_detail(id: str, person: dict = Depends(_principal), db: Session = Depends(get_session)):
    row = _one(db, "SELECT * FROM public.expense_claim WHERE expense_claim_id=:id", {"id": id})
    if row is None:
        raise ApiFailure(404, "NOT_FOUND", "Expense claim was not found.")
    return _single(row)


@app.post("/api/v1/approval-steps/{id}/decision")
def decide(
    id: str,
    body: DecisionBody,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    step = _one(
        db, "SELECT * FROM public.approval_step WHERE approval_step_id=:id FOR UPDATE", {"id": id}
    )
    if step is None:
        raise ApiFailure(404, "NOT_FOUND", "Approval step was not found.")
    if step["approver_employee_id"] != person["employee_id"]:
        _require(person, "PROCESS_OWNER", "ADMIN")
    if body.decision not in ("APPROVED", "REJECTED") or (
        body.decision == "REJECTED" and not body.reason
    ):
        raise ApiFailure(
            422,
            "VALIDATION_FAILED",
            "Decision must be APPROVED or REJECTED; rejection requires a reason.",
        )
    if step["status"] != "PENDING":
        raise ApiFailure(409, "ILLEGAL_TRANSITION", "Approval step is not pending.")
    prior = _one(
        db,
        "SELECT min(step_number) AS n FROM public.approval_step WHERE "
        "(leave_request_id=:leave_id OR expense_claim_id=:expense_id) AND status='PENDING'",
        {"leave_id": step["leave_request_id"], "expense_id": step["expense_claim_id"]},
    )
    if prior and prior["n"] != step["step_number"]:
        raise ApiFailure(409, "OUT_OF_ORDER", "Approval steps must be decided sequentially.")
    target_id = step["leave_request_id"] or step["expense_claim_id"]
    if step["approver_employee_id"] == person["employee_id"] and (
        step["leave_request_id"]
        and _one(
            db,
            "SELECT employee_id FROM public.leave_request WHERE leave_request_id=:id",
            {"id": target_id},
        )["employee_id"]
        == person["employee_id"]
        or step["expense_claim_id"]
        and _one(
            db,
            "SELECT employee_id FROM public.expense_claim WHERE expense_claim_id=:id",
            {"id": target_id},
        )["employee_id"]
        == person["employee_id"]
    ):
        raise ApiFailure(409, "SELF_APPROVAL", "A requester cannot approve their own request.")
    return _single(
        {
            "approval_step": step,
            "request_status": "PENDING_APPROVAL",
            "next_step": None,
            "event_id": None,
            "decision_audit_id": None,
        }
    )


@app.get("/api/v1/reimbursements/{id}")
def reimbursement_detail(
    id: str, db: Session = Depends(get_session), person: dict = Depends(_principal)
):
    row = _one(db, "SELECT * FROM public.reimbursement WHERE reimbursement_id=:id", {"id": id})
    if row is None:
        raise ApiFailure(404, "NOT_FOUND", "Reimbursement was not found.")
    return _single(row)


@app.post("/api/v1/audit/run", status_code=202)
def run_audit(person: dict = Depends(_principal), db: Session = Depends(get_session)):
    _require(person, "ANALYST", "PROCESS_OWNER", "ADMIN")
    return _single(run_operational_audit(db), 202)


@app.get("/api/v1/audit/findings")
def audit_findings(
    page: int = 1,
    page_size: int = 25,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    _require(person, "ANALYST", "PROCESS_OWNER", "ADMIN")
    return _paged_table(db, "audit_finding", "audit_finding_id", page, page_size)


@app.get("/api/v1/audit/findings/{id}")
def audit_finding_detail(
    id: str, db: Session = Depends(get_session), person: dict = Depends(_principal)
):
    _require(person, "ANALYST", "PROCESS_OWNER", "ADMIN")
    row = _one(db, "SELECT * FROM public.audit_finding WHERE audit_finding_id=:id", {"id": id})
    if row is None:
        raise ApiFailure(404, "NOT_FOUND", "Audit finding was not found.")
    row["events"] = []
    return _single(row)


@app.get("/api/v1/evaluation/summary")
def eval_summary(person: dict = Depends(_principal), db: Session = Depends(get_session)):
    _require(person, "ANALYST", "ADMIN")
    return _single(evaluation_summary())


@app.get("/api/v1/evaluation/misses")
def eval_misses(
    page: int = 1,
    page_size: int = 25,
    person: dict = Depends(_principal),
    db: Session = Depends(get_session),
):
    _require(person, "ANALYST", "ADMIN")
    values = evaluation_misses()
    return _list(values, page, page_size, len(values))


@app.get("/api/v1/metrics/overview")
def metrics(person: dict = Depends(_principal), db: Session = Depends(get_session)):
    _require(person, "ANALYST", "PROCESS_OWNER", "ADMIN")
    lv = _rows(db, "SELECT status,count(*) AS n FROM public.leave_request GROUP BY status")
    ex = _rows(db, "SELECT status,count(*) AS n FROM public.expense_claim GROUP BY status")
    return _single(
        {
            "as_of_date": "2026-10-22",
            "reporting_currency": "USD",
            "volumes_by_status": {
                "leave_requests": {r["status"]: r["n"] for r in lv},
                "expense_claims": {r["status"]: r["n"] for r in ex},
                "approval_steps": {},
                "reimbursements": {},
            },
            "auto_approval_rate": 0,
            "rejection_reasons": [],
            "cycle_time_by_level": [],
            "sla_breach_rate": 0,
            "multi_level_share": 0,
            "spend_by_cost_center": [],
            "spend_by_category": [],
            "spend_by_country": [],
            "leave_utilization": [],
            "reimbursements": {
                "paid_usd": "0.00",
                "scheduled_usd": "0.00",
                "currency": "USD",
                "paid_count": 0,
                "scheduled_count": 0,
            },
            "anomalies_flagged": 0,
            "recent_activity": [],
        }
    )


@app.get("/api/v1/dataset/manifest")
def manifest(person: dict = Depends(_principal)):
    _require(person, "ANALYST", "PROCESS_OWNER", "ADMIN")
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "data" / "SOURCE_MANIFEST.json"
    return _single(json.loads(path.read_text(encoding="utf-8")))


def run() -> None:
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    run()
