import { describe, expect, it, vi } from "vitest"
import { ApiClient, ApiError, parseProblemDetails } from "@/api/client"
import { ApiErrorCode, type GetAuthPersonasResponse } from "@/api/types"

describe("API client", () => {
    it("parses RFC 7807 problem+json into a typed ApiError", async () => {
        const response = new Response(
            JSON.stringify({
                type: "about:blank",
                title: "Out-of-order approval",
                status: 409,
                detail: "The next approval step is not ready.",
                code: "OUT_OF_ORDER",
            }),
            {
                status: 409,
                headers: { "Content-Type": "application/problem+json" },
            },
        )

        const error = await parseProblemDetails(response)

        expect(error).toBeInstanceOf(ApiError)
        expect(error).toMatchObject({
            status: 409,
            code: ApiErrorCode.OUT_OF_ORDER,
            detail: "The next approval step is not ready.",
        })
    })

    it("surfaces malformed error documents as typed API errors", async () => {
        const error = await parseProblemDetails(
            new Response("not json", {
                status: 502,
                statusText: "Bad Gateway",
            }),
        )

        expect(error).toBeInstanceOf(ApiError)
        expect(error.status).toBe(502)
        expect(error.code).toBe(ApiErrorCode.VALIDATION_FAILED)
        expect(error.detail).toContain("without a valid problem document")
    })

    it("sends the persona JWT and preserves false query values", async () => {
        const fetcher = vi
            .fn<typeof fetch>()
            .mockResolvedValue(
                new Response(JSON.stringify({ data: [] }), { status: 200 }),
            )
        const client = new ApiClient("/api/v1", false, fetcher)
        client.setToken("demo-jwt")

        await client.get<GetAuthPersonasResponse>("/auth/personas", {
            active: false,
            page: 1,
        })

        expect(fetcher).toHaveBeenCalledWith(
            "/api/v1/auth/personas?active=false&page=1",
            expect.objectContaining({ method: "GET" }),
        )
        const options = fetcher.mock.calls[0]?.[1]
        expect(new Headers(options?.headers).get("Authorization")).toBe(
            "Bearer demo-jwt",
        )
    })

    it("serves repeatable contract fixtures when explicitly enabled", async () => {
        const client = new ApiClient("/api/v1", true)
        const first = await client.get<GetAuthPersonasResponse>(
            "/auth/personas",
            {
                page: 1,
                page_size: 5,
            },
        )
        const second = await client.get<GetAuthPersonasResponse>(
            "/auth/personas",
            {
                page: 1,
                page_size: 5,
            },
        )

        expect(first).toEqual(second)
        expect(first.meta).toEqual({ page: 1, page_size: 5, total: 5 })
        expect(first.data[0]).toMatchObject({
            employee_id: "EMP-000001",
            display_name: "Avery Chen",
            system_role: "REQUESTER",
        })
    })
})
