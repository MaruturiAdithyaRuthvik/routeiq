# RouteIQ API Contract

This document is the contract shared by the frontend and backend. Implementations must preserve the field names, enum values, envelopes, and status semantics below. Persisted entity fields follow `docs/DATA_DICTIONARY.md`; calculations and transitions follow `docs/BUSINESS_RULES.md`.

## 1. Conventions

- **Base path:** `/api/v1`. All endpoint paths below are relative to that prefix.
- **Media type:** requests and successful responses use `application/json`. Errors use `application/problem+json`.
- **Authentication:** send `Authorization: Bearer <JWT>` on every endpoint except `GET /auth/personas` and `POST /auth/demo-login`. Demo tokens are signed JWTs and identify one synthetic `employee_id`, `functional_role`, and `system_role`.
- **JSON naming:** `snake_case`; unknown request fields are rejected with `VALIDATION_FAILED`.
- **List envelope:** every collection endpoint returns exactly `{"data":[...],"meta":{"page":1,"page_size":25,"total":0}}`. `total` is the count before pagination.
- **Single envelope:** every successful non-list endpoint returns `{"data":{...}}`.
- **Errors:** RFC 7807 shape is exactly `{"type":"about:blank","title":"...","status":400,"detail":"...","code":"VALIDATION_FAILED"}`. `code` is one of `SELF_APPROVAL`, `OUT_OF_ORDER`, `ILLEGAL_TRANSITION`, `INSUFFICIENT_BALANCE`, `VALIDATION_FAILED`, `FORBIDDEN`, `NOT_FOUND`, or `CONFLICT`. `type` is `about:blank`; `status` is the HTTP status; `detail` is safe, actionable text and never contains ground-truth labels.
- **HTTP status mapping:** `200` reads/previews/decisions; `201` creates a request or claim; `202` queues a requested audit run; `400` malformed query or JSON; `401` missing/invalid JWT (`FORBIDDEN`); `403` authenticated but not authorized (`FORBIDDEN`); `404` missing resource (`NOT_FOUND`); `409` duplicate/idempotency conflict (`CONFLICT`), self-approval (`SELF_APPROVAL`), out-of-order step (`OUT_OF_ORDER`), or illegal lifecycle transition (`ILLEGAL_TRANSITION`); `422` rule validation (`VALIDATION_FAILED`) or insufficient leave balance (`INSUFFICIENT_BALANCE`).
- **Pagination:** list endpoints accept `page` (1-based, default `1`) and `page_size` (default `25`, maximum `100`). Invalid or out-of-range values return `400 VALIDATION_FAILED`.
- **Sorting:** list endpoints accept `sort=field:asc` or `sort=field:desc`; comma-separated terms are supported. Each endpoint lists sortable fields. The primary key ascending is the deterministic tie-breaker. Unsupported fields/directions return `400 VALIDATION_FAILED`.
- **Filtering:** query parameters are exact-match unless specified otherwise. Date filters use inclusive `from` and `to` (`YYYY-MM-DD`). `q` is a case-insensitive substring search over the endpoint's documented display-name fields.
- **Dates and timestamps:** date-only values are ISO-8601 `YYYY-MM-DD`; timestamps are ISO-8601 UTC with `Z`. Business calculations use `AS_OF_DATE = 2026-10-22`; an API response timestamp is a persisted scenario/workflow timestamp, not an instruction to use the wall clock in the engine.
- **Numbers and money:** day counts, percentages, scores, and rates are JSON numbers. Monetary values are decimal strings (for example `"120.00"`) and have a sibling currency field. All `*_usd` values use `reporting_currency: "USD"` (or a local `currency: "USD"` on nested metric rows). Source-currency amounts have `currency` and `fx_rate_to_usd`; no binary floating-point representation is used for money.
- **IDs:** IDs are immutable and use the exact formats in the dictionary, including `EMP-000001`, `LVE-2026-000001`, `EXP-2026-000001`, `EXPL-EXP-2026-000001-01`, `APR-LVE-2026-000001-01`, and `RMB-2026-000001`. The server assigns persistent IDs on creation. A preview is side-effect-free; a new unsaved preview line has `line_id: null`.
- **Idempotency:** `POST /leave-requests` and `POST /expense-claims` accept optional `Idempotency-Key`. Replaying the same key and identical body returns the original `201` result; reusing it with a different body returns `409 CONFLICT`.

### Access roles

`PUBLIC` requires no token. `AUTHENTICATED` means any valid persona token. `REQUESTER` means the requester's own records; a requester cannot choose another `employee_id`. `APPROVER` means a pending step assigned to the caller. `PROCESS_OWNER` and `ADMIN` can operate across employees and may submit on behalf of an employee. `ANALYST` is read-only for operational data and may run audit/evaluation operations. No role is implicitly a higher role than another unless stated for an endpoint.

The evaluation endpoints are served by the evaluation service using the evaluator-only database login. Only `ANALYST` and `ADMIN` callers may invoke them. Request routing, audit detection, metrics, and feature endpoints never query or serialize `ground_truth`.

### Error example

```json
{
  "type": "about:blank",
  "title": "Out-of-order approval",
  "status": 409,
  "detail": "Approval step APR-EXP-2026-000001-02 cannot be decided before step 01.",
  "code": "OUT_OF_ORDER"
}
```

## 2. Endpoint catalogue

Unless stated otherwise, examples show a successful response body. Query parameters not listed for an endpoint are rejected.

### Authentication

#### `GET /auth/personas`

- **Access:** `PUBLIC`.
- **Query:** `page`, `page_size`, `sort` (`employee_id`, `display_name`, `system_role`).
- **Request JSON:** none.
- **Response:** `200`, list envelope of demo personas.

```json
{
  "data": [
    {"employee_id":"EMP-000001","display_name":"Avery Chen","country":"US","functional_role":"NONE","system_role":"REQUESTER"},
    {"employee_id":"EMP-000002","display_name":"Jordan Patel","country":"US","functional_role":"DEPT_HEAD","system_role":"APPROVER"},
    {"employee_id":"EMP-000003","display_name":"Riley Morgan","country":"US","functional_role":"HR_PARTNER","system_role":"APPROVER"}
  ],
  "meta": {"page":1,"page_size":25,"total":3}
}
```

#### `POST /auth/demo-login`

- **Access:** `PUBLIC`.
- **Query:** none.
- **Request JSON:**

```json
{"employee_id":"EMP-000001"}
```

- **Response:** `200`, single envelope. The example token is illustrative and is not a usable credential.

```json
{
  "data": {
    "access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJFTVAtMDAwMDAxIiwic3lzdGVtX3JvbGUiOiJSRVFVRVNURVIifQ.demo-signature",
    "token_type":"Bearer",
    "expires_in_seconds":3600,
    "persona":{"employee_id":"EMP-000001","display_name":"Avery Chen","functional_role":"NONE","system_role":"REQUESTER"}
  }
}
```

#### `GET /me`

- **Access:** `AUTHENTICATED`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope containing the token principal and allowed capabilities.

```json
{
  "data": {
    "employee_id":"EMP-000001","display_name":"Avery Chen","country":"US","home_currency":"USD",
    "hire_date":"2020-04-15","termination_date":null,"manager_id":"EMP-000002","cost_center_id":"CC-0001",
    "functional_role":"NONE","system_role":"REQUESTER","job_level":4,"is_ceo":false,
    "permissions":["read:reference","read:own_requests","create:leave_request","create:expense_claim","cancel:own_request"]
  }
}
```

### Reference data

#### `GET /employees`

- **Access:** `AUTHENTICATED`; `q` searches `employee_id` and `display_name`.
- **Query:** `page`, `page_size`, `sort` (`employee_id`, `display_name`, `country`, `job_level`), `country`, `functional_role`, `system_role`, `active` (`true|false`), `q`.
- **Request JSON:** none.
- **Response:** `200`, list envelope of `Employee` records.

```json
{
  "data": [{
    "employee_id":"EMP-000001","display_name":"Avery Chen","country":"US","home_currency":"USD",
    "hire_date":"2020-04-15","termination_date":null,"manager_id":"EMP-000002","cost_center_id":"CC-0001",
    "functional_role":"NONE","system_role":"REQUESTER","job_level":4,"is_ceo":false
  }],
  "meta":{"page":1,"page_size":1,"total":400}
}
```

#### `GET /employees/{id}`

- **Access:** `AUTHENTICATED`.
- **Path:** `{id}` is an `employee_id`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope containing the same complete `Employee` shape as `GET /employees`.

```json
{
  "data": {
    "employee_id":"EMP-000001","display_name":"Avery Chen","country":"US","home_currency":"USD",
    "hire_date":"2020-04-15","termination_date":null,"manager_id":"EMP-000002","cost_center_id":"CC-0001",
    "functional_role":"NONE","system_role":"REQUESTER","job_level":4,"is_ceo":false
  }
}
```

#### `GET /employees/{id}/leave-balances`

- **Access:** employee themself, `PROCESS_OWNER`, or `ADMIN`.
- **Path:** `{id}` is an `employee_id`.
- **Query:** `as_of_date` (defaults to `2026-10-22`); `page`, `page_size`, `sort` (`leave_policy_id`, `available_days`).
- **Request JSON:** none.
- **Response:** `200`, list envelope of balance snapshots. `available_days` is derived from the ledger; `balance_year` is `2026`.

```json
{
  "data": [{
    "leave_balance_id":"LBL-EMP-000001-LPO-001-2026","employee_id":"EMP-000001",
    "leave_policy_id":"LPO-001","balance_year":2026,"as_of_date":"2026-10-22",
    "opening_days":6.000000,"accrued_days":18.000000,"adjustments_days":0.000000,
    "used_days":4.000000,"pending_days":2.000000,"available_days":18.000000
  }],
  "meta":{"page":1,"page_size":1,"total":6}
}
```

#### `GET /cost-centers`

- **Access:** `AUTHENTICATED`.
- **Query:** `page`, `page_size`, `sort` (`cost_center_id`, `name`, `country`), `country`, `employee_id`.
- **Request JSON:** none.
- **Response:** `200`, list envelope. `budget_usd` is a USD decimal string.

```json
{
  "data":[{
    "cost_center_id":"CC-0001","name":"North America Operations","country":"US",
    "owner_employee_id":"EMP-000002","owner_name":"Jordan Patel","budget_year":2026,
    "budget_usd":"250000.00","currency":"USD"
  }],
  "meta":{"page":1,"page_size":1,"total":20}
}
```

#### `GET /holidays?country=`

- **Access:** `AUTHENTICATED`.
- **Query:** required `country`; optional `year` (only `2026`), `page`, `page_size`, `sort` (`holiday_date`, `holiday_id`).
- **Request JSON:** none.
- **Response:** `200`, list envelope of synthetic illustrative holidays.

```json
{
  "data":[{
    "holiday_id":"HOL-2026-US-01","country":"US","holiday_date":"2026-01-12",
    "holiday_name":"Illustrative holiday 01","is_illustrative":true
  }],
  "meta":{"page":1,"page_size":1,"total":8}
}
```

#### `GET /leave-policies`

- **Access:** `AUTHENTICATED`.
- **Query:** `page`, `page_size`, `sort` (`leave_policy_id`, `name`), `effective_on`.
- **Request JSON:** none.
- **Response:** `200`, list envelope of policies.

```json
{
  "data":[{
    "leave_policy_id":"LPO-001","name":"Annual","annual_entitlement_days":24.00,
    "carry_forward_max_days":10.00,"max_consecutive_days":20,
    "medical_certificate_after_days":null,"tenure_required_months":0,
    "lump_sum_days":null,"is_unpaid":false,"effective_from":"2026-01-01","effective_to":null
  }],
  "meta":{"page":1,"page_size":1,"total":6}
}
```

#### `GET /expense-policies`

- **Access:** `AUTHENTICATED`.
- **Query:** `page`, `page_size`, `sort` (`expense_policy_id`, `category`, `country`), `country`, `category`, `effective_on`.
- **Request JSON:** none.
- **Response:** `200`, list envelope. Both USD limits are decimal strings with `currency: "USD"`.

```json
{
  "data":[{
    "expense_policy_id":"XPO-0011","category":"MEALS","country":"US",
    "per_line_limit_usd":"150.00","receipt_threshold_usd":"25.00","currency":"USD",
    "effective_from":"2026-01-01","effective_to":null,"version":1
  }],
  "meta":{"page":1,"page_size":1,"total":50}
}
```

#### `GET /approval-rules`

- **Access:** `AUTHENTICATED`.
- **Query:** `page`, `page_size`, `sort` (`approval_rule_id`, `priority`), `request_type`, `required_role`, `active`, `effective_on`, `category`.
- **Request JSON:** none.
- **Response:** `200`, list envelope of rules; category filters match the effective `ApprovalRuleCategory` bridge.

```json
{
  "data":[{
    "approval_rule_id":"ARL-001","rule_code":"EXPENSE_50_1000","request_type":"EXPENSE",
    "priority":1,"required_role":"MANAGER","condition_description":"Claim total is at least USD 50 and below USD 1,000.",
    "designated_employee_id":null,"effective_from":"2026-01-01","effective_to":null,
    "version":1,"is_active":true
  }],
  "meta":{"page":1,"page_size":1,"total":24}
}
```

### Leave

#### `POST /leave-requests/preview`

- **Access:** `REQUESTER`; `PROCESS_OWNER` or `ADMIN` may set another `employee_id`.
- **Query:** none.
- **Request JSON:** `employee_id` is optional and defaults to the caller; `reason` is optional.

```json
{
  "employee_id":"EMP-000001","leave_policy_id":"LPO-001",
  "start_date":"2026-11-23","end_date":"2026-11-28","reason":"Family visit"
}
```

- **Response:** `200`, single envelope. `excluded_dates` lists each calendar date excluded from business-day counting; `reason` is `WEEKEND` or `HOLIDAY`. `balance_before`/`balance_after` are days or `null` for Unpaid leave. All checks are returned in rule order; `blocking_reason` is the first blocking reason or `null`. `path` is empty when routing cannot be computed.

```json
{
  "data":{
    "employee_id":"EMP-000001","leave_policy_id":"LPO-001",
    "start_date":"2026-11-23","end_date":"2026-11-28","business_days":5,
    "excluded_dates":[{"date":"2026-11-28","reason":"WEEKEND"}],
    "balance_before":18.000000,"balance_after":13.000000,
    "checks":[
      {"code":"DATE_ORDER","ok":true,"message":"End date is on or after start date.","rule_id":"L4"},
      {"code":"BUSINESS_DAYS_POSITIVE","ok":true,"message":"The range contains 5 business days.","rule_id":"G4"},
      {"code":"EMPLOYEE_ACTIVE","ok":true,"message":"The employee is active for the requested dates.","rule_id":"L4"},
      {"code":"TENURE_ELIGIBLE","ok":true,"message":"The employee meets the policy tenure requirement.","rule_id":"L4"},
      {"code":"MAX_CONSECUTIVE","ok":true,"message":"The request is within the consecutive-day limit.","rule_id":"L4"},
      {"code":"NO_OVERLAP","ok":true,"message":"No active overlapping leave request exists.","rule_id":"L4"},
      {"code":"BALANCE_SUFFICIENT","ok":true,"message":"Available balance covers the request.","rule_id":"L4"}
    ],
    "valid":true,"blocking_reason":null,
    "path":[
      {"level":1,"approver_type":"MANAGER","approver_id":"EMP-000002","approver_name":"Jordan Patel","reason":"Direct manager per G5.","rule_ids":["L5","G5"]},
      {"level":2,"approver_type":"HR_PARTNER","approver_id":"EMP-000003","approver_name":"Riley Morgan","reason":"Deterministic same-country HR partner.","rule_ids":["L5","G5"]}
    ]
  }
}
```

#### `POST /leave-requests`

- **Access:** `REQUESTER`; `PROCESS_OWNER` or `ADMIN` may set another `employee_id`.
- **Query:** none. Optional header: `Idempotency-Key`.
- **Request JSON:** same fields as the preview request; `employee_id` defaults to the caller.

```json
{
  "employee_id":"EMP-000001","leave_policy_id":"LPO-001",
  "start_date":"2026-11-23","end_date":"2026-11-28","reason":"Family visit"
}
```

- **Response:** `201`, single envelope of the created request detail. The successful submit reserves five days and appends events, approval steps, and audit records.

```json
{
  "data":{
    "leave_request_id":"LVE-2026-000001","employee_id":"EMP-000001","employee_name":"Avery Chen",
    "leave_policy_id":"LPO-001","policy_name":"Annual","start_date":"2026-11-23","end_date":"2026-11-28",
    "business_days":5,"status":"PENDING_APPROVAL","submitted_at":"2026-10-22T09:00:00Z",
    "medical_certificate_required":false,"risk_score":0,"reason":"Family visit",
    "approval_steps":[
      {"approval_step_id":"APR-LVE-2026-000001-01","request_type":"LEAVE","request_id":"LVE-2026-000001",
       "step_number":1,"required_role":"MANAGER","approver_employee_id":"EMP-000002","approver_name":"Jordan Patel",
       "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27","decided_at":null,"reason_code":null},
      {"approval_step_id":"APR-LVE-2026-000001-02","request_type":"LEAVE","request_id":"LVE-2026-000001",
       "step_number":2,"required_role":"HR_PARTNER","approver_employee_id":"EMP-000003","approver_name":"Riley Morgan",
       "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27","decided_at":null,"reason_code":null}
    ],
    "events":[
      {"event_id":"LRE-2026-000001","sequence_number":1,"event_type":"CREATED","from_status":null,"to_status":"DRAFT","occurred_at":"2026-10-22T08:59:00Z","actor_employee_id":"EMP-000001","reason_code":null},
      {"event_id":"LRE-2026-000002","sequence_number":2,"event_type":"SUBMITTED","from_status":"DRAFT","to_status":"SUBMITTED","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":"EMP-000001","reason_code":null},
      {"event_id":"LRE-2026-000003","sequence_number":3,"event_type":"APPROVAL_STARTED","from_status":"SUBMITTED","to_status":"PENDING_APPROVAL","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":null,"reason_code":null}
    ],
    "ledger_entry_ids":["LLE-2026-000001"],"decision_audit_ids":["DAU-2026-000001"]
  }
}
```

#### `GET /leave-requests`

- **Access:** requesters see their own requests; approvers see requests with a step assigned to them; `PROCESS_OWNER`, `ANALYST`, and `ADMIN` may filter across employees.
- **Query:** `page`, `page_size`, `sort` (`leave_request_id`, `start_date`, `submitted_at`, `status`), `employee_id`, `status`, `leave_policy_id`, `from`, `to`.
- **Request JSON:** none.
- **Response:** `200`, list envelope of request summaries.

```json
{
  "data":[{
    "leave_request_id":"LVE-2026-000001","employee_id":"EMP-000001","employee_name":"Avery Chen",
    "leave_policy_id":"LPO-001","policy_name":"Annual","start_date":"2026-11-23","end_date":"2026-11-28",
    "business_days":5,"status":"PENDING_APPROVAL","submitted_at":"2026-10-22T09:00:00Z",
    "medical_certificate_required":false,"risk_score":0,"reason":"Family visit",
    "approval_progress":{"approved":0,"required":2}
  }],
  "meta":{"page":1,"page_size":1,"total":1}
}
```

#### `GET /leave-requests/{id}`

- **Access:** requester owner, assigned approver, `PROCESS_OWNER`, `ANALYST`, or `ADMIN`.
- **Path:** `{id}` is a `leave_request_id`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope of the same complete detail object returned by `POST /leave-requests`.

```json
{
  "data":{
    "leave_request_id":"LVE-2026-000001","employee_id":"EMP-000001","employee_name":"Avery Chen",
    "leave_policy_id":"LPO-001","policy_name":"Annual","start_date":"2026-11-23","end_date":"2026-11-28",
    "business_days":5,"status":"PENDING_APPROVAL","submitted_at":"2026-10-22T09:00:00Z",
    "medical_certificate_required":false,"risk_score":0,"reason":"Family visit",
    "approval_steps":[
      {"approval_step_id":"APR-LVE-2026-000001-01","request_type":"LEAVE","request_id":"LVE-2026-000001",
       "step_number":1,"required_role":"MANAGER","approver_employee_id":"EMP-000002","approver_name":"Jordan Patel",
       "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27","decided_at":null,"reason_code":null},
      {"approval_step_id":"APR-LVE-2026-000001-02","request_type":"LEAVE","request_id":"LVE-2026-000001",
       "step_number":2,"required_role":"HR_PARTNER","approver_employee_id":"EMP-000003","approver_name":"Riley Morgan",
       "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27","decided_at":null,"reason_code":null}
    ],
    "events":[
      {"event_id":"LRE-2026-000001","sequence_number":1,"event_type":"CREATED","from_status":null,"to_status":"DRAFT","occurred_at":"2026-10-22T08:59:00Z","actor_employee_id":"EMP-000001","reason_code":null},
      {"event_id":"LRE-2026-000002","sequence_number":2,"event_type":"SUBMITTED","from_status":"DRAFT","to_status":"SUBMITTED","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":"EMP-000001","reason_code":null},
      {"event_id":"LRE-2026-000003","sequence_number":3,"event_type":"APPROVAL_STARTED","from_status":"SUBMITTED","to_status":"PENDING_APPROVAL","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":null,"reason_code":null}
    ],
    "ledger_entry_ids":["LLE-2026-000001"],"decision_audit_ids":["DAU-2026-000001"]
  }
}
```

#### `POST /leave-requests/{id}/cancel`

- **Access:** requester owner, `PROCESS_OWNER`, or `ADMIN`.
- **Path:** `{id}` is a `leave_request_id`.
- **Query:** none.
- **Allowed state:** only `PENDING_APPROVAL`; already terminal requests return `409 ILLEGAL_TRANSITION`.
- **Request JSON:**

```json
{"reason":"Plans changed"}
```

- **Response:** `200`, single envelope. Cancellation appends an event and releases the reservation; prior history is unchanged.

```json
{
  "data":{
    "leave_request_id":"LVE-2026-000001","status":"CANCELLED",
    "event_id":"LRE-2026-000004","released_ledger_entry_ids":["LLE-2026-000002"],
    "decision_audit_id":"DAU-2026-000002","cancelled_at":"2026-10-22T10:00:00Z"
  }
}
```

### Expense

#### `POST /expense-claims/preview`

- **Access:** `REQUESTER`; `PROCESS_OWNER` or `ADMIN` may set another `employee_id`.
- **Query:** none.
- **Request JSON:** `employee_id` defaults to the caller. `cost_center_id` may be `null` for previewing a hard-reject case. Each source amount is a positive decimal string.

```json
{
  "employee_id":"EMP-000001","merchant_name":"Northstar Cafe","merchant_country":"US",
  "expense_date":"2026-10-15","cost_center_id":"CC-0001",
  "lines":[{
    "line_number":1,"category":"MEALS","description":"Team lunch",
    "amount":"120.00","currency":"USD","receipt_present":true,
    "receipt_id":"RCT-2026-000001",
    "receipt_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "file_type":"PDF","size_kb":250.00
  }]
}
```

- **Response:** `200`, single envelope. `line_id` is `null` for a new unsaved preview and uses the persisted `EXPL-<claim-id>-NN` format when previewing an existing draft. `fx_rate` is the G2 rate. `pct_over` is `(amount_usd / limit_usd - 1) * 100` for a limit breach and `null` for other flags. Checks are ordered by E4; `exception_banner` is a concise user-facing exception summary or `null`.

```json
{
  "data":{
    "employee_id":"EMP-000001","merchant_name":"Northstar Cafe","merchant_country":"US",
    "expense_date":"2026-10-15","cost_center_id":"CC-0001",
    "lines":[{
      "line_id":null,"line_number":1,"amount":"120.00","currency":"USD",
      "amount_usd":"120.00","fx_rate":"1.00000","reporting_currency":"USD",
      "flags":[],"limit_usd":"150.00"
    }],
    "total_usd":"120.00","reporting_currency":"USD",
    "checks":[
      {"code":"DATE_WITHIN_EMPLOYMENT","ok":true,"message":"Expense date is within employment.","rule_id":"E3"},
      {"code":"NOT_FUTURE_DATED","ok":true,"message":"Expense date is not after AS_OF_DATE.","rule_id":"E4"},
      {"code":"COST_CENTER_PRESENT","ok":true,"message":"A cost center is assigned.","rule_id":"E4"},
      {"code":"NO_DUPLICATE_RECEIPT","ok":true,"message":"Receipt hash is not duplicated.","rule_id":"E4"},
      {"code":"NO_HARD_LIMIT_BREACH","ok":true,"message":"No line exceeds 150% of its policy limit.","rule_id":"E4"},
      {"code":"RECEIPT_METADATA_VALID","ok":true,"message":"Receipt metadata is complete.","rule_id":"E2"}
    ],
    "path":[
      {"level":1,"approver_type":"MANAGER","approver_id":"EMP-000002","approver_name":"Jordan Patel",
       "reason":"USD total is in the 50-to-under-1,000 band.","rule_ids":["E5","E7"]}
    ],
    "exception_banner":null
  }
}
```

#### `POST /expense-claims`

- **Access:** `REQUESTER`; `PROCESS_OWNER` or `ADMIN` may set another `employee_id`.
- **Query:** none. Optional header: `Idempotency-Key`.
- **Request JSON:** same fields as the preview request. `amount` is a decimal string; `size_kb` is a positive JSON number. Receipt metadata fields must all be present when `receipt_present` is true and all `null` otherwise.

```json
{
  "employee_id":"EMP-000001","merchant_name":"Northstar Cafe","merchant_country":"US",
  "expense_date":"2026-10-15","cost_center_id":"CC-0001",
  "lines":[{
    "line_number":1,"category":"MEALS","description":"Team lunch",
    "amount":"120.00","currency":"USD","receipt_present":true,
    "receipt_id":"RCT-2026-000001",
    "receipt_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "file_type":"PDF","size_kb":250.00
  }]
}
```

- **Response:** `201`, single envelope of the created claim detail. `total_usd` is the sum of rounded line amounts; submission creates the first approval steps and immutable event/audit records.

```json
{
  "data":{
    "expense_claim_id":"EXP-2026-000001","employee_id":"EMP-000001","employee_name":"Avery Chen",
    "merchant_name":"Northstar Cafe","merchant_country":"US","expense_date":"2026-10-15",
    "cost_center_id":"CC-0001","total_usd":"120.00","reporting_currency":"USD",
    "status":"PENDING_APPROVAL","submitted_at":"2026-10-22T09:00:00Z","risk_score":0,
    "lines":[{
      "expense_line_id":"EXPL-EXP-2026-000001-01","expense_claim_id":"EXP-2026-000001",
      "line_number":1,"category":"MEALS","expense_policy_id":"XPO-0011","description":"Team lunch",
      "amount":"120.00","currency":"USD","fx_rate_to_usd":"1.00000","amount_usd":"120.00",
      "receipt_present":true,"receipt_id":"RCT-2026-000001",
      "receipt_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "file_type":"PDF","size_kb":250.00
    }],
    "approval_steps":[{
      "approval_step_id":"APR-EXP-2026-000001-01","request_type":"EXPENSE","request_id":"EXP-2026-000001",
      "step_number":1,"required_role":"MANAGER","approver_employee_id":"EMP-000002","approver_name":"Jordan Patel",
      "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27","decided_at":null,"reason_code":null
    }],
    "events":[
      {"event_id":"ECE-2026-000001","sequence_number":1,"event_type":"CREATED","from_status":null,"to_status":"DRAFT","occurred_at":"2026-10-22T08:59:00Z","actor_employee_id":"EMP-000001","reason_code":null,"event_payload":{}},
      {"event_id":"ECE-2026-000002","sequence_number":2,"event_type":"SUBMITTED","from_status":"DRAFT","to_status":"SUBMITTED","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":"EMP-000001","reason_code":null,"event_payload":{}},
      {"event_id":"ECE-2026-000003","sequence_number":3,"event_type":"APPROVAL_STARTED","from_status":"SUBMITTED","to_status":"PENDING_APPROVAL","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":null,"reason_code":null,"event_payload":{}}
    ],
    "finding_codes":[],"decision_audit_ids":["DAU-2026-000002"],"reimbursement_ids":[]
  }
}
```

#### `GET /expense-claims`

- **Access:** requesters see their own claims; approvers see claims with a step assigned to them; `PROCESS_OWNER`, `ANALYST`, and `ADMIN` may filter across employees.
- **Query:** `page`, `page_size`, `sort` (`expense_claim_id`, `expense_date`, `total_usd`, `status`), `employee_id`, `status`, `cost_center_id`, `merchant_country`, `from`, `to`.
- **Request JSON:** none.
- **Response:** `200`, list envelope of claim summaries.

```json
{
  "data":[{
    "expense_claim_id":"EXP-2026-000001","employee_id":"EMP-000001","employee_name":"Avery Chen",
    "merchant_name":"Northstar Cafe","merchant_country":"US","expense_date":"2026-10-15",
    "cost_center_id":"CC-0001","total_usd":"120.00","reporting_currency":"USD",
    "status":"PENDING_APPROVAL","submitted_at":"2026-10-22T09:00:00Z","risk_score":0,
    "line_count":1,"approval_progress":{"approved":0,"required":1}
  }],
  "meta":{"page":1,"page_size":1,"total":1}
}
```

#### `GET /expense-claims/{id}`

- **Access:** requester owner, assigned approver, `PROCESS_OWNER`, `ANALYST`, or `ADMIN`.
- **Path:** `{id}` is an `expense_claim_id`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope containing the same complete detail object returned by `POST /expense-claims`.

```json
{
  "data":{
    "expense_claim_id":"EXP-2026-000001","employee_id":"EMP-000001","employee_name":"Avery Chen",
    "merchant_name":"Northstar Cafe","merchant_country":"US","expense_date":"2026-10-15",
    "cost_center_id":"CC-0001","total_usd":"120.00","reporting_currency":"USD",
    "status":"PENDING_APPROVAL","submitted_at":"2026-10-22T09:00:00Z","risk_score":0,
    "lines":[{
      "expense_line_id":"EXPL-EXP-2026-000001-01","expense_claim_id":"EXP-2026-000001",
      "line_number":1,"category":"MEALS","expense_policy_id":"XPO-0011","description":"Team lunch",
      "amount":"120.00","currency":"USD","fx_rate_to_usd":"1.00000","amount_usd":"120.00",
      "receipt_present":true,"receipt_id":"RCT-2026-000001",
      "receipt_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "file_type":"PDF","size_kb":250.00
    }],
    "approval_steps":[{
      "approval_step_id":"APR-EXP-2026-000001-01","request_type":"EXPENSE","request_id":"EXP-2026-000001",
      "step_number":1,"required_role":"MANAGER","approver_employee_id":"EMP-000002","approver_name":"Jordan Patel",
      "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27","decided_at":null,"reason_code":null
    }],
    "events":[
      {"event_id":"ECE-2026-000001","sequence_number":1,"event_type":"CREATED","from_status":null,"to_status":"DRAFT","occurred_at":"2026-10-22T08:59:00Z","actor_employee_id":"EMP-000001","reason_code":null,"event_payload":{}},
      {"event_id":"ECE-2026-000002","sequence_number":2,"event_type":"SUBMITTED","from_status":"DRAFT","to_status":"SUBMITTED","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":"EMP-000001","reason_code":null,"event_payload":{}},
      {"event_id":"ECE-2026-000003","sequence_number":3,"event_type":"APPROVAL_STARTED","from_status":"SUBMITTED","to_status":"PENDING_APPROVAL","occurred_at":"2026-10-22T09:00:00Z","actor_employee_id":null,"reason_code":null,"event_payload":{}}
    ],
    "finding_codes":[],"decision_audit_ids":["DAU-2026-000002"],"reimbursement_ids":[]
  }
}
```

### Approvals

#### `GET /approvals/inbox`

- **Access:** `APPROVER`; `PROCESS_OWNER` and `ADMIN` may inspect all pending steps.
- **Query:** `page`, `page_size`, `sort` (`due_date`, `assigned_at`, `step_number`), `status` (default `PENDING`), `request_type`, `due_before`, `employee_id` (process owner/admin only).
- **Request JSON:** none.
- **Response:** `200`, list envelope of actionable approval steps.

```json
{
  "data":[{
    "approval_step_id":"APR-EXP-2026-000001-01","request_type":"EXPENSE","request_id":"EXP-2026-000001",
    "employee_id":"EMP-000001","employee_name":"Avery Chen","step_number":1,
    "required_role":"MANAGER","approver_employee_id":"EMP-000002","approver_name":"Jordan Patel",
    "status":"PENDING","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27",
    "amount_usd":"120.00","currency":"USD","reason_code":null
  }],
  "meta":{"page":1,"page_size":1,"total":1}
}
```

#### `POST /approval-steps/{id}/decision`

- **Access:** assigned `APPROVER`, `PROCESS_OWNER`, or `ADMIN`. A user may never approve their own request.
- **Path:** `{id}` is an `approval_step_id`.
- **Query:** none.
- **Request JSON:** a rejection requires `reason`; `reason_code` must be a documented `ReasonCode` when supplied.

```json
{"decision":"APPROVED","reason":null,"reason_code":null}
```

- **Response:** `200`, single envelope. `next_step` is the next pending step or `null`. A non-final approval leaves the request `PENDING_APPROVAL`; final approval transitions it to `APPROVED`.

```json
{
  "data":{
    "approval_step":{
      "approval_step_id":"APR-EXP-2026-000001-01","request_type":"EXPENSE","request_id":"EXP-2026-000001",
      "step_number":1,"required_role":"MANAGER","approver_employee_id":"EMP-000002","approver_name":"Jordan Patel",
      "status":"APPROVED","assigned_at":"2026-10-22T09:00:00Z","due_date":"2026-10-27",
      "decided_at":"2026-10-22T10:00:00Z","reason_code":null
    },
    "request_status":"APPROVED","next_step":null,
    "event_id":"ECE-2026-000004","decision_audit_id":"DAU-2026-000003"
  }
}
```

### Reimbursements

#### `GET /reimbursements`

- **Access:** requesters see their own; `PROCESS_OWNER`, `ANALYST`, and `ADMIN` may filter across employees.
- **Query:** `page`, `page_size`, `sort` (`reimbursement_id`, `payment_date`, `status`), `employee_id`, `expense_claim_id`, `status`, `from`, `to`.
- **Request JSON:** none.
- **Response:** `200`, list envelope. Reimbursement `expense_claim_id` is intentionally not unique.

```json
{
  "data":[{
    "reimbursement_id":"RMB-2026-000001","expense_claim_id":"EXP-2026-000001",
    "employee_id":"EMP-000001","amount_home_currency":"120.00","home_currency":"USD",
    "amount_usd":"120.00","reporting_currency":"USD","payment_date":"2026-10-29",
    "status":"SCHEDULED","created_at":"2026-10-22T10:00:00Z","paid_at":null,
    "payment_reference":"PAY-2026-000001"
  }],
  "meta":{"page":1,"page_size":1,"total":1}
}
```

#### `GET /reimbursements/{id}`

- **Access:** requester owner, `PROCESS_OWNER`, `ANALYST`, or `ADMIN`.
- **Path:** `{id}` is a `reimbursement_id`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope containing the complete reimbursement record from the list representation.

```json
{
  "data":{
    "reimbursement_id":"RMB-2026-000001","expense_claim_id":"EXP-2026-000001",
    "employee_id":"EMP-000001","amount_home_currency":"120.00","home_currency":"USD",
    "amount_usd":"120.00","reporting_currency":"USD","payment_date":"2026-10-29",
    "status":"SCHEDULED","created_at":"2026-10-22T10:00:00Z","paid_at":null,
    "payment_reference":"PAY-2026-000001"
  }
}
```

### Audit

#### `POST /audit/run`

- **Access:** `ANALYST`, `PROCESS_OWNER`, or `ADMIN`.
- **Query:** none.
- **Request JSON:** omitted fields default to `scope: "ALL"` and the fixed evaluation date. Audit detectors use operational data only and never read ground truth.

```json
{"scope":"ALL","as_of_date":"2026-10-22"}
```

- **Response:** `202`, single envelope with deterministic results and references to newly appended records.

```json
{
  "data":{
    "scope":"ALL","as_of_date":"2026-10-22","status":"COMPLETED",
    "scanned_requests":1800,"findings_created":1,"findings_by_code":{"DUPLICATE_RECEIPT":1},
    "finding_ids":["AFN-2026-000001"],"decision_audit_ids":["DAU-2026-000004"]
  }
}
```

#### `GET /audit/findings`

- **Access:** `ANALYST`, `PROCESS_OWNER`, or `ADMIN`.
- **Query:** `page`, `page_size`, `sort` (`audit_finding_id`, `detected_at`, `severity`), `finding_code`, `severity`, `status` (`OPEN|RESOLVED|DISMISSED`), `request_type`, `request_id`, `from`, `to`.
- **Request JSON:** none.
- **Response:** `200`, list envelope. `status` is derived from the latest `AuditFindingEvent`; the stored finding row remains immutable.

```json
{
  "data":[{
    "audit_finding_id":"AFN-2026-000001","finding_code":"DUPLICATE_RECEIPT","severity":"ERROR",
    "status":"OPEN","expense_claim_id":"EXP-2026-000001","expense_line_id":"EXPL-EXP-2026-000001-01",
    "leave_request_id":null,"approval_step_id":null,"reimbursement_id":null,
    "details":{"receipt_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
    "detected_at":"2026-10-22T11:00:00Z"
  }],
  "meta":{"page":1,"page_size":1,"total":1}
}
```

#### `GET /audit/findings/{id}`

- **Access:** `ANALYST`, `PROCESS_OWNER`, or `ADMIN`.
- **Path:** `{id}` is an `audit_finding_id`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope with the finding and its append-only history.

```json
{
  "data":{
    "audit_finding_id":"AFN-2026-000001","finding_code":"DUPLICATE_RECEIPT","severity":"ERROR",
    "status":"OPEN","expense_claim_id":"EXP-2026-000001","expense_line_id":"EXPL-EXP-2026-000001-01",
    "leave_request_id":null,"approval_step_id":null,"reimbursement_id":null,
    "details":{"receipt_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
    "detected_at":"2026-10-22T11:00:00Z",
    "events":[]
  }
}
```

### Evaluation

#### `GET /evaluation/summary`

- **Access:** `ANALYST` or `ADMIN`; served by the evaluator service.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope. Rates are fractions in `[0,1]`; counts are integers.

```json
{
  "data":{
    "as_of_date":"2026-10-22","evaluated_decisions":1800,
    "decision_accuracy":{"correct":1710,"total":1800,"rate":0.9500},
    "approval_path_accuracy":{"correct":1656,"total":1800,"rate":0.9200},
    "anomaly_precision":{"true_positive":72,"false_positive":8,"rate":0.9000},
    "anomaly_recall":{"true_positive":72,"false_negative":8,"rate":0.9000},
    "reimbursement_eligibility_accuracy":{"correct":990,"total":1000,"rate":0.9900},
    "validation_pass_counts":{"passed":1792,"failed":8,"total":1800}
  }
}
```

#### `GET /evaluation/misses`

- **Access:** `ANALYST` or `ADMIN`; served by the evaluator service. This endpoint is the only API surface that returns ground-truth labels.
- **Query:** `page`, `page_size`, `sort` (`target_id`, `issue_type`), `issue_type`, `miss_type`, `target_type`.
- **Request JSON:** none.
- **Response:** `200`, list envelope of expected-vs-actual mismatches.

```json
{
  "data":[{
    "ground_truth_id":"GTA-2026-000001","target_type":"EXPENSE_LINE",
    "target_id":"EXPL-EXP-2026-000001-01","expense_claim_id":"EXP-2026-000001",
    "issue_type":"DUPLICATE_RECEIPT","expected_finding_code":"DUPLICATE_RECEIPT",
    "actual_finding_codes":[],"miss_type":"MISSED_ANOMALY",
    "expected_status":null,"actual_status":null,
    "expected_approval_path":[],"actual_approval_path":[]
  }],
  "meta":{"page":1,"page_size":1,"total":8}
}
```

### Metrics

#### `GET /metrics/overview`

- **Access:** `ANALYST`, `PROCESS_OWNER`, or `ADMIN`.
- **Query:** optional `as_of_date`, which must be `2026-10-22`.
- **Request JSON:** none.
- **Response:** `200`, single envelope. `auto_approval_rate`, `sla_breach_rate`, `multi_level_share`, `utilization_pct` are percentages on a 0–100 scale. `cycle_time_by_level` times are hours. Spend includes `APPROVED` and `REIMBURSED` claims dated in 2026; `anomalies_flagged` counts open operational findings, not ground-truth labels. `recent_activity` is the latest ten operational events ordered by timestamp and event ID.

```json
{
  "data":{
    "as_of_date":"2026-10-22","reporting_currency":"USD",
    "volumes_by_status":{
      "leave_requests":{"DRAFT":20,"SUBMITTED":0,"PENDING_APPROVAL":18,"APPROVED":620,"REJECTED":120,"CANCELLED":22},
      "expense_claims":{"DRAFT":25,"SUBMITTED":0,"PENDING_APPROVAL":30,"APPROVED":700,"REJECTED":180,"CANCELLED":20,"REIMBURSED":45},
      "approval_steps":{"PENDING":33,"APPROVED":2450,"REJECTED":142},
      "reimbursements":{"SCHEDULED":12,"PAID":33}
    },
    "auto_approval_rate":12.00,
    "rejection_reasons":[{"code":"INSUFFICIENT_BALANCE","count":42,"share_pct":14.00}],
    "cycle_time_by_level":[
      {"level":1,"avg_hours":11.20,"p90_hours":30.50},
      {"level":2,"avg_hours":18.75,"p90_hours":46.00}
    ],
    "sla_breach_rate":4.25,"multi_level_share":41.00,
    "spend_by_cost_center":[{
      "cost_center_id":"CC-0001","name":"North America Operations",
      "spent_usd":"182500.00","budget_usd":"250000.00","utilization_pct":73.00,"currency":"USD"
    }],
    "spend_by_category":[{"category":"MEALS","spent_usd":"12500.00","claim_count":210,"currency":"USD"}],
    "spend_by_country":[{"country":"US","spent_usd":"220000.00","claim_count":310,"currency":"USD"}],
    "leave_utilization":[{
      "leave_policy_id":"LPO-001","name":"Annual","opening_days":1800.000000,
      "accrued_days":6000.000000,"used_days":1420.000000,"pending_days":90.000000,
      "available_days":6290.000000,"utilization_pct":18.21
    }],
    "reimbursements":{"paid_usd":"42000.00","scheduled_usd":"15800.00","currency":"USD","paid_count":33,"scheduled_count":12},
    "anomalies_flagged":72,
    "recent_activity":[{
      "event_id":"ECE-2026-000003","request_type":"EXPENSE","request_id":"EXP-2026-000001",
      "event_type":"APPROVAL_STARTED","from_status":"SUBMITTED","to_status":"PENDING_APPROVAL",
      "occurred_at":"2026-10-22T09:00:00Z","employee_id":"EMP-000001",
      "employee_name":"Avery Chen","summary":"Expense claim submitted for approval."
    }]
  }
}
```

### Dataset

#### `GET /dataset/manifest`

- **Access:** `ANALYST`, `PROCESS_OWNER`, or `ADMIN`.
- **Query / request JSON:** none.
- **Response:** `200`, single envelope. Checksums are lowercase SHA-256 hex. Ground-truth file metadata is listed separately and its contents are never returned by this endpoint.

```json
{
  "data":{
    "generator_name":"RouteIQ synthetic generator","generator_version":"1.0.0",
    "seed":20261022,"as_of_date":"2026-10-22","reporting_currency":"USD",
    "row_counts":{
      "employee":400,"leave_policy":6,"leave_balance":2400,"leave_request":800,
      "expense_policy":50,"expense_claim":1000,"expense_line":5500,
      "cost_center":20,"approval_rule":24,"holiday":40,"audit_finding":80,
      "ground_truth_anomaly":80,"ground_truth_decision":1800
    },
    "files":[
      {"path":"data/employees.csv","format":"csv","row_count":400,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","contains_ground_truth":false},
      {"path":"data/ground_truth.json","format":"json","row_count":80,"sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","contains_ground_truth":true}
    ],
    "reference_fixtures":{"countries":["IN","US","GB","DE","SG"],"holiday_count_per_country":8,"expense_policy_count":50},
    "validation":{"status":"PASSED","checks_passed":12,"checks_failed":0}
  }
}
```

## 3. Preview and workflow invariants

- Preview endpoints do not write rows, reserve balances, assign persistent IDs, or create events/findings/audits.
- A create endpoint reruns the same pure validation/routing engine used by preview. Client-supplied preview results are never trusted.
- Leave submission checks follow L4 order. A successful request reserves its balance. Approval releases the reservation and debits used leave; rejection/cancellation releases it.
- Expense hard rejects under E4 remain `DRAFT`; successful expense submission stores the total from rounded line values and creates the E5/E6 path.
- Approval decisions are strictly sequential. Deciding a later step before the current pending step returns `OUT_OF_ORDER`. A caller cannot decide their own request; that returns `SELF_APPROVAL`.
- Only a final approved expense claim can be reimbursed, and E9 eligibility is rechecked at reimbursement creation. Reimbursement records remain non-unique by claim to permit labeled duplicate anomalies.
- Audit results use operational records only. Ground-truth-based comparison is confined to the evaluator service and `/evaluation/*`.

## 4. Enums

The following are closed sets; requests using another value return `VALIDATION_FAILED`.

| Enum | Values |
|---|---|
| `LeaveRequestStatus` | `DRAFT`, `SUBMITTED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `CANCELLED` |
| `ExpenseClaimStatus` | `DRAFT`, `SUBMITTED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `CANCELLED`, `REIMBURSED` |
| `ReimbursementStatus` | `SCHEDULED`, `PAID` |
| `FunctionalRole` | `NONE`, `DEPT_HEAD`, `HR_PARTNER`, `FINANCE_CONTROLLER`, `CFO`, `COMPLIANCE_OFFICER` |
| `SystemRole` | `REQUESTER`, `APPROVER`, `PROCESS_OWNER`, `ANALYST`, `ADMIN` |
| `ApprovalRole` | `MANAGER`, `DEPT_HEAD`, `HR_PARTNER`, `FINANCE_CONTROLLER`, `CFO`, `COMPLIANCE_OFFICER`, `SYSTEM` |
| `RequestType` | `LEAVE`, `EXPENSE` |
| `ExpenseCategory` | `MEALS`, `LODGING`, `AIRFARE`, `GROUND_TRANSPORT`, `SOFTWARE`, `OFFICE_SUPPLIES`, `TRAINING`, `CLIENT_ENTERTAINMENT`, `GIFTS`, `COMMUNICATION` |
| `CountryCode` | `IN`, `US`, `GB`, `DE`, `SG` |
| `CurrencyCode` | `INR`, `USD`, `GBP`, `EUR`, `SGD` |
| `ReceiptFileType` | `PDF`, `JPG`, `JPEG`, `PNG`, `HEIC` |
| `ApprovalStepStatus` | `PENDING`, `APPROVED`, `REJECTED` |
| `LeaveLedgerEntryType` | `OPENING`, `ACCRUAL`, `RESERVE`, `RELEASE`, `DEBIT`, `ADJUSTMENT`, `REVERSAL` |
| `LeaveLedgerEffectBucket` | `AVAILABLE`, `RESERVED`, `USED` |
| `ExcludedDateReason` | `WEEKEND`, `HOLIDAY` |
| `LeavePreviewCheckCode` | `DATE_ORDER`, `BUSINESS_DAYS_POSITIVE`, `EMPLOYEE_ACTIVE`, `TENURE_ELIGIBLE`, `MAX_CONSECUTIVE`, `NO_OVERLAP`, `BALANCE_SUFFICIENT` |
| `ExpensePreviewCheckCode` | `DATE_WITHIN_EMPLOYMENT`, `NOT_FUTURE_DATED`, `COST_CENTER_PRESENT`, `NO_DUPLICATE_RECEIPT`, `NO_HARD_LIMIT_BREACH`, `RECEIPT_METADATA_VALID` |
| `LeaveRequestEventType` | `CREATED`, `SUBMISSION_ATTEMPT`, `SUBMITTED`, `APPROVAL_STARTED`, `APPROVAL_DECIDED`, `CANCELLED` |
| `ExpenseClaimEventType` | `CREATED`, `SUBMISSION_ATTEMPT`, `SUBMITTED`, `APPROVAL_STARTED`, `APPROVAL_DECIDED`, `CANCELLED`, `REIMBURSEMENT_CREATED`, `REIMBURSEMENT_PAID` |
| `AuditFindingCode` | `INVALID_DATE_RANGE`, `ZERO_BUSINESS_DAYS`, `EMPLOYEE_NOT_ACTIVE`, `TENURE_INELIGIBLE`, `MAX_CONSECUTIVE_DAYS`, `OVERLAP`, `INSUFFICIENT_BALANCE`, `POLICY_LIMIT_BREACH`, `MISSING_RECEIPT`, `DUPLICATE_RECEIPT`, `MISSING_COST_CENTER`, `DATE_OUTSIDE_EMPLOYMENT`, `FUTURE_EXPENSE_DATE`, `SPLIT_CLAIM`, `SELF_APPROVAL_PREVENTED`, `UNRESOLVED_APPROVER`, `DUPLICATE_REIMBURSEMENT` |
| `IssueType` | `NEGATIVE_LEAVE_BALANCE`, `OVERLAPPING_APPROVED_LEAVE`, `EXPENSE_OUTSIDE_EMPLOYMENT`, `FUTURE_EXPENSE_DATE`, `SPLIT_CLAIM`, `MISSING_COST_CENTER`, `SELF_APPROVAL`, `DUPLICATE_REIMBURSEMENT`, `MISSING_RECEIPT`, `DUPLICATE_RECEIPT`, `POLICY_LIMIT_BREACH`, `INSUFFICIENT_BALANCE`, `ZERO_BUSINESS_DAY_SPAN` |
| `Severity` | `INFO`, `WARNING`, `ERROR` |
| `FindingStatus` | `OPEN`, `RESOLVED`, `DISMISSED` |
| `ReasonCode` | `INVALID_DATE_RANGE`, `ZERO_BUSINESS_DAYS`, `EMPLOYEE_NOT_ACTIVE`, `TENURE_INELIGIBLE`, `MAX_CONSECUTIVE_DAYS`, `OVERLAP`, `INSUFFICIENT_BALANCE`, `LEAVE_UNPAID`, `LEAVE_DAYS_1_3`, `LEAVE_DAYS_4_10`, `LEAVE_DAYS_GT_10`, `PARENTAL_LEAVE`, `EXPENSE_LT_50_AUTO`, `EXPENSE_LT_50_FLAGGED`, `EXPENSE_50_1000`, `EXPENSE_1000_5000`, `EXPENSE_5000_20000`, `EXPENSE_GTE_20000`, `AIRFARE_INTERNATIONAL`, `CLIENT_ENTERTAINMENT_GT_250`, `GIFT_GT_250`, `POLICY_LIMIT_BREACH`, `MISSING_RECEIPT`, `DUPLICATE_RECEIPT`, `MISSING_COST_CENTER`, `DATE_OUTSIDE_EMPLOYMENT`, `FUTURE_EXPENSE_DATE`, `SPLIT_CLAIM`, `SELF_APPROVAL_PREVENTED`, `UNRESOLVED_APPROVER`, `CEO_MANAGER_FALLBACK`, `DUPLICATE_REIMBURSEMENT` |
| `EvaluationMissType` | `MISSED_ANOMALY`, `FALSE_POSITIVE`, `DECISION_MISMATCH`, `PATH_MISMATCH`, `REIMBURSEMENT_MISMATCH` |
| `EvaluationTargetType` | `LEAVE_REQUEST`, `LEAVE_BALANCE`, `EXPENSE_CLAIM`, `EXPENSE_LINE`, `APPROVAL_STEP`, `REIMBURSEMENT` |
| `ApiErrorCode` | `SELF_APPROVAL`, `OUT_OF_ORDER`, `ILLEGAL_TRANSITION`, `INSUFFICIENT_BALANCE`, `VALIDATION_FAILED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT` |
