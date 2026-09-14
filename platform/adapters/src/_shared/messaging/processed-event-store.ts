/**
 * Idempotency store for processed integration events (consumer side).
 */

import type { AdapterDynamoDBClient } from "../dynamodb-client-types.js";
import { getCoreTableName } from "../dynamodb-utils.js";

export class DynamoDbProcessedEventStore {
  private readonly tableName: string;

  constructor(private readonly dynamoClient: AdapterDynamoDBClient) {
    this.tableName = getCoreTableName();
  }

  async hasProcessed(eventId: string): Promise<boolean> {
    const result = await this.dynamoClient.get({
      TableName: this.tableName,
      Key: {
        PK: `PROCESSED_EVENT#${eventId}`,
        SK: "META",
      },
    });
    return Boolean(result.Item);
  }

  async markProcessed(eventId: string, eventType: string): Promise<void> {
    await this.dynamoClient.put({
      TableName: this.tableName,
      Item: {
        PK: `PROCESSED_EVENT#${eventId}`,
        SK: "META",
        entityType: "PROCESSED_EVENT",
        eventId,
        eventType,
        processedAt: new Date().toISOString(),
      },
      ConditionExpression: "attribute_not_exists(PK)",
    });
  }
}
