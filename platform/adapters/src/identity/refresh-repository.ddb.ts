/**
 * RefreshRepository — sandbox refresh via session map.
 */

import type { RefreshRepository } from '@denselink/services/identity';
import {
  generateAccessToken,
  generateRefreshToken,
} from '@denselink/services/_shared';
import {
  listUsersForTenant,
  responseMeta,
  usersById,
} from '../_shared/sandbox-store.js';
import { refreshSessions } from './login-repository.ddb.js';

export class RefreshRepositoryDdb implements RefreshRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async operatorRefresh(
    input: Parameters<RefreshRepository['operatorRefresh']>[0]
  ): Promise<Awaited<ReturnType<RefreshRepository['operatorRefresh']>>> {
    const raw = input as Record<string, unknown>;
    const correlationId = String(raw.correlationId ?? '');
    const refreshToken = String(raw.refreshToken ?? '');
    const userId = refreshSessions.get(refreshToken);

    if (!userId) {
      const err = new Error('Invalid refresh token') as Error & {
        statusCode?: number;
      };
      err.statusCode = 401;
      throw err;
    }

    const user = usersById.get(userId);
    if (!user) {
      const err = new Error('Invalid refresh token') as Error & {
        statusCode?: number;
      };
      err.statusCode = 401;
      throw err;
    }

    listUsersForTenant(user.tenantId);
    const claims = {
      userId: user.userId,
      email: user.email,
      role: user.role,
      tenantId: user.tenantId,
    };
    const accessToken = generateAccessToken(claims);
    const nextRefresh = generateRefreshToken(claims);
    refreshSessions.delete(refreshToken);
    refreshSessions.set(nextRefresh, user.userId);

    return {
      data: {
        accessToken,
        refreshToken: nextRefresh,
        tokenType: 'Bearer' as const,
        expiresIn: 900,
        operator: {
          userId: user.userId,
          email: user.email,
          displayName: user.displayName,
          role: user.role,
        },
      },
      ...responseMeta(correlationId),
    };
  }
}
