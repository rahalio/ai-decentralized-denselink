/**
 * VenueRepositoryDdb — sandbox (hand-maintained).
 */
import type { VenueRepository } from "@denselink/services/venues";
import {
  ensureDemoSeed,
  id,
  meta,
  nowIso,
  venues,
  type VenueProgrammeRecord,
} from "../_shared/denselink-sandbox-store.js";

export class VenueRepositoryDdb implements VenueRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listVenueProgrammes(input: Parameters<VenueRepository["listVenueProgrammes"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    let items = [...venues.values()];
    if (raw.venueType) items = items.filter((v) => v.venueType === raw.venueType);
    return { data: { items, nextCursor: undefined }, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<VenueRepository["listVenueProgrammes"]>>;
  }

  async createVenueProgramme(input: Parameters<VenueRepository["createVenueProgramme"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const record: VenueProgrammeRecord = {
      id: id("ven"),
      venueType: String(raw.venueType ?? "stadium"),
      name: String(raw.name ?? "Venue programme"),
      city: raw.city ? String(raw.city) : undefined,
      activeNodeTarget: raw.activeNodeTarget != null ? Number(raw.activeNodeTarget) : 100,
      status: "enrolled",
      eventWindowStart: raw.eventWindowStart ? String(raw.eventWindowStart) : undefined,
      eventWindowEnd: raw.eventWindowEnd ? String(raw.eventWindowEnd) : undefined,
      activeNodes: 0,
      sessionDurationMinutesAvg: 0,
      heatmapBins: 36,
      createdAt: nowIso(),
    };
    venues.set(record.id, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<VenueRepository["createVenueProgramme"]>>;
  }

  async getVenueProgramme(input: Parameters<VenueRepository["getVenueProgramme"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const venueProgrammeId = String(raw.venueProgrammeId ?? raw.id ?? "");
    const record = venues.get(venueProgrammeId);
    if (!record) {
      const err = new Error(`Venue programme not found: ${venueProgrammeId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<VenueRepository["getVenueProgramme"]>>;
  }
}
