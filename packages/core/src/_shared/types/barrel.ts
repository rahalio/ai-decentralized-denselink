/**
 * Shared types barrel. Re-exports OpenAPI-aligned shared types.
 * Only _master is re-exported here to avoid duplicate 'components'/'operations'/'paths'/'webhooks' from pagination.types.
 * For pagination-specific schemas (PageMeta, PageResponse, etc.) import from "./pagination.types.js".
 */

export type * from "./_master.types.js";