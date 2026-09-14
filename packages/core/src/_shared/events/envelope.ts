/**
 * Integration event envelope — shared contract for cross-domain async messaging.
 */

import { z } from 'zod';

export const INTEGRATION_EVENT_SOURCE_DOMAINS = ['identity'] as const;

export type IntegrationEventSourceDomain =
  (typeof INTEGRATION_EVENT_SOURCE_DOMAINS)[number];

export const IntegrationEventEnvelopeSchema = z.object({
  eventId: z.string().min(1),
  eventType: z.string().min(1),
  sourceDomain: z.enum(INTEGRATION_EVENT_SOURCE_DOMAINS),
  schemaVersion: z.number().int().positive(),
  occurredAt: z.string().datetime({ offset: true }).or(z.string().min(1)),
  correlationId: z.string().min(1),
  tenantId: z.string().min(1),
  accountId: z.string().min(1).optional(),
  aggregateId: z.string().min(1).optional(),
  payload: z.unknown(),
});

export type IntegrationEventEnvelope = z.infer<
  typeof IntegrationEventEnvelopeSchema
>;

/** Input for publishers — eventId / occurredAt filled by the bus. */
export type PublishIntegrationEventInput = {
  eventType: string;
  sourceDomain: IntegrationEventSourceDomain;
  schemaVersion: number;
  correlationId: string;
  tenantId: string;
  accountId?: string;
  aggregateId?: string;
  payload: unknown;
};
