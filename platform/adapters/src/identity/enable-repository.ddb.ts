/**
 * EnableRepository — sandbox re-enable operator user.
 */

import type { EnableRepository } from '@denselink/services/identity';
import {
  listUsersForTenant,
  nowIso,
  responseMeta,
  toPublicUser,
  usersById,
} from '../_shared/sandbox-store.js';

export class EnableRepositoryDdb implements EnableRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async enableTenantUser(
    input: Parameters<EnableRepository['enableTenantUser']>[0]
  ): Promise<Awaited<ReturnType<EnableRepository['enableTenantUser']>>> {
    const raw = input as Record<string, unknown>;
    const userId = String(raw.userId ?? '');
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    listUsersForTenant(tenantId);
    const user = usersById.get(userId);
    if (!user || user.tenantId !== tenantId) {
      return null as never;
    }

    user.status = 'active';
    user.disabledAt = undefined;
    user.updatedAt = nowIso();
    usersById.set(userId, user);

    return {
      data: toPublicUser(user),
      ...responseMeta(correlationId),
    };
  }
}
