import { useEffect, useMemo, useRef, useState } from "react"
import { format, parseISO } from "date-fns"
import { ArrowRight, CalendarCheck2, CheckCircle2 } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import type { DateRange } from "react-day-picker"
import { BlurFade } from "@/components/ui/blur-fade"
import { BorderBeam } from "@/components/ui/border-beam"
import { Button } from "@/components/ui/button"
import { NumberTicker } from "@/components/ui/number-ticker"
import { Skeleton } from "@/components/ui/skeleton"
import { DateRangePicker, Gauge, Segmented } from "@/components/ui/primitives"
import {
    ApprovalPath,
    FlowNotice,
    FlowPageIntro,
    PreviewChecks,
    RetryAction,
} from "@/components/flow-primitives"
import type {
    GetEmployeeLeaveBalancesResponse,
    GetHolidaysResponse,
    GetLeavePoliciesResponse,
    LeavePolicy,
    LeavePolicyId,
    LeaveRequestCreateRequest,
    LeaveRequestPreview,
    LeaveRequestPreviewRequest,
    PostLeaveRequestPreviewResponse,
    PostLeaveRequestResponse,
} from "@/api/types"
import { SystemRole } from "@/api/types"
import { useApiMutation, useApiQuery } from "@/hooks/use-api"
import { useAuth } from "@/providers/auth-provider"
import "../styles/flow-pages.css"

const initialRange: DateRange = {
    from: new Date(2026, 11, 7),
    to: new Date(2026, 11, 12),
}
const emptyPolicies: LeavePolicy[] = []

function localDate(date: Date): string {
    return format(date, "yyyy-MM-dd")
}

function reasonLabel(value: string): string {
    return value.replaceAll("_", " ").toLowerCase()
}

export function LeavePreviewCard({
    preview,
    loading,
    error,
    onRetry,
}: {
    preview: LeaveRequestPreview | null
    loading: boolean
    error: Error | null
    onRetry: () => void
}) {
    return (
        <article
            className="flow-card leave-preview-card"
            aria-labelledby="leave-preview-title"
        >
            <BorderBeam
                size={76}
                duration={8}
                colorFrom="#0071E3"
                colorTo="#9AC8FF"
                borderWidth={1}
            />
            <div className="flow-preview-topline">
                <div>
                    <p className="flow-card-eyebrow">Live policy check</p>
                    <h2 id="leave-preview-title">Decision preview</h2>
                </div>
                <span className="flow-preview-status">
                    {loading ? (
                        <span className="flow-pulse-dot" />
                    ) : (
                        <CheckCircle2 size={16} />
                    )}
                    {loading ? "Updating" : preview ? "Current" : "Waiting"}
                </span>
            </div>

            {error && (
                <FlowNotice
                    kind="error"
                    title="Preview unavailable."
                    message={error.message}
                    action={<RetryAction onRetry={onRetry} />}
                />
            )}

            {!preview && !error && loading && (
                <div
                    className="flow-preview-skeleton"
                    role="status"
                    aria-label="Calculating leave preview"
                >
                    <Skeleton className="h-14 w-32 rounded-xl" />
                    <Skeleton className="h-8 w-full rounded-xl" />
                    <Skeleton className="h-20 w-full rounded-xl" />
                </div>
            )}

            {!preview && !error && !loading && (
                <div className="flow-preview-empty">
                    <CalendarCheck2 size={24} aria-hidden="true" />
                    <p>
                        Your dates, balance, and approval path will appear here.
                    </p>
                </div>
            )}

            {preview && (
                <div
                    className={`leave-preview-content${loading ? "is-refreshing" : ""}`}
                >
                    <div className="leave-days-summary">
                        <div>
                            <span className="flow-card-eyebrow">
                                Business days
                            </span>
                            <strong className="leave-days-value">
                                <NumberTicker
                                    value={preview.business_days}
                                    className="leave-days-number"
                                    aria-label={`${preview.business_days} business days`}
                                />
                            </strong>
                            <span className="flow-card-caption">
                                {preview.start_date} – {preview.end_date}
                            </span>
                        </div>
                        <div className="leave-excluded">
                            <span className="flow-card-eyebrow">
                                Not counted
                            </span>
                            {preview.excluded_dates.length === 0 ? (
                                <span className="flow-card-caption">
                                    No excluded dates
                                </span>
                            ) : (
                                <ul>
                                    {preview.excluded_dates.map((item) => (
                                        <li key={`${item.date}-${item.reason}`}>
                                            <time dateTime={item.date}>
                                                {format(
                                                    parseISO(item.date),
                                                    "EEE, MMM d",
                                                )}
                                            </time>
                                            <span>
                                                {reasonLabel(item.reason)}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>

                    {preview.balance_before !== null &&
                        preview.balance_after !== null && (
                            <div className="leave-balance-preview">
                                <div>
                                    <p className="flow-card-eyebrow">
                                        Annual leave balance
                                    </p>
                                    <h3>
                                        {preview.balance_before}{" "}
                                        <span>days</span>
                                        <ArrowRight
                                            size={17}
                                            aria-hidden="true"
                                        />
                                        {preview.balance_after}{" "}
                                        <span>days</span>
                                    </h3>
                                    <p className="flow-card-caption">
                                        After this request is reserved
                                    </p>
                                </div>
                                <Gauge
                                    value={
                                        preview.balance_before > 0
                                            ? Math.round(
                                                  (preview.balance_after /
                                                      preview.balance_before) *
                                                      100,
                                              )
                                            : 0
                                    }
                                    label="Remaining"
                                    caption="of current balance"
                                />
                            </div>
                        )}

                    <div className="flow-preview-section">
                        <h3>Validation checks</h3>
                        <PreviewChecks checks={preview.checks} />
                    </div>

                    <div className="flow-preview-section">
                        <h3>Approval path</h3>
                        <ApprovalPath steps={preview.path} />
                    </div>
                </div>
            )}
        </article>
    )
}

export function LeaveRequestPage() {
    const { persona } = useAuth()
    const navigate = useNavigate()
    const canCreate =
        persona?.system_role === SystemRole.REQUESTER ||
        persona?.system_role === SystemRole.PROCESS_OWNER ||
        persona?.system_role === SystemRole.ADMIN
    const [range, setRange] = useState<DateRange | undefined>(initialRange)
    const [reason, setReason] = useState("")
    const [policyId, setPolicyId] = useState<LeavePolicyId>("LPO-001")
    const [previewResult, setPreviewResult] = useState<{
        key: string
        data: LeaveRequestPreview
    } | null>(null)
    const [previewErrorResult, setPreviewErrorResult] = useState<{
        key: string
        error: Error
    } | null>(null)
    const previewGeneration = useRef(0)
    const country = persona?.country

    const policies = useApiQuery<GetLeavePoliciesResponse>("/leave-policies", {
        effective_on: "2026-10-22",
        page: 1,
        page_size: 100,
    })
    const holidays = useApiQuery<GetHolidaysResponse>(
        "/holidays",
        {
            country,
            year: 2026,
            page: 1,
            page_size: 100,
        },
        Boolean(country),
    )
    const balances = useApiQuery<GetEmployeeLeaveBalancesResponse>(
        `/employees/${persona?.employee_id ?? ""}/leave-balances`,
        { as_of_date: "2026-10-22", page: 1, page_size: 100 },
        Boolean(persona && canCreate),
    )

    const policyOptions = policies.data?.data ?? emptyPolicies
    const selectedPolicy =
        policyOptions.find((policy) => policy.leave_policy_id === policyId) ??
        policyOptions[0] ??
        null
    const selectedPolicyId = selectedPolicy?.leave_policy_id
    const policySegmentOptions = policyOptions.map((policy: LeavePolicy) => ({
        value: policy.leave_policy_id,
        label: policy.name,
    }))
    const holidayDates = (holidays.data?.data ?? []).map((holiday) =>
        parseISO(holiday.holiday_date),
    )
    const payload = useMemo<LeaveRequestPreviewRequest | null>(() => {
        if (
            !persona ||
            !canCreate ||
            !selectedPolicyId ||
            !range?.from ||
            !range.to
        )
            return null
        return {
            leave_policy_id: selectedPolicyId,
            start_date: localDate(range.from),
            end_date: localDate(range.to),
            ...(reason.trim() ? { reason: reason.trim() } : {}),
        }
    }, [persona, canCreate, selectedPolicyId, range, reason])
    const payloadKey = payload ? JSON.stringify(payload) : ""
    const preview =
        previewResult?.key === payloadKey ? previewResult.data : null
    const previewError =
        previewErrorResult?.key === payloadKey ? previewErrorResult.error : null

    const previewMutation = useApiMutation<
        PostLeaveRequestPreviewResponse,
        LeaveRequestPreviewRequest
    >("/leave-requests/preview")
    const mutatePreview = previewMutation.mutate
    const createMutation = useApiMutation<
        PostLeaveRequestResponse,
        LeaveRequestCreateRequest
    >("/leave-requests", [
        "/leave-requests",
        `/employees/${persona?.employee_id ?? ""}/leave-balances`,
    ])

    useEffect(() => {
        const generation = ++previewGeneration.current
        if (!policies.data || !payload) return
        const timer = window.setTimeout(() => {
            mutatePreview(payload, {
                onSuccess: (response) => {
                    if (previewGeneration.current === generation) {
                        setPreviewResult({
                            key: payloadKey,
                            data: response.data,
                        })
                    }
                },
                onError: (error) => {
                    if (previewGeneration.current === generation) {
                        setPreviewErrorResult({ key: payloadKey, error })
                    }
                },
            })
        }, 300)
        return () => {
            window.clearTimeout(timer)
            if (previewGeneration.current === generation) {
                previewGeneration.current += 1
            }
        }
    }, [payload, payloadKey, policies.data, mutatePreview])

    const submit = () => {
        if (!payload || !preview?.valid) return
        createMutation.mutate(payload, {
            onSuccess: (response) => {
                toast.success("Your leave request is on its way.")
                navigate(`/leave-requests/${response.data.leave_request_id}`)
            },
            onError: (error) =>
                toast.error("The request could not be submitted.", {
                    description: error.message,
                }),
        })
    }

    const requestPreview = () => {
        if (!payload) return
        const generation = ++previewGeneration.current
        setPreviewErrorResult(null)
        mutatePreview(payload, {
            onSuccess: (response) => {
                if (previewGeneration.current === generation) {
                    setPreviewResult({ key: payloadKey, data: response.data })
                }
            },
            onError: (error) => {
                if (previewGeneration.current === generation) {
                    setPreviewErrorResult({ key: payloadKey, error })
                }
            },
        })
    }

    const invalidReason = !payload
        ? "Choose both a start and end date to see your decision preview."
        : !preview
          ? "Waiting for the live policy check before this request can be sent."
          : !preview.valid
            ? preview.blocking_reason
                ? `This request cannot be submitted: ${reasonLabel(preview.blocking_reason)}.`
                : "Resolve the failed checks before submitting."
            : null
    const hasQueryError = policies.error ?? holidays.error ?? balances.error

    if (!persona) {
        return (
            <FlowNotice
                kind="error"
                title="Your session is not ready."
                message="Sign in with a RouteIQ persona to create a leave request."
            />
        )
    }

    if (!canCreate) {
        return (
            <div className="flow-page-stack">
                <FlowPageIntro
                    eyebrow="Leave · New request"
                    title="Make room for time away."
                    description="Choose your dates. We’ll take care of the policy details."
                />
                <FlowNotice
                    kind="info"
                    title="Leave request creation is not available for this persona."
                    message="Switch to a requester, process owner, or admin persona to create a leave request."
                />
            </div>
        )
    }

    return (
        <div className="flow-page-stack">
            <FlowPageIntro
                eyebrow="Leave · New request"
                title="Make room for time away."
                description="Choose your dates. We’ll take care of the policy details."
            />

            {hasQueryError && (
                <FlowNotice
                    kind="error"
                    title="Some policy details could not load."
                    message={hasQueryError.message}
                    action={
                        <RetryAction
                            onRetry={() => {
                                void policies.refetch()
                                void holidays.refetch()
                                void balances.refetch()
                            }}
                        />
                    }
                />
            )}

            <div className="flow-form-layout">
                <form
                    className="flow-form-column"
                    onSubmit={(event) => {
                        event.preventDefault()
                        submit()
                    }}
                >
                    <BlurFade inView duration={0.55}>
                        <section className="flow-card flow-form-card">
                            <div className="flow-form-section-heading">
                                <span className="flow-section-index">01</span>
                                <div>
                                    <p className="flow-card-eyebrow">
                                        The policy
                                    </p>
                                    <h2>What kind of time away?</h2>
                                </div>
                            </div>
                            {policySegmentOptions.length === 0 ? (
                                <FlowNotice
                                    kind="empty"
                                    title="No leave policies available."
                                    message="Ask your RouteIQ administrator to check the policy setup."
                                />
                            ) : (
                                <Segmented
                                    options={policySegmentOptions}
                                    value={
                                        selectedPolicy?.leave_policy_id ??
                                        policyId
                                    }
                                    onChange={setPolicyId}
                                    label="Leave policy"
                                    className="leave-policy-segments"
                                />
                            )}
                            {selectedPolicy && (
                                <p className="flow-field-hint">
                                    {selectedPolicy.annual_entitlement_days ===
                                    null
                                        ? "This policy does not use a fixed annual entitlement."
                                        : `${selectedPolicy.annual_entitlement_days} days of annual entitlement`}
                                    {selectedPolicy.max_consecutive_days !==
                                    null
                                        ? ` · Up to ${selectedPolicy.max_consecutive_days} consecutive days`
                                        : ""}
                                </p>
                            )}
                        </section>
                    </BlurFade>

                    <BlurFade inView delay={0.06} duration={0.55}>
                        <section className="flow-card flow-form-card">
                            <div className="flow-form-section-heading">
                                <span className="flow-section-index">02</span>
                                <div>
                                    <p className="flow-card-eyebrow">
                                        The dates
                                    </p>
                                    <h2>When would you like to be away?</h2>
                                </div>
                            </div>
                            <label
                                className="flow-field-label"
                                htmlFor="leave-date-range"
                            >
                                Date range
                            </label>
                            <DateRangePicker
                                value={range}
                                onChange={setRange}
                                holidays={holidayDates}
                                label="Choose leave date range"
                            />
                            <p className="flow-field-hint">
                                Weekends and {persona.country} holidays are
                                marked and excluded from business-day totals.
                            </p>
                            {(holidays.isLoading || balances.isLoading) && (
                                <p className="flow-field-hint" role="status">
                                    Loading your country calendar and balance…
                                </p>
                            )}
                        </section>
                    </BlurFade>

                    <BlurFade inView delay={0.12} duration={0.55}>
                        <section className="flow-card flow-form-card">
                            <div className="flow-form-section-heading">
                                <span className="flow-section-index">03</span>
                                <div>
                                    <p className="flow-card-eyebrow">
                                        A little context
                                    </p>
                                    <h2>Anything you’d like to add?</h2>
                                </div>
                            </div>
                            <label
                                className="flow-field-label"
                                htmlFor="leave-reason"
                            >
                                Reason <span>Optional</span>
                            </label>
                            <textarea
                                id="leave-reason"
                                className="flow-textarea"
                                value={reason}
                                onChange={(event) =>
                                    setReason(event.target.value)
                                }
                                placeholder="Share a note for the people reviewing your request."
                                rows={4}
                                maxLength={500}
                            />
                            <div className="flow-textarea-footer">
                                <p className="flow-field-hint">
                                    Only the approvers on your path can see
                                    this.
                                </p>
                                <span className="tabular-nums">
                                    {reason.length}/500
                                </span>
                            </div>
                        </section>
                    </BlurFade>
                </form>

                <aside className="flow-preview-column">
                    <div className="flow-sticky-preview">
                        <LeavePreviewCard
                            preview={preview}
                            loading={
                                previewMutation.isPending ||
                                (!preview && Boolean(payload))
                            }
                            error={previewError}
                            onRetry={requestPreview}
                        />
                        <div className="flow-submit-desktop">
                            <Button
                                type="button"
                                size="lg"
                                className="w-full"
                                onClick={submit}
                                disabled={
                                    !preview?.valid ||
                                    createMutation.isPending ||
                                    previewMutation.isPending
                                }
                            >
                                {createMutation.isPending
                                    ? "Submitting…"
                                    : "Submit request"}
                                <ArrowRight aria-hidden="true" />
                            </Button>
                            <p
                                className={
                                    invalidReason
                                        ? "flow-submit-reason"
                                        : "flow-submit-reason flow-submit-ready"
                                }
                            >
                                {invalidReason ??
                                    "Your request is ready to submit."}
                            </p>
                        </div>
                        {createMutation.error && (
                            <FlowNotice
                                kind="error"
                                title="Submission failed."
                                message={createMutation.error.message}
                                action={<RetryAction onRetry={submit} />}
                            />
                        )}
                    </div>
                </aside>
            </div>
        </div>
    )
}
