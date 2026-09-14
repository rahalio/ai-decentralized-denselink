/**
 * GrantRepositoryDdb — sandbox (hand-maintained).
 */
import type { GrantRepository } from "@denselink/services/grants";
import {
  ensureDemoSeed,
  grants,
  id,
  meta,
  nowIso,
  type GrantProgrammeRecord,
} from "../_shared/denselink-sandbox-store.js";

export class GrantRepositoryDdb implements GrantRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listGrantProgrammes(input: Parameters<GrantRepository["listGrantProgrammes"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const items = [...grants.values()];
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<GrantRepository["listGrantProgrammes"]>>;
  }

  async createGrantProgramme(input: Parameters<GrantRepository["createGrantProgramme"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const record: GrantProgrammeRecord = {
      id: id("grt"),
      name: String(raw.name ?? "Grant programme"),
      milestoneMetric: String(raw.milestoneMetric ?? "active_nodes"),
      milestoneThreshold: raw.milestoneThreshold != null ? Number(raw.milestoneThreshold) : undefined,
      rewardAmount: Number(raw.rewardAmount ?? 0),
      status: "open",
      densityModelId: raw.densityModelId ? String(raw.densityModelId) : undefined,
      createdAt: nowIso(),
    };
    grants.set(record.id, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<GrantRepository["createGrantProgramme"]>>;
  }

  async getGrantProgramme(input: Parameters<GrantRepository["getGrantProgramme"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const grantProgrammeId = String(raw.grantProgrammeId ?? raw.id ?? "");
    const record = grants.get(grantProgrammeId);
    if (!record) {
      const err = new Error(`Grant programme not found: ${grantProgrammeId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<GrantRepository["getGrantProgramme"]>>;
  }
}
