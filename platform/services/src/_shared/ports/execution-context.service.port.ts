/**
 * ExecutionContext Service Port — request-scoped tenant context.
 */

export interface ExecutionContextService {
  /**
   * Get the current FI tenant ID from context.
   * @throws Error if tenantId is not set
   */
  getTenantId(): string;

  /** Optional operator / user id (future FI UI). */
  getUserId(): string | undefined;

  setTenantId(tenantId: string): void;

  setUserId(userId: string): void;

  /** @deprecated Use getTenantId — kept for gradual codegen compatibility */
  getOrgId(): string;

  /** @deprecated Use setTenantId */
  setOrgId(orgId: string): void;
}
