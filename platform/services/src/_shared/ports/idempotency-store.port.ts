/**
 * Idempotency store port for mutating POSTs.
 */

export interface IdempotencyRecord {
  key: string;
  tenantId: string;
  bodyHash: string;
  statusCode: number;
  responseBody: unknown;
  createdAt: string;
}

export interface IdempotencyStore {
  get(
    tenantId: string,
    key: string
  ): Promise<IdempotencyRecord | null>;
  put(record: IdempotencyRecord): Promise<void>;
}
