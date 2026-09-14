/**
 * AggregateRepositoryDdb — sandbox (hand-maintained).
 */
import type { AggregateRepository } from "@denselink/services/telemetry";
import {
  ensureDemoSeed,
  id,
  meta,
  nowIso,
  telemetry,
  type TelemetryRecord,
} from "../_shared/denselink-sandbox-store.js";

export class AggregateRepositoryDdb implements AggregateRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async ingestNodeTelemetry(input: Parameters<AggregateRepository["ingestNodeTelemetry"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const record: TelemetryRecord = {
      id: id("tla"),
      appId: String(raw.appId ?? ""),
      licenseId: String(raw.licenseId ?? ""),
      activeNodes: Number(raw.activeNodes ?? 0),
      geoBin: raw.geoBin ? String(raw.geoBin) : undefined,
      sessionDurationMinutesAvg: raw.sessionDurationMinutesAvg != null ? Number(raw.sessionDurationMinutesAvg) : undefined,
      capturedAt: String(raw.capturedAt ?? nowIso()),
      ingestedAt: nowIso(),
    };
    telemetry.set(record.id, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<AggregateRepository["ingestNodeTelemetry"]>>;
  }
}
