/**
 * Shared Repository Contracts (barrel)
 *
 * Centralizes exports for repository contracts and multi-tenant helpers.
 */

export type {
  // Base types
  OrgId,
  PaginationParams,
  PaginatedResult,

  // Type utilities
  RepositoryList,
  RepositoryGet,
  RepositoryCreate,

  // Multi-tenant repository contracts
  ReadRepository,
  CreateReadRepository,
  UpdateReadRepository,
  DeleteReadRepository,
  CreateUpdateReadRepository,
  CreateDeleteReadRepository,
  UpdateDeleteReadRepository,
  CrudRepository,

  // Single-tenant repository contracts
  SingleTenantReadRepository,
  SingleTenantCreateReadRepository,
  SingleTenantUpdateReadRepository,
  SingleTenantDeleteReadRepository,
  SingleTenantCreateUpdateReadRepository,
  SingleTenantCreateDeleteReadRepository,
  SingleTenantUpdateDeleteReadRepository,
  SingleTenantCrudRepository,

  // Marker interfaces
  BulkOperationRepository,
  QueryableRepository,
  SearchableRepository,
  ActionRepository,
} from "./_base-repository.js";

export type {
  UserContext,
  SingleTenantRepository,
  PaginatedResponse,
} from "./base-repository-convenience.js";

