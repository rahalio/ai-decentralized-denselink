/**
 * Reports Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/reports.openapi.types";

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type BetaCohortSummary = components["schemas"]["BetaCohortSummary"];
export type ContributionRankEntry = components["schemas"]["ContributionRankEntry"];
export type ContributionRankListData = components["schemas"]["ContributionRankListData"];
export type DensityReport = components["schemas"]["DensityReport"];
export type SponsorRoiReport = components["schemas"]["SponsorRoiReport"];
export type BetaCohort = components["schemas"]["BetaCohortResponse"];



// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type GetDensityReportParams = NonNullable<operations["getDensityReport"]["parameters"]["query"]>;
export type GetContributionRankParams = NonNullable<operations["getContributionRank"]["parameters"]["query"]>;
export type GetSponsorRoiReportParams = NonNullable<operations["getSponsorRoiReport"]["parameters"]["query"]>;


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type GetDensityReportResponse = operations["getDensityReport"]["responses"]["200"]["content"]["application/json"];
export type GetContributionRankResponse = operations["getContributionRank"]["responses"]["200"]["content"]["application/json"];
export type GetBetaCohortResponse = operations["getBetaCohort"]["responses"]["200"]["content"]["application/json"];
export type GetSponsorRoiReportResponse = operations["getSponsorRoiReport"]["responses"]["200"]["content"]["application/json"];


