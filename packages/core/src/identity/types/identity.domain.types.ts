/**
 * Identity Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/identity.openapi.types";

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type ApiKey = components["schemas"]["ApiKey"];
export type ApiKeyCreated = components["schemas"]["ApiKeyCreated"];
export type ApiKeyId = components["schemas"]["ApiKeyId"];
export type ApiKeyListData = components["schemas"]["ApiKeyListData"];
export type AuthTokens = components["schemas"]["AuthTokens"];
export type OperatorRole = components["schemas"]["OperatorRole"];
export type OperatorSession = components["schemas"]["OperatorSession"];
export type OperatorStatus = components["schemas"]["OperatorStatus"];
export type SessionOperator = components["schemas"]["SessionOperator"];
export type SessionTenantSummary = components["schemas"]["SessionTenantSummary"];
export type TenantUser = components["schemas"]["TenantUser"];
export type TenantUserListData = components["schemas"]["TenantUserListData"];
export type ApiKeyCreateRequest = components["schemas"]["ApiKeyCreateRequest"];
export type CreateTenantUserRequest = components["schemas"]["CreateTenantUserRequest"];
export type OperatorLoginRequest = components["schemas"]["OperatorLoginRequest"];
export type RefreshTokenRequest = components["schemas"]["RefreshTokenRequest"];
export type UpdateOperatorMeRequest = components["schemas"]["UpdateOperatorMeRequest"];
export type UpdateTenantUserRequest = components["schemas"]["UpdateTenantUserRequest"];
export type User = operations["listTenantUsers"]["responses"]["200"]["content"]["application/json"]["data"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type CreateTenantApiKeyRequestInput = NonNullable<operations["createTenantApiKey"]["requestBody"]>["content"]["application/json"];
export type CreateTenantUserRequestInput = NonNullable<operations["createTenantUser"]["requestBody"]>["content"]["application/json"];
export type UpdateTenantUserRequestInput = NonNullable<operations["updateTenantUser"]["requestBody"]>["content"]["application/json"];
export type OperatorLoginRequestInput = NonNullable<operations["operatorLogin"]["requestBody"]>["content"]["application/json"];
export type UpdateOperatorMeRequestInput = NonNullable<operations["updateOperatorMe"]["requestBody"]>["content"]["application/json"];
export type OperatorRefreshRequestInput = NonNullable<operations["operatorRefresh"]["requestBody"]>["content"]["application/json"];


// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type GetTenantApiKeyParams = operations["getTenantApiKey"]["parameters"]["path"];
export type RevokeTenantApiKeyParams = operations["revokeTenantApiKey"]["parameters"]["path"];
export type GetTenantUserParams = operations["getTenantUser"]["parameters"]["path"];
export type UpdateTenantUserParams = operations["updateTenantUser"]["parameters"]["path"];
export type DisableTenantUserParams = operations["disableTenantUser"]["parameters"]["path"];
export type EnableTenantUserParams = operations["enableTenantUser"]["parameters"]["path"];


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type ListTenantApiKeysResponse = operations["listTenantApiKeys"]["responses"]["200"]["content"]["application/json"];
export type CreateTenantApiKeyResponse = operations["createTenantApiKey"]["responses"]["201"]["content"]["application/json"];
export type GetTenantApiKeyResponse = operations["getTenantApiKey"]["responses"]["200"]["content"]["application/json"];
export type ListTenantUsersResponse = operations["listTenantUsers"]["responses"]["200"]["content"]["application/json"];
export type CreateTenantUserResponse = operations["createTenantUser"]["responses"]["201"]["content"]["application/json"];
export type GetTenantUserResponse = operations["getTenantUser"]["responses"]["200"]["content"]["application/json"];
export type UpdateTenantUserResponse = operations["updateTenantUser"]["responses"]["200"]["content"]["application/json"];
export type DisableTenantUserResponse = operations["disableTenantUser"]["responses"]["200"]["content"]["application/json"];
export type EnableTenantUserResponse = operations["enableTenantUser"]["responses"]["200"]["content"]["application/json"];
export type OperatorLoginResponse = operations["operatorLogin"]["responses"]["200"]["content"]["application/json"];
export type GetOperatorMeResponse = operations["getOperatorMe"]["responses"]["200"]["content"]["application/json"];
export type UpdateOperatorMeResponse = operations["updateOperatorMe"]["responses"]["200"]["content"]["application/json"];
export type OperatorRefreshResponse = operations["operatorRefresh"]["responses"]["200"]["content"]["application/json"];


