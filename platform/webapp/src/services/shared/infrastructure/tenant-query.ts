/**
 * Tenant-scoped React Query helpers for generated hooks.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { getEffectiveOrgId } from "./tenant-state";
import type { ApiError } from "./types";

export function useTenantQuery<T>(
  queryKey: (string | undefined)[],
  queryFn: (orgId: string, signal?: AbortSignal) => Promise<T>,
  options?: Omit<UseQueryOptions<T, ApiError>, "queryKey" | "queryFn"> & {
    enabled?: boolean;
  },
) {
  const orgId = getEffectiveOrgId();
  const tenantKey = orgId ? [...queryKey, "org", orgId] : queryKey;
  const enabled = !!orgId && options?.enabled !== false;

  return useQuery<T, ApiError>({
    ...options,
    queryKey: tenantKey as any,
    enabled,
    queryFn: ({ signal }) => {
      if (!orgId) throw new Error("Organization ID is required");
      return queryFn(orgId, signal);
    },
  });
}

export function useTenantMutation<TData, TVariables>(
  mutationFn: (orgId: string, variables: TVariables) => Promise<TData>,
  options?: {
    invalidateQueries?: unknown[][];
    onSuccess?: (data: TData) => void;
  },
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: TVariables) => {
      const orgId = getEffectiveOrgId();
      if (!orgId) throw new Error("Organization ID is required");
      return mutationFn(orgId, variables);
    },
    onSuccess: (data) => {
      for (const key of options?.invalidateQueries || []) {
        void queryClient.invalidateQueries({ queryKey: key as any });
      }
      options?.onSuccess?.(data);
    },
  });
}

export function useTenantQueryInvalidation() {
  const queryClient = useQueryClient();
  return (queryKey: unknown[]) =>
    queryClient.invalidateQueries({ queryKey: queryKey as any });
}
