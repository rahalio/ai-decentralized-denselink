/**
 * Shared OpenAPI-derived type stubs for the DDD starter.
 * Prefer generated domain modules (e.g. identity) for full types.
 */

export type paths = Record<string, never>;
export type webhooks = Record<string, never>;

/** Domain ID prefixes (3-letter, lowercase). See _shared/helpers/id-contracts.ts. */
export type DomainPrefix = 'tnt' | 'aut' | 'key' | 'idn';

export interface components {
  schemas: {
    Currency: string;
    ErrorResponse: {
      error: {
        code: string;
        message: string;
        details?: Record<string, unknown>;
      };
    };
    DataEnvelope: {
      data: unknown;
    };
    Pagination: {
      page: number;
      limit: number;
      total: number;
    };
    PagedDataEnvelope: {
      data: { items: unknown[] };
      pagination: components['schemas']['Pagination'];
    };
    PageInfo: {
      nextCursor?: string | null;
      prevCursor?: string | null;
      limit: number;
    };
  };
  responses: Record<string, never>;
  parameters: Record<string, unknown>;
  requestBodies: Record<string, never>;
  headers: Record<string, never>;
  pathItems: Record<string, never>;
}
export type operations = Record<string, never>;
