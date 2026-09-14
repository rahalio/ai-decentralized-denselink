/**
 * ContributionRankRepositoryDdb — sandbox (hand-maintained).
 */
import type { ContributionRankRepository } from "@denselink/services/reports";
import { ensureDemoSeed, licenses, meshPorts, meta, piggybackSeed } from "../_shared/denselink-sandbox-store.js";

export class ContributionRankRepositoryDdb implements ContributionRankRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async getContributionRank(input: Parameters<ContributionRankRepository["getContributionRank"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const apps = piggybackSeed().flatMap((r) => r.contributorApps);
    const byApp = new Map<string, { activeNodes: number; densityRank: number }>();
    for (const a of apps) {
      const prev = byApp.get(a.appId);
      byApp.set(a.appId, {
        activeNodes: (prev?.activeNodes ?? 0) + a.activeNodes,
        densityRank: Math.min(prev?.densityRank ?? a.densityRank, a.densityRank),
      });
    }
    const items = [...byApp.entries()]
      .map(([appId, v], idx) => {
        const port = [...meshPorts.values()].find((p) => p.appId === appId);
        const lic = [...licenses.values()].find((l) => l.appId === appId);
        return {
          rank: idx + 1,
          appId,
          sdkVersion: port?.sdkVersion ?? "1.0.0",
          meshPort: port?.port,
          densityContributionScore: v.activeNodes,
          activeNodes: v.activeNodes,
          tier: lic?.tier,
        };
      })
      .sort((a, b) => b.densityContributionScore - a.densityContributionScore)
      .map((item, idx) => ({ ...item, rank: idx + 1 }));
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<ContributionRankRepository["getContributionRank"]>>;
  }
}
