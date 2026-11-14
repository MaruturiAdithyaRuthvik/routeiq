import type { ReactNode } from "react"
import {
    ArrowDownRight,
    ArrowRight,
    ArrowUpRight,
    CircleCheck,
    Clock3,
    ShieldAlert,
} from "lucide-react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { BlurFade } from "@/components/ui/blur-fade"
import { NumberTicker } from "@/components/ui/number-ticker"
import { Ring, StatusPill } from "@/components/ui/primitives"
import {
    FlowLoading,
    FlowNotice,
    FlowPageIntro,
    formatUsd,
} from "@/components/flow-primitives"
import {
    type GetApprovalsInboxResponse,
    type GetAuditFindingsResponse,
    type GetEmployeeLeaveBalancesResponse,
    type GetEvaluationSummaryResponse,
    type GetExpenseClaimsResponse,
    type GetLeaveRequestsResponse,
    type GetMetricsOverviewResponse,
    SystemRole,
} from "@/api/types"
import { useApiQuery } from "@/hooks/use-api"
import { useAuth } from "@/providers/auth-provider"
import "../styles/flow-pages.css"

const requestPage = { page: 1, page_size: 100 }

function MiniSparkline({ values, label }: { values: number[]; label: string }) {
    const points = values
        .map((value, index) => {
            const x = (index / Math.max(values.length - 1, 1)) * 100
            const y = 31 - value * 27
            return `${x},${y}`
        })
        .join(" ")
    return (
        <svg
            className="flow-sparkline"
            viewBox="0 0 100 34"
            role="img"
            aria-label={label}
        >
            <polyline points={points} fill="none" />
        </svg>
    )
}

function KpiCard({
    label,
    value,
    suffix,
    prefix,
    note,
    visual,
    decimalPlaces = 0,
    index = 0,
}: {
    label: string
    value: number
    suffix?: string
    prefix?: string
    note: string
    visual: ReactNode
    decimalPlaces?: number
    index?: number
}) {
    return (
        <BlurFade inView delay={index * 0.045} duration={0.55}>
            <article className="flow-card flow-kpi-card">
                <div className="flow-kpi-top">
                    <p>{label}</p>
                    {visual}
                </div>
                <div className="flow-kpi-value">
                    {prefix}
                    <NumberTicker
                        value={value}
                        decimalPlaces={decimalPlaces}
                        className="flow-kpi-number"
                        aria-label={`${label}: ${prefix ?? ""}${value}${suffix ?? ""}`}
                    />
                    {suffix && (
                        <span className="flow-kpi-suffix">{suffix}</span>
                    )}
                </div>
                <p className="flow-kpi-note">{note}</p>
            </article>
        </BlurFade>
    )
}

function SectionHeading({
    eyebrow,
    title,
    link,
}: {
    eyebrow: string
    title: string
    link?: { href: string; label: string }
}) {
    return (
        <div className="flow-section-heading">
            <div>
                <p className="flow-eyebrow">{eyebrow}</p>
                <h2>{title}</h2>
            </div>
            {link && (
                <Link className="flow-link" to={link.href}>
                    {link.label} <ArrowRight size={15} aria-hidden="true" />
                </Link>
            )}
        </div>
    )
}

export function OverviewPage() {
    const { persona } = useAuth()
    const role = persona?.system_role
    const isRequester = role === SystemRole.REQUESTER
    const isApprover = role === SystemRole.APPROVER
    const isOperator =
        role === SystemRole.PROCESS_OWNER ||
        role === SystemRole.ANALYST ||
        role === SystemRole.ADMIN
    const canEvaluate = role === SystemRole.ANALYST || role === SystemRole.ADMIN

    const metrics = useApiQuery<GetMetricsOverviewResponse>(
        "/metrics/overview",
        undefined,
        isOperator,
    )
    const balances = useApiQuery<GetEmployeeLeaveBalancesResponse>(
        `/employees/${persona?.employee_id ?? ""}/leave-balances`,
        requestPage,
        isRequester && Boolean(persona),
    )
    const leaveRequests = useApiQuery<GetLeaveRequestsResponse>(
        "/leave-requests",
        { ...requestPage, employee_id: persona?.employee_id },
        isRequester && Boolean(persona),
    )
    const expenseClaims = useApiQuery<GetExpenseClaimsResponse>(
        "/expense-claims",
        { ...requestPage, employee_id: persona?.employee_id },
        isRequester && Boolean(persona),
    )
    const inbox = useApiQuery<GetApprovalsInboxResponse>(
        "/approvals/inbox",
        { ...requestPage, status: "PENDING" },
        isApprover,
    )
    const evaluation = useApiQuery<GetEvaluationSummaryResponse>(
        "/evaluation/summary",
        undefined,
        canEvaluate,
    )
    const findings = useApiQuery<GetAuditFindingsResponse>(
        "/audit/findings",
        { ...requestPage, status: "OPEN" },
        isOperator,
    )

    const operatorData = metrics.data?.data
    const leaveData = balances.data?.data ?? []
    const ownLeave = leaveRequests.data?.data ?? []
    const ownExpenses = expenseClaims.data?.data ?? []
    const pendingInbox = inbox.data?.data ?? []

    const pageLoading =
        (isOperator && (metrics.isLoading || findings.isLoading)) ||
        (isRequester &&
            (balances.isLoading ||
                leaveRequests.isLoading ||
                expenseClaims.isLoading)) ||
        (isApprover && inbox.isLoading) ||
        (canEvaluate && evaluation.isLoading)

    const pageError = isOperator
        ? (metrics.error ?? findings.error)
        : isRequester
          ? (balances.error ?? leaveRequests.error ?? expenseClaims.error)
          : isApprover
            ? inbox.error
            : canEvaluate
              ? evaluation.error
              : null

    const leaveAvailable = leaveData.reduce(
        (total, balance) => total + balance.available_days,
        0,
    )
    const openOwnRequests = [...ownLeave, ...ownExpenses].filter((request) =>
        ["SUBMITTED", "PENDING_APPROVAL"].includes(request.status),
    ).length
    const cycleHours = operatorData?.cycle_time_by_level.length
        ? operatorData.cycle_time_by_level.reduce(
              (total, level) => total + level.avg_hours,
              0,
          ) / operatorData.cycle_time_by_level.length
        : 0
    const openOperatorRequests = operatorData
        ? operatorData.volumes_by_status.leave_requests.PENDING_APPROVAL +
          operatorData.volumes_by_status.expense_claims.PENDING_APPROVAL
        : 0
    const totalSpent =
        operatorData?.spend_by_cost_center.reduce(
            (total, center) => total + Number(center.spent_usd),
            0,
        ) ?? 0
    const totalBudget =
        operatorData?.spend_by_cost_center.reduce(
            (total, center) => total + Number(center.budget_usd),
            0,
        ) ?? 0

    const retry = () => {
        if (isOperator) {
            void metrics.refetch()
            void findings.refetch()
        }
        if (isRequester) {
            void balances.refetch()
            void leaveRequests.refetch()
            void expenseClaims.refetch()
        }
        if (isApprover) void inbox.refetch()
        if (canEvaluate) void evaluation.refetch()
    }

    if (pageLoading) return <FlowLoading rows={6} />
    if (pageError) {
        return (
            <div className="flow-page-stack overview-page">
                <FlowNotice
                    kind="error"
                    title="Your overview could not load."
                    message={pageError.message}
                    action={
                        <button className="flow-inline-action" onClick={retry}>
                            Try again
                        </button>
                    }
                />
            </div>
        )
    }

    return (
        <div className="flow-page-stack overview-page">
            <FlowPageIntro
                eyebrow={`${persona?.display_name ?? "RouteIQ"} · ${role?.replaceAll("_", " ").toLowerCase() ?? "workspace"}`}
                title="Every request. Routed right."
                description="The right decisions, with a little more clarity at every step."
                gradient
                centered
                action={
                    <div className="flow-intro-actions">
                        {isRequester ? (
                            <>
                                <Link
                                    className="flow-button-primary"
                                    to="/leave/new"
                                >
                                    New leave request
                                </Link>
                                <Link className="flow-link" to="/expenses/new">
                                    Start an expense <ArrowRight size={15} />
                                </Link>
                            </>
                        ) : isApprover ? (
                            <>
                                <Link
                                    className="flow-button-primary"
                                    to="/approvals/inbox"
                                >
                                    Open inbox
                                </Link>
                                <Link
                                    className="flow-link"
                                    to="/approval-rules"
                                >
                                    How routing works <ArrowRight size={15} />
                                </Link>
                            </>
                        ) : (
                            <>
                                <Link
                                    className="flow-button-primary"
                                    to="/metrics/overview"
                                >
                                    Explore metrics
                                </Link>
                                <Link
                                    className="flow-link"
                                    to={
                                        role === SystemRole.ANALYST
                                            ? "/evaluation/summary"
                                            : "/audit/findings"
                                    }
                                >
                                    {role === SystemRole.ANALYST
                                        ? "Explore Evaluation"
                                        : "Review findings"}{" "}
                                    <ArrowRight size={15} />
                                </Link>
                            </>
                        )}
                    </div>
                }
            />

            {isOperator && operatorData && (
                <section
                    className="flow-section"
                    aria-label="Overview KPIs"
                >
                    <SectionHeading
                        eyebrow="At a glance"
                        title="A healthier flow, by the numbers."
                    />
                    <div className="flow-kpi-grid">
                        <KpiCard
                            label="Open requests"
                            value={openOperatorRequests}
                            note="Waiting for a decision"
                            visual={
                                <MiniSparkline
                                    values={[
                                        0.32, 0.42, 0.38, 0.62, 0.56, 0.76, 0.7,
                                    ]}
                                    label="Open requests trend"
                                />
                            }
                            index={0}
                        />
                        <KpiCard
                            label="Auto-approval rate"
                            value={operatorData.auto_approval_rate}
                            suffix="%"
                            note="Resolved without a handoff"
                            decimalPlaces={1}
                            visual={
                                <MiniSparkline
                                    values={[
                                        0.28, 0.42, 0.46, 0.57, 0.62, 0.72, 0.8,
                                    ]}
                                    label="Auto-approval rate trend"
                                />
                            }
                            index={1}
                        />
                        <KpiCard
                            label="Avg. cycle time"
                            value={cycleHours}
                            suffix=" hrs"
                            note="Across approval levels"
                            decimalPlaces={1}
                            visual={
                                <MiniSparkline
                                    values={[
                                        0.8, 0.72, 0.63, 0.6, 0.48, 0.52, 0.34,
                                    ]}
                                    label="Cycle time trend"
                                />
                            }
                            index={2}
                        />
                        <KpiCard
                            label="SLA breach rate"
                            value={operatorData.sla_breach_rate}
                            suffix="%"
                            note="Requests beyond their due date"
                            decimalPlaces={1}
                            visual={
                                <MiniSparkline
                                    values={[
                                        0.7, 0.61, 0.66, 0.5, 0.45, 0.38, 0.3,
                                    ]}
                                    label="SLA breach rate trend"
                                />
                            }
                            index={3}
                        />
                        <KpiCard
                            label="Spend vs. budget"
                            value={totalSpent}
                            prefix="$"
                            suffix={` / ${new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(totalBudget)}`}
                            note={`${totalBudget > 0 ? Math.round((totalSpent / totalBudget) * 100) : 0}% of allocated budget`}
                            visual={
                                <Ring
                                    value={
                                        totalBudget > 0
                                            ? (totalSpent / totalBudget) * 100
                                            : 0
                                    }
                                    label="Budget used"
                                />
                            }
                            index={4}
                        />
                        <KpiCard
                            label="Anomalies flagged"
                            value={operatorData.anomalies_flagged}
                            note={`${findings.data?.meta.total ?? 0} open for review`}
                            visual={
                                <MiniSparkline
                                    values={[
                                        0.35, 0.52, 0.4, 0.7, 0.59, 0.76, 0.9,
                                    ]}
                                    label="Anomalies flagged trend"
                                />
                            }
                            index={5}
                        />
                    </div>
                </section>
            )}

            {isRequester && (
                <section className="flow-section">
                    <SectionHeading
                        eyebrow="Your workspace"
                        title="A clear view of what is yours."
                        link={{
                            href: "/leave-requests",
                            label: "All requests",
                        }}
                    />
                    <div className="flow-requester-grid">
                        <article className="flow-card flow-balance-card">
                            <div>
                                <p className="flow-card-eyebrow">
                                    Available leave
                                </p>
                                <h3>
                                    <NumberTicker
                                        value={leaveAvailable}
                                        className="flow-kpi-number"
                                    />{" "}
                                    <span>days</span>
                                </h3>
                                <p className="flow-card-caption">
                                    Across your active leave policies
                                </p>
                            </div>
                            <Ring
                                value={Math.min(100, leaveAvailable * 4)}
                                size={76}
                                label="Leave available"
                            />
                            <Link className="flow-link" to="/leave/new">
                                Plan time away <ArrowRight size={15} />
                            </Link>
                        </article>
                        <article className="flow-card flow-personal-stats">
                            <div>
                                <p className="flow-card-eyebrow">In progress</p>
                                <strong>
                                    <NumberTicker
                                        value={openOwnRequests}
                                        className="flow-kpi-number"
                                    />
                                </strong>
                                <span>requests</span>
                            </div>
                            <div>
                                <p className="flow-card-eyebrow">
                                    Expense claims
                                </p>
                                <strong>
                                    <NumberTicker
                                        value={ownExpenses.length}
                                        className="flow-kpi-number"
                                    />
                                </strong>
                                <span>submitted this year</span>
                            </div>
                            <Link className="flow-link" to="/expenses/new">
                                Start a claim <ArrowRight size={15} />
                            </Link>
                        </article>
                        <article className="flow-card flow-own-requests">
                            <div className="flow-card-heading">
                                <div>
                                    <p className="flow-card-eyebrow">
                                        Recently updated
                                    </p>
                                    <h3>Your requests</h3>
                                </div>
                                <Link
                                    className="flow-icon-link"
                                    to="/leave-requests"
                                    aria-label="View all requests"
                                >
                                    <ArrowRight size={18} />
                                </Link>
                            </div>
                            {ownLeave.length === 0 &&
                            ownExpenses.length === 0 ? (
                                <p className="flow-muted-copy">
                                    Your first request will appear here when you
                                    submit it.
                                </p>
                            ) : (
                                <ul className="flow-request-list">
                                    {[
                                        ...ownLeave.map((item) => ({
                                            id: item.leave_request_id,
                                            title: `${item.policy_name} leave`,
                                            date: item.start_date,
                                            status: item.status,
                                        })),
                                        ...ownExpenses.map((item) => ({
                                            id: item.expense_claim_id,
                                            title: item.merchant_name,
                                            date: item.expense_date,
                                            status: item.status,
                                        })),
                                    ]
                                        .sort((a, b) =>
                                            b.date.localeCompare(a.date),
                                        )
                                        .slice(0, 4)
                                        .map((item) => (
                                            <li key={item.id}>
                                                <div>
                                                    <strong>
                                                        {item.title}
                                                    </strong>
                                                    <time dateTime={item.date}>
                                                        {new Date(
                                                            `${item.date}T00:00:00`,
                                                        ).toLocaleDateString(
                                                            "en-US",
                                                            {
                                                                month: "short",
                                                                day: "numeric",
                                                            },
                                                        )}
                                                    </time>
                                                </div>
                                                <StatusPill
                                                    status={item.status}
                                                />
                                            </li>
                                        ))}
                                </ul>
                            )}
                        </article>
                    </div>
                </section>
            )}

            {isApprover && (
                <section className="flow-section">
                    <SectionHeading
                        eyebrow="Your next decisions"
                        title="A little context goes a long way."
                        link={{
                            href: "/approvals/inbox",
                            label: "Open approval inbox",
                        }}
                    />
                    <div className="flow-card flow-inbox-card">
                        <div className="flow-inbox-summary">
                            <div className="flow-inbox-count">
                                <NumberTicker
                                    value={pendingInbox.length}
                                    className="flow-kpi-number"
                                />
                                <span>waiting for your review</span>
                            </div>
                            <div className="flow-inbox-icon">
                                <Clock3 size={22} />
                            </div>
                        </div>
                        {pendingInbox.length === 0 ? (
                            <p className="flow-muted-copy">
                                Your inbox is clear. New approvals will appear
                                here.
                            </p>
                        ) : (
                            <ul className="flow-request-list">
                                {pendingInbox.slice(0, 4).map((item) => (
                                    <li key={item.approval_step_id}>
                                        <div>
                                            <strong>
                                                {item.employee_name}
                                            </strong>
                                            <time dateTime={item.due_date}>
                                                {item.request_type === "LEAVE"
                                                    ? "Leave request"
                                                    : formatUsd(
                                                          item.amount_usd,
                                                      )}{" "}
                                                · due{" "}
                                                {new Date(
                                                    `${item.due_date}T00:00:00`,
                                                ).toLocaleDateString("en-US", {
                                                    month: "short",
                                                    day: "numeric",
                                                })}
                                            </time>
                                        </div>
                                        <StatusPill status={item.status} />
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </section>
            )}

            {isOperator && operatorData && (
                <section className="flow-section">
                    <SectionHeading
                        eyebrow="Operational health"
                        title="The details behind the decisions."
                        link={{
                            href: "/metrics/overview",
                            label: "All metrics",
                        }}
                    />
                    <div className="flow-operations-grid">
                        <article className="flow-card flow-spend-card">
                            <div className="flow-card-heading">
                                <div>
                                    <p className="flow-card-eyebrow">
                                        Budget utilization
                                    </p>
                                    <h3>Spend by cost center</h3>
                                </div>
                                <ArrowUpRight size={18} aria-hidden="true" />
                            </div>
                            {operatorData.spend_by_cost_center
                                .slice(0, 5)
                                .map((center, index) => {
                                    const spendPct =
                                        center.budget_usd === "0"
                                            ? 0
                                            : Math.min(
                                                  100,
                                                  (Number(center.spent_usd) /
                                                      Number(
                                                          center.budget_usd,
                                                      )) *
                                                      100,
                                              )
                                    return (
                                        <div
                                            className="flow-spend-row"
                                            key={center.cost_center_id}
                                        >
                                            <div className="flow-spend-label">
                                                <strong>{center.name}</strong>
                                                <span>
                                                    {formatUsd(
                                                        center.spent_usd,
                                                    )}{" "}
                                                    <i>
                                                        /{" "}
                                                        {formatUsd(
                                                            center.budget_usd,
                                                        )}
                                                    </i>
                                                </span>
                                            </div>
                                            <div
                                                className="flow-spend-track"
                                                aria-label={`${center.name}: ${Math.round(spendPct)}% utilized`}
                                            >
                                                <motion.div
                                                    className={`flow-spend-fill${spendPct >= 90 ? "flow-spend-warning" : ""}`}
                                                    initial={{ width: 0 }}
                                                    whileInView={{
                                                        width: `${spendPct}%`,
                                                    }}
                                                    viewport={{ once: true }}
                                                    transition={{
                                                        duration: 0.75,
                                                        delay: index * 0.06,
                                                        ease: [
                                                            0.28, 0.11, 0.32, 1,
                                                        ],
                                                    }}
                                                />
                                                <span
                                                    className="flow-spend-marker"
                                                    style={{ left: "80%" }}
                                                />
                                            </div>
                                            <span className="flow-spend-pct">
                                                {Math.round(
                                                    center.utilization_pct,
                                                )}
                                                %
                                            </span>
                                        </div>
                                    )
                                })}
                        </article>
                        <article className="flow-card flow-leave-card">
                            <div className="flow-card-heading">
                                <div>
                                    <p className="flow-card-eyebrow">
                                        People & policy
                                    </p>
                                    <h3>Leave utilization</h3>
                                </div>
                                <CircleCheck size={18} aria-hidden="true" />
                            </div>
                            {operatorData.leave_utilization
                                .slice(0, 3)
                                .map((policy) => (
                                    <div
                                        className="flow-leave-row"
                                        key={policy.leave_policy_id}
                                    >
                                        <Ring
                                            value={policy.utilization_pct}
                                            size={48}
                                            stroke={4}
                                            label={`${policy.name} leave utilization`}
                                        />
                                        <div>
                                            <strong>{policy.name}</strong>
                                            <span>
                                                {policy.available_days} days
                                                available · {policy.used_days}{" "}
                                                used
                                            </span>
                                        </div>
                                    </div>
                                ))}
                        </article>
                        <article className="flow-card flow-funnel-card">
                            <div className="flow-card-heading">
                                <div>
                                    <p className="flow-card-eyebrow">
                                        Requests at a glance
                                    </p>
                                    <h3>Approval funnel</h3>
                                </div>
                                <ArrowDownRight size={18} aria-hidden="true" />
                            </div>
                            {[
                                [
                                    "Submitted",
                                    operatorData.volumes_by_status
                                        .leave_requests.SUBMITTED +
                                        operatorData.volumes_by_status
                                            .expense_claims.SUBMITTED,
                                ],
                                ["In review", openOperatorRequests],
                                [
                                    "Approved",
                                    operatorData.volumes_by_status
                                        .leave_requests.APPROVED +
                                        operatorData.volumes_by_status
                                            .expense_claims.APPROVED,
                                ],
                            ].map(([label, count], index) => (
                                <div className="flow-funnel-row" key={label}>
                                    <div className="flow-funnel-label">
                                        <span>{label}</span>
                                        <strong>
                                            <NumberTicker
                                                value={Number(count)}
                                                className="flow-kpi-number"
                                            />
                                        </strong>
                                    </div>
                                    <div className="flow-funnel-track">
                                        <motion.span
                                            initial={{ width: 0 }}
                                            whileInView={{
                                                width: `${Math.min(100, (Number(count) / Math.max(openOperatorRequests, 1)) * 100)}%`,
                                            }}
                                            viewport={{ once: true }}
                                            transition={{
                                                duration: 0.7,
                                                delay: index * 0.08,
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </article>
                    </div>
                </section>
            )}

            {isOperator && operatorData && (
                <section className="flow-section">
                    <SectionHeading
                        eyebrow="Recent activity"
                        title="A steady stream of progress."
                        link={{
                            href: "/audit/findings",
                            label: "Review findings",
                        }}
                    />
                    <div className="flow-card flow-activity-card">
                        {operatorData.recent_activity.length === 0 ? (
                            <p className="flow-muted-copy">
                                Recent decisions will appear here as work moves
                                through RouteIQ.
                            </p>
                        ) : (
                            <ul className="flow-activity-list">
                                {operatorData.recent_activity
                                    .slice(0, 5)
                                    .map((activity, index) => (
                                        <motion.li
                                            key={activity.event_id}
                                            initial={{ opacity: 0, y: 8 }}
                                            whileInView={{ opacity: 1, y: 0 }}
                                            viewport={{ once: true }}
                                            transition={{
                                                duration: 0.35,
                                                delay: index * 0.06,
                                            }}
                                        >
                                            <span className="flow-activity-mark">
                                                <CircleCheck size={15} />
                                            </span>
                                            <div>
                                                <strong>
                                                    {activity.summary}
                                                </strong>
                                                <p>
                                                    {activity.employee_name} ·{" "}
                                                    {new Date(
                                                        activity.occurred_at,
                                                    ).toLocaleDateString(
                                                        "en-US",
                                                        {
                                                            month: "short",
                                                            day: "numeric",
                                                        },
                                                    )}
                                                </p>
                                            </div>
                                            <span className="flow-activity-type">
                                                {activity.request_type.toLowerCase()}
                                            </span>
                                        </motion.li>
                                    ))}
                            </ul>
                        )}
                    </div>
                </section>
            )}

            {canEvaluate && (
                <section className="flow-section">
                    <SectionHeading
                        eyebrow="Decision quality"
                        title="Confidence, measured."
                        link={{
                            href: "/evaluation/summary",
                            label: "Explore Evaluation",
                        }}
                    />
                    <div className="flow-analyst-grid">
                        <article className="flow-card flow-evaluation-card">
                            <div className="flow-evaluation-ring">
                                <Ring
                                    value={
                                        (evaluation.data?.data.decision_accuracy
                                            .rate ?? 0) * 100
                                    }
                                    size={86}
                                    stroke={6}
                                    label="Decision accuracy"
                                />
                                <strong>
                                    {Math.round(
                                        (evaluation.data?.data.decision_accuracy
                                            .rate ?? 0) * 100,
                                    )}
                                    %
                                </strong>
                            </div>
                            <div>
                                <p className="flow-card-eyebrow">
                                    Decision accuracy
                                </p>
                                <h3>
                                    {evaluation.data?.data.evaluated_decisions.toLocaleString(
                                        "en-US",
                                    ) ?? "—"}{" "}
                                    decisions evaluated
                                </h3>
                                <p className="flow-card-caption">
                                    Across outcomes, routing, and reimbursement
                                    eligibility.
                                </p>
                            </div>
                            <Link
                                className="flow-link"
                                to="/evaluation/summary"
                            >
                                View Evaluation <ArrowRight size={15} />
                            </Link>
                        </article>
                        <article className="flow-card flow-detection-card">
                            <div className="flow-detection-icon">
                                <ShieldAlert size={20} />
                            </div>
                            <p className="flow-card-eyebrow">
                                Detection signals
                            </p>
                            <h3>
                                <NumberTicker
                                    value={
                                        operatorData?.anomalies_flagged ??
                                        findings.data?.meta.total ??
                                        0
                                    }
                                    className="flow-kpi-number"
                                />{" "}
                                signals flagged
                            </h3>
                            <p className="flow-card-caption">
                                Review findings, confirm the signal, and keep
                                the system honest.
                            </p>
                            <Link className="flow-link" to="/audit/findings">
                                Review detection <ArrowRight size={15} />
                            </Link>
                        </article>
                    </div>
                </section>
            )}
        </div>
    )
}
