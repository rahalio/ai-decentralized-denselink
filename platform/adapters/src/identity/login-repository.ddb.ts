/**
 * LoginRepository — sandbox auth + session me.
 */

import type { LoginRepository } from '@denselink/services/identity';
import {
  generateAccessToken,
  generateRefreshToken,
} from '@denselink/services/_shared';
import {
  getOrCreateTenantProfile,
  listUsersForTenant,
  nowIso,
  responseMeta,
  usersById,
  type SandboxUser,
} from '../_shared/sandbox-store.js';

/** refreshToken → userId for sandbox refresh without jwt dep in adapters */
export const refreshSessions = new Map<string, string>();

function resolveTenantId(raw: Record<string, unknown>): string {
  const orgId = String(raw.orgId ?? 'tnt_demo');
  return !orgId || orgId === 'system' ? 'tnt_demo' : orgId;
}

function toSessionOperator(user: SandboxUser) {
  return {
    userId: user.userId,
    email: user.email,
    displayName: user.displayName,
    role: user.role,
  };
}

function tenantSummary(tenantId: string) {
  const profile = getOrCreateTenantProfile(tenantId);
  return {
    tenantId,
    displayNameEn: profile.displayNameEn,
    displayNameAr: profile.displayNameAr,
  };
}

function syntheticApiKeyOperator() {
  return {
    userId: 'usr_api_key_demo',
    email: 'api-key@demo.local',
    displayName: 'Demo API key',
    role: 'admin' as const,
  };
}

function issueTokens(user: SandboxUser, tenantId: string, correlationId: string) {
  const claims = {
    userId: user.userId,
    email: user.email,
    role: user.role,
    tenantId,
  };
  const accessToken = generateAccessToken(claims);
  const refreshToken = generateRefreshToken(claims);
  refreshSessions.set(refreshToken, user.userId);
  return {
    data: {
      accessToken,
      refreshToken,
      tokenType: 'Bearer' as const,
      expiresIn: 900,
      operator: toSessionOperator(user),
    },
    ...responseMeta(correlationId),
  };
}

export class LoginRepositoryDdb implements LoginRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async operatorLogin(
    input: Parameters<LoginRepository['operatorLogin']>[0]
  ): Promise<Awaited<ReturnType<LoginRepository['operatorLogin']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = resolveTenantId(raw);
    const correlationId = String(raw.correlationId ?? '');
    const email = String(raw.email ?? '')
      .trim()
      .toLowerCase();
    const password = String(raw.password ?? '');

    const user = listUsersForTenant(tenantId).find(
      (u) => u.email.toLowerCase() === email
    );
    if (!user || user.password !== password || user.status !== 'active') {
      const err = new Error('Invalid email or password') as Error & {
        statusCode?: number;
      };
      err.statusCode = 401;
      throw err;
    }

    user.lastLoginAt = nowIso();
    usersById.set(user.userId, user);

    return issueTokens(user, tenantId, correlationId);
  }

  async getOperatorMe(
    input: Parameters<LoginRepository['getOperatorMe']>[0]
  ): Promise<Awaited<ReturnType<LoginRepository['getOperatorMe']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = resolveTenantId(raw);
    const correlationId = String(raw.correlationId ?? '');
    const userId = raw.userId ? String(raw.userId) : '';

    if (!userId || userId === 'usr_api_key_demo') {
      return {
        data: {
          operator: syntheticApiKeyOperator(),
          tenant: tenantSummary(tenantId),
        },
        ...responseMeta(correlationId),
      };
    }

    listUsersForTenant(tenantId);
    const user = usersById.get(userId);
    if (!user || user.tenantId !== tenantId) {
      return null as never;
    }

    return {
      data: {
        operator: toSessionOperator(user),
        tenant: tenantSummary(tenantId),
      },
      ...responseMeta(correlationId),
    };
  }

  async updateOperatorMe(
    input: Parameters<LoginRepository['updateOperatorMe']>[0]
  ): Promise<Awaited<ReturnType<LoginRepository['updateOperatorMe']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = resolveTenantId(raw);
    const correlationId = String(raw.correlationId ?? '');
    const userId = raw.userId ? String(raw.userId) : '';
    const displayName = String(raw.displayName ?? '').trim();

    if (!userId || userId === 'usr_api_key_demo') {
      const op = syntheticApiKeyOperator();
      return {
        data: {
          operator: { ...op, displayName: displayName || op.displayName },
          tenant: tenantSummary(tenantId),
        },
        ...responseMeta(correlationId),
      };
    }

    listUsersForTenant(tenantId);
    const user = usersById.get(userId);
    if (!user || user.tenantId !== tenantId) {
      return null as never;
    }

    user.displayName = displayName;
    user.updatedAt = nowIso();
    usersById.set(user.userId, user);

    return {
      data: {
        operator: toSessionOperator(user),
        tenant: tenantSummary(tenantId),
      },
      ...responseMeta(correlationId),
    };
  }
}
