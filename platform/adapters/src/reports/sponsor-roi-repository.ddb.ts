/**
 * SponsorRoiRepositoryDdb — sandbox (hand-maintained).
 */
import type { SponsorRoiRepository } from "@denselink/services/reports";
import { ensureDemoSeed, meta, venues } from "../_shared/denselink-sandbox-store.js";

export class SponsorRoiRepositoryDdb implements SponsorRoiRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async getSponsorRoiReport(input: Parameters<SponsorRoiRepository["getSponsorRoiReport"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const venueProgrammeId = String(raw.venueProgrammeId ?? "");
    const venue = venues.get(venueProgrammeId) ?? [...venues.values()][0];
    if (!venue) {
      const err = new Error(`Venue programme not found: ${venueProgrammeId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    return {
      data: {
        venueProgrammeId: venue.id,
        venueName: venue.name,
        activeNodes: venue.activeNodes ?? 0,
        sessions: Math.round((venue.activeNodes ?? 0) * 1.4),
        avgSessionMinutes: venue.sessionDurationMinutesAvg ?? 0,
        affordabilityBenchmarkNote:
          "Contextual affordability narrative (90% price-drop goal) — not a guaranteed SLA.",
        heatmapBins: venue.heatmapBins ?? 36,
      },
      ...meta(String(raw.correlationId ?? "")),
    } as Awaited<ReturnType<SponsorRoiRepository["getSponsorRoiReport"]>>;
  }
}
