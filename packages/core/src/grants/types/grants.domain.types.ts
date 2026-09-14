/**
 * Grants Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/grants.openapi.types";

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type GrantProgramme = components["schemas"]["GrantProgramme"];
export type GrantProgrammeCreate = components["schemas"]["GrantProgrammeCreate"];
export type GrantProgrammeListData = components["schemas"]["GrantProgrammeListData"];
export type GrantProgrammeStatus = components["schemas"]["GrantProgrammeStatus"];
export type Milestone = components["schemas"]["Milestone"];
export type MilestoneDisburse = components["schemas"]["MilestoneDisburse"];
export type MilestoneListData = components["schemas"]["MilestoneListData"];
export type MilestoneMetric = components["schemas"]["MilestoneMetric"];
export type MilestoneStatus = components["schemas"]["MilestoneStatus"];
export type Grant = operations["listGrantProgrammes"]["responses"]["200"]["content"]["application/json"]["data"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type CreateGrantProgrammeRequestInput = NonNullable<operations["createGrantProgramme"]["requestBody"]>["content"]["application/json"];
export type DisburseMilestoneRequestInput = NonNullable<operations["disburseMilestone"]["requestBody"]>["content"]["application/json"];


// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type ListGrantProgrammesParams = NonNullable<operations["listGrantProgrammes"]["parameters"]["query"]>;
export type GetGrantProgrammeParams = operations["getGrantProgramme"]["parameters"]["path"];
export type ListGrantMilestonesParams = NonNullable<operations["listGrantMilestones"]["parameters"]["query"]>;
export type DisburseMilestoneParams = operations["disburseMilestone"]["parameters"]["path"];


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type ListGrantProgrammesResponse = operations["listGrantProgrammes"]["responses"]["200"]["content"]["application/json"];
export type CreateGrantProgrammeResponse = operations["createGrantProgramme"]["responses"]["201"]["content"]["application/json"];
export type GetGrantProgrammeResponse = operations["getGrantProgramme"]["responses"]["200"]["content"]["application/json"];
export type ListGrantMilestonesResponse = operations["listGrantMilestones"]["responses"]["200"]["content"]["application/json"];
export type DisburseMilestoneResponse = operations["disburseMilestone"]["responses"]["200"]["content"]["application/json"];


