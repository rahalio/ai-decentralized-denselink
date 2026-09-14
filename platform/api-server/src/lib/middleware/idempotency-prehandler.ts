/**
 * Idempotency preHandler for mutating POSTs with Idempotency-Key.
 * In-memory / injectable store; 409 when same key + different body hash.
 */

import { createHash } from 'node:crypto';
import type { FastifyRequest, FastifyReply } from 'fastify';
import type { IdempotencyStore } from '@denselink/services/_shared';
import type { RouteSecurityConfig } from '../types/fastify-types.js';

let store: IdempotencyStore | null = null;

export function setIdempotencyStore(s: IdempotencyStore): void {
  store = s;
}

function bodyHash(request: FastifyRequest): string {
  const raw = request.body;
  const serialized =
    typeof raw === 'string' ? raw : JSON.stringify(raw ?? null);
  return createHash('sha256').update(serialized).digest('hex');
}

export async function idempotencyPreHandler(
  request: FastifyRequest,
  reply: FastifyReply
): Promise<void> {
  const config = request.routeOptions?.config as RouteSecurityConfig | undefined;
  const method = request.method.toUpperCase();
  const needsKey =
    config?.requireIdempotency === true ||
    (method === 'POST' && (request.url.startsWith('/v0/') || false));

  if (!needsKey || method === 'GET' || method === 'HEAD') {
    return;
  }

  // Soft-require when header present or when explicitly configured
  const keyHeader = request.headers['idempotency-key'];
  const key = Array.isArray(keyHeader) ? keyHeader[0] : keyHeader;

  if (!key) {
    if (config?.requireIdempotency) {
      reply.status(400).type('application/problem+json').send({
        type: 'https://ddd-codegen-starter.local/problems/IDEMPOTENCY_KEY_REQUIRED',
        title: 'Bad Request',
        status: 400,
        detail: 'Idempotency-Key header is required',
        code: 'IDEMPOTENCY_KEY_REQUIRED',
      });
    }
    return;
  }

  if (!store) return;

  const tenantId = request.effectiveTenantId ?? request.auth?.tenantId;
  if (!tenantId) return;

  const hash = bodyHash(request);
  const existing = await store.get(tenantId, key);
  if (existing) {
    if (existing.bodyHash !== hash) {
      reply.status(409).type('application/problem+json').send({
        type: 'https://ddd-codegen-starter.local/problems/IDEMPOTENCY_KEY_CONFLICT',
        title: 'Conflict',
        status: 409,
        detail: 'Idempotency-Key was reused with a different request body',
        code: 'IDEMPOTENCY_KEY_CONFLICT',
      });
      return;
    }
    reply.status(existing.statusCode).send(existing.responseBody);
  }
}
