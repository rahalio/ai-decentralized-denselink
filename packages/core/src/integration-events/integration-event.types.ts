export type IntegrationEventTypeDefinition = {
  type: string;
  version?: string;
  description?: string;
};

export type IntegrationEventPayload = Record<string, unknown>;
