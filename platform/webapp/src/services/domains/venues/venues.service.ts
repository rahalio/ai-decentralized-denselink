/**
 * Venues Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async listVenueProgrammes(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/venues${qs}`, { signal });
    return response.data;
  },
  async createVenueProgramme(body: Record<string, unknown>, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/venues", { body, signal });
    return response.data;
  },
  async getVenueProgramme(venueProgrammeId: string, signal?: AbortSignal) {
    const response = await apiClient.get<any>(`/v1/venues/${venueProgrammeId}`, { signal });
    return response.data;
  },
  async listAlwaysOnCampaigns(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/always-on-campaigns${qs}`, { signal });
    return response.data;
  },
  async createAlwaysOnCampaign(body: Record<string, unknown>, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/always-on-campaigns", { body, signal });
    return response.data;
  },
};

export const venuesService = makeService(raw, "venues");
