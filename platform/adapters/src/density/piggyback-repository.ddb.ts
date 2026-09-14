/**
 * PiggybackRepositoryDdb — sandbox (hand-maintained).
 */
import type { PiggybackRepository } from "@denselink/services/density";
import { meta, piggybackSeed } from "../_shared/denselink-sandbox-store.js";

export class PiggybackRepositoryDdb implements PiggybackRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listPiggybackRegions(input: Parameters<PiggybackRepository["listPiggybackRegions"]>[0]) {
    const raw = input as Record<string, unknown>;
    let items = piggybackSeed();
    if (raw.region) {
      const region = String(raw.region).toLowerCase();
      items = items.filter((r) => r.region.toLowerCase().includes(region));
    }
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<PiggybackRepository["listPiggybackRegions"]>>;
  }
}
