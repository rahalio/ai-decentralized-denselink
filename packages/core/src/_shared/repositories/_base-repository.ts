/**
 * =======================================================================
 *  BASE REPOSITORY CONTRACTS (DDD Codegen Starter Investor Portal)
 *  -----------------------------------------------------------------------
 *  Domain repositories and codegen depend on these interfaces.
 *
 *  Responsibilities:
 *    ✓ Org/investor scoping (orgId required where applicable)
 *    ✓ Cursor-based pagination standard
 *    ✓ Read-only vs CRUD vs action repository separation
 *    ✓ OpenAPI-aligned method signatures
 *    ✓ Single-tenant and multi-tenant variants
 *
 *  Extend via marker interfaces (BulkOperationRepository, ActionRepository, etc.)
 *  rather than adding methods to base interfaces.
 * =======================================================================
 */

/**
 * Cursor-based pagination parameters shared by all list operations.
 */
export interface PaginationParams {
  cursor?: string;
  limit?: number;
}

/**
 * Envelope returned by all repository list operations.
 */
export interface PaginatedResult<T> {
  items: T[];
  nextCursor?: string | null;
  prevCursor?: string | null;
  total?: number;
}

/**
 * Multi-tenant organization identifier.
 */
export type OrgId = string;

/**
 * =======================================================================
 * TYPE UTILITIES for Repository Generic Parameters
 * -----------------------------------------------------------------------
 * Export helper types for consistent repository definitions across domains.
 * Use these when defining domain-specific repository types to enable
 * automatic generator tooling.
 * =======================================================================
 */

/**
 * Extract List Result Type from Repository
 * @example RepositoryList<ProductRepository> → PaginatedResult<Product>
 */
export type RepositoryList<TRepo extends ReadRepository<any>> =
  TRepo extends ReadRepository<infer TEntity, any, any>
    ? PaginatedResult<TEntity>
    : never;

/**
 * Extract Get Result Type from Repository
 * @example RepositoryGet<ProductRepository> → Product | null
 */
export type RepositoryGet<TRepo extends ReadRepository<any>> =
  TRepo extends ReadRepository<infer TEntity, any, any>
    ? TEntity | null
    : never;

/**
 * Extract Create Input Type from Repository
 * @example RepositoryCreate<ProductRepository> → CreateProductRequest
 */
export type RepositoryCreate<TRepo extends CrudRepository<any, any, any>> =
  TRepo extends CrudRepository<any, infer TCreate, any> ? TCreate : never;

/**
 * =======================================================================
 * READ-ONLY REPOSITORY (LIST + GET)
 * -----------------------------------------------------------------------
 * Used for domains that expose:
 *   • list<Entity>
 *   • get<Entity>
 *
 * Examples:
 *   - Events (activity)
 *   - Audit Logs (compliance)
 *   - Metrics (observability)
 *   - Analytics (metrics)
 * =======================================================================
 */
export interface ReadRepository<
  TEntity,
  TId = string,
  TListParams = PaginationParams
> {
  /**
   * List resources within an organization.
   *
   * @operationId list<Entity>
   */
  list(orgId: OrgId, params?: TListParams): Promise<PaginatedResult<TEntity>>;

  /**
   * Retrieve a single resource by ID.
   *
   * @operationId get<Entity>
   */
  findById(orgId: OrgId, id: TId): Promise<TEntity | null>;

  /**
   * Retrieve a single resource by ID (alias for findById).
   *
   * @operationId get<Entity>
   */
  get(orgId: OrgId, id: TId): Promise<TEntity | null>;
}

/**
 * =======================================================================
 * SINGLE OPERATION REPOSITORIES (extends ReadRepository)
 * -----------------------------------------------------------------------
 * Used when resources support only specific operations.
 * =======================================================================
 */

/**
 * Repository with create operation only
 * Used for resources that can be created but not updated/deleted
 *
 * Examples:
 *   - Event deliveries (create only, immutable)
 *   - Audit logs (create only)
 */
export interface CreateReadRepository<
  TEntity,
  TCreate,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Create a new resource.
   *
   * @operationId create<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  create(orgId: OrgId, data: TCreate): Promise<TEntity>;
}

/**
 * Repository with update operation only
 * Used for resources that can be updated but not created/deleted via API
 *
 * Examples:
 *   - Passwords (updated, but created during account creation)
 *   - Session tokens (refreshed, but created during login)
 */
export interface UpdateReadRepository<
  TEntity,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Update an existing resource.
   *
   * @operationId update<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  update(orgId: OrgId, id: TId, data: TUpdate): Promise<TEntity>;
}

/**
 * Repository with delete operation only
 * Used for resources that can be deleted but not created/updated via API
 *
 * Examples:
 *   - Temporary resources (delete only)
 */
export interface DeleteReadRepository<
  TEntity,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Delete a resource.
   *
   * @operationId delete<Entity>
   */
  delete(orgId: OrgId, id: TId): Promise<void>;
}

/**
 * =======================================================================
 * TWO OPERATION REPOSITORIES (extends ReadRepository)
 * -----------------------------------------------------------------------
 * Used when resources support two operations (but not all three).
 * =======================================================================
 */

/**
 * Repository with create and update operations
 * Used for resources that can be created and updated but not deleted
 *
 * Examples:
 *   - Configuration (create, update, but soft-delete only)
 */
export interface CreateUpdateReadRepository<
  TEntity,
  TCreate,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Create a new resource.
   *
   * @operationId create<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  create(orgId: OrgId, data: TCreate): Promise<TEntity>;

  /**
   * Update an existing resource.
   *
   * @operationId update<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  update(orgId: OrgId, id: TId, data: TUpdate): Promise<TEntity>;
}

/**
 * Repository with create and delete operations
 * Used for resources that can be created and deleted but not updated
 *
 * Examples:
 *   - Immutable resources (create, delete, but no updates)
 */
export interface CreateDeleteReadRepository<
  TEntity,
  TCreate,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Create a new resource.
   *
   * @operationId create<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  create(orgId: OrgId, data: TCreate): Promise<TEntity>;

  /**
   * Delete a resource.
   *
   * @operationId delete<Entity>
   */
  delete(orgId: OrgId, id: TId): Promise<void>;
}

/**
 * Repository with update and delete operations
 * Used for resources that can be updated and deleted but not created via API
 *
 * Examples:
 *   - System-managed resources (created by system, but can be updated/deleted)
 */
export interface UpdateDeleteReadRepository<
  TEntity,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Update an existing resource.
   *
   * @operationId update<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  update(orgId: OrgId, id: TId, data: TUpdate): Promise<TEntity>;

  /**
   * Delete a resource.
   *
   * @operationId delete<Entity>
   */
  delete(orgId: OrgId, id: TId): Promise<void>;
}

/**
 * =======================================================================
 * FULL CRUD REPOSITORY (CREATE + READ + UPDATE + DELETE)
 * -----------------------------------------------------------------------
 * Used for domains that support all modification operations:
 *   • create<Entity>
 *   • get<Entity>
 *   • list<Entity>
 *   • update<Entity>
 *   • delete<Entity>
 *
 * Examples:
 *   - Products
 *   - Content Items
 *   - Campaigns
 *   - Conversations
 *   - Schedules
 * =======================================================================
 */
export interface CrudRepository<
  TEntity,
  TCreate,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends ReadRepository<TEntity, TId, TListParams> {
  /**
   * Create a new resource.
   *
   * @operationId create<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  create(orgId: OrgId, data: TCreate): Promise<TEntity>;

  /**
   * Update an existing resource.
   *
   * @operationId update<Entity>
   * @param data - Validated input (type is compatible with Zod passthrough)
   */
  update(orgId: OrgId, id: TId, data: TUpdate): Promise<TEntity>;

  /**
   * Delete a resource.
   *
   * @operationId delete<Entity>
   */
  delete(orgId: OrgId, id: TId): Promise<void>;
}

/**
 * =======================================================================
 * SINGLE-TENANT REPOSITORIES (no orgId parameter)
 * -----------------------------------------------------------------------
 * Parallel interfaces for single-tenant deployments. All methods drop
 * the orgId parameter since there is only one tenant.
 *
 * Examples:
 *   - B2C apps with a single logical tenant
 *   - Embedded/local deployments
 *   - System/internal repositories (configuration, migrations)
 * =======================================================================
 */

/**
 * Single-tenant read-only repository (list + get).
 */
export interface SingleTenantReadRepository<
  TEntity,
  TId = string,
  TListParams = PaginationParams
> {
  /**
   * List all resources.
   *
   * @operationId list<Entity>
   */
  list(params?: TListParams): Promise<PaginatedResult<TEntity>>;

  /**
   * Retrieve a single resource by ID.
   *
   * @operationId get<Entity>
   */
  findById(id: TId): Promise<TEntity | null>;

  /**
   * Retrieve a single resource by ID (alias for findById).
   *
   * @operationId get<Entity>
   */
  get(id: TId): Promise<TEntity | null>;
}

/**
 * Single-tenant repository with create operation only.
 */
export interface SingleTenantCreateReadRepository<
  TEntity,
  TCreate,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  create(data: TCreate): Promise<TEntity>;
}

/**
 * Single-tenant repository with update operation only.
 */
export interface SingleTenantUpdateReadRepository<
  TEntity,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  update(id: TId, data: TUpdate): Promise<TEntity>;
}

/**
 * Single-tenant repository with delete operation only.
 */
export interface SingleTenantDeleteReadRepository<
  TEntity,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  delete(id: TId): Promise<void>;
}

/**
 * Single-tenant repository with create and update operations.
 */
export interface SingleTenantCreateUpdateReadRepository<
  TEntity,
  TCreate,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  create(data: TCreate): Promise<TEntity>;
  update(id: TId, data: TUpdate): Promise<TEntity>;
}

/**
 * Single-tenant repository with create and delete operations.
 */
export interface SingleTenantCreateDeleteReadRepository<
  TEntity,
  TCreate,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  create(data: TCreate): Promise<TEntity>;
  delete(id: TId): Promise<void>;
}

/**
 * Single-tenant repository with update and delete operations.
 */
export interface SingleTenantUpdateDeleteReadRepository<
  TEntity,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  update(id: TId, data: TUpdate): Promise<TEntity>;
  delete(id: TId): Promise<void>;
}

/**
 * Single-tenant full CRUD repository.
 */
export interface SingleTenantCrudRepository<
  TEntity,
  TCreate,
  TUpdate,
  TId = string,
  TListParams = PaginationParams
> extends SingleTenantReadRepository<TEntity, TId, TListParams> {
  create(data: TCreate): Promise<TEntity>;
  update(id: TId, data: TUpdate): Promise<TEntity>;
  delete(id: TId): Promise<void>;
}

/**
 * =======================================================================
 * MARKER INTERFACES FOR SAFE REPOSITORY EXTENSION
 * -----------------------------------------------------------------------
 * These are empty interfaces that serve as markers for repository capabilities.
 * Use them to extend repositories WITHOUT modifying base interfaces
 * (which would require regenerating all 88+ dependent repositories).
 *
 * Example:
 *   export interface ProductRepository
 *     extends CrudRepository<Product, CreateProductInput, UpdateProductInput>,
 *             BulkOperationRepository {
 *     bulkCreate(orgId: OrgId, items: CreateProductInput[]): Promise<Product[]>;
 *     bulkUpdate(orgId: OrgId, items: UpdateProductInput[]): Promise<Product[]>;
 *   }
 *
 * DO NOT add methods directly to base interfaces (ReadRepository, CrudRepository).
 * =======================================================================
 */

/**
 * Marker interface for repositories supporting bulk operations.
 * Implementing repositories should add bulkCreate(), bulkUpdate(), etc.
 */
export interface BulkOperationRepository {
  // No members — this is an identifier for bulk-capable repositories.
  // Add bulk* methods in implementing repository interface.
}

/**
 * Marker interface for repositories supporting advanced querying.
 * Implementing repositories should add search(), query(), filter(), etc.
 */
export interface QueryableRepository {
  // No members — this is an identifier for query-capable repositories.
  // Add query/search/filter methods in implementing repository interface.
}

/**
 * Marker interface for repositories supporting full-text search.
 * Implementing repositories should add search() method(s).
 */
export interface SearchableRepository {
  // No members — this is an identifier for search-capable repositories.
  // Add search/indexing methods in implementing repository interface.
}

/**
 * =======================================================================
 * ACTION REPOSITORY MIXIN
 * -----------------------------------------------------------------------
 * Marker interface for repositories that define non-CRUD actions:
 *
 *   - approve
 *   - reject
 *   - cancel
 *   - settle
 *   - lock/unlock
 *   - process
 *   - refresh
 *   - trigger
 *   - migrate
 *
 * Methods should be added individually in each domain repository.
 * =======================================================================
 */
export interface ActionRepository {
  // No members — this is an identifier for repositories with custom actions.
}
