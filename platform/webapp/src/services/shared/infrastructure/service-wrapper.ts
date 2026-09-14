/**
 * Wraps generated service objects with consistent error rethrow.
 */

export function makeService<T extends Record<string, Function>>(
  service: T,
  _domain: string,
): T {
  return new Proxy(service, {
    get(target, prop: string) {
      const fn = target[prop];
      if (typeof fn !== "function") return fn;

      return async (...args: unknown[]) => {
        try {
          return await fn.apply(target, args);
        } catch (error: any) {
          if (
            (error instanceof DOMException && error.name === "AbortError") ||
            error?.name === "AbortError"
          ) {
            throw error;
          }
          const message =
            error?.message || error?.error || `Failed to ${String(prop)}`;
          const userError = new Error(message);
          if (error?.statusCode) {
            (userError as any).statusCode = error.statusCode;
          }
          throw userError;
        }
      };
    },
  });
}
