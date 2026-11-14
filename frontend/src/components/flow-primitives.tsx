import type { ReactNode } from "react"
import { CheckCircle2, CircleAlert, CircleHelp, XCircle } from "lucide-react"
import { BlurFade } from "@/components/ui/blur-fade"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ApprovalPathStep, PreviewCheck } from "@/api/types"

export function FlowPageIntro({
    eyebrow,
    title,
    description,
    action,
    gradient = false,
    centered = false,
}: {
    eyebrow: string
    title: string
    description: string
    action?: ReactNode
    gradient?: boolean
    centered?: boolean
}) {
    return (
        <BlurFade duration={0.6} inView>
            <header
                className={`flow-page-intro${centered ? " flow-page-intro-centered" : ""}`}
            >
                <div>
                    <p className="flow-eyebrow">{eyebrow}</p>
                    <h1
                        className={
                            gradient
                                ? "flow-title flow-title-gradient"
                                : "flow-title"
                        }
                    >
                        {title}
                    </h1>
                    <p className="flow-subhead">{description}</p>
                </div>
                {action}
            </header>
        </BlurFade>
    )
}

export function FlowLoading({ rows = 4 }: { rows?: number }) {
    return (
        <div
            className="flow-loading"
            role="status"
            aria-label="Loading page data"
        >
            <Skeleton className="h-7 w-48 rounded-full" />
            <div className="flow-loading-grid">
                {Array.from({ length: rows }, (_, index) => (
                    <Skeleton
                        key={index}
                        className="h-36 w-full rounded-[24px]"
                    />
                ))}
            </div>
        </div>
    )
}

export function FlowNotice({
    kind,
    title,
    message,
    action,
}: {
    kind: "empty" | "error" | "info"
    title: string
    message: string
    action?: ReactNode
}) {
    const Icon =
        kind === "error"
            ? CircleAlert
            : kind === "empty"
              ? CircleHelp
              : CheckCircle2
    return (
        <div
            className={`flow-notice flow-notice-${kind}`}
            role={kind === "error" ? "alert" : "status"}
        >
            <Icon aria-hidden="true" size={22} strokeWidth={1.5} />
            <div>
                <h2>{title}</h2>
                <p>{message}</p>
                {action}
            </div>
        </div>
    )
}

export function PreviewChecks<Code extends string>({
    checks,
}: {
    checks: PreviewCheck<Code>[]
}) {
    return (
        <ul className="preview-check-list" aria-label="Validation checks">
            {checks.map((check) => {
                const Icon = check.ok ? CheckCircle2 : XCircle
                return (
                    <li
                        key={`${check.code}-${check.rule_id}`}
                        className={
                            check.ok
                                ? "preview-check-ok"
                                : "preview-check-failed"
                        }
                    >
                        <Icon size={16} aria-hidden="true" strokeWidth={1.7} />
                        <span>{check.message}</span>
                        <code>{check.rule_id}</code>
                    </li>
                )
            })}
        </ul>
    )
}

export function ApprovalPath({ steps }: { steps: ApprovalPathStep[] }) {
    if (steps.length === 0) {
        return (
            <FlowNotice
                kind="info"
                title="No route yet"
                message="The approval path will appear after the request details are ready."
            />
        )
    }

    return (
        <ol className="flow-approval-path" aria-label="Approval path">
            {steps.map((step) => (
                <li key={`${step.level}-${step.approver_type}`}>
                    <span className="flow-approval-marker">{step.level}</span>
                    <div className="flow-approval-copy">
                        <strong>
                            {step.approver_name ?? step.approver_type}
                        </strong>
                        <span>{step.approver_type.replaceAll("_", " ")}</span>
                        <p>{step.reason}</p>
                        <div
                            className="flow-rule-ids"
                            aria-label="Matched rules"
                        >
                            {step.rule_ids.map((ruleId) => (
                                <code key={ruleId}>{ruleId}</code>
                            ))}
                        </div>
                    </div>
                </li>
            ))}
        </ol>
    )
}

export function formatUsd(value: string | number): string {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
    }).format(Number(value))
}

export function RetryAction({ onRetry }: { onRetry: () => void }) {
    return (
        <Button type="button" variant="secondary" onClick={onRetry}>
            Try again
        </Button>
    )
}
