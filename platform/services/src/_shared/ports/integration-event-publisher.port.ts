/**
 * IntegrationEventPublisher — application port for async cross-domain events.
 *
 * Implementations live in adapters (in-process bus, DynamoDB outbox, …).
 * Use cases publish after successful writes; they must not await consumers.
 */

import type { PublishIntegrationEventInput } from "@denselink/core/_shared/events";

export interface IntegrationEventPublisher {
  /**
   * Hand off one or more integration events for asynchronous delivery.
   * Resolves after durable/local enqueue — not after handler completion.
   */
  publish(
    event: PublishIntegrationEventInput | PublishIntegrationEventInput[],
  ): Promise<void>;
}
