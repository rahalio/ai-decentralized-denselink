/**
 * Auth preHandler: JWT (optional operator) or X-API-Key → request.auth.
 * API keys resolved via injectable ApiKeyLookup (real hash lookup, not stub).
 */

import type { FastifyRequest, FastifyReply } from 'fastify';
import jwt from 'jsonwebtoken';
import type { ApiKeyLookup } from '@denselink/services/_shared';
import type { RequestAuth } from '../types/fastify-types.js';

const BEARER_PREFIX = 'Bearer ';
const API_KEY_HEADER = 'x-api-key';

interface JwtPayload {
  tenantId?: string;
  userId?: string;
  sub?: string;
  email?: string;
  role?: string;
  roles?: string[];
  scopes?: string[];
  clientId?: string;
  [key: string]: unknown;
}

let apiKeyLookup: ApiKeyLookup | null = null;

/** Wire the lookup implementation from bootstrap / DI. */
export function setApiKeyLookup(lookup: ApiKeyLookup): void {
  apiKeyLookup = lookup;
}

function getSecret(): string {
  return process.env.JWT_SECRET || 'ddd-codegen-starter-sandbox-dev-secret';
}

export async function authPreHandler(
  request: FastifyRequest,
  _reply: FastifyReply
): Promise<void> {
  const authHeader = request.headers.authorization;
  const apiKey = request.headers[API_KEY_HEADER] as string | undefined;

  if (authHeader?.startsWith(BEARER_PREFIX)) {
    const token = authHeader.slice(BEARER_PREFIX.length).trim();
    const secret = getSecret();
    try {
      const decoded = jwt.verify(token, secret) as JwtPayload;
      (request as FastifyRequest).auth = {
        type: 'jwt',
        userId: decoded.userId ?? decoded.sub,
        email: decoded.email,
        tenantId: decoded.tenantId,
        clientId: decoded.clientId,
        roles: decoded.roles ?? (decoded.role ? [decoded.role] : undefined),
        scopes: decoded.scopes,
      } satisfies RequestAuth;
      return;
    } catch {
      (request as FastifyRequest).auth = { type: 'none' };
      return;
    }
  }

  if (apiKey) {
    if (!apiKeyLookup) {
      (request as FastifyRequest).auth = { type: 'none' };
      return;
    }
    const record = await apiKeyLookup.lookup(apiKey);
    if (!record) {
      (request as FastifyRequest).auth = { type: 'none' };
      return;
    }
    (request as FastifyRequest).auth = {
      type: 'apiKey',
      tenantId: record.tenantId,
      keyId: record.keyId,
      scopes: record.scopes,
    } satisfies RequestAuth;
    return;
  }

  (request as FastifyRequest).auth = { type: 'none' };
}
