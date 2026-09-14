/**
 * ApiKeyRepository — in-memory sandbox implementation.
 */

import type { ApiKeyRepository } from '@denselink/services/identity';
import { seedApiKey } from '../_shared/in-memory-api-key-lookup.js';
import {
  apiKeysById,
  apiKeysByTenant,
  generateApiKeySecret,
  nowIso,
  responseMeta,
  sandboxId,
  type SandboxApiKey,
} from '../_shared/sandbox-store.js';

function toPublicKey(key: SandboxApiKey) {
  return {
    keyId: key.keyId,
    name: key.name,
    prefix: key.prefix,
    status: key.status,
    scopes: key.scopes,
    createdAt: key.createdAt,
    lastUsedAt: key.lastUsedAt,
    expiresAt: key.expiresAt,
  };
}

export class ApiKeyRepositoryDdb implements ApiKeyRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listTenantApiKeys(
    input: Parameters<ApiKeyRepository['listTenantApiKeys']>[0]
  ): Promise<Awaited<ReturnType<ApiKeyRepository['listTenantApiKeys']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    const ids = apiKeysByTenant.get(tenantId) ?? new Set<string>();
    const items = [...ids]
      .map((id) => apiKeysById.get(id))
      .filter((k): k is SandboxApiKey => Boolean(k))
      .map(toPublicKey);

    return {
      data: { items },
      ...responseMeta(correlationId),
    };
  }

  async createTenantApiKey(
    input: Parameters<ApiKeyRepository['createTenantApiKey']>[0]
  ): Promise<Awaited<ReturnType<ApiKeyRepository['createTenantApiKey']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    const keyId = String(raw.id ?? sandboxId('key'));
    const name = String(raw.name ?? 'sandbox-key');
    const scopes = (raw.scopes as string[] | undefined) ?? [
      'packs:read',
      'packs:write',
      'ingest:write',
    ];
    const secret = generateApiKeySecret('zzk_demo');
    const prefix = secret.slice(0, 16);
    const createdAt = nowIso();

    const record: SandboxApiKey = {
      keyId,
      tenantId,
      name,
      prefix,
      secret,
      status: 'active',
      scopes,
      createdAt,
      expiresAt: raw.expiresAt ? String(raw.expiresAt) : undefined,
    };

    apiKeysById.set(keyId, record);
    const tenantKeys = apiKeysByTenant.get(tenantId) ?? new Set<string>();
    tenantKeys.add(keyId);
    apiKeysByTenant.set(tenantId, tenantKeys);

    seedApiKey(secret, {
      keyId,
      tenantId,
      scopes,
      expiresAt: record.expiresAt,
    });

    return {
      data: {
        ...toPublicKey(record),
        secret,
      },
      ...responseMeta(correlationId),
    };
  }

  async getTenantApiKey(
    input: Parameters<ApiKeyRepository['getTenantApiKey']>[0]
  ): Promise<Awaited<ReturnType<ApiKeyRepository['getTenantApiKey']>>> {
    const raw = input as Record<string, unknown>;
    const keyId = String(raw.keyId ?? '');
    const correlationId = String(raw.correlationId ?? '');
    const key = apiKeysById.get(keyId);

    if (!key) {
      return null as never;
    }

    return {
      data: toPublicKey(key),
      ...responseMeta(correlationId),
    };
  }

  async revokeTenantApiKey(
    input: Parameters<ApiKeyRepository['revokeTenantApiKey']>[0]
  ): Promise<Awaited<ReturnType<ApiKeyRepository['revokeTenantApiKey']>>> {
    const raw = input as Record<string, unknown>;
    const keyId = String(raw.keyId ?? '');
    const key = apiKeysById.get(keyId);

    if (!key) {
      return null as never;
    }

    key.status = 'revoked';
    apiKeysById.set(keyId, key);
    seedApiKey(key.secret, {
      keyId: key.keyId,
      tenantId: key.tenantId,
      scopes: key.scopes,
      expiresAt: key.expiresAt,
      revoked: true,
    });

    return {} as Awaited<ReturnType<ApiKeyRepository['revokeTenantApiKey']>>;
  }
}
