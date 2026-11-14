import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react"
import { useQueryClient } from "@tanstack/react-query"
import { api } from "@/api/client"
import type {
    AuthPersona,
    DemoLoginRequest,
    GetAuthPersonasResponse,
    PostAuthDemoLoginResponse,
} from "@/api/types"
import { useApiQuery } from "@/hooks/use-api"

interface AuthContextValue {
    personas: AuthPersona[]
    persona: AuthPersona | null
    ready: boolean
    error: Error | null
    selectPersona: (employeeId: AuthPersona["employee_id"]) => void
    retry: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const queryClient = useQueryClient()
    const people = useApiQuery<GetAuthPersonasResponse>("/auth/personas")
    const refetchPeople = people.refetch
    const personas = useMemo(() => people.data?.data ?? [], [people.data])
    const [employeeId, setEmployeeId] = useState<AuthPersona["employee_id"]>(
        () => {
            if (typeof window === "undefined") return "EMP-000001"
            return (
                (window.localStorage.getItem("routeiq.persona") as
                    AuthPersona["employee_id"] | null) ?? "EMP-000001"
            )
        },
    )
    const [ready, setReady] = useState(false)
    const [loginError, setLoginError] = useState<Error | null>(null)
    const [attempt, setAttempt] = useState(0)
    const persona =
        personas.find((item) => item.employee_id === employeeId) ??
        personas[0] ??
        null

    useEffect(() => {
        if (!persona) return
        let active = true
        const request: DemoLoginRequest = { employee_id: persona.employee_id }

        void api
            .post<PostAuthDemoLoginResponse, DemoLoginRequest>(
                "/auth/demo-login",
                request,
            )
            .then((response) => {
                if (!active) return
                api.setToken(response.data.access_token)
                setReady(true)
                void queryClient.invalidateQueries({ queryKey: ["api"] })
            })
            .catch((error: unknown) => {
                if (!active) return
                setLoginError(
                    error instanceof Error
                        ? error
                        : new Error("Unable to sign in."),
                )
            })

        return () => {
            active = false
        }
    }, [persona, queryClient, attempt])

    const selectPersona = useCallback((nextId: AuthPersona["employee_id"]) => {
        api.setToken(null)
        setReady(false)
        setLoginError(null)
        setEmployeeId(nextId)
        window.localStorage.setItem("routeiq.persona", nextId)
    }, [])

    const retry = useCallback(() => {
        setLoginError(null)
        setReady(false)
        setAttempt((value) => value + 1)
        void refetchPeople()
    }, [refetchPeople])

    const value = useMemo<AuthContextValue>(
        () => ({
            personas,
            persona,
            ready,
            error: loginError ?? people.error,
            selectPersona,
            retry,
        }),
        [
            personas,
            persona,
            ready,
            loginError,
            people.error,
            selectPersona,
            retry,
        ],
    )

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext)
    if (!context) throw new Error("useAuth must be used within AuthProvider.")
    return context
}
