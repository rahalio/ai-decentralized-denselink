/**
 * DynamoDB outbox store + worker unit tests (mocked client).
 */

import { describe, it, expect, vi } from "vitest";
import { DynamoDbOutboxStore } from "@denselink/adapters/_shared/messaging/dynamodb-outbox-store.js";
import { startOutboxWorker } from "@denselink/adapters/_shared/messaging/outbox-worker.js";
import { createInProcessIntegrationEventBus } from "@denselink/adapters/_shared/messaging/in-process-integration-event-bus.js";
import type { AdapterDynamoDBClient } from "@denselink/adapters";
import type { IntegrationEventEnvelope } from "@denselink/core/_shared/events";

describe("DynamoDbOutboxStore", () => {
  it("writes a pending outbox item", async () => {
    process.env.TABLE_NAME = "test-core";
    const put = vi.fn(async () => ({}));
    const client = { put } as unknown as AdapterDynamoDBClient;
    const store = new DynamoDbOutboxStore(client);

    const event: IntegrationEventEnvelope = {
      eventId: "evt_1",
      eventType: "payment.deposit.created",
      sourceDomain: "payment",
      schemaVersion: 1,
      occurredAt: "2026-01-01T00:00:00.000Z",
      correlationId: "c",
      orgId: "org_1",
      payload: { depositId: "d1" },
    };

    await store.putPending(event);

    expect(put).toHaveBeenCalledWith(
      expect.objectContaining({
        TableName: "test-core",
        Item: expect.objectContaining({
          PK: "OUTBOX#org_1",
          status: "pending",
          eventId: "evt_1",
          GSI2PK: "OUTBOX#STATUS#pending",
        }),
      }),
    );
  });
});

describe("outbox worker", () => {
  it("dispatches pending items and marks them processed", async () => {
    process.env.TABLE_NAME = "test-core";
    const event: IntegrationEventEnvelope = {
      eventId: "evt_2",
      eventType: "payment.deposit.created",
      sourceDomain: "payment",
      schemaVersion: 1,
      occurredAt: "2026-01-01T00:00:00.000Z",
      correlationId: "c",
      orgId: "org_1",
      payload: {},
    };

    const store = {
      listPending: vi.fn(async () => [{ ...event, status: "pending", attempts: 0 }]),
      markProcessed: vi.fn(async () => undefined),
      markFailed: vi.fn(async () => undefined),
    };

    const bus = createInProcessIntegrationEventBus();
    const handle = vi.fn(async () => undefined);
    bus.register({ eventType: "*", handle });

    const worker = startOutboxWorker(store as any, bus, { intervalMs: 60_000 });
    await worker.tick();
    worker.stop();

    expect(handle).toHaveBeenCalled();
    expect(store.markProcessed).toHaveBeenCalledWith(
      expect.objectContaining({ eventId: "evt_2" }),
    );
  });
});
