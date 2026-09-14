/**
 * Outbox-backed publisher: durable write, then local async dispatch + mark processed.
 *
 * If the process dies after putPending and before markProcessed, the outbox worker
 * retries (at-least-once). Handlers should use eventId idempotency when needed.
 */

import { ulid } from "ulid";
import type {
  IntegrationEventEnvelope,
  PublishIntegrationEventInput,
} from "@denselink/core/_shared/events";
import type { IntegrationEventPublisher } from "@denselink/services/_shared";
import type { DynamoDbOutboxStore } from "./dynamodb-outbox-store.js";
import type { InProcessIntegrationEventBus } from "./in-process-integration-event-bus.js";

function toEnvelope(
  input: PublishIntegrationEventInput,
): IntegrationEventEnvelope {
  return {
    eventId: `evt_${ulid().toLowerCase()}`,
    eventType: input.eventType,
    sourceDomain: input.sourceDomain,
    schemaVersion: input.schemaVersion,
    occurredAt: new Date().toISOString(),
    correlationId: input.correlationId,
    tenantId: input.tenantId,
    accountId: input.accountId,
    aggregateId: input.aggregateId,
    payload: input.payload,
  };
}

export class OutboxIntegrationEventPublisher
  implements IntegrationEventPublisher
{
  constructor(
    private readonly outbox: DynamoDbOutboxStore,
    private readonly bus: InProcessIntegrationEventBus,
    private readonly options: { dispatchLocally?: boolean } = {
      dispatchLocally: true,
    },
  ) {}

  async publish(
    event: PublishIntegrationEventInput | PublishIntegrationEventInput[],
  ): Promise<void> {
    const inputs = Array.isArray(event) ? event : [event];
    for (const input of inputs) {
      const envelope = toEnvelope(input);
      await this.outbox.putPending(envelope);
      if (this.options.dispatchLocally !== false) {
        // Do not await handlers — publish must return after durable handoff.
        void (async () => {
          try {
            await this.bus.dispatch(envelope);
            await this.outbox.markProcessed(envelope);
          } catch (error) {
            await this.outbox.markFailed(envelope, error);
          }
        })();
      }
    }
  }
}
