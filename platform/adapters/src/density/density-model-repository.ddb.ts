/**
 * DensityModelRepositoryDdb — sandbox (hand-maintained).
 */
import type { DensityModelRepository } from "@denselink/services/density";
import {
  densityModels,
  ensureDemoSeed,
  id,
  meta,
  nowIso,
  type DensityModelRecord,
} from "../_shared/denselink-sandbox-store.js";

export class DensityModelRepositoryDdb implements DensityModelRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listDensityModels(input: Parameters<DensityModelRepository["listDensityModels"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const items = [...densityModels.values()];
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<DensityModelRepository["listDensityModels"]>>;
  }

  async runDensityModel(input: Parameters<DensityModelRepository["runDensityModel"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const city = String(raw.city ?? "Unknown");
    const pop = Number(raw.populationPerSqKm ?? 0);
    const target = Number(raw.targetPenetrationPercent ?? (pop > 15000 ? 5 : 90));
    const range = Number(raw.nodeRangeMeters ?? 90);
    const required = target;
    const gap = required < 20 && pop > 10000 ? true : required > 80 ? false : required < 10;
    const useful = !gap;
    const estimatedNodes = Math.max(50, Math.round((pop * (required / 100)) / Math.max(1, range / 10)));
    const record: DensityModelRecord = {
      id: id("den"),
      city,
      requiredPenetrationPercent: required,
      estimatedUsefulCoverage: useful,
      gapBelowThreshold: gap,
      estimatedNodes,
      benchmarkNote:
        city.toLowerCase().includes("dhaka") || Number(raw.benchmarkPreset === "dhaka")
          ? "Dhaka-class density — useful blanket needs ~5% penetration."
          : city.toLowerCase().includes("san francisco") || raw.benchmarkPreset === "san_francisco"
            ? "SF-class density — high penetration (~90%) already modelled."
            : `Custom model for ${city}.`,
      createdAt: nowIso(),
    };
    densityModels.set(record.id, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<DensityModelRepository["runDensityModel"]>>;
  }

  async getDensityModel(input: Parameters<DensityModelRepository["getDensityModel"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const densityModelId = String(raw.densityModelId ?? raw.id ?? "");
    const record = densityModels.get(densityModelId);
    if (!record) {
      const err = new Error(`Density model not found: ${densityModelId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<DensityModelRepository["getDensityModel"]>>;
  }
}
