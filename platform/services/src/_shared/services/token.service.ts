/**
 * Token Service — JWT for optional FI operator sessions (stub identity).
 */

import jwt from 'jsonwebtoken';

export interface TokenClaims {
  userId: string;
  email: string;
  role: string;
  tenantId?: string;
  clientId?: string;
  scopes?: string[];
}

const ACCESS_TOKEN_EXPIRY = '15m';
const REFRESH_TOKEN_EXPIRY = '7d';

function getJwtSecret(): string {
  return (
    process.env.JWT_SECRET ||
    'ddd-codegen-starter-sandbox-dev-secret'
  );
}

export function generateAccessToken(claims: TokenClaims): string {
  return jwt.sign(
    {
      tenantId: claims.tenantId,
      clientId: claims.clientId,
      userId: claims.userId,
      email: claims.email,
      role: claims.role,
      scopes: claims.scopes,
      type: 'access',
    },
    getJwtSecret(),
    {
      expiresIn: ACCESS_TOKEN_EXPIRY,
      issuer: 'ddd-codegen-starter-api',
      audience: 'ddd-codegen-starter-client',
    }
  );
}

export function generateRefreshToken(claims: TokenClaims): string {
  return jwt.sign(
    {
      tenantId: claims.tenantId,
      clientId: claims.clientId,
      userId: claims.userId,
      email: claims.email,
      role: claims.role,
      scopes: claims.scopes,
      type: 'refresh',
    },
    getJwtSecret(),
    {
      expiresIn: REFRESH_TOKEN_EXPIRY,
      issuer: 'ddd-codegen-starter-api',
      audience: 'ddd-codegen-starter-client',
    }
  );
}
