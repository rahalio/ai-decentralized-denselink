/**
 * AttestationRepositoryDdb — sandbox attestation bind (hand-maintained).
 */
import type { AttestationRepository } from "@denselink/services/licenses";
import { ensureDemoSeed, licenses, meta } from "../_shared/denselink-sandbox-store.js";

export class AttestationRepositoryDdb implements AttestationRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async bindLicenseAttestation(input: Parameters<AttestationRepository["bindLicenseAttestation"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const licenseId = String(raw.licenseId ?? raw.id ?? "");
    const record = licenses.get(licenseId);
    if (!record) {
      const err = new Error(`License not found: ${licenseId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    const passed = raw.passed !== false;
    record.buildFingerprint = String(raw.buildFingerprint ?? "");
    record.encryptionAttestation = passed;
    record.attestationStatus = passed ? "passed" : "failed";
    licenses.set(licenseId, record);
    const { secret, ...publicRec } = record;
    return { data: publicRec, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<AttestationRepository["bindLicenseAttestation"]>>;
  }
}
