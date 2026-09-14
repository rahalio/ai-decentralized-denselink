import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const ingestNodeTelemetry_Body = z
  .object({
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    licenseId: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
    activeNodes: z.number().int().gte(0),
    geoBin: z.string().optional(),
    sessionDurationMinutesAvg: z.number().optional(),
    capturedAt: z.string().datetime({ offset: true }),
  })
  .passthrough();
const AppId = z.string();
const LicenseId = z.string();
const NodeTelemetryAggregateCreate = z
  .object({
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    licenseId: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
    activeNodes: z.number().int().gte(0),
    geoBin: z.string().optional(),
    sessionDurationMinutesAvg: z.number().optional(),
    capturedAt: z.string().datetime({ offset: true }),
  })
  .passthrough();
const Problem = z
  .object({
    type: z.string().url(),
    title: z.string(),
    status: z.number().int(),
    detail: z.string(),
    instance: z.string().url(),
    code: z.string(),
  })
  .partial()
  .passthrough();
const TelemetryAggregateId = z.string();
const NodeTelemetryAggregate = z
  .object({
    id: z.string().regex(/^tla_[0-9A-HJKMNP-TV-Z]{26}$/),
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    licenseId: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
    activeNodes: z.number().int().gte(0),
    geoBin: z.string().optional(),
    sessionDurationMinutesAvg: z.number().optional(),
    capturedAt: z.string().datetime({ offset: true }),
    ingestedAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const ResponseMeta = z
  .object({
    requestId: z.string().uuid(),
    correlationId: z.string(),
    generatedAt: z.string().datetime({ offset: true }),
  })
  .partial()
  .passthrough();
const NodeTelemetryAggregateResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^tla_[0-9A-HJKMNP-TV-Z]{26}$/),
        appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
        licenseId: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
        activeNodes: z.number().int().gte(0),
        geoBin: z.string().optional(),
        sessionDurationMinutesAvg: z.number().optional(),
        capturedAt: z.string().datetime({ offset: true }),
        ingestedAt: z.string().datetime({ offset: true }).optional(),
      })
      .passthrough(),
    meta: z
      .object({
        requestId: z.string().uuid(),
        correlationId: z.string(),
        generatedAt: z.string().datetime({ offset: true }),
      })
      .partial()
      .passthrough()
      .optional(),
  })
  .passthrough();

export const schemas: any = {
  ingestNodeTelemetry_Body,
  AppId,
  LicenseId,
  NodeTelemetryAggregateCreate,
  Problem,
  TelemetryAggregateId,
  NodeTelemetryAggregate,
  ResponseMeta,
  NodeTelemetryAggregateResponse,
};

const endpoints = makeApi([
  {
    method: 'post',
    path: '/v1/telemetry/aggregates',
    alias: 'ingestNodeTelemetry',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: ingestNodeTelemetry_Body,
      },
      {
        name: 'Idempotency-Key',
        type: 'Header',
        schema: z.string().min(1).max(128),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            id: z.string().regex(/^tla_[0-9A-HJKMNP-TV-Z]{26}$/),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            licenseId: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
            activeNodes: z.number().int().gte(0),
            geoBin: z.string().optional(),
            sessionDurationMinutesAvg: z.number().optional(),
            capturedAt: z.string().datetime({ offset: true }),
            ingestedAt: z.string().datetime({ offset: true }).optional(),
          })
          .passthrough(),
        meta: z
          .object({
            requestId: z.string().uuid(),
            correlationId: z.string(),
            generatedAt: z.string().datetime({ offset: true }),
          })
          .partial()
          .passthrough()
          .optional(),
      })
      .passthrough(),
    errors: [
      {
        status: 400,
        description: `Malformed request`,
        schema: z
          .object({
            type: z.string().url(),
            title: z.string(),
            status: z.number().int(),
            detail: z.string(),
            instance: z.string().url(),
            code: z.string(),
          })
          .partial()
          .passthrough(),
      },
      {
        status: 401,
        description: `Missing or invalid API key`,
        schema: z
          .object({
            type: z.string().url(),
            title: z.string(),
            status: z.number().int(),
            detail: z.string(),
            instance: z.string().url(),
            code: z.string(),
          })
          .partial()
          .passthrough(),
      },
    ],
  },
]);

export const api: any = new Zodios(
  'https://api.ddd-codegen-starter.local/v1',
  endpoints
);

export function createApiClient(baseUrl: string, options?: ZodiosOptions): any {
  return new Zodios(baseUrl, endpoints, options);
}
