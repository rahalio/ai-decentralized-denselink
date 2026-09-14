/**
 * Route registry — tracks registered HTTP routes for /routes/full.
 * Handwritten companion to generated system-routes.ts.
 */

export type RegisteredRoute = {
  method: string;
  path: string;
};

const routes: RegisteredRoute[] = [];

export function registerRoute(method: string, path: string): void {
  routes.push({ method: method.toUpperCase(), path });
}

export function getRegisteredRoutes(): RegisteredRoute[] {
  return [...routes];
}

export function clearRegisteredRoutes(): void {
  routes.length = 0;
}
