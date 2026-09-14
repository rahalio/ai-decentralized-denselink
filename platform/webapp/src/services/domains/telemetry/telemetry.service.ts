/**
 * Telemetry Service — hand-maintained API client.
 */
import { apiClient } from "@/services/shared/infrastructure";
import { makeService } from "@/services/shared/infrastructure/service-wrapper";

const raw = {
  async ingestNodeTelemetry(body: Record<string, unknown>, signal?: AbortSignal) {
    const response = await apiClient.post<any>("/v1/telemetry/aggregates", { body, signal });
    return response.data;
  },
};

export const telemetryService = makeService(raw, "telemetry");
