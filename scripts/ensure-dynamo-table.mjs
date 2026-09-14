#!/usr/bin/env node
/**
 * Ensure Dynamo Local product table exists.
 * Usage: TABLE_NAME=denselink-core-local AWS_ENDPOINT_URL=http://localhost:8000 node scripts/ensure-dynamo-table.mjs
 */

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

async function main() {
  process.env.TABLE_NAME =
    process.env.TABLE_NAME || 'denselink-core-local';
  process.env.AWS_ENDPOINT_URL =
    process.env.AWS_ENDPOINT_URL || 'http://localhost:8000';
  process.env.AWS_REGION = process.env.AWS_REGION || 'us-east-1';

  // Dynamic import of built or ts adapters is heavy; use AWS SDK directly
  const { DynamoDBClient, CreateTableCommand, DescribeTableCommand } =
    await import('@aws-sdk/client-dynamodb');

  const client = new DynamoDBClient({
    region: process.env.AWS_REGION,
    endpoint: process.env.AWS_ENDPOINT_URL,
    credentials: { accessKeyId: 'local', secretAccessKey: 'local' },
  });
  const TableName = process.env.TABLE_NAME;

  try {
    await client.send(new DescribeTableCommand({ TableName }));
    console.log(`Table exists: ${TableName}`);
    return;
  } catch {
    // create
  }

  await client.send(
    new CreateTableCommand({
      TableName,
      BillingMode: 'PAY_PER_REQUEST',
      AttributeDefinitions: [
        { AttributeName: 'PK', AttributeType: 'S' },
        { AttributeName: 'SK', AttributeType: 'S' },
      ],
      KeySchema: [
        { AttributeName: 'PK', KeyType: 'HASH' },
        { AttributeName: 'SK', KeyType: 'RANGE' },
      ],
    }),
  );
  console.log(`Created table: ${TableName}`);
  void require;
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
