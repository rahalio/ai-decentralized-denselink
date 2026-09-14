/**
 * Density Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async listDensityModels(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/density-models${qs}`, { signal });
    return response.data;
  },
  async runDensityModel(body: Record<string, unknown>, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/density-models", { body, signal });
    return response.data;
  },
  async getDensityModel(densityModelId: string, signal?: AbortSignal) {
    const response = await apiClient.get<any>(`/v1/density-models/${densityModelId}`, { signal });
    return response.data;
  },
  async listPiggybackRegions(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/piggyback${qs}`, { signal });
    return response.data;
  },
};

export const densityService = makeService(raw, "density");
