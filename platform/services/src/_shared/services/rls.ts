/**
 * Tenant isolation helpers (application-level multi-tenancy).
 */

export const SYSTEM_TENANT_ID = 'system';

/** @deprecated Use SYSTEM_TENANT_ID */
export const SYSTEM_ORG_ID = SYSTEM_TENANT_ID;

/**
 * Validate tenant ID — prefers tnt_ ULID; also accepts plain sandbox ids.
 */
export function isValidTenantId(tenantId: string): boolean {
  if (!tenantId || typeof tenantId !== 'string') {
    return false;
  }
  if (tenantId === SYSTEM_TENANT_ID) return true;
  const domainPrefixedRegex = /^[a-z]{3}_[0-9a-hjkmnp-tv-z]{26}$/;
  if (domainPrefixedRegex.test(tenantId)) {
    return true;
  }
  const plainIdRegex = /^[a-zA-Z0-9_-]+$/;
  return plainIdRegex.test(tenantId);
}

/** @deprecated Use isValidTenantId */
export function isValidOrgId(orgId: string): boolean {
  return isValidTenantId(orgId);
}
