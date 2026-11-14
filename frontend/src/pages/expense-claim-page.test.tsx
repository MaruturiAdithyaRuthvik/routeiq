// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { useState } from "react"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { CurrencyCode, ExpenseCategory } from "@/api/types"
import {
    ExpenseLineEditor,
    type ExpenseLineDraft,
} from "@/pages/expense-claim-page"

function TestEditor({ initialLines }: { initialLines?: ExpenseLineDraft[] }) {
    const [lines, setLines] = useState<ExpenseLineDraft[]>(
        initialLines ?? [
            {
                id: "line-1",
                category: ExpenseCategory.MEALS,
                description: "",
                amount: "12.00",
                currency: CurrencyCode.USD,
                receipt: null,
            },
        ],
    )
    return (
        <div>
            <ExpenseLineEditor lines={lines} onChange={setLines} />
            <output>{lines.length} total lines</output>
        </div>
    )
}

afterEach(cleanup)

describe("ExpenseLineEditor", () => {
    it("adds and removes lines while keeping one line in the editor", async () => {
        const user = userEvent.setup()
        render(<TestEditor />)

        expect(screen.getByText("1 of 10 lines")).toBeVisible()
        expect(
            screen.getByRole("button", { name: "Remove line 1" }),
        ).toBeDisabled()

        await user.click(
            screen.getByRole("button", { name: "Add expense line" }),
        )
        expect(screen.getByText("2 of 10 lines")).toBeVisible()
        expect(
            screen.getByRole("button", { name: "Remove line 2" }),
        ).toBeEnabled()

        await user.click(screen.getByRole("button", { name: "Remove line 2" }))
        await waitFor(() =>
            expect(screen.getByText("1 of 10 lines")).toBeVisible(),
        )
        expect(
            screen.getByRole("button", { name: "Remove line 1" }),
        ).toBeDisabled()
    })

    it("caps the editor at ten lines", () => {
        const onChange = vi.fn()
        const lines = Array.from({ length: 10 }, (_, index) => ({
            id: `line-${index + 1}`,
            category: ExpenseCategory.MEALS,
            description: "",
            amount: "12.00",
            currency: CurrencyCode.USD,
            receipt: null,
        }))

        render(<ExpenseLineEditor lines={lines} onChange={onChange} />)

        expect(screen.getByText("10 of 10 lines")).toBeVisible()
        expect(
            screen.getByRole("button", { name: "Add expense line" }),
        ).toBeDisabled()
        expect(onChange).not.toHaveBeenCalled()
    })
})
