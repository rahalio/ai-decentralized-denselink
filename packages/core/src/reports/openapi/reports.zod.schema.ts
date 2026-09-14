import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

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
const DensityReport = z
  .object({
    city: z.string(),
    penetrationPercent: z.number(),
    activeNodes: z.number().int(),
    piggybackApps: z.array(z.string()).optional(),
    heatmapBins: z.number().int().optional(),
    gapBelowThreshold: z.boolean().optional(),
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
const DensityReportResponse = z
  .object({
    data: z
      .object({
        city: z.string(),
        penetrationPercent: z.number(),
        activeNodes: z.number().int(),
        piggybackApps: z.array(z.string()).optional(),
        heatmapBins: z.number().int().optional(),
        gapBelowThreshold: z.boolean().optional(),
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
const ContributionRankEntry = z
  .object({
    rank: z.number().int(),
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    sdkVersion: z.string().optional(),
    meshPort: z.number().int().optional(),
    densityContributionScore: z.number(),
    activeNodes: z.number().int().optional(),
  })
  .passthrough();
const ContributionRankListData = z
  .object({
    items: z.array(
      z
        .object({
          rank: z.number().int(),
          appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
          sdkVersion: z.string().optional(),
          meshPort: z.number().int().optional(),
          densityContributionScore: z.number(),
          activeNodes: z.number().int().optional(),
        })
        .passthrough()
    ),
    nextCursor: z.string().optional(),
  })
  .passthrough();
const ContributionRankListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              rank: z.number().int(),
              appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
              sdkVersion: z.string().optional(),
              meshPort: z.number().int().optional(),
              densityContributionScore: z.number(),
              activeNodes: z.number().int().optional(),
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
const BetaCohortSummary = z
  .object({
    cohortSize: z.number().int(),
    privateBetaProjects: z.number().int(),
    readyForPublicBeta: z.boolean(),
    averageDensityContribution: z.number().optional(),
    collisionIncidents: z.number().int().optional(),
  })
  .passthrough();
const BetaCohortResponse = z
  .object({
    data: z
      .object({
        cohortSize: z.number().int(),
        privateBetaProjects: z.number().int(),
        readyForPublicBeta: z.boolean(),
        averageDensityContribution: z.number().optional(),
        collisionIncidents: z.number().int().optional(),
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
const VenueProgrammeId = z.string();
const SponsorRoiReport = z
  .object({
    venueProgrammeId: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
    venueName: z.string().optional(),
    activeNodes: z.number().int(),
    sessions: z.number().int(),
    avgSessionMinutes: z.number().optional(),
    affordabilityBenchmarkNote: z.string().optional(),
    heatmapBins: z.number().int().optional(),
  })
  .passthrough();
const SponsorRoiReportResponse = z
  .object({
    data: z
      .object({
        venueProgrammeId: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
        venueName: z.string().optional(),
        activeNodes: z.number().int(),
        sessions: z.number().int(),
        avgSessionMinutes: z.number().optional(),
        affordabilityBenchmarkNote: z.string().optional(),
        heatmapBins: z.number().int().optional(),
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
  AppId,
  Problem,
  DensityReport,
  ResponseMeta,
  DensityReportResponse,
  ContributionRankEntry,
  ContributionRankListData,
  ContributionRankListResponse,
  BetaCohortSummary,
  BetaCohortResponse,
  VenueProgrammeId,
  SponsorRoiReport,
  SponsorRoiReportResponse,
};

const endpoints = makeApi([
  {
    method: 'get',
    path: '/v1/reports/beta-cohort',
    alias: 'getBetaCohort',
    requestFormat: 'json',
    response: z
      .object({
        data: z
          .object({
            cohortSize: z.number().int(),
            privateBetaProjects: z.number().int(),
            readyForPublicBeta: z.boolean(),
            averageDensityContribution: z.number().optional(),
            collisionIncidents: z.number().int().optional(),
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
    method: 'get',
    path: '/v1/reports/contribution-rank',
    alias: 'getContributionRank',
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
        name: 'city',
        type: 'Query',
        schema: z.string().optional(),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  rank: z.number().int(),
                  appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
                  sdkVersion: z.string().optional(),
                  meshPort: z.number().int().optional(),
                  densityContributionScore: z.number(),
                  activeNodes: z.number().int().optional(),
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
    method: 'get',
    path: '/v1/reports/density',
    alias: 'getDensityReport',
    requestFormat: 'json',
    parameters: [
      {
        name: 'city',
        type: 'Query',
        schema: z.string().optional(),
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
            city: z.string(),
            penetrationPercent: z.number(),
            activeNodes: z.number().int(),
            piggybackApps: z.array(z.string()).optional(),
            heatmapBins: z.number().int().optional(),
            gapBelowThreshold: z.boolean().optional(),
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
    method: 'get',
    path: '/v1/reports/sponsor-roi',
    alias: 'getSponsorRoiReport',
    requestFormat: 'json',
    parameters: [
      {
        name: 'venueProgrammeId',
        type: 'Query',
        schema: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            venueProgrammeId: z.string().regex(/^ven_[0-9A-HJKMNP-TV-Z]{26}$/),
            venueName: z.string().optional(),
            activeNodes: z.number().int(),
            sessions: z.number().int(),
            avgSessionMinutes: z.number().optional(),
            affordabilityBenchmarkNote: z.string().optional(),
            heatmapBins: z.number().int().optional(),
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
