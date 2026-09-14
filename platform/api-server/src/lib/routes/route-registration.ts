/**
 * Register Fastify plugins exported from a domain routes module.
 * Codegen domain-routes.ts calls this for each domain.
 */

import type { FastifyInstance } from 'fastify';

/**
 * Register every export whose name ends with `Routes` (except excluded).
 */
export async function registerDomainFromModule(
  fastify: FastifyInstance,
  domain: string,
  mod: Record<string, unknown>,
  exclude: string[] = []
): Promise<void> {
  const excluded = new Set(exclude);
  for (const [name, value] of Object.entries(mod)) {
    if (excluded.has(name)) continue;
    if (!name.endsWith('Routes')) continue;
    if (typeof value !== 'function') continue;
    await fastify.register(value as (app: FastifyInstance) => Promise<void> | void);
    // eslint-disable-next-line no-console
    console.log(`[DEBUG] ✅ ${domain}.${name} registered`);
  }
}
