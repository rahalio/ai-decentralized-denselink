/**
 * DynamoDB outbox store for durable integration events.
 *
 * Item shape uses status + GSI-friendly keys on the core table:
 *   PK = OUTBOX#{orgId}
 *   SK = EVENT#{occurredAt}#{eventId}
 *   GSI2 PK = OUTBOX#STATUS#{status}, SK = EVENT#{occurredAt}#{eventId}
 */

import type { IntegrationEventEnvelope } from "@denselink/core/_shared/events";
import type { AdapterDynamoDBClient } from "../dynamodb-client-types.js";
import { getCoreTableName } from "../dynamodb-utils.js";

export type OutboxStatus = "pending" | "processing" | "processed" | "failed";

export type OutboxItem = IntegrationEventEnvelope & {
  status: OutboxStatus;
  attempts: number;
  lastError?: string;
  availableAt?: string;
};

export class DynamoDbOutboxStore {
  private readonly tableName: string;

  constructor(private readonly dynamoClient: AdapterDynamoDBClient) {
    this.tableName = getCoreTableName();
  }

  private buildKeys(event: IntegrationEventEnvelope) {
    const pk = `OUTBOX#${event.tenantId}`;
    const sk = `EVENT#${event.occurredAt}#${event.eventId}`;
    return { pk, sk };
  }

  async putPending(event: IntegrationEventEnvelope): Promise<void> {
    const { pk, sk } = this.buildKeys(event);
    const item: Record<string, unknown> = {
      PK: pk,
      SK: sk,
      entityType: "OUTBOX_EVENT",
      GSI2PK: "OUTBOX#STATUS#pending",
      GSI2SK: sk,
      status: "pending" satisfies OutboxStatus,
      attempts: 0,
      ...event,
    };

    await this.dynamoClient.put({
      TableName: this.tableName,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    });
  }

  async listPending(limit = 25): Promise<OutboxItem[]> {
    const result = await this.dynamoClient.query({
      TableName: this.tableName,
      IndexName: "GSI2",
      KeyConditionExpression: "GSI2PK = :pk",
      ExpressionAttributeValues: {
        ":pk": "OUTBOX#STATUS#pending",
      },
      Limit: limit,
    });

    return (result.Items ?? []).map((item) => this.toOutboxItem(item));
  }

  async markProcessed(event: IntegrationEventEnvelope): Promise<void> {
    const { pk, sk } = this.buildKeys(event);
    await this.dynamoClient.update({
      TableName: this.tableName,
      Key: { PK: pk, SK: sk },
      UpdateExpression:
        "SET #status = :processed, GSI2PK = :gsi, attempts = if_not_exists(attempts, :zero) + :one",
      ExpressionAttributeNames: { "#status": "status" },
      ExpressionAttributeValues: {
        ":processed": "processed",
        ":gsi": "OUTBOX#STATUS#processed",
        ":zero": 0,
        ":one": 1,
      },
    });
  }

  async markFailed(
    event: IntegrationEventEnvelope,
    error: unknown,
  ): Promise<void> {
    const { pk, sk } = this.buildKeys(event);
    const message =
      error instanceof Error ? error.message : String(error ?? "unknown");
    await this.dynamoClient.update({
      TableName: this.tableName,
      Key: { PK: pk, SK: sk },
      UpdateExpression:
        "SET #status = :failed, GSI2PK = :gsi, lastError = :err, attempts = if_not_exists(attempts, :zero) + :one",
      ExpressionAttributeNames: { "#status": "status" },
      ExpressionAttributeValues: {
        ":failed": "failed",
        ":gsi": "OUTBOX#STATUS#failed",
        ":err": message.slice(0, 1000),
        ":zero": 0,
        ":one": 1,
      },
    });
  }

  private toOutboxItem(item: Record<string, unknown>): OutboxItem {
    return {
      eventId: String(item.eventId),
      eventType: String(item.eventType),
      sourceDomain: item.sourceDomain as IntegrationEventEnvelope["sourceDomain"],
      schemaVersion: Number(item.schemaVersion),
      occurredAt: String(item.occurredAt),
      correlationId: String(item.correlationId),
      tenantId: String(item.tenantId),
      accountId: item.accountId ? String(item.accountId) : undefined,
      aggregateId: item.aggregateId ? String(item.aggregateId) : undefined,
      payload: item.payload,
      status: (item.status as OutboxStatus) ?? "pending",
      attempts: Number(item.attempts ?? 0),
      lastError: item.lastError ? String(item.lastError) : undefined,
      availableAt: item.availableAt ? String(item.availableAt) : undefined,
    };
  }
}
