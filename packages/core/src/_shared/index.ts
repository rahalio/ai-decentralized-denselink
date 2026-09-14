/**
 * Shared utilities and types for DDD Codegen Starter core.
 */

export type {
  PaginationParams,
  PaginatedResult,
  RepositoryList,
  RepositoryGet,
  RepositoryCreate,
  ReadRepository,
  CreateReadRepository,
  UpdateReadRepository,
  DeleteReadRepository,
  CreateUpdateReadRepository,
  CreateDeleteReadRepository,
  UpdateDeleteReadRepository,
  CrudRepository,
  SingleTenantReadRepository,
  SingleTenantCreateReadRepository,
  SingleTenantUpdateReadRepository,
  SingleTenantDeleteReadRepository,
  SingleTenantCreateUpdateReadRepository,
  SingleTenantCreateDeleteReadRepository,
  SingleTenantUpdateDeleteReadRepository,
  SingleTenantCrudRepository,
  BulkOperationRepository,
  QueryableRepository,
  SearchableRepository,
  ActionRepository,
  UserContext,
  SingleTenantRepository,
  PaginatedResponse,
} from './repositories/index.js';

export {
  DOMAIN_PREFIX_MAP,
  isValidDomainId,
  extractDomainFromId,
} from './helpers/id-contracts.js';
export type {
  DomainCode,
  DomainPrefix, DomainPrefix as IdDomainPrefix,
} from './helpers/id-contracts.js';
export * from './helpers/id-validators.js';
export * from './types/barrel.js';
export type * from './types/index.js';
export * from './events/index.js';
