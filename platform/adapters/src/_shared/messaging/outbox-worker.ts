/**
 * Outbox drain worker — polls pending events and dispatches via the in-process bus.
 *
 * Safe to run in-process alongside the API or as a compose sidecar entrypoint.
 */

import type { InProcessIntegrationEventBus } from "./in-process-integration-event-bus.js";
import type { DynamoDbOutboxStore } from "./dynamodb-outbox-store.js";

export type OutboxWorkerOptions = {
  intervalMs?: number;
  batchSize?: number;
  onError?: (error: unknown) => void;
};

export type OutboxWorkerHandle = {
  stop(): void;
  /** Run a single drain cycle (useful in tests). */
  tick(): Promise<void>;
};

export function startOutboxWorker(
  outbox: DynamoDbOutboxStore,
  bus: InProcessIntegrationEventBus,
  options: OutboxWorkerOptions = {},
): OutboxWorkerHandle {
  const intervalMs = options.intervalMs ?? 5_000;
  const batchSize = options.batchSize ?? 25;
  const onError =
    options.onError ??
    ((error: unknown) => {
      console.error("[outbox-worker] drain failed", error);
    });

  let stopped = false;
  let timer: ReturnType<typeof setInterval> | undefined;

  async function tick(): Promise<void> {
    const pending = await outbox.listPending(batchSize);
    for (const item of pending) {
      try {
        await bus.dispatch(item);
        await outbox.markProcessed(item);
      } catch (error) {
        await outbox.markFailed(item, error);
        onError(error);
      }
    }
  }

  timer = setInterval(() => {
    if (stopped) return;
    void tick().catch(onError);
  }, intervalMs);

  // Avoid keeping the process alive solely for the worker in tests
  if (typeof timer.unref === "function") {
    timer.unref();
  }

  return {
    stop() {
      stopped = true;
      if (timer) clearInterval(timer);
    },
    tick,
  };
}
