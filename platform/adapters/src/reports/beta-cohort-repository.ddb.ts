/**
 * BetaCohortRepositoryDdb — sandbox (hand-maintained).
 */
import type { BetaCohortRepository } from "@denselink/services/reports";
import { ensureDemoSeed, licenses, meshPorts, meta } from "../_shared/denselink-sandbox-store.js";

export class BetaCohortRepositoryDdb implements BetaCohortRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async getBetaCohort(input: Parameters<BetaCohortRepository["getBetaCohort"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const cohortSize = [...licenses.values()].filter((l) => l.status === "active").length;
    const collisions = [...meshPorts.values()].filter((p) => p.collisionBlocked).length;
    return {
      data: {
        cohortSize,
        privateBetaProjects: 80,
        readyForPublicBeta: cohortSize >= 80 && collisions === 0,
        averageDensityContribution: 210,
        collisionIncidents: collisions,
      },
      ...meta(String(raw.correlationId ?? "")),
    } as Awaited<ReturnType<BetaCohortRepository["getBetaCohort"]>>;
  }
}
