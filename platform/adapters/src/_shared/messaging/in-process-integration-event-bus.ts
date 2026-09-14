/**
 * In-process async integration event bus.
 *
 * Implements publisher + handler registry for the monolith. Handlers run
 * off the request path via queueMicrotask; failures are logged and do not
 * reject the publish promise.
 */

import { ulid } from "ulid";
import type {
  IntegrationEventEnvelope,
  PublishIntegrationEventInput,
} from "@denselink/core/_shared/events";
import type { IntegrationEventPublisher } from "@denselink/services/_shared";
import type {
  EventHandlerRegistry,
  IntegrationEventHandler,
} from "@denselink/services/_shared";

export type InProcessIntegrationEventBus = IntegrationEventPublisher &
  EventHandlerRegistry & {
    /** Dispatch a fully-formed envelope to matching handlers (async). */
    dispatch(event: IntegrationEventEnvelope): Promise<void>;
  };

function matches(
  handler: IntegrationEventHandler,
  eventType: string,
): boolean {
  const types = Array.isArray(handler.eventType)
    ? handler.eventType
    : [handler.eventType];
  return types.some((t) => t === "*" || t === eventType);
}

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

export function createInProcessIntegrationEventBus(
  options: {
    onHandlerError?: (
      error: unknown,
      event: IntegrationEventEnvelope,
      handler: IntegrationEventHandler,
    ) => void;
  } = {},
): InProcessIntegrationEventBus {
  const handlers: IntegrationEventHandler[] = [];
  const onHandlerError =
    options.onHandlerError ??
    ((error, event, handler) => {
      console.error(
        "[integration-event-bus] handler failed",
        {
          eventType: event.eventType,
          eventId: event.eventId,
          handlerEventType: handler.eventType,
        },
        error,
      );
    });

  async function runHandlers(event: IntegrationEventEnvelope): Promise<void> {
    const matched = handlers.filter((h) => matches(h, event.eventType));
    await Promise.all(
      matched.map(async (handler) => {
        try {
          await handler.handle(event);
        } catch (error) {
          onHandlerError(error, event, handler);
        }
      }),
    );
  }

  function enqueue(event: IntegrationEventEnvelope): void {
    queueMicrotask(() => {
      void runHandlers(event);
    });
  }

  return {
    register(handler: IntegrationEventHandler): void {
      handlers.push(handler);
    },

    listHandlers(): readonly IntegrationEventHandler[] {
      return handlers;
    },

    async publish(
      event: PublishIntegrationEventInput | PublishIntegrationEventInput[],
    ): Promise<void> {
      const inputs = Array.isArray(event) ? event : [event];
      for (const input of inputs) {
        enqueue(toEnvelope(input));
      }
    },

    /** Await matching handlers (used by outbox worker / durable path). */
    async dispatch(event: IntegrationEventEnvelope): Promise<void> {
      await runHandlers(event);
    },
  };
}
