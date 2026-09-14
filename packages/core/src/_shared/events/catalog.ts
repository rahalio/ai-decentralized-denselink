/**
 * Integration event type catalog — identity starter.
 * Extend in consumer repos when adding product domains.
 */

import { z } from 'zod';

export const IntegrationEventTypes = {
  IDENTITY_API_KEY_CREATED: 'identity.api-key.created',
  IDENTITY_API_KEY_REVOKED: 'identity.api-key.revoked',
  IDENTITY_USER_CREATED: 'identity.user.created',
  IDENTITY_USER_DISABLED: 'identity.user.disabled',
} as const;

export type IntegrationEventType =
  (typeof IntegrationEventTypes)[keyof typeof IntegrationEventTypes];

export const ApiKeyCreatedPayloadSchema = z.object({
  keyId: z.string().min(1),
  tenantId: z.string().min(1),
});

export type ApiKeyCreatedPayload = z.infer<typeof ApiKeyCreatedPayloadSchema>;
