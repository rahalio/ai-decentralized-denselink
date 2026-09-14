/**
 * Messaging adapters — in-process bus, DynamoDB outbox, worker.
 */

export {
  createInProcessIntegrationEventBus,
  type InProcessIntegrationEventBus,
} from "./in-process-integration-event-bus.js";
export {
  DynamoDbOutboxStore,
  type OutboxItem,
  type OutboxStatus,
} from "./dynamodb-outbox-store.js";
export { DynamoDbProcessedEventStore } from "./processed-event-store.js";
export { OutboxIntegrationEventPublisher } from "./outbox-integration-event-publisher.js";
export {
  startOutboxWorker,
  type OutboxWorkerHandle,
  type OutboxWorkerOptions,
} from "./outbox-worker.js";
export { withIdempotency } from "./with-idempotency.js";
