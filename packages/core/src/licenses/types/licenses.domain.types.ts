/**
 * Licenses Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v2.0.0
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

import type { components, operations } from "../openapi/licenses.openapi.types";

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

export type AttestationBind = components["schemas"]["AttestationBind"];
export type AttestationStatus = components["schemas"]["AttestationStatus"];
export type LicenseKey = components["schemas"]["LicenseKey"];
export type LicenseKeyCreate = components["schemas"]["LicenseKeyCreate"];
export type LicenseKeyCreated = components["schemas"]["LicenseKeyCreated"];
export type LicenseKeyListData = components["schemas"]["LicenseKeyListData"];
export type LicenseStatus = components["schemas"]["LicenseStatus"];
export type LicenseTier = components["schemas"]["LicenseTier"];
export type License = operations["listLicenseKeys"]["responses"]["200"]["content"]["application/json"]["data"];


// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

export type IssueLicenseKeyRequestInput = NonNullable<operations["issueLicenseKey"]["requestBody"]>["content"]["application/json"];
export type BindLicenseAttestationRequestInput = NonNullable<operations["bindLicenseAttestation"]["requestBody"]>["content"]["application/json"];


// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

export type ListLicenseKeysParams = NonNullable<operations["listLicenseKeys"]["parameters"]["query"]>;
export type GetLicenseKeyParams = operations["getLicenseKey"]["parameters"]["path"];
export type RevokeLicenseKeyParams = operations["revokeLicenseKey"]["parameters"]["path"];
export type BindLicenseAttestationParams = operations["bindLicenseAttestation"]["parameters"]["path"];


// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

export type ListLicenseKeysResponse = operations["listLicenseKeys"]["responses"]["200"]["content"]["application/json"];
export type IssueLicenseKeyResponse = operations["issueLicenseKey"]["responses"]["201"]["content"]["application/json"];
export type GetLicenseKeyResponse = operations["getLicenseKey"]["responses"]["200"]["content"]["application/json"];
export type RevokeLicenseKeyResponse = operations["revokeLicenseKey"]["responses"]["200"]["content"]["application/json"];
export type BindLicenseAttestationResponse = operations["bindLicenseAttestation"]["responses"]["200"]["content"]["application/json"];


