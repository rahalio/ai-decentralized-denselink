import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const createGrantProgramme_Body = z
  .object({
    name: z.string(),
    milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
    milestoneThreshold: z.number().optional(),
    rewardAmount: z.number(),
    densityModelId: z
      .string()
      .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
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
const GrantProgrammeId = z.string();
const MilestoneMetric = z.enum(['active_nodes', 'penetration_percent']);
const GrantProgrammeStatus = z.enum(['draft', 'open', 'closed']);
const DensityModelId = z.string();
const GrantProgramme = z
  .object({
    id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
    name: z.string(),
    milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
    milestoneThreshold: z.number().optional(),
    rewardAmount: z.number(),
    status: z.enum(['draft', 'open', 'closed']),
    densityModelId: z
      .string()
      .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
    createdAt: z.string().datetime({ offset: true }),
  })
  .passthrough();
const GrantProgrammeListData = z
  .object({
    items: z.array(
      z
        .object({
          id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
          name: z.string(),
          milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
          milestoneThreshold: z.number().optional(),
          rewardAmount: z.number(),
          status: z.enum(['draft', 'open', 'closed']),
          densityModelId: z
            .string()
            .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
            .optional(),
          createdAt: z.string().datetime({ offset: true }),
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
const GrantProgrammeListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
              name: z.string(),
              milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
              milestoneThreshold: z.number().optional(),
              rewardAmount: z.number(),
              status: z.enum(['draft', 'open', 'closed']),
              densityModelId: z
                .string()
                .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
                .optional(),
              createdAt: z.string().datetime({ offset: true }),
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
const GrantProgrammeCreate = z
  .object({
    name: z.string(),
    milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
    milestoneThreshold: z.number().optional(),
    rewardAmount: z.number(),
    densityModelId: z
      .string()
      .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
  })
  .passthrough();
const GrantProgrammeResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
        name: z.string(),
        milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
        milestoneThreshold: z.number().optional(),
        rewardAmount: z.number(),
        status: z.enum(['draft', 'open', 'closed']),
        densityModelId: z
          .string()
          .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
          .optional(),
        createdAt: z.string().datetime({ offset: true }),
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
const MilestoneId = z.string();
const AppId = z.string();
const MilestoneStatus = z.enum([
  'pending',
  'achieved',
  'disbursed',
  'rejected',
]);
const Milestone = z
  .object({
    id: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
    grantProgrammeId: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
    appId: z
      .string()
      .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
    status: z.enum(['pending', 'achieved', 'disbursed', 'rejected']),
    measuredValue: z.number(),
    reviewedAt: z.string().datetime({ offset: true }).optional(),
    disbursedAt: z.string().datetime({ offset: true }).optional(),
    createdAt: z.string().datetime({ offset: true }),
  })
  .passthrough();
const MilestoneListData = z
  .object({
    items: z.array(
      z
        .object({
          id: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
          grantProgrammeId: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
          appId: z
            .string()
            .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
            .optional(),
          status: z.enum(['pending', 'achieved', 'disbursed', 'rejected']),
          measuredValue: z.number(),
          reviewedAt: z.string().datetime({ offset: true }).optional(),
          disbursedAt: z.string().datetime({ offset: true }).optional(),
          createdAt: z.string().datetime({ offset: true }),
        })
        .passthrough()
    ),
    nextCursor: z.string().optional(),
  })
  .passthrough();
const MilestoneListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              id: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
              grantProgrammeId: z
                .string()
                .regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
              appId: z
                .string()
                .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
                .optional(),
              status: z.enum(['pending', 'achieved', 'disbursed', 'rejected']),
              measuredValue: z.number(),
              reviewedAt: z.string().datetime({ offset: true }).optional(),
              disbursedAt: z.string().datetime({ offset: true }).optional(),
              createdAt: z.string().datetime({ offset: true }),
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
const MilestoneDisburse = z
  .object({ note: z.string() })
  .partial()
  .passthrough();
const MilestoneResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
        grantProgrammeId: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
        appId: z
          .string()
          .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
          .optional(),
        status: z.enum(['pending', 'achieved', 'disbursed', 'rejected']),
        measuredValue: z.number(),
        reviewedAt: z.string().datetime({ offset: true }).optional(),
        disbursedAt: z.string().datetime({ offset: true }).optional(),
        createdAt: z.string().datetime({ offset: true }),
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
  createGrantProgramme_Body,
  Problem,
  GrantProgrammeId,
  MilestoneMetric,
  GrantProgrammeStatus,
  DensityModelId,
  GrantProgramme,
  GrantProgrammeListData,
  ResponseMeta,
  GrantProgrammeListResponse,
  GrantProgrammeCreate,
  GrantProgrammeResponse,
  MilestoneId,
  AppId,
  MilestoneStatus,
  Milestone,
  MilestoneListData,
  MilestoneListResponse,
  MilestoneDisburse,
  MilestoneResponse,
};

const endpoints = makeApi([
  {
    method: 'get',
    path: '/v1/grants',
    alias: 'listGrantProgrammes',
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
    ],
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
                  name: z.string(),
                  milestoneMetric: z.enum([
                    'active_nodes',
                    'penetration_percent',
                  ]),
                  milestoneThreshold: z.number().optional(),
                  rewardAmount: z.number(),
                  status: z.enum(['draft', 'open', 'closed']),
                  densityModelId: z
                    .string()
                    .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
                    .optional(),
                  createdAt: z.string().datetime({ offset: true }),
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
    path: '/v1/grants',
    alias: 'createGrantProgramme',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: createGrantProgramme_Body,
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
            id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
            name: z.string(),
            milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
            milestoneThreshold: z.number().optional(),
            rewardAmount: z.number(),
            status: z.enum(['draft', 'open', 'closed']),
            densityModelId: z
              .string()
              .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            createdAt: z.string().datetime({ offset: true }),
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
  {
    method: 'get',
    path: '/v1/grants/:grantProgrammeId',
    alias: 'getGrantProgramme',
    requestFormat: 'json',
    parameters: [
      {
        name: 'grantProgrammeId',
        type: 'Path',
        schema: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            id: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
            name: z.string(),
            milestoneMetric: z.enum(['active_nodes', 'penetration_percent']),
            milestoneThreshold: z.number().optional(),
            rewardAmount: z.number(),
            status: z.enum(['draft', 'open', 'closed']),
            densityModelId: z
              .string()
              .regex(/^den_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            createdAt: z.string().datetime({ offset: true }),
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
    method: 'get',
    path: '/v1/grants/:grantProgrammeId/milestones',
    alias: 'listGrantMilestones',
    requestFormat: 'json',
    parameters: [
      {
        name: 'grantProgrammeId',
        type: 'Path',
        schema: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
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
    ],
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  id: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
                  grantProgrammeId: z
                    .string()
                    .regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
                  appId: z
                    .string()
                    .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
                    .optional(),
                  status: z.enum([
                    'pending',
                    'achieved',
                    'disbursed',
                    'rejected',
                  ]),
                  measuredValue: z.number(),
                  reviewedAt: z.string().datetime({ offset: true }).optional(),
                  disbursedAt: z.string().datetime({ offset: true }).optional(),
                  createdAt: z.string().datetime({ offset: true }),
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
    method: 'post',
    path: '/v1/milestones/:milestoneId/disburse',
    alias: 'disburseMilestone',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: z
          .object({ note: z.string() })
          .partial()
          .passthrough()
          .optional(),
      },
      {
        name: 'milestoneId',
        type: 'Path',
        schema: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
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
            id: z.string().regex(/^msn_[0-9A-HJKMNP-TV-Z]{26}$/),
            grantProgrammeId: z.string().regex(/^grt_[0-9A-HJKMNP-TV-Z]{26}$/),
            appId: z
              .string()
              .regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            status: z.enum(['pending', 'achieved', 'disbursed', 'rejected']),
            measuredValue: z.number(),
            reviewedAt: z.string().datetime({ offset: true }).optional(),
            disbursedAt: z.string().datetime({ offset: true }).optional(),
            createdAt: z.string().datetime({ offset: true }),
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
