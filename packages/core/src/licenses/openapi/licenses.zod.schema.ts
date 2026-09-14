import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const issueLicenseKey_Body = z
  .object({
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
    tier: z
      .enum(['private_beta', 'public_beta', 'production'])
      .optional()
      .default('private_beta'),
    meshPort: z.number().int().optional(),
  })
  .passthrough();
const bindLicenseAttestation_Body = z
  .object({
    buildFingerprint: z.string(),
    encryptionProtocol: z.string().optional().default('signal-protocol'),
    passed: z.boolean().optional().default(true),
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
const LicenseId = z.string();
const DeveloperId = z.string();
const LicenseTier = z.enum(['private_beta', 'public_beta', 'production']);
const LicenseStatus = z.enum(['active', 'revoked']);
const AttestationStatus = z.enum(['pending', 'passed', 'failed']);
const LicenseKey = z
  .object({
    id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
    tier: z.enum(['private_beta', 'public_beta', 'production']),
    status: z.enum(['active', 'revoked']),
    meshPort: z.number().int().optional(),
    encryptionAttestation: z.boolean().optional(),
    attestationStatus: z.enum(['pending', 'passed', 'failed']).optional(),
    buildFingerprint: z.string().optional(),
    createdAt: z.string().datetime({ offset: true }),
    revokedAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const LicenseKeyListData = z
  .object({
    items: z.array(
      z
        .object({
          id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
          appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
          developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
          tier: z.enum(['private_beta', 'public_beta', 'production']),
          status: z.enum(['active', 'revoked']),
          meshPort: z.number().int().optional(),
          encryptionAttestation: z.boolean().optional(),
          attestationStatus: z.enum(['pending', 'passed', 'failed']).optional(),
          buildFingerprint: z.string().optional(),
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
const LicenseKeyListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
              appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
              developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
              tier: z.enum(['private_beta', 'public_beta', 'production']),
              status: z.enum(['active', 'revoked']),
              meshPort: z.number().int().optional(),
              encryptionAttestation: z.boolean().optional(),
              attestationStatus: z
                .enum(['pending', 'passed', 'failed'])
                .optional(),
              buildFingerprint: z.string().optional(),
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
const LicenseKeyCreate = z
  .object({
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
    tier: z
      .enum(['private_beta', 'public_beta', 'production'])
      .optional()
      .default('private_beta'),
    meshPort: z.number().int().optional(),
  })
  .passthrough();
const LicenseKeyCreated = z
  .object({
    id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
    appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
    developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
    tier: z.enum(['private_beta', 'public_beta', 'production']),
    status: z.enum(['active', 'revoked']),
    meshPort: z.number().int().optional(),
    encryptionAttestation: z.boolean().optional(),
    attestationStatus: z.enum(['pending', 'passed', 'failed']).optional(),
    buildFingerprint: z.string().optional(),
    createdAt: z.string().datetime({ offset: true }),
    revokedAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough()
  .and(z.object({ secret: z.string() }).partial().passthrough());
const LicenseKeyCreatedResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
        appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
        developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
        tier: z.enum(['private_beta', 'public_beta', 'production']),
        status: z.enum(['active', 'revoked']),
        meshPort: z.number().int().optional(),
        encryptionAttestation: z.boolean().optional(),
        attestationStatus: z.enum(['pending', 'passed', 'failed']).optional(),
        buildFingerprint: z.string().optional(),
        createdAt: z.string().datetime({ offset: true }),
        revokedAt: z.string().datetime({ offset: true }).optional(),
      })
      .passthrough()
      .and(z.object({ secret: z.string() }).partial().passthrough()),
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
const LicenseKeyResponse = z
  .object({
    data: z
      .object({
        id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
        appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
        developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
        tier: z.enum(['private_beta', 'public_beta', 'production']),
        status: z.enum(['active', 'revoked']),
        meshPort: z.number().int().optional(),
        encryptionAttestation: z.boolean().optional(),
        attestationStatus: z.enum(['pending', 'passed', 'failed']).optional(),
        buildFingerprint: z.string().optional(),
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
const AttestationBind = z
  .object({
    buildFingerprint: z.string(),
    encryptionProtocol: z.string().optional().default('signal-protocol'),
    passed: z.boolean().optional().default(true),
  })
  .passthrough();

export const schemas: any = {
  issueLicenseKey_Body,
  bindLicenseAttestation_Body,
  AppId,
  Problem,
  LicenseId,
  DeveloperId,
  LicenseTier,
  LicenseStatus,
  AttestationStatus,
  LicenseKey,
  LicenseKeyListData,
  ResponseMeta,
  LicenseKeyListResponse,
  LicenseKeyCreate,
  LicenseKeyCreated,
  LicenseKeyCreatedResponse,
  LicenseKeyResponse,
  AttestationBind,
};

const endpoints = makeApi([
  {
    method: 'get',
    path: '/v1/licenses',
    alias: 'listLicenseKeys',
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
      {
        name: 'status',
        type: 'Query',
        schema: z.enum(['active', 'revoked']).optional(),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
                  appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
                  developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
                  tier: z.enum(['private_beta', 'public_beta', 'production']),
                  status: z.enum(['active', 'revoked']),
                  meshPort: z.number().int().optional(),
                  encryptionAttestation: z.boolean().optional(),
                  attestationStatus: z
                    .enum(['pending', 'passed', 'failed'])
                    .optional(),
                  buildFingerprint: z.string().optional(),
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
    path: '/v1/licenses',
    alias: 'issueLicenseKey',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: issueLicenseKey_Body,
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
            id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
            tier: z.enum(['private_beta', 'public_beta', 'production']),
            status: z.enum(['active', 'revoked']),
            meshPort: z.number().int().optional(),
            encryptionAttestation: z.boolean().optional(),
            attestationStatus: z
              .enum(['pending', 'passed', 'failed'])
              .optional(),
            buildFingerprint: z.string().optional(),
            createdAt: z.string().datetime({ offset: true }),
            revokedAt: z.string().datetime({ offset: true }).optional(),
          })
          .passthrough()
          .and(z.object({ secret: z.string() }).partial().passthrough()),
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
    path: '/v1/licenses/:licenseId',
    alias: 'getLicenseKey',
    requestFormat: 'json',
    parameters: [
      {
        name: 'licenseId',
        type: 'Path',
        schema: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
            tier: z.enum(['private_beta', 'public_beta', 'production']),
            status: z.enum(['active', 'revoked']),
            meshPort: z.number().int().optional(),
            encryptionAttestation: z.boolean().optional(),
            attestationStatus: z
              .enum(['pending', 'passed', 'failed'])
              .optional(),
            buildFingerprint: z.string().optional(),
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
    method: 'post',
    path: '/v1/licenses/:licenseId/attestation',
    alias: 'bindLicenseAttestation',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: bindLicenseAttestation_Body,
      },
      {
        name: 'licenseId',
        type: 'Path',
        schema: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
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
            id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
            tier: z.enum(['private_beta', 'public_beta', 'production']),
            status: z.enum(['active', 'revoked']),
            meshPort: z.number().int().optional(),
            encryptionAttestation: z.boolean().optional(),
            attestationStatus: z
              .enum(['pending', 'passed', 'failed'])
              .optional(),
            buildFingerprint: z.string().optional(),
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
    path: '/v1/licenses/:licenseId/revoke',
    alias: 'revokeLicenseKey',
    requestFormat: 'json',
    parameters: [
      {
        name: 'licenseId',
        type: 'Path',
        schema: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
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
            id: z.string().regex(/^lic_[0-9A-HJKMNP-TV-Z]{26}$/),
            appId: z.string().regex(/^app_[0-9A-HJKMNP-TV-Z]{26}$/),
            developerId: z.string().regex(/^dev_[0-9A-HJKMNP-TV-Z]{26}$/),
            tier: z.enum(['private_beta', 'public_beta', 'production']),
            status: z.enum(['active', 'revoked']),
            meshPort: z.number().int().optional(),
            encryptionAttestation: z.boolean().optional(),
            attestationStatus: z
              .enum(['pending', 'passed', 'failed'])
              .optional(),
            buildFingerprint: z.string().optional(),
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
