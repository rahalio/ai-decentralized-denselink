/**
 * Meshports Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/meshports.openapi.types";

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type MeshPort = components["schemas"]["MeshPort"];
export type MeshPortAllocate = components["schemas"]["MeshPortAllocate"];
export type MeshPortListData = components["schemas"]["MeshPortListData"];
export type MeshPortStatus = components["schemas"]["MeshPortStatus"];
export type Meshport = operations["listMeshPorts"]["responses"]["200"]["content"]["application/json"]["data"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type AllocateMeshPortRequestInput = NonNullable<operations["allocateMeshPort"]["requestBody"]>["content"]["application/json"];


// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type ListMeshPortsParams = NonNullable<operations["listMeshPorts"]["parameters"]["query"]>;
export type GetMeshPortParams = operations["getMeshPort"]["parameters"]["path"];
export type RevokeMeshPortParams = operations["revokeMeshPort"]["parameters"]["path"];


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type ListMeshPortsResponse = operations["listMeshPorts"]["responses"]["200"]["content"]["application/json"];
export type AllocateMeshPortResponse = operations["allocateMeshPort"]["responses"]["201"]["content"]["application/json"];
export type GetMeshPortResponse = operations["getMeshPort"]["responses"]["200"]["content"]["application/json"];
export type RevokeMeshPortResponse = operations["revokeMeshPort"]["responses"]["200"]["content"]["application/json"];


