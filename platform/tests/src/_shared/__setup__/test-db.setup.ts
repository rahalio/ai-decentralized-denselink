/**
 * Test Database Setup
 *
 * Shared test utility for all domains.
 * Manages DynamoDB Local for integration/E2E tests
 *
 * DynamoDB Local should be started via docker-compose before running tests:
 *   docker-compose up -d dynamodb-local
 *
 * Or use the helper script:
 *   ./scripts/dynamodb-start.sh
 */

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";

let dynamoClient: DynamoDBClient | null = null;

/**
 * Get DynamoDB client instance
 */
export function getDynamoClient(): DynamoDBClient {
  if (!dynamoClient) {
    throw new Error("DynamoDB client not initialized. Call startTestDb() first.");
  }
  return dynamoClient;
}

/**
 * Start test database (DynamoDB Local)
 *
 * Assumes DynamoDB Local is already running via docker-compose.
 * Sets up environment variables and creates DynamoDB client.
 */
export async function startTestDb(): Promise<DynamoDBClient> {
  if (dynamoClient) {
    return getDynamoClient();
  }

  console.log("🚀 Connecting to DynamoDB Local...");

  // Set DynamoDB Local endpoint if not already set
  const endpoint = process.env.AWS_ENDPOINT_URL || "http://localhost:8000";
  const region = process.env.AWS_REGION || "us-east-1";

  // Set default credentials if not provided
  if (!process.env.AWS_ACCESS_KEY_ID) {
    process.env.AWS_ACCESS_KEY_ID = "test";
  }
  if (!process.env.AWS_SECRET_ACCESS_KEY) {
    process.env.AWS_SECRET_ACCESS_KEY = "test";
  }

  // Set table names if not already set
  if (!process.env.TABLE_NAME && !process.env.DYNAMODB_CORE_TABLE_NAME) {
    process.env.TABLE_NAME = "ddd-codegen-starter-core-test";
    process.env.DYNAMODB_CORE_TABLE_NAME = "ddd-codegen-starter-core-test";
  }
  if (!process.env.BASE_TABLE_NAME && !process.env.DYNAMODB_BASE_TABLE_NAME) {
    process.env.BASE_TABLE_NAME = "ddd-codegen-starter-base-test";
    process.env.DYNAMODB_BASE_TABLE_NAME = "ddd-codegen-starter-base-test";
  }
  if (!process.env.ANALYTICS_TABLE_NAME && !process.env.DYNAMODB_ANALYTICS_TABLE_NAME) {
    process.env.ANALYTICS_TABLE_NAME = "ddd-codegen-starter-analytics-test";
    process.env.DYNAMODB_ANALYTICS_TABLE_NAME = "ddd-codegen-starter-analytics-test";
  }

  // Initialize DynamoDB client
  dynamoClient = new DynamoDBClient({
    endpoint,
    region,
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
  });

  console.log("✅ DynamoDB Local ready");
  console.log(`   Endpoint: ${endpoint}`);
  console.log(`   Core Table: ${process.env.TABLE_NAME || process.env.DYNAMODB_CORE_TABLE_NAME}`);

  return dynamoClient;
}

/**
 * Stop test database (cleanup DynamoDB client)
 */
export async function stopTestDb(): Promise<void> {
  if (dynamoClient) {
    dynamoClient.destroy();
    dynamoClient = null;
    console.log("🛑 DynamoDB client stopped");
  }
}
