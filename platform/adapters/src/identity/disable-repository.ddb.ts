/**
 * DisableRepository — sandbox disable operator user.
 */

import type { DisableRepository } from '@denselink/services/identity';
import {
  listUsersForTenant,
  nowIso,
  responseMeta,
  toPublicUser,
  usersById,
} from '../_shared/sandbox-store.js';

export class DisableRepositoryDdb implements DisableRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async disableTenantUser(
    input: Parameters<DisableRepository['disableTenantUser']>[0]
  ): Promise<Awaited<ReturnType<DisableRepository['disableTenantUser']>>> {
    const raw = input as Record<string, unknown>;
    const userId = String(raw.userId ?? '');
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    listUsersForTenant(tenantId);
    const user = usersById.get(userId);
    if (!user || user.tenantId !== tenantId) {
      return null as never;
    }

    user.status = 'disabled';
    user.disabledAt = nowIso();
    user.updatedAt = user.disabledAt;
    usersById.set(userId, user);

    return {
      data: toPublicUser(user),
      ...responseMeta(correlationId),
    };
  }
}
