/**
 * DynamoDB Utilities
 *
 * Table name resolvers and shared helpers for DynamoDB repository adapters.
 * Entity-specific key building is done via each adapter's private buildPK/buildSK.
 */

export { sanitizeItem } from "./dynamodb-key-helpers.js";

/**
 * Get the core DynamoDB table name from environment variables
 *
 * @returns The core table name (e.g., "ddd-codegen-starter-core-dev")
 * @throws Error if TABLE_NAME or DYNAMODB_CORE_TABLE_NAME environment variable is not set
 */
export function getCoreTableName(): string {
  const tableName = process.env.TABLE_NAME || process.env.DYNAMODB_CORE_TABLE_NAME;
  if (!tableName) {
    throw new Error(
      "TABLE_NAME or DYNAMODB_CORE_TABLE_NAME environment variable is not set. Please set one of these to your DynamoDB core table name."
    );
  }
  return tableName;
}

/**
 * Get the base DynamoDB table name from environment variables
 *
 * @returns The base table name (e.g., "ddd-codegen-starter-base-dev")
 * @throws Error if BASE_TABLE_NAME or DYNAMODB_BASE_TABLE_NAME environment variable is not set
 */
export function getBaseTableName(): string {
  const tableName = process.env.BASE_TABLE_NAME || process.env.DYNAMODB_BASE_TABLE_NAME;
  if (!tableName) {
    throw new Error(
      "BASE_TABLE_NAME or DYNAMODB_BASE_TABLE_NAME environment variable is not set. Please set one of these to your DynamoDB base table name."
    );
  }
  return tableName;
}

/**
 * Get the analytics DynamoDB table name from environment variables
 *
 * @returns The analytics table name (e.g., "ddd-codegen-starter-analytics-dev")
 * @throws Error if ANALYTICS_TABLE_NAME or DYNAMODB_ANALYTICS_TABLE_NAME environment variable is not set
 */
export function getAnalyticsTableName(): string {
  const tableName = process.env.ANALYTICS_TABLE_NAME || process.env.DYNAMODB_ANALYTICS_TABLE_NAME;
  if (!tableName) {
    throw new Error(
      "ANALYTICS_TABLE_NAME or DYNAMODB_ANALYTICS_TABLE_NAME environment variable is not set. Please set one of these to your DynamoDB analytics table name."
    );
  }
  return tableName;
}

/**
 * Get the realtime DynamoDB table name from environment variables
 *
 * @returns The realtime table name (e.g., "ddd-codegen-starter-app-realtime-dev")
 * @throws Error if REALTIME_TABLE_NAME or DYNAMODB_REALTIME_TABLE_NAME environment variable is not set
 */
export function getRealtimeTableName(): string {
  const tableName =
    process.env.REALTIME_TABLE_NAME || process.env.DYNAMODB_REALTIME_TABLE_NAME;
  if (!tableName) {
    throw new Error(
      "REALTIME_TABLE_NAME or DYNAMODB_REALTIME_TABLE_NAME environment variable is not set. Please set one of these to your DynamoDB realtime table name."
    );
  }
  return tableName;
}
