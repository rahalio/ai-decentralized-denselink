/** Unwrap list payloads from domain services (already de-enveloped once). */
export function itemsOf(payload: unknown): any[] {
  if (!payload || typeof payload !== "object") return [];
  const p = payload as Record<string, any>;
  if (Array.isArray(p.items)) return p.items;
  if (p.data && Array.isArray(p.data.items)) return p.data.items;
  if (Array.isArray(p.data)) return p.data;
  return [];
}

export function dataOf<T = any>(payload: unknown): T | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const p = payload as Record<string, any>;
  if ("data" in p) return p.data as T;
  return payload as T;
}
