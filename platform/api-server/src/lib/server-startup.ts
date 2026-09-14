/* eslint-disable no-console -- intentional bootstrap logging */
/**
 * Server Startup - Server startup and graceful shutdown
 */

import type { FastifyInstance } from "fastify";
import { createErrorHandler } from "./errors/error-handler.js";

/**
 * Setup error handler and graceful shutdown
 */
export function setupServerLifecycle(fastify: FastifyInstance): void {
  // Error handler - standardized error handling
  fastify.setErrorHandler(createErrorHandler());

  // Graceful shutdown
  const gracefulShutdown = async () => {
    fastify.log.info("Shutting down gracefully...");
    await fastify.close();
    process.exit(0);
  };

  process.on("SIGTERM", gracefulShutdown);
  process.on("SIGINT", gracefulShutdown);
}

/**
 * Start the server
 */
export async function startServer(fastify: FastifyInstance): Promise<void> {
  console.log("[DEBUG] ========================================");
  console.log("[DEBUG] STARTING SERVER");
  console.log("[DEBUG] ========================================");
  const port = Number(process.env.PORT) || 4000;
  const host = process.env.HOST || "0.0.0.0";
  console.log("[DEBUG] Port:", port);
  console.log("[DEBUG] Host:", host);
  console.log("[DEBUG] Environment:", process.env.NODE_ENV || "development");

  try {
    console.log("[DEBUG] Attempting to listen on", host, "port", port);
    await fastify.listen({ port, host });
    console.log("[DEBUG] ========================================");
    console.log("[DEBUG] ✅ SERVER SUCCESSFULLY STARTED!");
    console.log("[DEBUG] ========================================");
    console.log(`[DEBUG] API ready at http://${host}:${port}`);
    console.log(`[DEBUG] Health check: http://${host}:${port}/health`);
    fastify.log.info(`Server listening on http://${host}:${port}`);
    // Log readiness marker for deployment scripts (deterministic readiness check)
    console.log(`API_READY: listening on port ${port}`);
    console.log("[DEBUG] ========================================");
    console.log("[DEBUG] REGISTERED ROUTES:");
    console.log("[DEBUG] ========================================");
    try {
      const routes = fastify.printRoutes({
        includeHooks: false,
        includeMeta: false,
      });
      console.log(routes);
    } catch (err: any) {
      console.log(
        "[DEBUG] Could not print routes:",
        err?.message || String(err),
      );
    }
  } catch (err: any) {
    console.error("[DEBUG] ========================================");
    console.error("[DEBUG] ❌ SERVER STARTUP FAILED!");
    console.error("[DEBUG] ========================================");
    console.error("[DEBUG] Error type:", err?.constructor?.name || typeof err);
    console.error("[DEBUG] Error message:", err?.message || String(err));
    if (err?.code) {
      console.error("[DEBUG] Error code:", err.code);
    }
    if (err instanceof Error && err.stack) {
      console.error("[DEBUG] Error stack:");
      console.error(err.stack);
    }
    fastify.log.error(err);
    process.exit(1);
  }
}
