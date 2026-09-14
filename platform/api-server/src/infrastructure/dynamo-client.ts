/**
 * Creates an AdapterDynamoDBClient from AWS SDK (DynamoDB + DocumentClient).
 * Used by the composition root to build domain dependencies.
 */

import {
  BatchWriteItemCommand,
  type BatchWriteItemCommandInput,
  type BatchWriteItemCommandOutput,
} from "@aws-sdk/client-dynamodb";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  GetCommand,
  PutCommand,
  QueryCommand,
  UpdateCommand,
  DeleteCommand,
  ScanCommand,
  TransactWriteCommand,
} from "@aws-sdk/lib-dynamodb";
import type { AdapterDynamoDBClient } from "@denselink/adapters";

/**
 * Builds a DynamoDB client suitable for the current environment.
 * Uses AWS_ENDPOINT_URL for local (e.g. DynamoDB Local); otherwise default AWS config.
 */
function createRawClient(): DynamoDBClient {
  const region = process.env.AWS_REGION || "us-east-1";
  const endpoint = process.env.AWS_ENDPOINT_URL;
  const config: ConstructorParameters<typeof DynamoDBClient>[0] = { region };
  if (endpoint) {
    config.endpoint = endpoint;
  }
  return new DynamoDBClient(config);
}

/**
 * Returns an AdapterDynamoDBClient backed by AWS SDK DynamoDB + DocumentClient.
 */
export function createAdapterDynamoClient(): AdapterDynamoDBClient {
  const rawClient = createRawClient();
  const docClient = DynamoDBDocumentClient.from(rawClient);

  return {
    get: (input) => docClient.send(new GetCommand(input)),
    put: (input) => docClient.send(new PutCommand(input)),
    query: (input) => docClient.send(new QueryCommand(input)),
    update: (input) => docClient.send(new UpdateCommand(input)),
    delete: (input) => docClient.send(new DeleteCommand(input)),
    scan: (input) => docClient.send(new ScanCommand(input)),
    transactWrite: (input) => docClient.send(new TransactWriteCommand(input)),
    batchWrite: (input: BatchWriteItemCommandInput): Promise<BatchWriteItemCommandOutput> =>
      rawClient.send(new BatchWriteItemCommand(input)),
    send: (command) => docClient.send(command as any),
  };
}
