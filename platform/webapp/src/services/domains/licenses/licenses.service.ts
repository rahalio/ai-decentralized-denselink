/**
 * Licenses Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async listLicenseKeys(params?: Record<string, string>, signal?: AbortSignal) {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    const response = await apiClient.get<any>(`/v1/licenses${qs}`, { signal });
    return response.data;
  },
  async issueLicenseKey(body: { appId: string; developerId: string; tier?: string; meshPort?: number }, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/licenses", { body, signal });
    return response.data;
  },
  async getLicenseKey(licenseId: string, signal?: AbortSignal) {
    const response = await apiClient.get<any>(`/v1/licenses/${licenseId}`, { signal });
    return response.data;
  },
  async revokeLicenseKey(licenseId: string, signal?: AbortSignal) {
    const response = await apiClient.post<any>(`/v1/licenses/${licenseId}/revoke`, { body: {}, signal });
    return response.data;
  },
  async bindLicenseAttestation(licenseId: string, body: { buildFingerprint: string; encryptionProtocol?: string; passed?: boolean }, signal?: AbortSignal) {
    const response = await apiClient.post<any>(`/v1/licenses/${licenseId}/attestation`, { body, signal });
    return response.data;
  },
};

export const licensesService = makeService(raw, "licenses");
