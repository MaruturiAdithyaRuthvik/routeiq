import { useEffect, useMemo, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
    ArrowRight,
    FileCheck2,
    FilePlus2,
    Plus,
    ReceiptText,
    ShieldAlert,
    X,
} from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { BlurFade } from "@/components/ui/blur-fade"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import {
    ApprovalPath,
    FlowNotice,
    FlowPageIntro,
    formatUsd,
    PreviewChecks,
    RetryAction,
} from "@/components/flow-primitives"
import type {
    CountryCode,
    CostCenterId,
    CurrencyCode,
    ExpenseCategory,
    ExpenseClaimCreateRequest,
    ExpenseClaimPreview,
    ExpenseClaimPreviewRequest,
    ExpenseLineInput,
    ExpensePreviewFlag,
    ExpensePreviewLine,
    GetCostCentersResponse,
    PostExpenseClaimPreviewResponse,
    PostExpenseClaimResponse,
    ReceiptFileType,
} from "@/api/types"
import {
    AuditFindingCode,
    CountryCode as Country,
    CurrencyCode as Currency,
    ExpenseCategory as Category,
    ReceiptFileType as FileType,
    SystemRole,
} from "@/api/types"
import { useApiMutation, useApiQuery } from "@/hooks/use-api"
import { useAuth } from "@/providers/auth-provider"
import "../styles/flow-pages.css"

export interface ExpenseReceipt {
    fileName: string
    mimeType: string
    sizeBytes: number
    sizeKb: number
    sha256: string
    receiptId: string
    fileType: ReceiptFileType
}

export interface ExpenseLineDraft {
    id: string
    category: ExpenseCategory
    description: string
    amount: string
    currency: CurrencyCode
    receipt: ExpenseReceipt | null
}

function receiptFileType(file: File): ReceiptFileType | null {
    const extension = file.name.split(".").pop()?.toLowerCase()
    const mimeTypes: Record<string, ReceiptFileType> = {
        "application/pdf": FileType.PDF,
        "image/jpeg": FileType.JPEG,
        "image/jpg": FileType.JPG,
        "image/png": FileType.PNG,
        "image/heic": FileType.HEIC,
    }
    if (mimeTypes[file.type]) return mimeTypes[file.type]
    if (extension === "pdf") return FileType.PDF
    if (extension === "jpg") return FileType.JPG
    if (extension === "jpeg") return FileType.JPEG
    if (extension === "png") return FileType.PNG
    if (extension === "heic") return FileType.HEIC
    return null
}

async function hashFile(file: File): Promise<string> {
    const bytes = await file.arrayBuffer()
    const digest = await crypto.subtle.digest("SHA-256", bytes)
    return Array.from(new Uint8Array(digest), (byte) =>
        byte.toString(16).padStart(2, "0"),
    ).join("")
}

export function ExpenseLineEditor({
    lines,
    onChange,
}: {
    lines: ExpenseLineDraft[]
    onChange: (lines: ExpenseLineDraft[]) => void
}) {
    const [receiptErrors, setReceiptErrors] = useState<Record<string, string>>(
        {},
    )
    const nextLineId = useRef(2)
    const receiptVersions = useRef(new Map<string, number>())

    const updateLine = (id: string, patch: Partial<ExpenseLineDraft>) => {
        onChange(
            lines.map((line) =>
                line.id === id ? { ...line, ...patch } : line,
            ),
        )
    }

    const addLine = () => {
        if (lines.length >= 10) return
        const nextId = `line-${nextLineId.current++}`
        onChange([
            ...lines,
            {
                id: nextId,
                category: Category.MEALS,
                description: "",
                amount: "",
                currency: Currency.USD,
                receipt: null,
            },
        ])
    }

    const removeLine = (id: string) => {
        if (lines.length <= 1) return
        receiptVersions.current.set(
            id,
            (receiptVersions.current.get(id) ?? 0) + 1,
        )
        setReceiptErrors((errors) => {
            const next = { ...errors }
            delete next[id]
            return next
        })
        onChange(lines.filter((line) => line.id !== id))
    }

    const selectReceipt = async (id: string, file?: File) => {
        if (!file) return
        const version = (receiptVersions.current.get(id) ?? 0) + 1
        receiptVersions.current.set(id, version)
        const fileType = receiptFileType(file)
        if (!fileType) {
            setReceiptErrors((errors) => ({
                ...errors,
                [id]: "Choose a PDF, JPG, PNG, or HEIC receipt.",
            }))
            updateLine(id, { receipt: null })
            return
        }
        if (file.size === 0) {
            setReceiptErrors((errors) => ({
                ...errors,
                [id]: "This file is empty. Choose another receipt.",
            }))
            updateLine(id, { receipt: null })
            return
        }
        try {
            const sha256 = await hashFile(file)
            if (receiptVersions.current.get(id) !== version) return
            const receipt: ExpenseReceipt = {
                fileName: file.name,
                mimeType: file.type || `application/${fileType.toLowerCase()}`,
                sizeBytes: file.size,
                sizeKb: Math.round((file.size / 1024) * 100) / 100,
                sha256,
                receiptId: `RCT-2026-${sha256.slice(0, 12).toUpperCase()}`,
                fileType,
            }
            setReceiptErrors((errors) => ({ ...errors, [id]: "" }))
            updateLine(id, { receipt })
        } catch (error) {
            if (receiptVersions.current.get(id) !== version) return
            setReceiptErrors((errors) => ({
                ...errors,
                [id]:
                    error instanceof Error
                        ? `Could not read this receipt: ${error.message}`
                        : "Could not read this receipt.",
            }))
            updateLine(id, { receipt: null })
        }
    }

    return (
        <div className="expense-line-editor">
            <AnimatePresence initial={false}>
                {lines.map((line, index) => (
                    <motion.section
                        key={line.id}
                        className="expense-line-card"
                        initial={{ opacity: 0, height: 0, y: 8 }}
                        animate={{ opacity: 1, height: "auto", y: 0 }}
                        exit={{ opacity: 0, height: 0, y: -8 }}
                        transition={{
                            duration: 0.24,
                            ease: [0.28, 0.11, 0.32, 1],
                        }}
                        aria-label={`Expense line ${index + 1}`}
                    >
                        <div className="expense-line-heading">
                            <span className="expense-line-number">
                                Line {index + 1}
                            </span>
                            <button
                                type="button"
                                className="flow-icon-button"
                                aria-label={`Remove line ${index + 1}`}
                                disabled={lines.length === 1}
                                onClick={() => removeLine(line.id)}
                            >
                                <X size={16} aria-hidden="true" />
                            </button>
                        </div>
                        <div className="expense-line-fields">
                            <label className="flow-field">
                                <span>Category</span>
                                <select
                                    value={line.category}
                                    onChange={(event) =>
                                        updateLine(line.id, {
                                            category: event.target
                                                .value as ExpenseCategory,
                                        })
                                    }
                                >
                                    {Object.values(Category).map((category) => (
                                        <option key={category} value={category}>
                                            {category.replaceAll("_", " ")}
                                        </option>
                                    ))}
                                </select>
                            </label>
                            <label className="flow-field">
                                <span>
                                    Description <i>Optional</i>
                                </span>
                                <input
                                    value={line.description}
                                    onChange={(event) =>
                                        updateLine(line.id, {
                                            description: event.target.value,
                                        })
                                    }
                                    placeholder="What was this expense for?"
                                    maxLength={200}
                                />
                            </label>
                            <label className="flow-field">
                                <span>Amount</span>
                                <input
                                    type="number"
                                    inputMode="decimal"
                                    min="0.01"
                                    step="0.01"
                                    value={line.amount}
                                    onChange={(event) =>
                                        updateLine(line.id, {
                                            amount: event.target.value,
                                        })
                                    }
                                    placeholder="0.00"
                                    required
                                />
                            </label>
                            <label className="flow-field">
                                <span>Currency</span>
                                <select
                                    value={line.currency}
                                    onChange={(event) =>
                                        updateLine(line.id, {
                                            currency: event.target
                                                .value as CurrencyCode,
                                        })
                                    }
                                >
                                    {Object.values(Currency).map((currency) => (
                                        <option key={currency} value={currency}>
                                            {currency}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        </div>

                        <div className="expense-receipt-row">
                            <div className="expense-receipt-copy">
                                <ReceiptText size={17} aria-hidden="true" />
                                <div>
                                    <strong>
                                        {line.receipt?.fileName ?? "Receipt"}
                                    </strong>
                                    <span>
                                        {line.receipt
                                            ? `${line.receipt.fileType} · ${(line.receipt.sizeBytes / 1024).toFixed(1)} KB · SHA-256 verified`
                                            : "Upload a file or mark this line as having no receipt."}
                                    </span>
                                </div>
                            </div>
                            <div className="expense-receipt-actions">
                                <label className="flow-upload-button">
                                    <FilePlus2 size={15} aria-hidden="true" />
                                    {line.receipt ? "Replace" : "Choose file"}
                                    <input
                                        type="file"
                                        accept=".pdf,.jpg,.jpeg,.png,.heic,application/pdf,image/jpeg,image/png,image/heic"
                                        aria-label={`Choose receipt for line ${index + 1}`}
                                        onChange={(event) => {
                                            void selectReceipt(
                                                line.id,
                                                event.currentTarget.files?.[0],
                                            )
                                            event.currentTarget.value = ""
                                        }}
                                    />
                                </label>
                                <button
                                    type="button"
                                    className={cn(
                                        "flow-no-receipt",
                                        !line.receipt && "is-selected",
                                    )}
                                    aria-pressed={!line.receipt}
                                    onClick={() => {
                                        receiptVersions.current.set(
                                            line.id,
                                            (receiptVersions.current.get(
                                                line.id,
                                            ) ?? 0) + 1,
                                        )
                                        setReceiptErrors((errors) => ({
                                            ...errors,
                                            [line.id]: "",
                                        }))
                                        updateLine(line.id, { receipt: null })
                                    }}
                                >
                                    No receipt
                                </button>
                            </div>
                        </div>
                        {receiptErrors[line.id] && (
                            <p className="flow-field-error" role="alert">
                                {receiptErrors[line.id]}
                            </p>
                        )}
                        {line.receipt && (
                            <p className="flow-receipt-hash">
                                SHA-256 <code>{line.receipt.sha256}</code>
                            </p>
                        )}
                    </motion.section>
                ))}
            </AnimatePresence>
            <div className="expense-editor-footer">
                <Button
                    type="button"
                    variant="secondary"
                    onClick={addLine}
                    disabled={lines.length >= 10}
                    aria-label="Add expense line"
                >
                    <Plus size={16} aria-hidden="true" />
                    Add a line
                </Button>
                <span>{lines.length} of 10 lines</span>
            </div>
        </div>
    )
}

function flagLabel(flag: ExpensePreviewFlag, line: ExpensePreviewLine): string {
    if (flag.code === AuditFindingCode.POLICY_LIMIT_BREACH) {
        const pct =
            flag.pct_over ??
            Math.round(
                (Number(line.amount_usd) / Number(line.limit_usd) - 1) * 100,
            )
        return `${Math.max(0, pct)}% over limit`
    }
    if (flag.code === AuditFindingCode.MISSING_RECEIPT) return "Receipt needed"
    if (flag.code === AuditFindingCode.DUPLICATE_RECEIPT)
        return "Duplicate receipt"
    return flag.message
}

export function ExpensePreviewCard({
    preview,
    loading,
    error,
    onRetry,
}: {
    preview: ExpenseClaimPreview | null
    loading: boolean
    error: Error | null
    onRetry: () => void
}) {
    return (
        <article
            className="flow-card expense-preview-card"
            aria-labelledby="expense-preview-title"
        >
            <div className="flow-preview-topline">
                <div>
                    <p className="flow-card-eyebrow">Live policy check</p>
                    <h2 id="expense-preview-title">Claim preview</h2>
                </div>
                <span className="flow-preview-status">
                    {loading ? (
                        <span className="flow-pulse-dot" />
                    ) : (
                        <FileCheck2 size={16} />
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
                    aria-label="Calculating expense preview"
                >
                    <Skeleton className="h-10 w-full rounded-xl" />
                    <Skeleton className="h-16 w-full rounded-xl" />
                    <Skeleton className="h-8 w-2/3 rounded-xl" />
                </div>
            )}
            {!preview && !error && !loading && (
                <div className="flow-preview-empty">
                    <ReceiptText size={24} aria-hidden="true" />
                    <p>
                        Your policy checks, FX conversion, and approval path
                        will appear here.
                    </p>
                </div>
            )}
            {preview && (
                <div
                    className={`expense-preview-content${loading ? "is-refreshing" : ""}`}
                >
                    {preview.exception_banner && (
                        <div className="expense-exception-banner" role="status">
                            <ShieldAlert size={18} aria-hidden="true" />
                            <span>{preview.exception_banner}</span>
                        </div>
                    )}
                    <div className="expense-preview-lines">
                        {preview.lines.map((line) => (
                            <div
                                className="expense-preview-line"
                                key={line.line_number}
                            >
                                <div className="expense-preview-line-top">
                                    <strong>Line {line.line_number}</strong>
                                    <span>{formatUsd(line.amount_usd)}</span>
                                </div>
                                <p>
                                    {line.amount} {line.currency} · 1{" "}
                                    {line.currency} = ${line.fx_rate} USD
                                </p>
                                <div className="expense-preview-flags">
                                    {line.flags.length === 0 ? (
                                        <span className="expense-flag expense-flag-good">
                                            Within limit
                                        </span>
                                    ) : (
                                        line.flags.map((flag, index) => (
                                            <span
                                                className={`expense-flag ${
                                                    flag.code ===
                                                    AuditFindingCode.POLICY_LIMIT_BREACH
                                                        ? "expense-flag-warning"
                                                        : "expense-flag-alert"
                                                }`}
                                                key={`${flag.code}-${index}`}
                                            >
                                                {flagLabel(flag, line)}
                                            </span>
                                        ))
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="expense-preview-total">
                        <div>
                            <span>Total in USD</span>
                            <strong>{formatUsd(preview.total_usd)}</strong>
                        </div>
                        <span className="flow-card-caption">
                            Reporting currency · {preview.reporting_currency}
                        </span>
                    </div>
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

const countryNames: Record<CountryCode, string> = {
    IN: "India",
    US: "United States",
    GB: "United Kingdom",
    DE: "Germany",
    SG: "Singapore",
}

function buildLineInput(
    line: ExpenseLineDraft,
    lineNumber: number,
): ExpenseLineInput {
    return {
        line_number: lineNumber,
        category: line.category,
        description: line.description.trim() || null,
        amount: line.amount.trim() || "0.00",
        currency: line.currency,
        receipt_present: line.receipt !== null,
        receipt_id: line.receipt?.receiptId ?? null,
        receipt_hash: line.receipt?.sha256 ?? null,
        file_type: line.receipt?.fileType ?? null,
        size_kb: line.receipt?.sizeKb ?? null,
    }
}

export function ExpenseClaimPage() {
    const { persona } = useAuth()
    const navigate = useNavigate()
    const [merchant, setMerchant] = useState("Northstar Cafe")
    const [merchantCountryOverride, setMerchantCountryOverride] =
        useState<CountryCode | null>(null)
    const merchantCountry =
        merchantCountryOverride ?? persona?.country ?? Country.US
    const [expenseDate, setExpenseDate] = useState("2026-10-15")
    const [costCenterId, setCostCenterId] = useState<CostCenterId | "">("")
    const [lines, setLines] = useState<ExpenseLineDraft[]>([
        {
            id: "line-1",
            category: Category.MEALS,
            description: "Team lunch",
            amount: "120.00",
            currency: Currency.USD,
            receipt: null,
        },
    ])
    const [previewResult, setPreviewResult] = useState<{
        key: string
        data: ExpenseClaimPreview
    } | null>(null)
    const [previewErrorResult, setPreviewErrorResult] = useState<{
        key: string
        error: Error
    } | null>(null)
    const generation = useRef(0)

    const canCreate =
        persona?.system_role === SystemRole.REQUESTER ||
        persona?.system_role === SystemRole.PROCESS_OWNER ||
        persona?.system_role === SystemRole.ADMIN
    const costCenters = useApiQuery<GetCostCentersResponse>(
        "/cost-centers",
        {
            country: persona?.country,
            employee_id: persona?.employee_id,
            page: 1,
            page_size: 100,
        },
        Boolean(persona && canCreate),
    )

    const availableCostCenters = costCenters.data?.data ?? []
    const selectedCostCenter =
        availableCostCenters.find(
            (center) => center.cost_center_id === costCenterId,
        ) ??
        availableCostCenters.find(
            (center) => center.country === persona?.country,
        ) ??
        availableCostCenters[0]
    const selectedCostCenterId =
        selectedCostCenter?.cost_center_id ?? costCenterId

    const payload = useMemo<ExpenseClaimPreviewRequest | null>(() => {
        if (
            !persona ||
            !merchant.trim() ||
            !expenseDate ||
            lines.length === 0 ||
            lines.some(
                (line) =>
                    !line.amount.trim() ||
                    !Number.isFinite(Number(line.amount)) ||
                    Number(line.amount) <= 0,
            )
        ) {
            return null
        }
        return {
            merchant_name: merchant.trim(),
            merchant_country: merchantCountry,
            expense_date: expenseDate,
            cost_center_id: selectedCostCenterId || null,
            lines: lines.map((line, index) => buildLineInput(line, index + 1)),
        }
    }, [
        persona,
        merchant,
        merchantCountry,
        expenseDate,
        selectedCostCenterId,
        lines,
    ])
    const payloadKey = payload ? JSON.stringify(payload) : ""
    const preview =
        previewResult?.key === payloadKey ? previewResult.data : null
    const previewError =
        previewErrorResult?.key === payloadKey ? previewErrorResult.error : null

    const previewMutation = useApiMutation<
        PostExpenseClaimPreviewResponse,
        ExpenseClaimPreviewRequest
    >("/expense-claims/preview")
    const mutatePreview = previewMutation.mutate
    const createMutation = useApiMutation<
        PostExpenseClaimResponse,
        ExpenseClaimCreateRequest
    >("/expense-claims", ["/expense-claims", "/metrics/overview"])

    useEffect(() => {
        const currentGeneration = ++generation.current
        if (!payload || !costCenters.data) return
        const timer = window.setTimeout(() => {
            mutatePreview(payload, {
                onSuccess: (response) => {
                    if (generation.current === currentGeneration) {
                        setPreviewResult({
                            key: payloadKey,
                            data: response.data,
                        })
                    }
                },
                onError: (error) => {
                    if (generation.current === currentGeneration) {
                        setPreviewErrorResult({ key: payloadKey, error })
                    }
                },
            })
        }, 300)
        return () => {
            window.clearTimeout(timer)
            if (generation.current === currentGeneration) {
                generation.current += 1
            }
        }
    }, [payload, payloadKey, costCenters.data, mutatePreview])

    const requestPreview = () => {
        if (!payload) return
        const currentGeneration = ++generation.current
        setPreviewErrorResult(null)
        mutatePreview(payload, {
            onSuccess: (response) => {
                if (generation.current === currentGeneration) {
                    setPreviewResult({ key: payloadKey, data: response.data })
                }
            },
            onError: (error) => {
                if (generation.current === currentGeneration) {
                    setPreviewErrorResult({ key: payloadKey, error })
                }
            },
        })
    }

    const submit = () => {
        if (!payload || !preview || preview.checks.some((check) => !check.ok))
            return
        createMutation.mutate(payload, {
            onSuccess: (response) => {
                toast.success("Your expense claim has been submitted.")
                navigate(`/expense-claims/${response.data.expense_claim_id}`)
            },
            onError: (error) =>
                toast.error("The claim could not be submitted.", {
                    description: error.message,
                }),
        })
    }

    const blockingCheck = preview?.checks.find((check) => !check.ok)
    const invalidReason = !payload
        ? "Add a merchant, date, and at least one valid line to preview this claim."
        : !preview
          ? "Waiting for the live policy check before this claim can be sent."
          : blockingCheck
            ? `This claim cannot be submitted: ${blockingCheck.message}`
            : null
    const queryError = costCenters.error
    const loading =
        previewMutation.isPending ||
        (!preview && Boolean(payload) && Boolean(costCenters.data))

    if (!persona) {
        return (
            <FlowNotice
                kind="error"
                title="Your session is not ready."
                message="Sign in with a RouteIQ persona to create an expense claim."
            />
        )
    }

    if (!canCreate) {
        return (
            <div className="flow-page-stack">
                <FlowPageIntro
                    eyebrow="Expenses · New claim"
                    title="Every detail, accounted for."
                    description="Build a claim with clear policy checks before it moves forward."
                />
                <FlowNotice
                    kind="info"
                    title="Claim creation is not available for this persona."
                    message="Switch to a requester, process owner, or admin persona to create an expense claim."
                />
            </div>
        )
    }

    return (
        <div className="flow-page-stack">
            <FlowPageIntro
                eyebrow="Expenses · New claim"
                title="Every detail, accounted for."
                description="Build a claim with clear policy checks before it moves forward."
            />

            {queryError && (
                <FlowNotice
                    kind="error"
                    title="Cost centers could not load."
                    message={queryError.message}
                    action={
                        <RetryAction
                            onRetry={() => void costCenters.refetch()}
                        />
                    }
                />
            )}

            <div className="flow-form-layout expense-form-layout">
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
                                        The basics
                                    </p>
                                    <h2>Where and when?</h2>
                                </div>
                            </div>
                            <div className="flow-form-two-col">
                                <label className="flow-field">
                                    <span>Merchant</span>
                                    <input
                                        value={merchant}
                                        onChange={(event) =>
                                            setMerchant(event.target.value)
                                        }
                                        maxLength={120}
                                        required
                                    />
                                </label>
                                <label className="flow-field">
                                    <span>Expense date</span>
                                    <input
                                        type="date"
                                        value={expenseDate}
                                        max="2026-10-22"
                                        onChange={(event) =>
                                            setExpenseDate(event.target.value)
                                        }
                                        required
                                    />
                                </label>
                                <label className="flow-field">
                                    <span>Merchant country</span>
                                    <select
                                        value={merchantCountry}
                                        onChange={(event) =>
                                            setMerchantCountryOverride(
                                                event.target
                                                    .value as CountryCode,
                                            )
                                        }
                                    >
                                        {Object.entries(countryNames).map(
                                            ([code, name]) => (
                                                <option key={code} value={code}>
                                                    {name}
                                                </option>
                                            ),
                                        )}
                                    </select>
                                </label>
                                <label className="flow-field">
                                    <span>Cost center</span>
                                    <select
                                        value={selectedCostCenterId}
                                        onChange={(event) =>
                                            setCostCenterId(
                                                event.target
                                                    .value as CostCenterId,
                                            )
                                        }
                                        required
                                        disabled={
                                            costCenters.isLoading ||
                                            !costCenters.data?.data.length
                                        }
                                    >
                                        <option value="" disabled>
                                            Select a cost center
                                        </option>
                                        {(costCenters.data?.data ?? []).map(
                                            (center) => (
                                                <option
                                                    key={center.cost_center_id}
                                                    value={
                                                        center.cost_center_id
                                                    }
                                                >
                                                    {center.name}
                                                </option>
                                            ),
                                        )}
                                    </select>
                                </label>
                            </div>
                        </section>
                    </BlurFade>

                    <BlurFade inView delay={0.06} duration={0.55}>
                        <section className="flow-card flow-form-card">
                            <div className="flow-form-section-heading">
                                <span className="flow-section-index">02</span>
                                <div>
                                    <p className="flow-card-eyebrow">
                                        The details
                                    </p>
                                    <h2>What did you spend?</h2>
                                </div>
                            </div>
                            <p className="flow-field-hint expense-line-hint">
                                Add up to 10 lines. Receipts are hashed locally;
                                the file itself never leaves this form.
                            </p>
                            <ExpenseLineEditor
                                lines={lines}
                                onChange={setLines}
                            />
                        </section>
                    </BlurFade>
                </form>

                <aside className="flow-preview-column">
                    <div className="flow-sticky-preview">
                        <ExpensePreviewCard
                            preview={preview}
                            loading={loading}
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
                                    !preview ||
                                    Boolean(blockingCheck) ||
                                    createMutation.isPending ||
                                    previewMutation.isPending
                                }
                            >
                                {createMutation.isPending
                                    ? "Submitting…"
                                    : "Submit claim"}
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
                                    "Your claim is ready to submit."}
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
