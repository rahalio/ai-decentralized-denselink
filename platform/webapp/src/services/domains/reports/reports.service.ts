/**
 * Reports Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async getDensityReport(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/reports/density${qs}`, { signal });
    return response.data;
  },
  async getContributionRank(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/reports/contribution-rank${qs}`, { signal });
    return response.data;
  },
  async getBetaCohort(signal?: AbortSignal) {
    const response = await apiClient.get<any>("/v1/reports/beta-cohort", { signal });
    return response.data;
  },
  async getSponsorRoiReport(venueProgrammeId: string, signal?: AbortSignal) {
    const qs = `?${new URLSearchParams({ venueProgrammeId })}`;
    const response = await apiClient.get<any>(`/v1/reports/sponsor-roi${qs}`, { signal });
    return response.data;
  },
};

export const reportsService = makeService(raw, "reports");
