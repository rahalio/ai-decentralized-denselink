/**
 * UserRepository — in-memory sandbox operator users.
 */

import type { UserRepository } from '@denselink/services/identity';
import {
  listUsersForTenant,
  nowIso,
  responseMeta,
  sandboxId,
  toPublicUser,
  usersById,
  usersByTenant,
  type SandboxUser,
} from '../_shared/sandbox-store.js';

export class UserRepositoryDdb implements UserRepository {
  constructor(private readonly _dynamoClient: unknown) {}

  async listTenantUsers(
    input: Parameters<UserRepository['listTenantUsers']>[0]
  ): Promise<Awaited<ReturnType<UserRepository['listTenantUsers']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    const items = listUsersForTenant(tenantId).map(toPublicUser);

    return {
      data: { items },
      ...responseMeta(correlationId),
    };
  }

  async createTenantUser(
    input: Parameters<UserRepository['createTenantUser']>[0]
  ): Promise<Awaited<ReturnType<UserRepository['createTenantUser']>>> {
    const raw = input as Record<string, unknown>;
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    const email = String(raw.email ?? '').toLowerCase();
    const displayName = String(raw.displayName ?? '');
    const role = String(raw.role ?? 'viewer') as SandboxUser['role'];
    const password = String(raw.password ?? '');

    const existing = listUsersForTenant(tenantId).find(
      (u) => u.email.toLowerCase() === email,
    );
    if (existing) {
      const err = new Error('User with this email already exists') as Error & {
        statusCode?: number;
      };
      err.statusCode = 409;
      throw err;
    }

    const now = nowIso();
    const userId = sandboxId('usr');
    const user: SandboxUser = {
      userId,
      tenantId,
      email,
      displayName,
      role:
        role === 'admin' ||
        role === 'analyst' ||
        role === 'viewer' ||
        role === 'ops'
          ? role
          : 'viewer',
      status: 'active',
      password,
      createdAt: now,
      updatedAt: now,
    };

    usersById.set(userId, user);
    const ids = usersByTenant.get(tenantId) ?? new Set<string>();
    ids.add(userId);
    usersByTenant.set(tenantId, ids);

    return {
      data: toPublicUser(user),
      ...responseMeta(correlationId),
    };
  }

  async getTenantUser(
    input: Parameters<UserRepository['getTenantUser']>[0]
  ): Promise<Awaited<ReturnType<UserRepository['getTenantUser']>>> {
    const raw = input as Record<string, unknown>;
    const userId = String(raw.userId ?? '');
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    listUsersForTenant(tenantId);
    const user = usersById.get(userId);
    if (!user || user.tenantId !== tenantId) {
      return null as never;
    }

    return {
      data: toPublicUser(user),
      ...responseMeta(correlationId),
    };
  }

  async updateTenantUser(
    input: Parameters<UserRepository['updateTenantUser']>[0]
  ): Promise<Awaited<ReturnType<UserRepository['updateTenantUser']>>> {
    const raw = input as Record<string, unknown>;
    const userId = String(raw.userId ?? '');
    const tenantId = String(raw.orgId ?? 'tnt_demo');
    const correlationId = String(raw.correlationId ?? '');
    listUsersForTenant(tenantId);
    const user = usersById.get(userId);
    if (!user || user.tenantId !== tenantId) {
      return null as never;
    }

    if (raw.displayName !== undefined) {
      user.displayName = String(raw.displayName);
    }
    if (
      raw.role === 'admin' ||
      raw.role === 'analyst' ||
      raw.role === 'viewer' ||
      raw.role === 'ops'
    ) {
      user.role = raw.role;
    }
    if (raw.password !== undefined) {
      user.password = String(raw.password);
    }
    user.updatedAt = nowIso();
    usersById.set(userId, user);

    return {
      data: toPublicUser(user),
      ...responseMeta(correlationId),
    };
  }
}
