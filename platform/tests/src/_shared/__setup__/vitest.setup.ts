/**
 * Vitest Global Setup
 *
 * Shared test utility for all domains.
 * Configures test environment with:
 * - DynamoDB Local connection
 * - Frozen time
 * - Seeded faker
 * - Baseline data
 */

import { beforeAll, afterAll, beforeEach, afterEach, vi } from "vitest";
import { startTestDb, stopTestDb } from "./test-db.setup.js";

// Set required environment variables
process.env.TZ = "UTC";
process.env.TEST_FIXED_DATE = "2025-01-01T00:00:00Z";
process.env.TEST_FAKER_SEED = "12345";

/**
 * Global setup - runs once per worker
 */
beforeAll(async () => {
  console.log("🚀 Starting test environment...");

  // Connect to DynamoDB Local (assumes it's already running via docker-compose)
  const client = await startTestDb();

  // Make DynamoDB client available globally
  (globalThis as any).dynamoClient = client;

  console.log("✅ Test environment ready");
}, 10000); // 10s timeout

/**
 * Global teardown - runs once per worker
 */
afterAll(async () => {
  await stopTestDb();
});

/**
 * Per-test setup
 */
beforeEach(() => {
  // ⚠️ DO NOT use fake timers globally - breaks Fastify async operations!
  // Tests that need frozen time should opt-in explicitly with:
  //   vi.useFakeTimers(); vi.setSystemTime(new Date("2025-01-01"));
});

/**
 * Per-test teardown
 */
afterEach(() => {
  // Ensure real timers are restored (in case test used fake timers)
  vi.useRealTimers();
});
