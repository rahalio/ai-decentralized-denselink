/**
 * Tenant-context preHandler: bind effectiveTenantId from API key / JWT.
 * Emits RFC7807 Problem on auth failures.
 */

import type { FastifyRequest, FastifyReply } from 'fastify';
import type { RequestAuth, RouteScope } from '../types/fastify-types.js';

function sendProblem(
  reply: FastifyReply,
  status: number,
  title: string,
  detail: string,
  code: string
): void {
  reply.status(status).type('application/problem+json').send({
    type: `https://ddd-codegen-starter.local/problems/${code}`,
    title,
    status,
    detail,
    code,
  });
}

export async function tenantContextPreHandler(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  const routeScope = request.routeScope as RouteScope | undefined;
  const auth = request.auth as RequestAuth | undefined;

  if (routeScope !== 'tenant') {
    return;
  }

  if (!auth || auth.type === 'none') {
    sendProblem(
      reply,
      401,
      'Unauthorized',
      'Tenant-scoped route requires X-API-Key or Bearer token',
      'UNAUTHORIZED'
    );
    return;
  }

  const tenantId = auth.tenantId;
  if (!tenantId) {
    sendProblem(
      reply,
      403,
      'Forbidden',
      'Credential is not bound to a tenant',
      'TENANT_REQUIRED'
    );
    return;
  }

  request.effectiveTenantId = tenantId;
}

/** @deprecated Use tenantContextPreHandler */
export const orgContextPreHandler = tenantContextPreHandler;
