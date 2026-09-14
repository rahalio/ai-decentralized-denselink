/**
 * Density Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/density.openapi.types";

// ============================================================================
// Re-export all generated types
// ============================================================================
// Note: components and operations are exported here but should be accessed via namespace
// in main index.ts to avoid duplicate export errors (e.g., blockchain.types.components)

export type { components, operations };


// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type DensityModelListData = components["schemas"]["DensityModelListData"];
export type DensityModelResult = components["schemas"]["DensityModelResult"];
export type PiggybackListData = components["schemas"]["PiggybackListData"];
export type PiggybackRegion = components["schemas"]["PiggybackRegion"];
export type DensityModelRequest = components["schemas"]["DensityModelRequest"];
export type DensityModel = components["schemas"]["DensityModelResponse"];
export type Piggyback = operations["listPiggybackRegions"]["responses"]["200"]["content"]["application/json"]["data"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type RunDensityModelRequestInput = NonNullable<operations["runDensityModel"]["requestBody"]>["content"]["application/json"];


// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type ListDensityModelsParams = NonNullable<operations["listDensityModels"]["parameters"]["query"]>;
export type GetDensityModelParams = operations["getDensityModel"]["parameters"]["path"];
export type ListPiggybackRegionsParams = NonNullable<operations["listPiggybackRegions"]["parameters"]["query"]>;


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type ListDensityModelsResponse = operations["listDensityModels"]["responses"]["200"]["content"]["application/json"];
export type RunDensityModelResponse = operations["runDensityModel"]["responses"]["200"]["content"]["application/json"];
export type GetDensityModelResponse = operations["getDensityModel"]["responses"]["200"]["content"]["application/json"];
export type ListPiggybackRegionsResponse = operations["listPiggybackRegions"]["responses"]["200"]["content"]["application/json"];


