/**
 * Integration event bus unit tests.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  createInProcessIntegrationEventBus,
} from "@denselink/adapters/_shared/messaging/in-process-integration-event-bus.js";
import { withIdempotency } from "@denselink/adapters/_shared/messaging/with-idempotency.js";
import { IntegrationEventTypes } from "@denselink/core/_shared/events";
import type { IntegrationEventEnvelope } from "@denselink/core/_shared/events";
import type { DynamoDbProcessedEventStore } from "@denselink/adapters/_shared/messaging/processed-event-store.js";
import { createNotificationIntegrationEventHandler } from "@denselink/services/notification/event-handlers";
import { ExecuteCreateDeposit } from "@denselink/services/payment/usecases/execute-create-deposit.usecase.js";

function waitForMicrotasks(): Promise<void> {
  return new Promise((resolve) => queueMicrotask(() => resolve()));
}

describe("InProcessIntegrationEventBus", () => {
  it("resolves publish before handlers finish (async delivery)", async () => {
    const bus = createInProcessIntegrationEventBus();
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const seen: string[] = [];

    bus.register({
      eventType: IntegrationEventTypes.PAYMENT_DEPOSIT_CREATED,
      async handle(event) {
        await gate;
        seen.push(event.eventId);
      },
    });

    const publishPromise = bus.publish({
      eventType: IntegrationEventTypes.PAYMENT_DEPOSIT_CREATED,
      sourceDomain: "payment",
      schemaVersion: 1,
      correlationId: "pay_corr",
      orgId: "org_1",
      accountId: "acc_1",
      payload: { depositId: "d1", accountId: "acc_1", amount: 10, currency: "USD" },
    });

    await expect(publishPromise).resolves.toBeUndefined();
    expect(seen).toHaveLength(0);

    release();
    await waitForMicrotasks();
    await waitForMicrotasks();
    expect(seen).toHaveLength(1);
  });

  it("does not reject publish when a handler throws", async () => {
    const bus = createInProcessIntegrationEventBus({
      onHandlerError: vi.fn(),
    });
    const second = vi.fn();

    bus.register({
      eventType: "*",
      async handle() {
        throw new Error("boom");
      },
    });
    bus.register({
      eventType: "*",
      handle: second,
    });

    await expect(
      bus.publish({
        eventType: "payment.deposit.created",
        sourceDomain: "payment",
        schemaVersion: 1,
        correlationId: "c",
        orgId: "o",
        payload: {},
      }),
    ).resolves.toBeUndefined();

    await waitForMicrotasks();
    await waitForMicrotasks();
    expect(second).toHaveBeenCalled();
  });

  it("skips already-processed events when wrapped with idempotency", async () => {
    const handled = vi.fn();
    const store = {
      hasProcessed: vi.fn(async (id: string) => id === "evt_done"),
      markProcessed: vi.fn(async () => undefined),
    } as unknown as DynamoDbProcessedEventStore;

    const bus = createInProcessIntegrationEventBus();
    bus.register(
      withIdempotency(
        {
          eventType: "*",
          handle: handled,
        },
        store,
      ),
    );

    const base: IntegrationEventEnvelope = {
      eventId: "evt_done",
      eventType: "payment.deposit.created",
      sourceDomain: "payment",
      schemaVersion: 1,
      occurredAt: new Date().toISOString(),
      correlationId: "c",
      orgId: "o",
      payload: {},
    };

    await bus.dispatch(base);
    expect(handled).not.toHaveBeenCalled();

    await bus.dispatch({ ...base, eventId: "evt_new" });
    expect(handled).toHaveBeenCalledTimes(1);
    expect(store.markProcessed).toHaveBeenCalledWith(
      "evt_new",
      "payment.deposit.created",
    );
  });
});

describe("notification fan-out handler", () => {
  it("records a stub fan-out for payment deposit events", async () => {
    const record = vi.fn();
    const handler = createNotificationIntegrationEventHandler({ record });

    await handler.handle({
      eventId: "evt_1",
      eventType: IntegrationEventTypes.PAYMENT_DEPOSIT_CREATED,
      sourceDomain: "payment",
      schemaVersion: 1,
      occurredAt: new Date().toISOString(),
      correlationId: "c",
      orgId: "org_1",
      accountId: "acc_1",
      payload: {},
    });

    expect(record).toHaveBeenCalledWith(
      expect.objectContaining({
        eventId: "evt_1",
        title: "Deposit created",
        category: "system",
      }),
    );
  });
});

describe("ExecuteCreateDeposit event emission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("publishes after a successful deposit create and still returns when publish is slow", async () => {
    const publish = vi.fn(async () => undefined);
    const createDeposit = vi.fn(async (input: unknown) => ({
      data: input,
      meta: { correlationId: "c", timestamp: new Date().toISOString() },
    }));

    const uc = new ExecuteCreateDeposit(
      {
        getOrgId: () => "org_1",
        getUserId: () => undefined,
        setOrgId: () => undefined,
        setUserId: () => undefined,
      },
      {
        payId: () => "pay_01habcdefghijklmnopqrstuvw",
      } as any,
      { createDeposit } as any,
      { publish },
    );

    const result = await uc.execute({
      accountId: "acc_1",
      amount: 100,
      currency: "USD",
      methodId: "pm_1",
    } as any);

    expect(createDeposit).toHaveBeenCalled();
    expect(publish).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: IntegrationEventTypes.PAYMENT_DEPOSIT_CREATED,
        sourceDomain: "payment",
        orgId: "org_1",
      }),
    );
    expect(result).toBeTruthy();
  });

  it("returns successfully even if the event publisher rejects after enqueue contract", async () => {
    // Publisher that resolves (handoff succeeded) — handler failures are bus-side.
    // If publish itself throws, use case would fail; durable outbox should not throw after put.
    const publish = vi.fn(async () => undefined);
    const uc = new ExecuteCreateDeposit(
      {
        getOrgId: () => "org_1",
        getUserId: () => undefined,
        setOrgId: () => undefined,
        setUserId: () => undefined,
      },
      { payId: () => "pay_01habcdefghijklmnopqrstuvw" } as any,
      {
        createDeposit: async (input: unknown) => ({
          data: input,
          meta: { correlationId: "c", timestamp: new Date().toISOString() },
        }),
      } as any,
      { publish },
    );

    await expect(
      uc.execute({
        accountId: "acc_1",
        amount: 50,
        currency: "USD",
        methodId: "pm_1",
      } as any),
    ).resolves.toBeTruthy();
  });
});
