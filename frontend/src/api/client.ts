import { getFixture } from "@/api/fixtures"
import { ApiErrorCode, type ApiError as ApiProblem } from "@/api/types"

export class ApiError extends Error implements ApiProblem {
    readonly type = "about:blank" as const
    readonly title: string
    readonly status: number
    readonly detail: string
    readonly code: ApiErrorCode

    constructor(problem: ApiProblem) {
        super(problem.detail)
        this.name = "ApiError"
        this.title = problem.title
        this.status = problem.status
        this.detail = problem.detail
        this.code = problem.code
    }
}

type QueryValue = string | number | boolean | null | undefined
export type ApiQuery = Record<string, QueryValue>

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") || "/api/v1"

// Contract fixtures are deterministic and local-development only; builds always use the API.
export const useFixtures =
    import.meta.env.DEV && import.meta.env.VITE_USE_FIXTURES === "true"

function isProblem(value: unknown): value is ApiProblem {
    if (typeof value !== "object" || value === null) return false
    const problem = value as Record<string, unknown>
    const validCodes: readonly string[] = [
        "SELF_APPROVAL",
        "OUT_OF_ORDER",
        "ILLEGAL_TRANSITION",
        "INSUFFICIENT_BALANCE",
        "VALIDATION_FAILED",
        "FORBIDDEN",
        "NOT_FOUND",
        "CONFLICT",
    ]

    return (
        problem.type === "about:blank" &&
        typeof problem.title === "string" &&
        typeof problem.status === "number" &&
        typeof problem.detail === "string" &&
        typeof problem.code === "string" &&
        validCodes.includes(problem.code)
    )
}

export async function parseProblemDetails(
    response: Response,
): Promise<ApiError> {
    let payload: unknown

    try {
        payload = await response.json()
    } catch {
        return new ApiError({
            type: "about:blank",
            title: response.statusText || "Request failed",
            status: response.status,
            detail: `The server returned ${response.status} without a valid problem document.`,
            code: ApiErrorCode.VALIDATION_FAILED,
        })
    }

    if (isProblem(payload)) return new ApiError(payload)

    return new ApiError({
        type: "about:blank",
        title: response.statusText || "Request failed",
        status: response.status,
        detail: `The server returned ${response.status} with an invalid problem document.`,
        code: ApiErrorCode.VALIDATION_FAILED,
    })
}

function queryString(query?: ApiQuery): string {
    if (!query) return ""
    const search = new URLSearchParams()
    for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== null)
            search.set(key, String(value))
    }
    const encoded = search.toString()
    return encoded ? `?${encoded}` : ""
}

function storedToken(): string | null {
    if (typeof window === "undefined") return null
    return window.sessionStorage.getItem("routeiq.access_token")
}

export class ApiClient {
    private token: string | null

    constructor(
        private readonly baseUrl = API_BASE_URL,
        private readonly fixtureMode = useFixtures,
        private readonly fetcher: typeof fetch = globalThis.fetch.bind(globalThis),
    ) {
        this.token = storedToken()
    }

    setToken(token: string | null): void {
        this.token = token
        if (typeof window === "undefined") return
        if (token) window.sessionStorage.setItem("routeiq.access_token", token)
        else window.sessionStorage.removeItem("routeiq.access_token")
    }

    async request<T>(
        path: string,
        options: {
            method?: "GET" | "POST" | "PATCH" | "DELETE"
            query?: ApiQuery
            body?: unknown
            headers?: HeadersInit
        } = {},
    ): Promise<T> {
        const method = options.method ?? "GET"
        const suffix = queryString(options.query)

        if (this.fixtureMode) {
            try {
                return (await getFixture(
                    path,
                    method,
                    options.body,
                    options.query,
                    this.token,
                )) as T
            } catch (error) {
                if (
                    error instanceof Error &&
                    error.name === "FixtureNotFoundError"
                ) {
                    throw new ApiError({
                        type: "about:blank",
                        title: "Fixture not found",
                        status: 404,
                        detail: error.message,
                        code: ApiErrorCode.NOT_FOUND,
                    })
                }
                throw error
            }
        }

        const headers = new Headers(options.headers)
        headers.set("Accept", "application/json, application/problem+json")
        if (options.body !== undefined)
            headers.set("Content-Type", "application/json")
        if (this.token) headers.set("Authorization", `Bearer ${this.token}`)

        const response = await this.fetcher(`${this.baseUrl}${path}${suffix}`, {
            method,
            headers,
            body:
                options.body === undefined
                    ? undefined
                    : JSON.stringify(options.body),
        })

        if (!response.ok) throw await parseProblemDetails(response)
        return (await response.json()) as T
    }

    get<T>(path: string, query?: ApiQuery): Promise<T> {
        return this.request<T>(path, { method: "GET", query })
    }

    post<T, TBody = unknown>(
        path: string,
        body?: TBody,
        headers?: HeadersInit,
    ): Promise<T> {
        return this.request<T>(path, { method: "POST", body, headers })
    }
}

export const api = new ApiClient()
