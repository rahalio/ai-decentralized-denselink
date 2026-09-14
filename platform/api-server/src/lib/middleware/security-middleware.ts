/**
 * Global security middleware: auth → scope → tenant → idempotency.
 */

import type { FastifyInstance } from 'fastify';
import { authPreHandler } from './auth-prehandler.js';
import { scopePreHandler } from './scope-prehandler.js';
import { tenantContextPreHandler } from './tenant-context-prehandler.js';
import { idempotencyPreHandler } from './idempotency-prehandler.js';

export async function registerSecurityMiddleware(
  fastify: FastifyInstance
): Promise<void> {
  fastify.addHook('preHandler', async (request, reply) => {
    await authPreHandler(request, reply);
    if (reply.sent) return;
    await scopePreHandler(request, reply);
    if (reply.sent) return;
    await tenantContextPreHandler(request, reply);
    if (reply.sent) return;
    await idempotencyPreHandler(request, reply);
  });
}

export { authPreHandler, scopePreHandler, tenantContextPreHandler };
export { orgContextPreHandler } from './tenant-context-prehandler.js';
export { idempotencyPreHandler } from './idempotency-prehandler.js';
export { setApiKeyLookup } from './auth-prehandler.js';
export { setIdempotencyStore } from './idempotency-prehandler.js';
