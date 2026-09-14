/**
 * Fastify type extensions — tenant-scoped tenant auth.
 */

export interface JwtPayloadShape {
  tenantId?: string;
  userId?: string;
  email?: string;
  scopes?: string[];
  [key: string]: unknown;
}

export interface RequestAuth {
  type: 'jwt' | 'apiKey' | 'none';
  userId?: string;
  email?: string;
  tenantId?: string;
  clientId?: string;
  keyId?: string;
  roles?: string[];
  scopes?: string[];
}

export type RouteScope = 'tenant' | 'public';

declare module 'fastify' {
  interface FastifyRequest {
    auth?: RequestAuth;
    /** Effective FI tenant after tenant-context validation */
    effectiveTenantId?: string;
    routeScope?: RouteScope;
    user?: JwtPayloadShape;
  }
}

export interface RouteSecurityConfig {
  scope?: RouteScope;
  /** When true, require Idempotency-Key on this route */
  requireIdempotency?: boolean;
}

export {};
