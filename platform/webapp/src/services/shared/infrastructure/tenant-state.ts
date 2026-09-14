/**
 * Tenant / org state for non-React callers (generated services).
 * Denselink is tenant-keyed; default demo tenant matches api-server seed.
 */

const DEFAULT_ORG_ID = "tnt_demo";

let currentOrgId: string | null = DEFAULT_ORG_ID;
let authOrgId: string | null = null;

export function setCurrentOrgId(orgId: string | null) {
  currentOrgId = orgId;
}

export function setAuthOrgId(orgId: string | null) {
  authOrgId = orgId;
}

export function getEffectiveOrgId(): string | null {
  if (currentOrgId || authOrgId) {
    return currentOrgId || authOrgId;
  }
  if (typeof window === "undefined") return DEFAULT_ORG_ID;
  return (
    localStorage.getItem("orgId") ||
    localStorage.getItem("org_id") ||
    DEFAULT_ORG_ID
  );
}
