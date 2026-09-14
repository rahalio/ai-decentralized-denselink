/**
 * MeshportRepositoryDdb — sandbox in-memory implementation (hand-maintained).
 */
import type { MeshportRepository } from "@denselink/services/meshports";
import {
  ensureDemoSeed,
  id,
  meshPorts,
  meta,
  nextPort,
  nowIso,
  type MeshPortRecord,
} from "../_shared/denselink-sandbox-store.js";

export class MeshportRepositoryDdb implements MeshportRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listMeshPorts(input: Parameters<MeshportRepository["listMeshPorts"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    let items = [...meshPorts.values()];
    if (raw.appId) items = items.filter((p) => p.appId === raw.appId);
    return {
      data: { items, nextCursor: undefined },
      ...meta(String(raw.correlationId ?? "")),
    } as Awaited<ReturnType<MeshportRepository["listMeshPorts"]>>;
  }

  async allocateMeshPort(input: Parameters<MeshportRepository["allocateMeshPort"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const appId = String(raw.appId ?? "");
    const preferred = raw.preferredPort != null ? Number(raw.preferredPort) : undefined;
    const existing = [...meshPorts.values()].find(
      (p) => p.status === "allocated" && preferred != null && p.port === preferred && p.appId !== appId
    );
    if (existing) {
      const err = new Error(`MeshPort ${preferred} collision with ${existing.appId}`) as Error & { statusCode?: number };
      err.statusCode = 409;
      throw err;
    }
    const port = preferred && ![...meshPorts.values()].some((p) => p.port === preferred && p.status === "allocated")
      ? preferred
      : nextPort();
    const record: MeshPortRecord = {
      id: id("mpt"),
      port,
      appId,
      sdkVersion: raw.sdkVersion ? String(raw.sdkVersion) : undefined,
      status: "allocated",
      createdAt: nowIso(),
    };
    meshPorts.set(record.id, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<MeshportRepository["allocateMeshPort"]>>;
  }

  async getMeshPort(input: Parameters<MeshportRepository["getMeshPort"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const meshPortId = String(raw.meshPortId ?? raw.id ?? "");
    const record = meshPorts.get(meshPortId);
    if (!record) {
      const err = new Error(`MeshPort not found: ${meshPortId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<MeshportRepository["getMeshPort"]>>;
  }

  async revokeMeshPort(input: Parameters<MeshportRepository["revokeMeshPort"]>[0]) {
    ensureDemoSeed();
    const raw = input as Record<string, unknown>;
    const meshPortId = String(raw.meshPortId ?? raw.id ?? "");
    const record = meshPorts.get(meshPortId);
    if (!record) {
      const err = new Error(`MeshPort not found: ${meshPortId}`) as Error & { statusCode?: number };
      err.statusCode = 404;
      throw err;
    }
    record.status = "revoked";
    record.revokedAt = nowIso();
    meshPorts.set(meshPortId, record);
    return { data: record, ...meta(String(raw.correlationId ?? "")) } as Awaited<ReturnType<MeshportRepository["revokeMeshPort"]>>;
  }
}
