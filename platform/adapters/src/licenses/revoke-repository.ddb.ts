/**
 * RevokeRepositoryDdb — sandbox revoke (hand-maintained).
 */
import type { RevokeRepository } from "@denselink/services/licenses";
import { ensureDemoSeed, licenses, meta, nowIso } from "../_shared/denselink-sandbox-store.js";

export class RevokeRepositoryDdb implements RevokeRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async revokeLicenseKey(input: Parameters<RevokeRepository["revokeLicenseKey"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const licenseId = String(raw.licenseId ?? raw.id ?? "");
    const record = licenses.get(licenseId);
    if (!record) {
      const err = new Error(`License not found: ${licenseId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    record.status = "revoked";
    record.revokedAt = nowIso();
    licenses.set(licenseId, record);
    const { secret, ...publicRec } = record;
    return { data: publicRec, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<RevokeRepository["revokeLicenseKey"]>>;
  }
}
