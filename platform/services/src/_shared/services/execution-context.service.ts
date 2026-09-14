/**
 * ExecutionContext Service — AsyncLocalStorage tenant + optional user.
 */

import { AsyncLocalStorage } from 'async_hooks';
import type { ExecutionContextService } from '../ports/execution-context.service.port.js';

interface ExecutionContextData {
  tenantId: string;
  userId?: string;
}

class ExecutionContextServiceImpl implements ExecutionContextService {
  private readonly asyncLocalStorage =
    new AsyncLocalStorage<ExecutionContextData>();

  run<T>(context: ExecutionContextData, fn: () => T): T {
    return this.asyncLocalStorage.run(context, fn);
  }

  async runAsync<T>(
    context: ExecutionContextData,
    fn: () => Promise<T>
  ): Promise<T> {
    return this.asyncLocalStorage.run(context, fn);
  }

  getTenantId(): string {
    const context = this.asyncLocalStorage.getStore();
    if (!context?.tenantId) {
      throw new Error(
        'tenantId not set in execution context. Ensure context is set before calling usecase.'
      );
    }
    return context.tenantId;
  }

  getUserId(): string | undefined {
    return this.asyncLocalStorage.getStore()?.userId;
  }

  setTenantId(tenantId: string): void {
    const context = this.asyncLocalStorage.getStore();
    if (!context) {
      throw new Error(
        'Cannot set tenantId: execution context not initialized. Use run() or runAsync() first.'
      );
    }
    context.tenantId = tenantId;
  }

  setUserId(userId: string): void {
    const context = this.asyncLocalStorage.getStore();
    if (!context) {
      throw new Error(
        'Cannot set userId: execution context not initialized. Use run() or runAsync() first.'
      );
    }
    context.userId = userId;
  }

  getOrgId(): string {
    return this.getTenantId();
  }

  setOrgId(orgId: string): void {
    this.setTenantId(orgId);
  }
}

export const executionContextService = new ExecutionContextServiceImpl();
