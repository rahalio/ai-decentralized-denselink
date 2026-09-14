/**
 * Query parameter parsing helpers for Fastify routes
 */

/**
 * Parse query parameters from Fastify request
 * Handles optional parameters and type conversion
 *
 * @param query - Query object from Fastify request
 * @param defaults - Default values for optional parameters
 * @returns Parsed query parameters object
 */
export function parseQueryParams<T extends Record<string, any>>(
  query: any,
  defaults?: Partial<T>
): T {
  const result = { ...defaults } as T;

  if (!query) {
    return result;
  }

  // Copy all query parameters, overriding defaults
  for (const key in query) {
    if (query[key] !== undefined && query[key] !== null) {
      result[key as keyof T] = query[key];
    }
  }

  return result;
}
