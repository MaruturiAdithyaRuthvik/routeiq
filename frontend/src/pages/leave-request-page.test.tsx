// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen, within } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
    ApprovalRole,
    ExcludedDateReason,
    type LeaveRequestPreview,
} from "@/api/types"
import { LeavePreviewCard } from "@/pages/leave-request-page"

const preview: LeaveRequestPreview = {
    employee_id: "EMP-000001",
    leave_policy_id: "LPO-001",
    start_date: "2026-11-23",
    end_date: "2026-11-28",
    business_days: 5,
    excluded_dates: [
        { date: "2026-11-28", reason: ExcludedDateReason.WEEKEND },
    ],
    balance_before: 18,
    balance_after: 13,
    checks: [
        {
            code: "BUSINESS_DAYS_POSITIVE",
            ok: true,
            message: "The range contains 5 business days.",
            rule_id: "G4",
        },
        {
            code: "BALANCE_SUFFICIENT",
            ok: true,
            message: "Available balance covers the request.",
            rule_id: "L4",
        },
    ],
    valid: true,
    blocking_reason: null,
    path: [
        {
            level: 1,
            approver_type: ApprovalRole.MANAGER,
            approver_id: "EMP-000002",
            approver_name: "Jordan Patel",
            reason: "Direct manager per G5.",
            rule_ids: ["L5", "G5"],
        },
    ],
}

class ImmediateIntersectionObserver implements IntersectionObserver {
    readonly root = null
    readonly rootMargin = "0px"
    readonly scrollMargin = "0px"
    readonly thresholds = [0]

    constructor(private readonly callback: IntersectionObserverCallback) {}

    observe(target: Element) {
        this.callback(
            [
                {
                    isIntersecting: true,
                    intersectionRatio: 1,
                    target,
                } as IntersectionObserverEntry,
            ],
            this,
        )
    }

    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
        return []
    }
}

beforeEach(() => {
    vi.stubGlobal("IntersectionObserver", ImmediateIntersectionObserver)
})

afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
})

describe("LeavePreviewCard", () => {
    it("renders the business-day, balance, validation, and approval details", () => {
        render(
            <LeavePreviewCard
                preview={preview}
                loading={false}
                error={null}
                onRetry={vi.fn()}
            />,
        )

        expect(
            screen.getByRole("heading", { name: "Decision preview" }),
        ).toBeVisible()
        expect(screen.getByLabelText("5 business days")).toBeVisible()
        expect(screen.getByText("Sat, Nov 28")).toBeVisible()
        expect(screen.getByText("weekend")).toBeVisible()
        const balanceHeading = screen.getByText(
            "Annual leave balance",
        ).parentElement
        expect(within(balanceHeading!).getByRole("heading")).toHaveTextContent(
            "18 days13 days",
        )
        expect(
            screen.getByText("Available balance covers the request."),
        ).toBeVisible()
        expect(screen.getByText("Jordan Patel")).toBeVisible()
        expect(screen.getByText("G5")).toBeVisible()
    })

    it("shows a clear empty state before a preview is available", () => {
        render(
            <LeavePreviewCard
                preview={null}
                loading={false}
                error={null}
                onRetry={vi.fn()}
            />,
        )

        expect(
            screen.getByText(
                "Your dates, balance, and approval path will appear here.",
            ),
        ).toBeVisible()
    })
})
