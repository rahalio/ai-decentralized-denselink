import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const allocateMeshPort_Body = z
  .object({
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    preferredPort: z.number().int().gte(1).lte(65535).optional(),
    sdkVersion: z.string().optional(),
  })
  .passthrough();
const AppId = z.string();
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
const MeshPortId = z.string();
const MeshPortStatus = z.enum(['allocated', 'revoked']);
const MeshPort = z
  .object({
    id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
    port: z.number().int().gte(1).lte(65535),
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    sdkVersion: z.string().optional(),
    status: z.enum(['allocated', 'revoked']),
    collisionBlocked: z.boolean().optional(),
    conflictingAppId: z
      .string()
      .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
    createdAt: z.string().datetime({ offset: true }),
    revokedAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const MeshPortListData = z
  .object({
    items: z.array(
      z
        .object({
          id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
          port: z.number().int().gte(1).lte(65535),
          appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
          sdkVersion: z.string().optional(),
          status: z.enum(['allocated', 'revoked']),
          collisionBlocked: z.boolean().optional(),
          conflictingAppId: z
            .string()
            .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
            .optional(),
          createdAt: z.string().datetime({ offset: true }),
          revokedAt: z.string().datetime({ offset: true }).optional(),
        })
        .passthrough()
    ),
    nextCursor: z.string().optional(),
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
const MeshPortListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
              port: z.number().int().gte(1).lte(65535),
              appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
              sdkVersion: z.string().optional(),
              status: z.enum(['allocated', 'revoked']),
              collisionBlocked: z.boolean().optional(),
              conflictingAppId: z
                .string()
                .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
                .optional(),
              createdAt: z.string().datetime({ offset: true }),
              revokedAt: z.string().datetime({ offset: true }).optional(),
            })
            .passthrough()
        ),
        nextCursor: z.string().optional(),
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
const MeshPortAllocate = z
  .object({
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    preferredPort: z.number().int().gte(1).lte(65535).optional(),
    sdkVersion: z.string().optional(),
  })
  .passthrough();
const MeshPortResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
        port: z.number().int().gte(1).lte(65535),
        appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
        sdkVersion: z.string().optional(),
        status: z.enum(['allocated', 'revoked']),
        collisionBlocked: z.boolean().optional(),
        conflictingAppId: z
          .string()
          .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
          .optional(),
        createdAt: z.string().datetime({ offset: true }),
        revokedAt: z.string().datetime({ offset: true }).optional(),
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
  allocateMeshPort_Body,
  AppId,
  Problem,
  MeshPortId,
  MeshPortStatus,
  MeshPort,
  MeshPortListData,
  ResponseMeta,
  MeshPortListResponse,
  MeshPortAllocate,
  MeshPortResponse,
};

const endpoints = makeApi([
  {
    method: 'get',
    path: '/v1/meshports',
    alias: 'listMeshPorts',
    requestFormat: 'json',
    parameters: [
      {
        name: 'cursor',
        type: 'Query',
        schema: z.string().optional(),
      },
      {
        name: 'limit',
        type: 'Query',
        schema: z.number().int().gte(1).lte(100).optional().default(25),
      },
      {
        name: 'appId',
        type: 'Query',
        schema: z
          .string()
          .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
          .optional(),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
                  port: z.number().int().gte(1).lte(65535),
                  appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
                  sdkVersion: z.string().optional(),
                  status: z.enum(['allocated', 'revoked']),
                  collisionBlocked: z.boolean().optional(),
                  conflictingAppId: z
                    .string()
                    .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
                    .optional(),
                  createdAt: z.string().datetime({ offset: true }),
                  revokedAt: z.string().datetime({ offset: true }).optional(),
                })
                .passthrough()
            ),
            nextCursor: z.string().optional(),
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
  {
    method: 'post',
    path: '/v1/meshports',
    alias: 'allocateMeshPort',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: allocateMeshPort_Body,
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
            id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
            port: z.number().int().gte(1).lte(65535),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            sdkVersion: z.string().optional(),
            status: z.enum(['allocated', 'revoked']),
            collisionBlocked: z.boolean().optional(),
            conflictingAppId: z
              .string()
              .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            createdAt: z.string().datetime({ offset: true }),
            revokedAt: z.string().datetime({ offset: true }).optional(),
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
      {
        status: 409,
        description: `Idempotency key reuse with different body, or state conflict`,
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
  {
    method: 'get',
    path: '/v1/meshports/:meshPortId',
    alias: 'getMeshPort',
    requestFormat: 'json',
    parameters: [
      {
        name: 'meshPortId',
        type: 'Path',
        schema: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
            port: z.number().int().gte(1).lte(65535),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            sdkVersion: z.string().optional(),
            status: z.enum(['allocated', 'revoked']),
            collisionBlocked: z.boolean().optional(),
            conflictingAppId: z
              .string()
              .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            createdAt: z.string().datetime({ offset: true }),
            revokedAt: z.string().datetime({ offset: true }).optional(),
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
      {
        status: 404,
        description: `Resource not found`,
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
  {
    method: 'delete',
    path: '/v1/meshports/:meshPortId',
    alias: 'revokeMeshPort',
    requestFormat: 'json',
    parameters: [
      {
        name: 'meshPortId',
        type: 'Path',
        schema: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            id: z.string().regex(/^mpt_[0-9A-HJKMNP-TV-Z]{26}$/),
            port: z.number().int().gte(1).lte(65535),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            sdkVersion: z.string().optional(),
            status: z.enum(['allocated', 'revoked']),
            collisionBlocked: z.boolean().optional(),
            conflictingAppId: z
              .string()
              .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            createdAt: z.string().datetime({ offset: true }),
            revokedAt: z.string().datetime({ offset: true }).optional(),
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
      {
        status: 404,
        description: `Resource not found`,
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
