/**
 * Venues Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/venues.openapi.types";

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type AlwaysOnCampaign = components["schemas"]["AlwaysOnCampaign"];
export type AlwaysOnCampaignCreate = components["schemas"]["AlwaysOnCampaignCreate"];
export type AlwaysOnCampaignListData = components["schemas"]["AlwaysOnCampaignListData"];
export type VenueProgramme = components["schemas"]["VenueProgramme"];
export type VenueProgrammeCreate = components["schemas"]["VenueProgrammeCreate"];
export type VenueProgrammeListData = components["schemas"]["VenueProgrammeListData"];
export type VenueProgrammeStatus = components["schemas"]["VenueProgrammeStatus"];
export type VenueType = components["schemas"]["VenueType"];
export type Venue = operations["listVenueProgrammes"]["responses"]["200"]["content"]["application/json"]["data"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type CreateVenueProgrammeRequestInput = NonNullable<operations["createVenueProgramme"]["requestBody"]>["content"]["application/json"];
export type CreateAlwaysOnCampaignRequestInput = NonNullable<operations["createAlwaysOnCampaign"]["requestBody"]>["content"]["application/json"];


// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type ListVenueProgrammesParams = NonNullable<operations["listVenueProgrammes"]["parameters"]["query"]>;
export type GetVenueProgrammeParams = operations["getVenueProgramme"]["parameters"]["path"];
export type ListAlwaysOnCampaignsParams = NonNullable<operations["listAlwaysOnCampaigns"]["parameters"]["query"]>;


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type ListVenueProgrammesResponse = operations["listVenueProgrammes"]["responses"]["200"]["content"]["application/json"];
export type CreateVenueProgrammeResponse = operations["createVenueProgramme"]["responses"]["201"]["content"]["application/json"];
export type GetVenueProgrammeResponse = operations["getVenueProgramme"]["responses"]["200"]["content"]["application/json"];
export type ListAlwaysOnCampaignsResponse = operations["listAlwaysOnCampaigns"]["responses"]["200"]["content"]["application/json"];
export type CreateAlwaysOnCampaignResponse = operations["createAlwaysOnCampaign"]["responses"]["201"]["content"]["application/json"];


