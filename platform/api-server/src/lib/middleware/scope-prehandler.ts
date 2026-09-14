/**
 * Scope preHandler: tenant | public from route config or path heuristics.
 */

import type { FastifyRequest, FastifyReply } from 'fastify';
import type { RouteScope } from '../types/fastify-types.js';

interface RouteConfig {
  scope?: RouteScope;
}

export async function scopePreHandler(
  request: FastifyRequest,
  _reply: FastifyReply
): Promise<void> {
  const config = request.routeOptions?.config as RouteConfig | undefined;
  if (config?.scope) {
    request.routeScope = config.scope;
    return;
  }
  const path = request.routeOptions?.url ?? request.url;
  // Product APIs under /v0 are tenant-scoped by default
  if (path.startsWith('/v0/')) {
    // Auth stubs marked public in route config; default tenant for the rest
    if (
      path.startsWith('/v0/auth/login') ||
      path.startsWith('/v0/auth/refresh')
    ) {
      request.routeScope = 'public';
      return;
    }
    request.routeScope = 'tenant';
    return;
  }
  request.routeScope = 'public';
}
