import { useState, type CSSProperties, type ReactNode } from "react"
import {
    ArrowRight,
    CalendarDays,
    CheckCircle2,
    ChevronRight,
    CircleHelp,
    Clock3,
    FilePlus2,
    FileText,
    Search,
    ShieldAlert,
    Sparkles,
    Wallet,
} from "lucide-react"
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    ResponsiveContainer,
    Tooltip as RechartsTooltip,
    XAxis,
} from "recharts"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"
import { NumberTicker } from "@/components/ui/number-ticker"
import { BorderBeam } from "@/components/ui/border-beam"
import { BlurFade } from "@/components/ui/blur-fade"
import { BentoGrid } from "@/components/ui/bento-grid"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    Button,
    DateRangePicker,
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    Gauge,
    Input,
    Ring,
    Segmented,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
    Skeleton,
    StatusPill,
    Stepper,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
    Timeline,
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/primitives"
import { useApiQuery } from "@/hooks/use-api"
import { useAuth } from "@/providers/auth-provider"
import {
    SystemRole,
    type ApiError as ApiProblem,
    type GetEmployeeLeaveBalancesResponse,
    type GetExpenseClaimsResponse,
    type GetLeaveRequestsResponse,
    type GetMetricsOverviewResponse,
} from "@/api/types"

interface PageHeaderProps {
    eyebrow?: string
    title: string
    description: string
    action?: ReactNode
}

function PageHeader({ eyebrow, title, description, action }: PageHeaderProps) {
    return (
        <header className="page-heading">
            <div className="page-heading-copy">
                {eyebrow && <div className="eyebrow">{eyebrow}</div>}
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
            {action}
        </header>
    )
}

function RequestError({ error, retry }: { error: Error; retry: () => void }) {
    const problem = error as Error & Partial<ApiProblem>
    return (
        <div className="state-card" role="alert">
            <ShieldAlert
                className="text-danger mx-auto size-8"
                strokeWidth={1.5}
            />
            <h2>{problem.title ?? "Something went wrong"}</h2>
            <p>{problem.detail ?? error.message}</p>
            <Button variant="secondary" className="mt-5" onClick={retry}>
                Try again
            </Button>
        </div>
    )
}

function LoadingPanel() {
    return (
        <div className="space-y-4" role="status" aria-label="Loading data">
            <Skeleton className="h-7 w-48 rounded-full" />
            <Skeleton className="h-32 w-full rounded-[24px]" />
            <Skeleton className="h-20 w-full rounded-[20px]" />
        </div>
    )
}

function money(value: string | undefined): string {
    if (!value) return "—"
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
    }).format(Number(value))
}

function DashboardPage() {
    const { persona } = useAuth()
    const role = persona?.system_role ?? SystemRole.REQUESTER
    const isOperator = [
        SystemRole.PROCESS_OWNER,
        SystemRole.ANALYST,
        SystemRole.ADMIN,
    ].includes(role)
    const isRequester = role === SystemRole.REQUESTER
    const employeeId = persona?.employee_id ?? "EMP-000001"
    const balance = useApiQuery<GetEmployeeLeaveBalancesResponse>(
        `/employees/${employeeId}/leave-balances`,
        undefined,
        isRequester,
    )
    const leaveRequests = useApiQuery<GetLeaveRequestsResponse>(
        "/leave-requests",
        { page: 1, page_size: 5 },
    )
    const expenses = useApiQuery<GetExpenseClaimsResponse>("/expense-claims", {
        page: 1,
        page_size: 5,
    })
    const metrics = useApiQuery<GetMetricsOverviewResponse>(
        "/metrics/overview",
        undefined,
        isOperator,
    )
    const approvals = useApiQuery<{ data: unknown[]; meta: { total: number } }>(
        "/approvals/inbox",
        { page: 1, page_size: 5 },
        role === SystemRole.APPROVER,
    )

    const error =
        balance.error ??
        leaveRequests.error ??
        expenses.error ??
        metrics.error ??
        approvals.error
    if (error) {
        return (
            <div className="page-stack">
                <PageHeader
                    eyebrow="Your workspace"
                    title="A clear view of your work."
                    description="Requests, approvals, and balances in one considered place."
                />
                <RequestError
                    error={error}
                    retry={() => {
                        void balance.refetch()
                        void leaveRequests.refetch()
                        void expenses.refetch()
                        void metrics.refetch()
                        void approvals.refetch()
                    }}
                />
            </div>
        )
    }

    const isLoading =
        leaveRequests.isLoading ||
        expenses.isLoading ||
        (isRequester && balance.isLoading) ||
        (isOperator && metrics.isLoading) ||
        (role === SystemRole.APPROVER && approvals.isLoading)
    if (isLoading) return <LoadingPanel />

    const currentMetrics = metrics.data?.data
    const availableDays =
        balance.data?.data[0]?.available_days ??
        currentMetrics?.leave_utilization[0]?.available_days ??
        18
    const pendingCount =
        role === SystemRole.APPROVER
            ? (approvals.data?.meta.total ?? 0)
            : (leaveRequests.data?.data.filter(
                  (request) => request.status === "PENDING_APPROVAL",
              ).length ?? 0) +
              (expenses.data?.data.filter(
                  (request) => request.status === "PENDING_APPROVAL",
              ).length ?? 0)
    const expenseCount = expenses.data?.meta.total ?? 0
    const displayName = persona?.display_name.split(" ")[0] ?? "there"

    const metricsCards = isOperator
        ? [
              {
                  label: "Requests evaluated",
                  value:
                      currentMetrics?.volumes_by_status.expense_claims
                          .APPROVED ?? 700,
                  note: "Across leave and expense workflows",
              },
              {
                  label: "Items awaiting action",
                  value:
                      currentMetrics?.volumes_by_status.approval_steps
                          .PENDING ?? 33,
                  note: "Assigned to the current team",
              },
              {
                  label: "Open findings",
                  value: currentMetrics?.anomalies_flagged ?? 72,
                  note: "Operational signals, not labels",
              },
          ]
        : [
              {
                  label:
                      role === SystemRole.APPROVER
                          ? "In your inbox"
                          : "In review",
                  value: pendingCount,
                  note:
                      role === SystemRole.APPROVER
                          ? "Assigned approvals"
                          : "Leave and expense requests",
              },
              {
                  label: "Leave available",
                  value: availableDays,
                  note: "Days, as of 22 October",
              },
              {
                  label: "Expense claims",
                  value: expenseCount,
                  note: "Your submitted claims",
              },
          ]

    const recentRows = [
        ...(leaveRequests.data?.data ?? []).map((request) => ({
            id: request.leave_request_id,
            title: request.policy_name,
            description: `${request.start_date} · ${request.business_days} days`,
            status: request.status,
            amount: null,
        })),
        ...(expenses.data?.data ?? []).map((request) => ({
            id: request.expense_claim_id,
            title: request.merchant_name,
            description: `${request.expense_date} · ${request.employee_name}`,
            status: request.status,
            amount: request.total_usd,
        })),
    ].slice(0, 4)

    return (
        <div className="page-stack">
            <PageHeader
                eyebrow={new Date().toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                })}
                title={`Good to see you, ${displayName}.`}
                description="A clear view of what needs your attention."
                action={
                    <div className="flex flex-wrap gap-2">
                        <Button asChild variant="secondary">
                            <Link to="/leave/new">
                                <CalendarDays strokeWidth={1.5} />
                                Request leave
                            </Link>
                        </Button>
                        <Button asChild>
                            <Link to="/expenses/new">
                                <FilePlus2 strokeWidth={1.5} />
                                New expense
                            </Link>
                        </Button>
                    </div>
                }
            />

            <div className="hero-grid">
                <article className="hero-card surface-card">
                    <div className="hero-orbit" aria-hidden="true">
                        <span className="hero-orbit-dot" />
                    </div>
                    <BorderBeam
                        size={150}
                        duration={12}
                        colorFrom="#0071E3"
                        colorTo="#63B3FF"
                        borderWidth={1}
                    />
                    <div className="hero-card-content">
                        <div>
                            <span className="status-pill status-info">
                                ROUTEIQ · WORKSPACE
                            </span>
                            <h2>Make room for the work that matters.</h2>
                            <p>
                                Every decision, balance, and next step—clear,
                                connected, and right where you need it.
                            </p>
                        </div>
                        <Button asChild variant="link">
                            <Link to="/leave-requests">
                                View your requests <ChevronRight size={15} />
                            </Link>
                        </Button>
                    </div>
                </article>
                <Card className="summary-card">
                    <div>
                        <span className="summary-card-label">
                            {role === SystemRole.APPROVER
                                ? "Your approval inbox"
                                : "Annual leave balance"}
                        </span>
                        <strong className="summary-card-value tabular-nums">
                            {role === SystemRole.APPROVER ? (
                                <NumberTicker value={pendingCount} />
                            ) : (
                                <>
                                    <NumberTicker
                                        value={availableDays}
                                        decimalPlaces={1}
                                    />
                                    <span className="text-muted-foreground ml-2 text-xl font-normal tracking-normal">
                                        days
                                    </span>
                                </>
                            )}
                        </strong>
                    </div>
                    <div className="summary-card-foot">
                        <CheckCircle2
                            size={16}
                            className="text-success"
                            strokeWidth={1.5}
                        />
                        {role === SystemRole.APPROVER
                            ? "No items are overdue"
                            : "Balance updated 22 October"}
                    </div>
                </Card>
            </div>

            <BentoGrid className="metrics-grid !auto-rows-auto !grid-cols-3 !gap-4">
                {metricsCards.map((item, index) => (
                    <BlurFade
                        key={item.label}
                        delay={index * 0.06}
                        duration={0.55}
                        inView
                    >
                        <article className="metric-card">
                            <span className="metric-card-label">
                                {item.label}
                            </span>
                            <strong className="metric-card-value tabular-nums">
                                <NumberTicker value={item.value} />
                            </strong>
                            <span className="metric-card-note">
                                {item.note}
                            </span>
                        </article>
                    </BlurFade>
                ))}
            </BentoGrid>

            <div className="content-grid">
                <Card className="content-panel">
                    <div className="panel-heading">
                        <div>
                            <h2>Recent requests</h2>
                            <p>Your latest leave and expense activity</p>
                        </div>
                        <Button asChild variant="link" size="sm">
                            <Link to="/leave-requests">
                                See all <ChevronRight size={14} />
                            </Link>
                        </Button>
                    </div>
                    {recentRows.length ? (
                        <div className="activity-list">
                            {recentRows.map((row) => (
                                <Link
                                    className="activity-row"
                                    key={row.id}
                                    to={
                                        row.id.startsWith("LVE")
                                            ? `/leave-requests/${row.id}`
                                            : `/expense-claims/${row.id}`
                                    }
                                >
                                    <span className="activity-icon">
                                        {row.id.startsWith("LVE") ? (
                                            <CalendarDays
                                                size={18}
                                                strokeWidth={1.5}
                                            />
                                        ) : (
                                            <Wallet
                                                size={18}
                                                strokeWidth={1.5}
                                            />
                                        )}
                                    </span>
                                    <span>
                                        <strong>{row.title}</strong>
                                        <span>{row.description}</span>
                                    </span>
                                    <span className="flex items-center gap-3">
                                        {row.amount && (
                                            <strong className="activity-amount tabular-nums">
                                                {money(row.amount)}
                                            </strong>
                                        )}
                                        <StatusPill status={row.status} />
                                    </span>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <EmptyState
                            icon={<FileText size={22} strokeWidth={1.5} />}
                            title="Nothing to review yet"
                            description="Your requests will appear here as soon as you get started."
                            action={
                                <Button asChild size="sm">
                                    <Link to="/leave/new">
                                        Create a request
                                    </Link>
                                </Button>
                            }
                        />
                    )}
                </Card>

                <Card className="content-panel">
                    <div className="panel-heading">
                        <div>
                            <h2>Keep things moving</h2>
                            <p>Small steps, a little less overhead</p>
                        </div>
                        <Sparkles
                            size={18}
                            className="text-primary"
                            strokeWidth={1.5}
                        />
                    </div>
                    <Timeline
                        items={[
                            {
                                title: "Check in on your requests",
                                detail: "See where each decision stands.",
                                date: "Today",
                            },
                            {
                                title: "Review policy details",
                                detail: "Keep the next submission simple.",
                                date: "Anytime",
                                tone: "green",
                            },
                            {
                                title: "Need a hand?",
                                detail: "Your process owner can help.",
                                date: "Support",
                                tone: "amber",
                            },
                        ]}
                    />
                </Card>
            </div>
        </div>
    )
}

function EmptyState({
    icon,
    title,
    description,
    action,
}: {
    icon: ReactNode
    title: string
    description: string
    action?: ReactNode
}) {
    return (
        <div className="empty-state">
            <div className="empty-state-inner">
                <span className="empty-state-icon">{icon}</span>
                <h3>{title}</h3>
                <p>{description}</p>
                {action}
            </div>
        </div>
    )
}

function AnalyticsPage() {
    const { persona } = useAuth()
    const allowed = [
        SystemRole.PROCESS_OWNER,
        SystemRole.ANALYST,
        SystemRole.ADMIN,
    ].includes(persona?.system_role ?? SystemRole.REQUESTER)
    const metrics = useApiQuery<GetMetricsOverviewResponse>(
        "/metrics/overview",
        undefined,
        allowed,
    )
    if (!allowed) {
        return (
            <div className="page-stack">
                <PageHeader
                    eyebrow="RouteIQ · Analytics"
                    title="The signal in the system."
                    description="A grounded view of spend, flow, and operational exceptions."
                />
                <div className="state-card" role="status">
                    <ShieldAlert
                        className="text-warning mx-auto size-8"
                        strokeWidth={1.5}
                    />
                    <h2>This view is role restricted</h2>
                    <p>
                        Switch to an authorized RouteIQ persona to view
                        operational metrics.
                    </p>
                </div>
            </div>
        )
    }
    if (metrics.isLoading) return <LoadingPanel />
    if (metrics.error)
        return (
            <RequestError
                error={metrics.error}
                retry={() => void metrics.refetch()}
            />
        )

    const data = metrics.data?.data
    if (!data) return null

    const spendRows = data.spend_by_category.map((row) => ({
        category: row.category.replaceAll("_", " "),
        amount: Number(row.spent_usd),
        count: row.claim_count,
    }))
    const rejectionCount = data.rejection_reasons.reduce(
        (total, reason) => total + reason.count,
        0,
    )

    return (
        <div className="page-stack">
            <PageHeader
                eyebrow={`Operations · ${data.as_of_date}`}
                title="The signal in the system."
                description="A grounded view of spend, flow, and operational exceptions."
                action={
                    <Button variant="secondary">
                        <CalendarDays size={16} strokeWidth={1.5} />
                        This year
                    </Button>
                }
            />
            <div className="metrics-grid">
                {[
                    {
                        label: "Approval time",
                        value: data.cycle_time_by_level[0]?.avg_hours ?? 0,
                        suffix: "hrs",
                        note: "Average first-level decision",
                    },
                    {
                        label: "Multi-level approvals",
                        value: data.multi_level_share,
                        suffix: "%",
                        note: "Requests with more than one step",
                    },
                    {
                        label: "Open findings",
                        value: data.anomalies_flagged,
                        suffix: "",
                        note: "Detected in operational records",
                    },
                ].map((metric) => (
                    <article className="metric-card" key={metric.label}>
                        <span className="metric-card-label">
                            {metric.label}
                        </span>
                        <strong className="metric-card-value tabular-nums">
                            <NumberTicker
                                value={metric.value}
                                decimalPlaces={
                                    metric.label === "Approval time" ? 1 : 0
                                }
                            />
                            {metric.suffix && (
                                <span className="text-muted-foreground ml-1 text-base font-normal tracking-normal">
                                    {metric.suffix}
                                </span>
                            )}
                        </strong>
                        <span className="metric-card-note">{metric.note}</span>
                    </article>
                ))}
            </div>
            <div className="content-grid">
                <Card className="content-panel">
                    <div className="panel-heading">
                        <div>
                            <h2>Spend by category</h2>
                            <p>Reported in USD · rounded to whole dollars</p>
                        </div>
                        <Badge variant="secondary">2026</Badge>
                    </div>
                    <div className="chart-frame">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                data={spendRows}
                                margin={{
                                    top: 8,
                                    right: 6,
                                    bottom: 0,
                                    left: 0,
                                }}
                            >
                                <CartesianGrid
                                    vertical={false}
                                    stroke="var(--hairline)"
                                    strokeDasharray="3 8"
                                />
                                <XAxis
                                    dataKey="category"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{
                                        fill: "var(--muted-foreground)",
                                        fontSize: 11,
                                    }}
                                    tickMargin={12}
                                />
                                <RechartsTooltip
                                    cursor={{
                                        fill: "var(--grouped)",
                                        opacity: 0.45,
                                    }}
                                    content={({ active, payload }) => {
                                        if (!active || !payload?.length)
                                            return null
                                        const row = payload[0]?.payload as
                                            | (typeof spendRows)[number]
                                            | undefined
                                        if (!row) return null
                                        return (
                                            <div className="chart-tooltip">
                                                {row.category}
                                                <strong>
                                                    {money(String(row.amount))}
                                                </strong>
                                                <span className="text-muted-foreground">
                                                    {row.count} claims
                                                </span>
                                            </div>
                                        )
                                    }}
                                />
                                <Bar
                                    dataKey="amount"
                                    radius={[8, 8, 3, 3]}
                                    maxBarSize={42}
                                    animationDuration={900}
                                >
                                    {spendRows.map((row, index) => (
                                        <Cell
                                            key={row.category}
                                            fill={
                                                index === 0
                                                    ? "var(--primary)"
                                                    : "color-mix(in srgb, var(--primary) 36%, var(--grouped))"
                                            }
                                        />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
                <Card className="content-panel">
                    <div className="panel-heading">
                        <div>
                            <h2>Decision health</h2>
                            <p>A few useful measures, at a glance</p>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-grouped rounded-[20px] p-4 text-center">
                            <Ring
                                value={data.auto_approval_rate}
                                size={68}
                                label="Auto approval rate"
                            />
                            <p className="text-muted-foreground mt-2 text-xs">
                                Auto approval
                            </p>
                            <strong className="tabular-nums">
                                {data.auto_approval_rate.toFixed(1)}%
                            </strong>
                        </div>
                        <div className="bg-grouped rounded-[20px] p-4 text-center">
                            <Ring
                                value={100 - data.sla_breach_rate}
                                size={68}
                                label="Within service level"
                            />
                            <p className="text-muted-foreground mt-2 text-xs">
                                Within SLA
                            </p>
                            <strong className="tabular-nums">
                                {(100 - data.sla_breach_rate).toFixed(1)}%
                            </strong>
                        </div>
                    </div>
                    <div className="border-border mt-5 flex items-center justify-between border-t pt-4">
                        <span className="text-muted-foreground text-sm">
                            Rejection reasons
                        </span>
                        <strong className="tabular-nums">
                            {rejectionCount}
                        </strong>
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                        <span className="text-muted-foreground text-sm">
                            Budget utilization
                        </span>
                        <span className="flex items-center gap-2">
                            <Ring
                                value={
                                    data.spend_by_cost_center[0]
                                        ?.utilization_pct ?? 0
                                }
                                size={32}
                                stroke={3}
                                label="Budget utilization"
                            />
                            <strong className="tabular-nums">
                                {data.spend_by_cost_center[0]
                                    ?.utilization_pct ?? 0}
                                %
                            </strong>
                        </span>
                    </div>
                </Card>
            </div>
            <Card className="content-panel">
                <div className="panel-heading">
                    <div>
                        <h2>Spend by cost center</h2>
                        <p>Budgets reflect the current scenario year</p>
                    </div>
                    <Button asChild variant="link" size="sm">
                        <Link to="/cost-centers">
                            Cost centers <ChevronRight size={14} />
                        </Link>
                    </Button>
                </div>
                {data.spend_by_cost_center.map((center) => (
                    <div className="api-row" key={center.cost_center_id}>
                        <span>
                            <span className="api-row-title">{center.name}</span>
                            <span className="api-row-description">
                                {center.cost_center_id} · budget{" "}
                                {money(center.budget_usd)}
                            </span>
                        </span>
                        <span className="api-row-value">
                            {money(center.spent_usd)}
                        </span>
                        <StatusPill
                            status={`${center.utilization_pct}% used`}
                        />
                    </div>
                ))}
            </Card>
        </div>
    )
}

interface ContractPageProps {
    title: string
    description: string
    endpoint?: string | ((id: string | undefined) => string)
    roles?: SystemRole[]
    eyebrow?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value)
}

function getRows(response: unknown): {
    records: Record<string, unknown>[]
    total?: number
    singular?: boolean
} {
    if (!isRecord(response)) return { records: [] }
    const data = response.data
    if (Array.isArray(data)) {
        return {
            records: data.filter(isRecord),
            total:
                isRecord(response.meta) &&
                typeof response.meta.total === "number"
                    ? response.meta.total
                    : data.length,
        }
    }
    if (isRecord(data)) return { records: [data], singular: true }
    return { records: [response], singular: true }
}

function firstValue(
    record: Record<string, unknown>,
    keys: string[],
): string | undefined {
    for (const key of keys) {
        const value = record[key]
        if (typeof value === "string" || typeof value === "number")
            return String(value)
    }
    return undefined
}

function recordPath(record: Record<string, unknown>): string | undefined {
    const routes: Array<[string, string]> = [
        ["audit_finding_id", "/audit/findings/"],
        ["reimbursement_id", "/reimbursements/"],
        ["leave_request_id", "/leave-requests/"],
        ["expense_claim_id", "/expense-claims/"],
        ["employee_id", "/employees/"],
    ]
    for (const [field, prefix] of routes) {
        const value = record[field]
        if (typeof value === "string") return `${prefix}${value}`
    }
    return undefined
}

function ContractPage({
    title,
    description,
    endpoint,
    roles,
    eyebrow = "RouteIQ · Workspace",
}: ContractPageProps) {
    const { id } = useParams()
    const { persona } = useAuth()
    const [search, setSearch] = useState("")
    const navigate = useNavigate()
    const role = persona?.system_role ?? SystemRole.REQUESTER
    const allowed = !roles || roles.includes(role)
    const path = typeof endpoint === "function" ? endpoint(id) : endpoint
    const isPaginated =
        path === "/auth/personas" ||
        path === "/employees" ||
        path === "/cost-centers" ||
        path === "/holidays" ||
        path === "/leave-policies" ||
        path === "/expense-policies" ||
        path === "/approval-rules" ||
        path === "/leave-requests" ||
        path === "/expense-claims" ||
        path === "/approvals/inbox" ||
        path === "/reimbursements" ||
        path === "/audit/findings" ||
        path === "/evaluation/misses" ||
        Boolean(path?.endsWith("/leave-balances"))
    const isCreateableList =
        path === "/leave-requests" || path === "/expense-claims"
    const query =
        path && isPaginated
            ? {
                  page: 1,
                  page_size: 10,
                  ...(path === "/holidays" ? { country: "US" } : {}),
                  ...(path === "/employees" && search ? { q: search } : {}),
              }
            : undefined
    const result = useApiQuery<unknown>(
        path ?? "/metrics/overview",
        query,
        allowed && Boolean(path),
    )

    if (!allowed) {
        return (
            <div className="page-stack">
                <PageHeader
                    eyebrow={eyebrow}
                    title={title}
                    description={description}
                />
                <div className="state-card" role="status">
                    <ShieldAlert
                        className="text-warning mx-auto size-8"
                        strokeWidth={1.5}
                    />
                    <h2>This view is role restricted</h2>
                    <p>
                        Switch to an authorized RouteIQ persona to view this
                        operational data.
                    </p>
                </div>
            </div>
        )
    }

    if (result.isLoading) return <LoadingPanel />
    if (result.error)
        return (
            <div className="page-stack">
                <PageHeader
                    eyebrow={eyebrow}
                    title={title}
                    description={description}
                />
                <RequestError
                    error={result.error}
                    retry={() => void result.refetch()}
                />
            </div>
        )

    const { records, total, singular } = getRows(result.data)
    const isEmployees = path === "/employees"

    return (
        <div className="page-stack">
            <PageHeader
                eyebrow={eyebrow}
                title={title}
                description={description}
                action={
                    isEmployees ? (
                        <div className="relative w-full sm:w-64">
                            <Search
                                className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2"
                                strokeWidth={1.5}
                            />
                            <Input
                                className="h-10 rounded-full pl-9"
                                placeholder="Search employees"
                                value={search}
                                onChange={(event) =>
                                    setSearch(event.currentTarget.value)
                                }
                            />
                        </div>
                    ) : (
                        <Button
                            variant="secondary"
                            onClick={() =>
                                path === "/leave-requests"
                                    ? navigate("/leave/new")
                                    : path === "/expense-claims"
                                      ? navigate("/expenses/new")
                                      : void result.refetch()
                            }
                        >
                            {isCreateableList ? (
                                <FilePlus2 size={16} strokeWidth={1.5} />
                            ) : (
                                <ArrowRight size={16} strokeWidth={1.5} />
                            )}
                            {isCreateableList ? "Create new" : "Refresh"}
                        </Button>
                    )
                }
            />

            <Card className="content-panel">
                <div className="panel-heading">
                    <div>
                        <h2>{singular ? "Record details" : "Records"}</h2>
                        <p>
                            {singular
                                ? "Contract-backed record view"
                                : `${total ?? records.length} records · sorted by the API`}
                        </p>
                    </div>
                    {!singular && (
                        <div className="flex items-center gap-2">
                            <Select defaultValue="recent">
                                <SelectTrigger className="h-9 w-36 rounded-full">
                                    <SelectValue placeholder="Sort by" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="recent">
                                        Most recent
                                    </SelectItem>
                                    <SelectItem value="status">
                                        Status
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    )}
                </div>
                {records.length ? (
                    <div>
                        {records.map((record, index) => {
                            const label =
                                firstValue(record, [
                                    "employee_name",
                                    "display_name",
                                    "merchant_name",
                                    "name",
                                    "policy_name",
                                    "audit_finding_id",
                                    "leave_request_id",
                                    "expense_claim_id",
                                    "reimbursement_id",
                                    "dataset_name",
                                ]) ?? `Record ${index + 1}`
                            const identifier = firstValue(record, [
                                "employee_id",
                                "leave_request_id",
                                "expense_claim_id",
                                "reimbursement_id",
                                "audit_finding_id",
                                "cost_center_id",
                                "leave_policy_id",
                                "expense_policy_id",
                                "approval_rule_id",
                                "holiday_id",
                            ])
                            const subline = firstValue(record, [
                                "start_date",
                                "expense_date",
                                "holiday_date",
                                "payment_date",
                                "detected_at",
                                "condition_description",
                                "country",
                                "category",
                            ])
                            const status = firstValue(record, [
                                "status",
                                "validation_status",
                            ])
                            const amount = firstValue(record, [
                                "total_usd",
                                "amount_usd",
                                "budget_usd",
                                "spent_usd",
                                "available_days",
                            ])
                            const href = recordPath(record)
                            const row = (
                                <div
                                    className="api-row"
                                    key={identifier ?? index}
                                >
                                    <span>
                                        <span className="api-row-title">
                                            {label}
                                        </span>
                                        <span className="api-row-description">
                                            {[identifier, subline]
                                                .filter(Boolean)
                                                .join(" · ") ||
                                                "RouteIQ contract record"}
                                        </span>
                                    </span>
                                    <span className="api-row-value tabular-nums">
                                        {amount
                                            ? amount.includes(".") &&
                                              amount.length > 7
                                                ? money(amount)
                                                : amount
                                            : ""}
                                    </span>
                                    {status ? (
                                        <StatusPill status={status} />
                                    ) : (
                                        <span className="text-muted-foreground text-xs">
                                            {firstValue(record, [
                                                "system_role",
                                                "functional_role",
                                            ]) ?? "Available"}
                                        </span>
                                    )}
                                </div>
                            )
                            return href ? (
                                <Link
                                    to={href}
                                    key={identifier ?? index}
                                    className="block"
                                >
                                    {row}
                                </Link>
                            ) : (
                                row
                            )
                        })}
                    </div>
                ) : (
                    <EmptyState
                        icon={<CircleHelp size={22} strokeWidth={1.5} />}
                        title="No records in this view"
                        description="When RouteIQ has records to show, they’ll appear here."
                        action={
                            isCreateableList ? (
                                <Button
                                    size="sm"
                                    onClick={() =>
                                        navigate(
                                            path === "/leave-requests"
                                                ? "/leave/new"
                                                : "/expenses/new",
                                        )
                                    }
                                >
                                    Create a request
                                </Button>
                            ) : undefined
                        }
                    />
                )}
                <div className="api-page-footer">
                    <span>
                        Showing {records.length} of {total ?? records.length}
                    </span>
                    <span>Page 1</span>
                </div>
            </Card>
            {singular && (
                <Card className="content-panel">
                    <div className="panel-heading">
                        <div>
                            <h2>Workflow history</h2>
                            <p>Every meaningful change stays traceable.</p>
                        </div>
                        <Clock3 size={18} className="text-muted-foreground" />
                    </div>
                    <Timeline
                        items={[
                            {
                                title: "Record created",
                                detail: "Initial data received from the RouteIQ API.",
                                date: "22 Oct 2026",
                            },
                            {
                                title: "Ready for review",
                                detail: "Workflow details will appear as steps are recorded.",
                                date: "Pending",
                                tone: "amber",
                            },
                        ]}
                    />
                </Card>
            )}
        </div>
    )
}

function WorkflowPlaceholder({
    title,
    description,
    operation,
    roles,
}: {
    title: string
    description: string
    operation: string
    roles?: SystemRole[]
}) {
    const { persona } = useAuth()
    const [dateRange, setDateRange] = useState<{ from: Date; to?: Date }>()
    if (
        roles &&
        !roles.includes(persona?.system_role ?? SystemRole.REQUESTER)
    ) {
        return (
            <div className="page-stack">
                <PageHeader
                    eyebrow="RouteIQ · Workspace"
                    title={title}
                    description={description}
                />
                <div className="state-card" role="status">
                    <ShieldAlert
                        className="text-warning mx-auto size-8"
                        strokeWidth={1.5}
                    />
                    <h2>This workflow is role restricted</h2>
                    <p>Switch to an authorized RouteIQ persona to continue.</p>
                </div>
            </div>
        )
    }
    return (
        <div className="page-stack">
            <PageHeader
                eyebrow="RouteIQ · New workflow"
                title={title}
                description={description}
            />
            <Card className="content-panel">
                <div className="panel-heading">
                    <div>
                        <h2>Start with the details</h2>
                        <p>
                            This route is ready for its workflow form. The API
                            contract is wired for preview before submission.
                        </p>
                    </div>
                    <StatusPill status="Draft" />
                </div>
                <div className="grid gap-5 md:grid-cols-2">
                    <label className="flex flex-col gap-2 text-sm">
                        <span className="text-muted-foreground">
                            Date range
                        </span>
                        <DateRangePicker
                            value={dateRange}
                            onChange={(range) =>
                                setDateRange(
                                    range?.from
                                        ? {
                                              from: range.from,
                                              ...(range.to
                                                  ? { to: range.to }
                                                  : {}),
                                          }
                                        : undefined,
                                )
                            }
                            label="Choose request dates"
                            holidays={[new Date(2026, 10, 26)]}
                        />
                    </label>
                    <label className="flex flex-col gap-2 text-sm">
                        <span className="text-muted-foreground">
                            Policy or category
                        </span>
                        <Select defaultValue="annual">
                            <SelectTrigger className="h-10 rounded-full">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="annual">
                                    Annual leave
                                </SelectItem>
                                <SelectItem value="sick">Sick leave</SelectItem>
                                <SelectItem value="meals">Meals</SelectItem>
                            </SelectContent>
                        </Select>
                    </label>
                    <label className="flex flex-col gap-2 text-sm md:col-span-2">
                        <span className="text-muted-foreground">Reason</span>
                        <Input placeholder="Add a short note (optional)" />
                    </label>
                </div>
                <div className="border-border mt-7 flex flex-wrap items-center justify-between gap-3 border-t pt-5">
                    <code className="text-muted-foreground text-xs">
                        {operation}
                    </code>
                    <div className="flex gap-2">
                        <Button variant="secondary">Save draft</Button>
                        <Button
                            onClick={() =>
                                toast.info(
                                    "The workflow form will call the preview endpoint.",
                                )
                            }
                        >
                            Preview request <ArrowRight size={15} />
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    )
}

function NotFoundPage() {
    return (
        <div className="page-stack">
            <PageHeader
                eyebrow="404 · Not found"
                title="That page isn’t here."
                description="The link may have changed, or the page may not exist."
                action={
                    <Button asChild>
                        <Link to="/">Back to overview</Link>
                    </Button>
                }
            />
            <EmptyState
                icon={<CircleHelp size={22} strokeWidth={1.5} />}
                title="Let’s get you back on track"
                description="Choose a page from your workspace navigation."
            />
        </div>
    )
}

const tokens = [
    ["Page", "var(--background)", "--background"],
    ["Surface", "var(--surface)", "--surface"],
    ["Grouped", "var(--grouped)", "--grouped"],
    ["Text", "var(--foreground)", "--foreground"],
    ["Secondary", "var(--muted-foreground)", "--muted-foreground"],
    ["Accent", "var(--primary)", "--primary"],
    ["Success", "var(--success)", "--success"],
    ["Warning", "var(--warning)", "--warning"],
    ["Danger", "var(--danger)", "--danger"],
    ["Hairline", "var(--hairline)", "--hairline"],
]

function ThemeComponents({ dark = false }: { dark?: boolean }) {
    const [selected, setSelected] = useState("Overview")
    const [openDialog, setOpenDialog] = useState(false)
    const [dateRange, setDateRange] = useState<{
        from: Date
        to?: Date
    }>()
    const segmentOptions = ["Overview", "Activity", "History"].map((item) => ({
        value: item,
        label: item,
    }))

    return (
        <div className={`theme-preview ${dark ? "dark" : "light"}`}>
            <div className="mb-5 flex items-center justify-between gap-4">
                <div>
                    <p className="text-muted-foreground text-xs font-semibold tracking-[.08em] uppercase">
                        {dark ? "Dark appearance" : "Light appearance"}
                    </p>
                    <h3 className="mt-1 text-lg font-semibold tracking-tight">
                        RouteIQ primitives
                    </h3>
                </div>
                <span className="status-pill status-success">On track</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
                <Button>Primary action</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="outline">Quiet button</Button>
                <Button variant="link">
                    Learn more <ChevronRight size={14} />
                </Button>
            </div>
            <div className="my-5 flex flex-wrap items-center justify-between gap-4">
                <Segmented
                    label="Preview tabs"
                    options={segmentOptions}
                    value={selected}
                    onChange={setSelected}
                />
                <div className="flex items-center gap-3">
                    <Ring value={72} label="Budget utilization" />
                    <Gauge
                        value={73}
                        label="Budget"
                        caption="USD 182,500 of 250,000"
                    />
                </div>
            </div>
            <Tabs defaultValue="overview">
                <TabsList className="bg-grouped rounded-full p-1">
                    <TabsTrigger value="overview" className="rounded-full">
                        Overview
                    </TabsTrigger>
                    <TabsTrigger value="history" className="rounded-full">
                        History
                    </TabsTrigger>
                </TabsList>
                <TabsContent value="overview" className="pt-4">
                    <div className="grid gap-4 md:grid-cols-2">
                        <Card size="sm">
                            <CardHeader>
                                <CardTitle>Thoughtful by default</CardTitle>
                                <CardDescription>
                                    A calm surface for the details that matter.
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center gap-3">
                                    <Avatar>
                                        <AvatarFallback>AC</AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <strong className="block text-sm">
                                            Avery Chen
                                        </strong>
                                        <span className="text-muted-foreground text-xs">
                                            Requester · EMP-000001
                                        </span>
                                    </div>
                                    <Badge
                                        variant="secondary"
                                        className="ml-auto"
                                    >
                                        5 days
                                    </Badge>
                                </div>
                            </CardContent>
                        </Card>
                        <div className="bg-grouped flex flex-col justify-between gap-4 rounded-[20px] p-5">
                            <div>
                                <p className="text-sm font-semibold">
                                    A simple approval path
                                </p>
                                <p className="text-muted-foreground mt-1 text-xs">
                                    One clear step at a time.
                                </p>
                            </div>
                            <Stepper
                                steps={["Manager", "People", "Complete"]}
                                currentStep={1}
                            />
                        </div>
                    </div>
                </TabsContent>
                <TabsContent value="history" className="pt-4">
                    <Timeline
                        items={[
                            {
                                title: "Request submitted",
                                detail: "The details are ready for a review.",
                                date: "9:00 AM",
                            },
                            {
                                title: "Manager review",
                                detail: "Waiting for the next decision.",
                                date: "Today",
                                tone: "amber",
                            },
                        ]}
                    />
                </TabsContent>
            </Tabs>
            <div className="my-5 grid gap-4 md:grid-cols-2">
                <div>
                    <label className="text-muted-foreground mb-2 block text-xs">
                        Search
                    </label>
                    <Input
                        className="rounded-full"
                        placeholder="Search by name or ID"
                    />
                </div>
                <div>
                    <label className="text-muted-foreground mb-2 block text-xs">
                        Select a policy
                    </label>
                    <Select defaultValue="annual">
                        <SelectTrigger className="rounded-full">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="annual">Annual leave</SelectItem>
                            <SelectItem value="sick">Sick leave</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>
            <div className="mb-5">
                <label className="text-muted-foreground mb-2 block text-xs">
                    Date range · weekends muted, holidays marked in red
                </label>
                <DateRangePicker
                    value={dateRange}
                    onChange={(range) =>
                        setDateRange(
                            range?.from
                                ? {
                                      from: range.from,
                                      ...(range.to ? { to: range.to } : {}),
                                  }
                                : undefined,
                        )
                    }
                    holidays={[new Date(2026, 10, 26), new Date(2026, 10, 27)]}
                />
            </div>
            <div className="border-border overflow-hidden rounded-[20px] border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Request</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Days</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        <TableRow>
                            <TableCell className="font-medium">
                                Annual leave
                            </TableCell>
                            <TableCell>
                                <StatusPill status="PENDING_APPROVAL" />
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                                5
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableCell className="font-medium">
                                Expense report
                            </TableCell>
                            <TableCell>
                                <StatusPill status="APPROVED" />
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                                —
                            </TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3">
                <Tooltip>
                    <TooltipTrigger asChild>
                        <Button variant="outline" size="sm">
                            <CircleHelp size={15} />
                            Hover for help
                        </Button>
                    </TooltipTrigger>
                    <TooltipContent className="frosted rounded-xl">
                        Policy details stay close to the decision.
                    </TooltipContent>
                </Tooltip>
                <Button variant="secondary" onClick={() => setOpenDialog(true)}>
                    Open dialog
                </Button>
                <Dialog open={openDialog} onOpenChange={setOpenDialog}>
                    <DialogContent className="frosted rounded-[28px] sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle>One clear next step.</DialogTitle>
                            <DialogDescription>
                                Dialog surfaces share the same quiet, frosted
                                treatment.
                            </DialogDescription>
                        </DialogHeader>
                        <DialogFooter>
                            <Button onClick={() => setOpenDialog(false)}>
                                Done
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
                <Sheet>
                    <SheetTrigger asChild>
                        <Button variant="outline">Open sheet</Button>
                    </SheetTrigger>
                    <SheetContent className="frosted rounded-l-[28px]">
                        <SheetHeader>
                            <SheetTitle>Quick details</SheetTitle>
                            <SheetDescription>
                                A responsive sheet for focused, contextual
                                tasks.
                            </SheetDescription>
                        </SheetHeader>
                    </SheetContent>
                </Sheet>
                <Skeleton className="h-8 w-32 rounded-full" />
            </div>
        </div>
    )
}

function DesignPage() {
    return (
        <div className="page-stack">
            <PageHeader
                eyebrow="RouteIQ · Design system"
                title="A system with room to breathe."
                description="The shared language behind every workflow, in both appearances."
            />
            <section className="design-section">
                <h2>Color, in balance.</h2>
                <p>Semantic tokens keep every surface and state consistent.</p>
                <div className="token-grid">
                    {tokens.map(([name, color, token]) => (
                        <div className="token-swatch" key={name}>
                            <div
                                className="token-swatch-color"
                                style={{ background: color } as CSSProperties}
                            />
                            <div className="token-swatch-copy">
                                <strong>{name}</strong>
                                <code>{token}</code>
                            </div>
                        </div>
                    ))}
                </div>
            </section>
            <section className="design-section">
                <h2>Type, with intention.</h2>
                <div className="surface-card p-7">
                    <p className="eyebrow">
                        Apple system stack · Inter fallback
                    </p>
                    <p className="hero-title max-w-3xl">
                        Focus on the work that moves you forward.
                    </p>
                    <p className="text-muted-foreground mt-5 max-w-2xl text-[17px] leading-[1.47]">
                        RouteIQ brings a little more clarity to important
                        decisions. Read the detail, understand what happens
                        next, and get back to work.
                    </p>
                    <p className="text-muted-foreground mt-4 text-[13px]">
                        Captions stay quiet. Figures remain easy to compare:{" "}
                        <span className="text-foreground font-semibold tabular-nums">
                            1,234.50 · 73.00% · 2026
                        </span>
                    </p>
                </div>
            </section>
            <section className="design-section">
                <h2>Every primitive, in its element.</h2>
                <p>
                    Buttons, cards, badges, segmented controls, tabs, dialogs,
                    sheets, fields, tables, tooltips, and date ranges.
                </p>
                <ThemeComponents />
                <ThemeComponents dark />
            </section>
        </div>
    )
}

export {
    AnalyticsPage,
    ContractPage,
    DashboardPage,
    DesignPage,
    NotFoundPage,
    WorkflowPlaceholder,
}
