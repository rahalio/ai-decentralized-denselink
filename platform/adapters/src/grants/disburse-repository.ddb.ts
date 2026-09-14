/**
 * DisburseRepositoryDdb — sandbox (hand-maintained).
 */
import type { DisburseRepository } from "@denselink/services/grants";
import { ensureDemoSeed, meta, milestones, nowIso } from "../_shared/denselink-sandbox-store.js";

export class DisburseRepositoryDdb implements DisburseRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async disburseMilestone(input: Parameters<DisburseRepository["disburseMilestone"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const milestoneId = String(raw.milestoneId ?? raw.id ?? "");
    const record = milestones.get(milestoneId);
    if (!record) {
      const err = new Error(`Milestone not found: ${milestoneId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    record.status = "disbursed";
    record.reviewedAt = nowIso();
    record.disbursedAt = nowIso();
    milestones.set(milestoneId, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<DisburseRepository["disburseMilestone"]>>;
  }
}
