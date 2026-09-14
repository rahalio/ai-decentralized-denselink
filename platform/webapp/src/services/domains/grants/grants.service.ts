/**
 * Grants Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async listGrantProgrammes(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/grants${qs}`, { signal });
    return response.data;
  },
  async createGrantProgramme(body: Record<string, unknown>, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/grants", { body, signal });
    return response.data;
  },
  async getGrantProgramme(grantProgrammeId: string, signal?: AbortSignal) {
    const response = await apiClient.get<any>(`/v1/grants/${grantProgrammeId}`, { signal });
    return response.data;
  },
  async listGrantMilestones(grantProgrammeId: string, params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/grants/${grantProgrammeId}/milestones${qs}`, { signal });
    return response.data;
  },
  async disburseMilestone(milestoneId: string, body?: { note?: string }, signal?: AbortSignal) {
    const response = await apiClient.post<any>(`/v1/milestones/${milestoneId}/disburse`, { body: body ?? {}, signal });
    return response.data;
  },
};

export const grantsService = makeService(raw, "grants");
