/**
 * DensityRepositoryDdb — sandbox density report (hand-maintained).
 */
import type { DensityRepository } from "@denselink/services/reports";
import { ensureDemoSeed, meta, meshPorts, piggybackSeed } from "../_shared/denselink-sandbox-store.js";

export class DensityRepositoryDdb implements DensityRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async getDensityReport(input: Parameters<DensityRepository["getDensityReport"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const city = String(raw.city ?? "Dhaka");
    const piggy = piggybackSeed().find((r) => r.region.toLowerCase() === city.toLowerCase()) ?? piggybackSeed()[0];
    const activeNodes = piggy.contributorApps.reduce((s, a) => s + a.activeNodes, 0);
    return {
      data: {
        city,
        penetrationPercent: city.toLowerCase().includes("francisco") ? 90.82 : 5.1,
        activeNodes,
        piggybackApps: piggy.contributorApps.map((a) => a.appId),
        heatmapBins: 48,
        gapBelowThreshold: !city.toLowerCase().includes("francisco"),
      },
      ...meta(String(raw.correlationId ?? "")),
    } as Awaited<ReturnType<DensityRepository["getDensityReport"]>>;
  }
}
