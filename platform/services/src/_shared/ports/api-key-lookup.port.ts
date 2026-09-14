/**
 * Port for resolving X-API-Key → FI tenant (tenant auth).
 * Adapters implement DynamoDB/hash lookup; skeleton ships an in-memory stub.
 */

export interface ApiKeyRecord {
  keyId: string;
  tenantId: string;
  scopes?: string[];
  expiresAt?: string;
  revoked?: boolean;
}

export interface ApiKeyLookup {
  /**
   * Resolve raw API key (or its hash) to a tenant binding.
   * Return null if unknown / revoked / expired.
   */
  lookup(rawApiKey: string): Promise<ApiKeyRecord | null>;
}
