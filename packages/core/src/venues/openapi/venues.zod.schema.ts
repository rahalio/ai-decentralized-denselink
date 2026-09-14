import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const createVenueProgramme_Body = z
  .object({
    venueType: z.enum(['stadium', 'school', 'mall']),
    name: z.string(),
    city: z.string().optional(),
    activeNodeTarget: z.number().int().optional(),
    eventWindowStart: z.string().datetime({ offset: true }).optional(),
    eventWindowEnd: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const createAlwaysOnCampaign_Body = z
  .object({
    name: z.string(),
    venueProgrammeId: z
      .string()
      .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
    enabled: z.boolean().optional().default(true),
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
const VenueProgrammeId = z.string();
const VenueType = z.enum(['stadium', 'school', 'mall']);
const VenueProgrammeStatus = z.enum(['draft', 'enrolled', 'live', 'completed']);
const VenueProgramme = z
  .object({
    id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
    venueType: z.enum(['stadium', 'school', 'mall']),
    name: z.string(),
    city: z.string().optional(),
    activeNodeTarget: z.number().int().optional(),
    status: z.enum(['draft', 'enrolled', 'live', 'completed']),
    eventWindowStart: z.string().datetime({ offset: true }).optional(),
    eventWindowEnd: z.string().datetime({ offset: true }).optional(),
    activeNodes: z.number().int().optional(),
    sessionDurationMinutesAvg: z.number().optional(),
    heatmapBins: z.number().int().optional(),
    createdAt: z.string().datetime({ offset: true }),
  })
  .passthrough();
const VenueProgrammeListData = z
  .object({
    items: z.array(
      z
        .object({
          id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
          venueType: z.enum(['stadium', 'school', 'mall']),
          name: z.string(),
          city: z.string().optional(),
          activeNodeTarget: z.number().int().optional(),
          status: z.enum(['draft', 'enrolled', 'live', 'completed']),
          eventWindowStart: z.string().datetime({ offset: true }).optional(),
          eventWindowEnd: z.string().datetime({ offset: true }).optional(),
          activeNodes: z.number().int().optional(),
          sessionDurationMinutesAvg: z.number().optional(),
          heatmapBins: z.number().int().optional(),
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
const VenueProgrammeListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
              venueType: z.enum(['stadium', 'school', 'mall']),
              name: z.string(),
              city: z.string().optional(),
              activeNodeTarget: z.number().int().optional(),
              status: z.enum(['draft', 'enrolled', 'live', 'completed']),
              eventWindowStart: z
                .string()
                .datetime({ offset: true })
                .optional(),
              eventWindowEnd: z.string().datetime({ offset: true }).optional(),
              activeNodes: z.number().int().optional(),
              sessionDurationMinutesAvg: z.number().optional(),
              heatmapBins: z.number().int().optional(),
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
const VenueProgrammeCreate = z
  .object({
    venueType: z.enum(['stadium', 'school', 'mall']),
    name: z.string(),
    city: z.string().optional(),
    activeNodeTarget: z.number().int().optional(),
    eventWindowStart: z.string().datetime({ offset: true }).optional(),
    eventWindowEnd: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const VenueProgrammeResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
        venueType: z.enum(['stadium', 'school', 'mall']),
        name: z.string(),
        city: z.string().optional(),
        activeNodeTarget: z.number().int().optional(),
        status: z.enum(['draft', 'enrolled', 'live', 'completed']),
        eventWindowStart: z.string().datetime({ offset: true }).optional(),
        eventWindowEnd: z.string().datetime({ offset: true }).optional(),
        activeNodes: z.number().int().optional(),
        sessionDurationMinutesAvg: z.number().optional(),
        heatmapBins: z.number().int().optional(),
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
const AlwaysOnCampaignId = z.string();
const AlwaysOnCampaign = z
  .object({
    id: z.string().regex(/^aon_[0-9A-HJKMNP-TV-Z]{26}$/),
    name: z.string(),
    venueProgrammeId: z
      .string()
      .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
    enabled: z.boolean(),
    inflateConsumerMetrics: z.boolean().optional().default(false),
    createdAt: z.string().datetime({ offset: true }),
  })
  .passthrough();
const AlwaysOnCampaignListData = z
  .object({
    items: z.array(
      z
        .object({
          id: z.string().regex(/^aon_[0-9A-HJKMNP-TV-Z]{26}$/),
          name: z.string(),
          venueProgrammeId: z
            .string()
            .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
            .optional(),
          enabled: z.boolean(),
          inflateConsumerMetrics: z.boolean().optional().default(false),
          createdAt: z.string().datetime({ offset: true }),
        })
        .passthrough()
    ),
    nextCursor: z.string().optional(),
  })
  .passthrough();
const AlwaysOnCampaignListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              id: z.string().regex(/^aon_[0-9A-HJKMNP-TV-Z]{26}$/),
              name: z.string(),
              venueProgrammeId: z
                .string()
                .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
                .optional(),
              enabled: z.boolean(),
              inflateConsumerMetrics: z.boolean().optional().default(false),
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
const AlwaysOnCampaignCreate = z
  .object({
    name: z.string(),
    venueProgrammeId: z
      .string()
      .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
      .optional(),
    enabled: z.boolean().optional().default(true),
  })
  .passthrough();
const AlwaysOnCampaignResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^aon_[0-9A-HJKMNP-TV-Z]{26}$/),
        name: z.string(),
        venueProgrammeId: z
          .string()
          .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
          .optional(),
        enabled: z.boolean(),
        inflateConsumerMetrics: z.boolean().optional().default(false),
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
  createVenueProgramme_Body,
  createAlwaysOnCampaign_Body,
  Problem,
  VenueProgrammeId,
  VenueType,
  VenueProgrammeStatus,
  VenueProgramme,
  VenueProgrammeListData,
  ResponseMeta,
  VenueProgrammeListResponse,
  VenueProgrammeCreate,
  VenueProgrammeResponse,
  AlwaysOnCampaignId,
  AlwaysOnCampaign,
  AlwaysOnCampaignListData,
  AlwaysOnCampaignListResponse,
  AlwaysOnCampaignCreate,
  AlwaysOnCampaignResponse,
};

const endpoints = makeApi([
  {
    method: 'get',
    path: '/v1/always-on-campaigns',
    alias: 'listAlwaysOnCampaigns',
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
                  id: z.string().regex(/^aon_[0-9A-HJKMNP-TV-Z]{26}$/),
                  name: z.string(),
                  venueProgrammeId: z
                    .string()
                    .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
                    .optional(),
                  enabled: z.boolean(),
                  inflateConsumerMetrics: z.boolean().optional().default(false),
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
    path: '/v1/always-on-campaigns',
    alias: 'createAlwaysOnCampaign',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: createAlwaysOnCampaign_Body,
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
            id: z.string().regex(/^aon_[0-9A-HJKMNP-TV-Z]{26}$/),
            name: z.string(),
            venueProgrammeId: z
              .string()
              .regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/)
              .optional(),
            enabled: z.boolean(),
            inflateConsumerMetrics: z.boolean().optional().default(false),
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
    path: '/v1/venues',
    alias: 'listVenueProgrammes',
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
        name: 'venueType',
        type: 'Query',
        schema: z.enum(['stadium', 'school', 'mall']).optional(),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
                  venueType: z.enum(['stadium', 'school', 'mall']),
                  name: z.string(),
                  city: z.string().optional(),
                  activeNodeTarget: z.number().int().optional(),
                  status: z.enum(['draft', 'enrolled', 'live', 'completed']),
                  eventWindowStart: z
                    .string()
                    .datetime({ offset: true })
                    .optional(),
                  eventWindowEnd: z
                    .string()
                    .datetime({ offset: true })
                    .optional(),
                  activeNodes: z.number().int().optional(),
                  sessionDurationMinutesAvg: z.number().optional(),
                  heatmapBins: z.number().int().optional(),
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
    path: '/v1/venues',
    alias: 'createVenueProgramme',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: createVenueProgramme_Body,
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
            id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
            venueType: z.enum(['stadium', 'school', 'mall']),
            name: z.string(),
            city: z.string().optional(),
            activeNodeTarget: z.number().int().optional(),
            status: z.enum(['draft', 'enrolled', 'live', 'completed']),
            eventWindowStart: z.string().datetime({ offset: true }).optional(),
            eventWindowEnd: z.string().datetime({ offset: true }).optional(),
            activeNodes: z.number().int().optional(),
            sessionDurationMinutesAvg: z.number().optional(),
            heatmapBins: z.number().int().optional(),
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
    path: '/v1/venues/:venueProgrammeId',
    alias: 'getVenueProgramme',
    requestFormat: 'json',
    parameters: [
      {
        name: 'venueProgrammeId',
        type: 'Path',
        schema: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            id: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
            venueType: z.enum(['stadium', 'school', 'mall']),
            name: z.string(),
            city: z.string().optional(),
            activeNodeTarget: z.number().int().optional(),
            status: z.enum(['draft', 'enrolled', 'live', 'completed']),
            eventWindowStart: z.string().datetime({ offset: true }).optional(),
            eventWindowEnd: z.string().datetime({ offset: true }).optional(),
            activeNodes: z.number().int().optional(),
            sessionDurationMinutesAvg: z.number().optional(),
            heatmapBins: z.number().int().optional(),
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
]);

export const api: any = new Zodios(
  'https://api.ddd-codegen-starter.local/v1',
  endpoints
);

export function createApiClient(baseUrl: string, options?: ZodiosOptions): any {
  return new Zodios(baseUrl, endpoints, options);
}
