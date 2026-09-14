/**
 * Adapter DynamoDB Client Type Definition
 *
 * Defines the interface for DynamoDB clients used by adapters.
 * This type is defined in the adapters package to maintain proper dependency direction:
 * - Adapters (infrastructure) should not depend on api-server (presentation)
 * - This type belongs to the adapters layer
 */

import type {
  QueryCommandInput,
  QueryCommandOutput,
  GetCommandInput,
  GetCommandOutput,
  PutCommandInput,
  PutCommandOutput,
  UpdateCommandInput,
  UpdateCommandOutput,
  DeleteCommandInput,
  DeleteCommandOutput,
  ScanCommandInput,
  ScanCommandOutput,
  TransactWriteCommandInput,
  TransactWriteCommandOutput,
} from "@aws-sdk/lib-dynamodb";
import type {
  BatchWriteItemCommandInput,
  BatchWriteItemCommandOutput,
} from "@aws-sdk/client-dynamodb";

/**
 * DynamoDB Client interface expected by adapters
 *
 * Adapters use DocumentClient methods (query, get, put, etc.) which are
 * convenience methods that wrap the AWS SDK v3 command pattern.
 */
export interface AdapterDynamoDBClient {
  query(input: QueryCommandInput): Promise<QueryCommandOutput>;
  get(input: GetCommandInput): Promise<GetCommandOutput>;
  put(input: PutCommandInput): Promise<PutCommandOutput>;
  update(input: UpdateCommandInput): Promise<UpdateCommandOutput>;
  delete(input: DeleteCommandInput): Promise<DeleteCommandOutput>;
  scan(input: ScanCommandInput): Promise<ScanCommandOutput>;
  batchWrite(
    input: BatchWriteItemCommandInput
  ): Promise<BatchWriteItemCommandOutput>;
  transactWrite(
    input: TransactWriteCommandInput
  ): Promise<TransactWriteCommandOutput>;
  send<T>(command: T): Promise<any>;
}
