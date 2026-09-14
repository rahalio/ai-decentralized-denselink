/**
 * Handler Test Factories
 *
 * Shared test utilities for all domains.
 * Provides factories for creating mock FastifyRequest, FastifyReply, and Dependencies
 * for testing api-server handlers.
 *
 * Handlers use nested DI: deps.useCases.{aggregate}.{operation}.execute(...)
 * Generated tests historically spy on flat execute{Operation} props — both paths
 * share the same mock objects so either style works.
 */

import type { FastifyRequest, FastifyReply } from "fastify";
import { vi } from "vitest";

/**
 * Extended FastifyRequest type for testing with effectiveTenantId
 */
interface TestFastifyRequest extends Partial<FastifyRequest> {
  effectiveTenantId?: string;
  params?: Record<string, string>;
  query?: Record<string, string | string[]>;
  body?: unknown;
}

type ExecuteMock = { execute: ReturnType<typeof vi.fn> };

/**
 * Creates a mock FastifyRequest for testing
 */
export function createMockRequest(overrides: Partial<TestFastifyRequest> = {}): TestFastifyRequest {
  const tenantId = overrides?.effectiveTenantId ?? "test-tenant-id";

  return {
    params: {},
    query: {},
    body: {},
    headers: {},
    effectiveTenantId: tenantId,
    ...overrides,
  };
}

/**
 * Creates a mock FastifyReply for testing
 */
export function createMockReply(overrides: Partial<FastifyReply> = {}): Partial<FastifyReply> {
  const send = vi.fn().mockReturnThis();
  const code = vi.fn().mockReturnThis();
  const status = vi.fn().mockReturnThis();

  return {
    send,
    code,
    status,
    ...overrides,
  } as Partial<FastifyReply>;
}

function verbFromExecuteName(name: string): string {
  if (!name.startsWith("execute")) return name;
  const rest = name.slice("execute".length);
  return rest.charAt(0).toLowerCase() + rest.slice(1);
}

function createNestedUseCasesProxy(byVerb: Record<string, ExecuteMock>): Record<string, Record<string, ExecuteMock>> {
  const aggregates: Record<string, Record<string, ExecuteMock>> = {};

  return new Proxy(aggregates, {
    get(target, aggregateKey: string | symbol) {
      if (typeof aggregateKey !== "string") return undefined;
      if (!(aggregateKey in target)) {
        const verbs: Record<string, ExecuteMock> = {};
        target[aggregateKey] = new Proxy(verbs, {
          get(verbTarget, verbKey: string | symbol) {
            if (typeof verbKey !== "string") return undefined;
            if (!(verbKey in verbTarget)) {
              const flatKey = `execute${verbKey.charAt(0).toUpperCase()}${verbKey.slice(1)}`;
              verbTarget[verbKey] =
                byVerb[verbKey] ??
                byVerb[flatKey] ??
                ({ execute: vi.fn() } as ExecuteMock);
              // Keep flat map in sync for late-created mocks
              byVerb[verbKey] = verbTarget[verbKey];
              byVerb[flatKey] = verbTarget[verbKey];
            }
            return verbTarget[verbKey];
          },
        });
      }
      return target[aggregateKey];
    },
  });
}

/**
 * Creates a mock Dependencies object for testing.
 *
 * Pre-creates flat execute{Op} mocks (for generated spyOn) and a nested
 * useCases Proxy matching runtime DomainModule shape.
 */
export function createMockDependencies<T = Record<string, unknown>>(
  useCaseNames: readonly string[] | string[],
  overrides: Partial<T> = {}
): T {
  const flatMocks: Record<string, ExecuteMock> = {};
  const byVerb: Record<string, ExecuteMock> = {};

  for (const name of useCaseNames) {
    const mock: ExecuteMock = { execute: vi.fn() };
    flatMocks[name] = mock;
    byVerb[name] = mock;
    byVerb[verbFromExecuteName(name)] = mock;
  }

  const mockDeps: Record<string, unknown> = {
    ...flatMocks,
    repos: {},
    useCases: createNestedUseCasesProxy(byVerb),
  };

  Object.assign(mockDeps, overrides);

  return mockDeps as T;
}
