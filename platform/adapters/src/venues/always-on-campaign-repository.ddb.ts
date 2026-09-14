/**
 * AlwaysOnCampaignRepositoryDdb — sandbox (hand-maintained).
 */
import type { AlwaysOnCampaignRepository } from "@denselink/services/venues";
import {
  alwaysOnCampaigns,
  ensureDemoSeed,
  id,
  meta,
  nowIso,
  type AlwaysOnCampaignRecord,
} from "../_shared/denselink-sandbox-store.js";

export class AlwaysOnCampaignRepositoryDdb implements AlwaysOnCampaignRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listAlwaysOnCampaigns(input: Parameters<AlwaysOnCampaignRepository["listAlwaysOnCampaigns"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const items = [...alwaysOnCampaigns.values()];
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<AlwaysOnCampaignRepository["listAlwaysOnCampaigns"]>>;
  }

  async createAlwaysOnCampaign(input: Parameters<AlwaysOnCampaignRepository["createAlwaysOnCampaign"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const record: AlwaysOnCampaignRecord = {
      id: id("aon"),
      name: String(raw.name ?? "Always-on campaign"),
      venueProgrammeId: raw.venueProgrammeId ? String(raw.venueProgrammeId) : undefined,
      enabled: raw.enabled !== false,
      inflateConsumerMetrics: false,
      createdAt: nowIso(),
    };
    alwaysOnCampaigns.set(record.id, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<AlwaysOnCampaignRepository["createAlwaysOnCampaign"]>>;
  }
}
