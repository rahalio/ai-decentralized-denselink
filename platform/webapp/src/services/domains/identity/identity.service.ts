/**
 * Identity Service — minimal hand-maintained stub for auth shell.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async listTenantApiKeys(signal?: AbortSignal) {
    const response = await apiClient.get<any>("/v0/tenants/me/api-keys", { signal });
    return response.data;
  },
};

export const identityService = makeService(raw, "identity");
