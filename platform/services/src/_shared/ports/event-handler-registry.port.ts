/**
 * Event handler registry — composition root registers consumers; bus dispatches.
 */

import type { IntegrationEventEnvelope } from "@denselink/core/_shared/events";

export interface IntegrationEventHandler {
  /**
   * Exact event type(s) or a single "*" wildcard for all events.
   */
  eventType: string | string[];
  handle(event: IntegrationEventEnvelope): Promise<void>;
}

export interface EventHandlerRegistry {
  register(handler: IntegrationEventHandler): void;
  listHandlers(): readonly IntegrationEventHandler[];
}
