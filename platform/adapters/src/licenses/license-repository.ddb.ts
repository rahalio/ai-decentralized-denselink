/**
 * LicenseRepositoryDdb — sandbox in-memory implementation (hand-maintained).
 */
import type { LicenseRepository } from "@denselink/services/licenses";
import {
  ensureDemoSeed,
  id,
  licenseSecret,
  licenses,
  meta,
  nowIso,
  type LicenseRecord,
} from "../_shared/denselink-sandbox-store.js";

export class LicenseRepositoryDdb implements LicenseRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listLicenseKeys(input: Parameters<LicenseRepository["listLicenseKeys"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    let items = [...licenses.values()].map(({ secret, ...rest }) => rest);
    if (raw.appId) items = items.filter((l) => l.appId === raw.appId);
    if (raw.status) items = items.filter((l) => l.status === raw.status);
    return {
      data: { items, nextCursor: undefined },
      ...meta(String(raw.correlationId ?? "")),
    } as Awaited<ReturnType<LicenseRepository["listLicenseKeys"]>>;
  }

  async issueLicenseKey(input: Parameters<LicenseRepository["issueLicenseKey"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const secret = licenseSecret();
    const record: LicenseRecord = {
      id: id("lic"),
      appId: String(raw.appId ?? ""),
      developerId: String(raw.developerId ?? ""),
      tier: String(raw.tier ?? "private_beta"),
      status: "active",
      meshPort: raw.meshPort != null ? Number(raw.meshPort) : undefined,
      encryptionAttestation: false,
      attestationStatus: "pending",
      secret,
      createdAt: nowIso(),
    };
    licenses.set(record.id, record);
    return {
      data: { ...record },
      ...meta(String(raw.correlationId ?? "")),
    } as Awaited<ReturnType<LicenseRepository["issueLicenseKey"]>>;
  }

  async getLicenseKey(input: Parameters<LicenseRepository["getLicenseKey"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const licenseId = String(raw.licenseId ?? raw.id ?? "");
    const record = licenses.get(licenseId);
    if (!record) {
      const err = new Error(`License not found: ${licenseId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    const { secret, ...publicRec } = record;
    return { data: publicRec, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<LicenseRepository["getLicenseKey"]>>;
  }
}
