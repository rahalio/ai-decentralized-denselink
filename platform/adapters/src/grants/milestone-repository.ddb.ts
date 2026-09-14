/**
 * MilestoneRepositoryDdb — sandbox (hand-maintained).
 */
import type { MilestoneRepository } from "@denselink/services/grants";
import { ensureDemoSeed, meta, milestones } from "../_shared/denselink-sandbox-store.js";

export class MilestoneRepositoryDdb implements MilestoneRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listGrantMilestones(input: Parameters<MilestoneRepository["listGrantMilestones"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const grantProgrammeId = String(raw.grantProgrammeId ?? "");
    const items = [...milestones.values()].filter((m) => m.grantProgrammeId === grantProgrammeId);
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<MilestoneRepository["listGrantMilestones"]>>;
  }
}
