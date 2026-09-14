/**
 * In-memory ApiKeyLookup for local/skeleton use.
 * Replace with DynamoDB adapter in production.
 */

import { createHash } from 'node:crypto';
import type {
  ApiKeyLookup,
  ApiKeyRecord,
} from '@denselink/services/_shared';

const store = new Map<string, ApiKeyRecord>();

function hashKey(raw: string): string {
  return createHash('sha256').update(raw).digest('hex');
}

/** Seed a known key for local testing (hash → record). */
export function seedApiKey(rawApiKey: string, record: ApiKeyRecord): void {
  store.set(hashKey(rawApiKey), { ...record });
}

export class InMemoryApiKeyLookup implements ApiKeyLookup {
  async lookup(rawApiKey: string): Promise<ApiKeyRecord | null> {
    const record = store.get(hashKey(rawApiKey));
    if (!record) return null;
    if (record.revoked) return null;
    if (record.expiresAt && Date.parse(record.expiresAt) < Date.now()) {
      return null;
    }
    return record;
  }
}

export const inMemoryApiKeyLookup = new InMemoryApiKeyLookup();
