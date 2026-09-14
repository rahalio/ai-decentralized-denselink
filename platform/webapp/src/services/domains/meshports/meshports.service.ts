/**
 * Meshports Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async listMeshPorts(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/meshports${qs}`, { signal });
    return response.data;
  },
  async allocateMeshPort(body: { appId: string; preferredPort?: number; sdkVersion?: string }, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/meshports", { body, signal });
    return response.data;
  },
  async getMeshPort(meshPortId: string, signal?: AbortSignal) {
    const response = await apiClient.get<any>(`/v1/meshports/${meshPortId}`, { signal });
    return response.data;
  },
  async revokeMeshPort(meshPortId: string, signal?: AbortSignal) {
    const response = await apiClient.delete<any>(`/v1/meshports/${meshPortId}`, { signal });
    return response.data;
  },
};

export const meshportsService = makeService(raw, "meshports");
