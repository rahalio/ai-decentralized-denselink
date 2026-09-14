/**
 * onSend: ensure success bodies carry meta.correlationId / timestamp / requestId.
 */

import type { FastifyReply, FastifyRequest } from 'fastify';
import { randomUUID } from 'node:crypto';

export async function responseEnvelopeOnSend(
  request: FastifyRequest,
  _reply: FastifyReply,
  payload: unknown
): Promise<unknown> {
  if (payload == null || typeof payload !== 'object') {
    return payload;
  }
  const body = payload as Record<string, unknown>;
  if ('type' in body && 'status' in body && 'title' in body) {
    // RFC7807 Problem — leave untouched
    return payload;
  }
  if (!('data' in body) && !('meta' in body)) {
    return payload;
  }
  const meta = {
    ...((body.meta as Record<string, unknown>) ?? {}),
    correlationId:
      (body.meta as { correlationId?: string } | undefined)?.correlationId ??
      (request.headers['x-correlation-id'] as string | undefined) ??
      randomUUID(),
    requestId: request.id,
    timestamp: new Date().toISOString(),
  };
  return { ...body, meta };
}

export function registerResponseEnvelope(fastify: {
  addHook: (
    name: 'onSend',
    fn: typeof responseEnvelopeOnSend
  ) => void;
}): void {
  fastify.addHook('onSend', responseEnvelopeOnSend);
}
