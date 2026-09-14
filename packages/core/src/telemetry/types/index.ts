/**
 * Telemetry Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/telemetry.openapi.types";

// ============================================================================
// Re-export all generated types
// ============================================================================
// Note: components and operations are exported here but should be accessed via namespace
// in main index.ts to avoid duplicate export errors (e.g., blockchain.types.components)

export type { components, operations };


// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type NodeTelemetryAggregate = components["schemas"]["NodeTelemetryAggregate"];
export type NodeTelemetryAggregateCreate = components["schemas"]["NodeTelemetryAggregateCreate"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type IngestNodeTelemetryRequestInput = NonNullable<operations["ingestNodeTelemetry"]["requestBody"]>["content"]["application/json"];



// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type IngestNodeTelemetryResponse = operations["ingestNodeTelemetry"]["responses"]["202"]["content"]["application/json"];


