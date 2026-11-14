import {
    useMutation,
    useQuery,
    useQueryClient,
    type UseMutationOptions,
} from "@tanstack/react-query"
import { api, type ApiQuery } from "@/api/client"

export function useApiQuery<TData>(
    path: string,
    query?: ApiQuery,
    enabled = true,
) {
    return useQuery({
        queryKey: ["api", path, query],
        queryFn: () => api.get<TData>(path, query),
        enabled,
    })
}

export function useApiMutation<TData, TVariables>(
    path: string | ((variables: TVariables) => string),
    invalidate: string[] = [],
    options?: Omit<UseMutationOptions<TData, Error, TVariables>, "mutationFn">,
) {
    const queryClient = useQueryClient()
    return useMutation({
        ...options,
        mutationFn: (variables) =>
            api.post<TData, TVariables>(
                typeof path === "function" ? path(variables) : path,
                variables,
            ),
        onSuccess: async (...args) => {
            await Promise.all(
                invalidate.map((prefix) =>
                    queryClient.invalidateQueries({
                        queryKey: ["api", prefix],
                    }),
                ),
            )
            await options?.onSuccess?.(...args)
        },
    })
}
