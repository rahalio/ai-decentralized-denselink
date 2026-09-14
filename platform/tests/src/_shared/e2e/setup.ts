/**
 * E2E Test Setup - Shared Configuration and Utilities
 *
 * JWT token generation and e2e config. Import from "@denselink/tests/shared/e2e" for e2e tests only.
 */

import jwt from "jsonwebtoken";
import { TEST_ORG_ID, TEST_ACCOUNT_ID, TEST_USER_EMAIL } from "../constants.js";

export { TEST_ORG_ID, TEST_ACCOUNT_ID, TEST_USER_EMAIL };

export const TEST_JWT_SECRET = "test-secret-key-for-e2e-testing";

// Set JWT_SECRET for auth middleware
process.env.JWT_SECRET = TEST_JWT_SECRET;

/**
 * Generate a valid JWT token for testing
 */
export function generateAuthToken(
  orgId: string = TEST_ORG_ID,
  email: string = TEST_USER_EMAIL
): string {
  return jwt.sign(
    {
      accountId: TEST_ACCOUNT_ID,
      orgIds: [orgId],
      email,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600,
    },
    TEST_JWT_SECRET
  );
}

/**
 * Helper to parse JSON response
 */
export function parseJsonResponse(body: string) {
  try {
    return JSON.parse(body);
  } catch {
    return null;
  }
}
