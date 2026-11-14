import { Component, type ErrorInfo, type ReactNode } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { MotionConfig } from "framer-motion"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "sonner"
import {
    AnalyticsPage,
    ContractPage,
    DesignPage,
    NotFoundPage,
    WorkflowPlaceholder,
} from "@/pages"
import { OverviewPage } from "@/pages/overview-page"
import { LeaveRequestPage } from "@/pages/leave-request-page"
import { ExpenseClaimPage } from "@/pages/expense-claim-page"
import { AppShell } from "@/components/app-shell"
import { Button, TooltipProvider } from "@/components/ui/primitives"
import { AuthProvider } from "@/providers/auth-provider"
import { ThemeProvider, useTheme } from "@/providers/theme-provider"
import { SystemRole } from "@/api/types"
import "./App.css"

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 1,
            staleTime: 30_000,
            refetchOnWindowFocus: false,
        },
    },
})

interface ErrorBoundaryState {
    error: Error | null
}

class AppErrorBoundary extends Component<
    { children: ReactNode },
    ErrorBoundaryState
> {
    state: ErrorBoundaryState = { error: null }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { error }
    }

    componentDidCatch(error: Error, info: ErrorInfo): void {
        console.error("RouteIQ render error", error, info.componentStack)
    }

    render() {
        if (this.state.error) {
            return (
                <main className="app-main">
                    <div className="state-card" role="alert">
                        <h1 className="text-3xl font-semibold tracking-tight">
                            This view needs a refresh.
                        </h1>
                        <p className="mt-2">{this.state.error.message}</p>
                        <Button
                            className="mt-5"
                            onClick={() => window.location.reload()}
                        >
                            Reload RouteIQ
                        </Button>
                    </div>
                </main>
            )
        }
        return this.props.children
    }
}

function ToastLayer() {
    const { theme } = useTheme()
    return (
        <Toaster
            theme={theme}
            position="bottom-right"
            className="toast-root"
            closeButton
            toastOptions={{
                classNames: {
                    toast: "toast-root",
                    title: "font-semibold",
                    description: "text-muted-foreground",
                },
            }}
        />
    )
}

function RouteTable() {
    const analystRoles = [SystemRole.ANALYST, SystemRole.ADMIN]
    const operationalRoles = [
        SystemRole.PROCESS_OWNER,
        SystemRole.ANALYST,
        SystemRole.ADMIN,
    ]

    return (
        <Routes>
            <Route element={<AppShell />}>
                <Route index element={<OverviewPage />} />
                <Route path="overview" element={<OverviewPage />} />
                <Route
                    path="leave"
                    element={<Navigate to="/leave-requests" replace />}
                />
                <Route
                    path="expenses"
                    element={<Navigate to="/expense-claims" replace />}
                />
                <Route
                    path="requests"
                    element={<Navigate to="/leave-requests" replace />}
                />
                <Route path="leave/new" element={<LeaveRequestPage />} />
                <Route path="expenses/new" element={<ExpenseClaimPage />} />
                <Route
                    path="expense-claims/new"
                    element={<Navigate to="/expenses/new" replace />}
                />
                <Route
                    path="leave-requests"
                    element={
                        <ContractPage
                            title="Your requests"
                            description="See each request, its status, and what happens next."
                            endpoint="/leave-requests"
                        />
                    }
                />
                <Route
                    path="leave-requests/:id"
                    element={
                        <ContractPage
                            title="Leave request"
                            description="A clear record of the request and its approval history."
                            endpoint={(id) => `/leave-requests/${id ?? ""}`}
                        />
                    }
                />
                <Route
                    path="expense-claims"
                    element={
                        <ContractPage
                            title="Expense claims"
                            description="A considered view of submitted claims and their status."
                            endpoint="/expense-claims"
                        />
                    }
                />
                <Route
                    path="expense-claims/:id"
                    element={
                        <ContractPage
                            title="Expense claim"
                            description="Every line, policy check, and approval in one place."
                            endpoint={(id) => `/expense-claims/${id ?? ""}`}
                        />
                    }
                />
                <Route
                    path="approvals/inbox"
                    element={
                        <ContractPage
                            title="Approval inbox"
                            description="The next decision, with the context to make it well."
                            endpoint="/approvals/inbox"
                            roles={[
                                SystemRole.APPROVER,
                                SystemRole.PROCESS_OWNER,
                                SystemRole.ADMIN,
                            ]}
                        />
                    }
                />
                <Route
                    path="approval-steps/:id/decision"
                    element={
                        <WorkflowPlaceholder
                            title="A thoughtful decision."
                            description="The approval step is ready for its decision form."
                            operation="POST /approval-steps/{id}/decision"
                            roles={[
                                SystemRole.APPROVER,
                                SystemRole.PROCESS_OWNER,
                                SystemRole.ADMIN,
                            ]}
                        />
                    }
                />
                <Route
                    path="reimbursements"
                    element={
                        <ContractPage
                            title="Reimbursements"
                            description="Follow approved expenses through to payment."
                            endpoint="/reimbursements"
                            roles={[
                                SystemRole.REQUESTER,
                                SystemRole.PROCESS_OWNER,
                                SystemRole.ANALYST,
                                SystemRole.ADMIN,
                            ]}
                        />
                    }
                />
                <Route
                    path="reimbursements/:id"
                    element={
                        <ContractPage
                            title="Reimbursement"
                            description="A complete record of the scheduled payment."
                            endpoint={(id) => `/reimbursements/${id ?? ""}`}
                            roles={[
                                SystemRole.REQUESTER,
                                SystemRole.PROCESS_OWNER,
                                SystemRole.ANALYST,
                                SystemRole.ADMIN,
                            ]}
                        />
                    }
                />
                <Route
                    path="audit/findings"
                    element={
                        <ContractPage
                            title="Audit findings"
                            description="Operational signals that deserve a closer look."
                            endpoint="/audit/findings"
                            roles={operationalRoles}
                        />
                    }
                />
                <Route
                    path="audit/findings/:id"
                    element={
                        <ContractPage
                            title="Finding details"
                            description="Understand the signal and its complete history."
                            endpoint={(id) => `/audit/findings/${id ?? ""}`}
                            roles={operationalRoles}
                        />
                    }
                />
                <Route
                    path="audit/run"
                    element={
                        <WorkflowPlaceholder
                            title="A clearer picture starts here."
                            description="Run operational checks against the current scenario."
                            operation="POST /audit/run · 202 Accepted"
                            roles={[
                                SystemRole.ANALYST,
                                SystemRole.PROCESS_OWNER,
                                SystemRole.ADMIN,
                            ]}
                        />
                    }
                />
                <Route
                    path="evaluation/summary"
                    element={
                        <ContractPage
                            title="Decision quality"
                            description="Measure decision and approval-path accuracy."
                            endpoint="/evaluation/summary"
                            roles={analystRoles}
                        />
                    }
                />
                <Route
                    path="evaluation/misses"
                    element={
                        <ContractPage
                            title="Evaluation misses"
                            description="Review expected outcomes alongside actual results."
                            endpoint="/evaluation/misses"
                            roles={analystRoles}
                        />
                    }
                />
                <Route path="metrics/overview" element={<AnalyticsPage />} />
                <Route
                    path="dataset/manifest"
                    element={
                        <ContractPage
                            title="Scenario manifest"
                            description="Source, scale, and validation status for this dataset."
                            endpoint="/dataset/manifest"
                            roles={operationalRoles}
                        />
                    }
                />
                <Route
                    path="employees"
                    element={
                        <ContractPage
                            title="People"
                            description="A synthetic view of teams and the roles behind each decision."
                            endpoint="/employees"
                        />
                    }
                />
                <Route
                    path="employees/:id"
                    element={
                        <ContractPage
                            title="Employee profile"
                            description="Reference details for a RouteIQ employee."
                            endpoint={(id) => `/employees/${id ?? ""}`}
                        />
                    }
                />
                <Route
                    path="employees/:id/leave-balances"
                    element={
                        <ContractPage
                            title="Leave balances"
                            description="Balance snapshots derived from the leave ledger."
                            endpoint={(id) =>
                                `/employees/${id ?? ""}/leave-balances`
                            }
                            roles={[
                                SystemRole.REQUESTER,
                                SystemRole.PROCESS_OWNER,
                                SystemRole.ADMIN,
                            ]}
                        />
                    }
                />
                <Route
                    path="cost-centers"
                    element={
                        <ContractPage
                            title="Cost centers"
                            description="A concise view of budgets, ownership, and spend."
                            endpoint="/cost-centers"
                        />
                    }
                />
                <Route
                    path="holidays"
                    element={
                        <ContractPage
                            title="Holidays"
                            description="Illustrative calendar dates used for business-day calculations."
                            endpoint="/holidays"
                        />
                    }
                />
                <Route
                    path="leave-policies"
                    element={
                        <ContractPage
                            title="Leave policies"
                            description="The rules that shape every request."
                            endpoint="/leave-policies"
                        />
                    }
                />
                <Route
                    path="expense-policies"
                    element={
                        <ContractPage
                            title="Expense policies"
                            description="Limits and receipt thresholds, clearly presented."
                            endpoint="/expense-policies"
                        />
                    }
                />
                <Route
                    path="approval-rules"
                    element={
                        <ContractPage
                            title="Approval rules"
                            description="Understand how a request finds its next reviewer."
                            endpoint="/approval-rules"
                        />
                    }
                />
                <Route
                    path="personas"
                    element={
                        <ContractPage
                            title="Demo personas"
                            description="Synthetic identities available in the RouteIQ workspace."
                            endpoint="/auth/personas"
                            eyebrow="Reference · Authentication"
                        />
                    }
                />
                <Route path="design" element={<DesignPage />} />
                <Route path="*" element={<NotFoundPage />} />
            </Route>
        </Routes>
    )
}

export default function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <ThemeProvider>
                    <AuthProvider>
                        <TooltipProvider>
                            <AppErrorBoundary>
                                <MotionConfig reducedMotion="user">
                                    <RouteTable />
                                </MotionConfig>
                            </AppErrorBoundary>
                            <ToastLayer />
                        </TooltipProvider>
                    </AuthProvider>
                </ThemeProvider>
            </BrowserRouter>
        </QueryClientProvider>
    )
}
