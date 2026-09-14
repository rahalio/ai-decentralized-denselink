/**
 * Wraps a handler in tenant execution context (AsyncLocalStorage).
 */

import type { FastifyRequest } from 'fastify';
import { executionContextService } from '@denselink/services/_shared';

const DEFAULT_TENANT_ID = process.env.DEFAULT_TENANT_ID || 'system';

export async function wrapHandlerInExecutionContext<T>(
  request: FastifyRequest,
  fn: () => Promise<T>
): Promise<T> {
  const tenantId =
    request.effectiveTenantId ??
    request.auth?.tenantId ??
    DEFAULT_TENANT_ID;
  if (!request.effectiveTenantId) {
    request.effectiveTenantId = tenantId;
  }
  const userId = request.auth?.userId;
  return executionContextService.runAsync({ tenantId, userId }, fn);
}
