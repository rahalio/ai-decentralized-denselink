/**
 * Single-Tenant Repository Convenience Types
 *
 * Convenience types for single-tenant deployments that don't need
 * org-level scoping on repository operations. Use the parallel
 * SingleTenant* interfaces from `_base-repository.ts` for the
 * actual repository contracts.
 *
 * Deprecation note: The original multi-tenant versions of these
 * types (OrgContext, MultiTenantRepository) were replaced to
 * reflect single-tenant semantics. See `_base-repository.ts` for
 * the multi-tenant contracts if needed.
 */

import type {
  PaginatedResult,
  PaginationParams,
} from "./_base-repository.js";

// Re-export pagination types for convenience
export type { PaginatedResult, PaginationParams };

// Alias for backward compatibility
export type PaginatedResponse<T> = PaginatedResult<T>;

/**
 * User context extracted from authentication (single-tenant).
 * Contains user-level identity without org scoping.
 */
export interface UserContext {
  /** Account ID of the authenticated user */
  accountId?: string;
  /** User email */
  email?: string;
  /** User roles */
  roles?: string[];
}

/**
 * Base interface for single-tenant repositories.
 * Provides standard query methods without org scoping.
 *
 * Note: This is a convenience interface. Actual repositories should extend
 * from the base repository types (SingleTenantReadRepository,
 * SingleTenantCrudRepository, etc.) in _base-repository.ts.
 */
export interface SingleTenantRepository<T> {
  /**
   * Find all entities (paginated)
   * @param params - Optional pagination parameters (cursor, limit)
   * @returns Paginated result with all entities
   */
  findAll(params?: PaginationParams): Promise<PaginatedResult<T>>;

  /**
   * Find a single entity by ID
   * @param id - Entity ID
   * @returns Entity or null if not found
   */
  findById(id: string): Promise<T | null>;
}