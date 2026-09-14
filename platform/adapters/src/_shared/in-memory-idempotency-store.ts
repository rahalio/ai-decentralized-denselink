/**
 * In-memory idempotency store for skeleton / local VPC pilots.
 */

import type {
  IdempotencyRecord,
  IdempotencyStore,
} from '@denselink/services/_shared';

const store = new Map<string, IdempotencyRecord>();

function composite(tenantId: string, key: string): string {
  return `${tenantId}::${key}`;
}

export class InMemoryIdempotencyStore implements IdempotencyStore {
  async get(
    tenantId: string,
    key: string
  ): Promise<IdempotencyRecord | null> {
    return store.get(composite(tenantId, key)) ?? null;
  }

  async put(record: IdempotencyRecord): Promise<void> {
    store.set(composite(record.tenantId, record.key), record);
  }
}

export const inMemoryIdempotencyStore = new InMemoryIdempotencyStore();
