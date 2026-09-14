/**
 * Idempotent handler wrapper — skips events already marked processed.
 */

import type { IntegrationEventEnvelope } from "@denselink/core/_shared/events";
import type { IntegrationEventHandler } from "@denselink/services/_shared";
import type { DynamoDbProcessedEventStore } from "./processed-event-store.js";

export function withIdempotency(
  handler: IntegrationEventHandler,
  store: DynamoDbProcessedEventStore,
): IntegrationEventHandler {
  return {
    eventType: handler.eventType,
    async handle(event: IntegrationEventEnvelope): Promise<void> {
      if (await store.hasProcessed(event.eventId)) {
        return;
      }
      await handler.handle(event);
      try {
        await store.markProcessed(event.eventId, event.eventType);
      } catch {
        // Concurrent consumer may have raced the condition — treat as success.
      }
    },
  };
}
