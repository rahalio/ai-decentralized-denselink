import { makeApi, Zodios, type ZodiosOptions } from '@zodios/core';
import { z } from 'zod';

const createTenantApiKey_Body = z
  .object({
    name: z.string().min(1).max(100),
    scopes: z.array(z.string()).optional(),
    expiresAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const createTenantUser_Body = z
  .object({
    email: z.string().email(),
    displayName: z.string().min(1).max(120),
    role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
    password: z.string().min(8),
  })
  .passthrough();
const updateTenantUser_Body = z
  .object({
    displayName: z.string().min(1).max(120),
    role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
    password: z.string().min(8),
  })
  .partial()
  .passthrough();
const operatorLogin_Body = z
  .object({ email: z.string().email(), password: z.string().min(8) })
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
const ApiKeyId = z.string();
const ApiKey = z
  .object({
    keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
    name: z.string().min(1).max(100),
    prefix: z.string().optional(),
    status: z.enum(['active', 'revoked']),
    scopes: z.array(z.string()).optional(),
    createdAt: z.string().datetime({ offset: true }),
    lastUsedAt: z.string().datetime({ offset: true }).optional(),
    expiresAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const ApiKeyListData = z
  .object({
    items: z.array(
      z
        .object({
          keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
          name: z.string().min(1).max(100),
          prefix: z.string().optional(),
          status: z.enum(['active', 'revoked']),
          scopes: z.array(z.string()).optional(),
          createdAt: z.string().datetime({ offset: true }),
          lastUsedAt: z.string().datetime({ offset: true }).optional(),
          expiresAt: z.string().datetime({ offset: true }).optional(),
        })
        .passthrough()
    ),
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
const ApiKeyListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
              name: z.string().min(1).max(100),
              prefix: z.string().optional(),
              status: z.enum(['active', 'revoked']),
              scopes: z.array(z.string()).optional(),
              createdAt: z.string().datetime({ offset: true }),
              lastUsedAt: z.string().datetime({ offset: true }).optional(),
              expiresAt: z.string().datetime({ offset: true }).optional(),
            })
            .passthrough()
        ),
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
const ApiKeyCreateRequest = z
  .object({
    name: z.string().min(1).max(100),
    scopes: z.array(z.string()).optional(),
    expiresAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const ApiKeyCreated = z
  .object({
    keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
    name: z.string().min(1).max(100),
    prefix: z.string().optional(),
    status: z.enum(['active', 'revoked']),
    scopes: z.array(z.string()).optional(),
    createdAt: z.string().datetime({ offset: true }),
    lastUsedAt: z.string().datetime({ offset: true }).optional(),
    expiresAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough()
  .and(z.object({ secret: z.string() }).passthrough());
const ApiKeyCreatedResponse = z
  .object({
    data: z
      .object({
        keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
        name: z.string().min(1).max(100),
        prefix: z.string().optional(),
        status: z.enum(['active', 'revoked']),
        scopes: z.array(z.string()).optional(),
        createdAt: z.string().datetime({ offset: true }),
        lastUsedAt: z.string().datetime({ offset: true }).optional(),
        expiresAt: z.string().datetime({ offset: true }).optional(),
      })
      .passthrough()
      .and(z.object({ secret: z.string() }).passthrough()),
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
const ApiKeyResponse = z
  .object({
    data: z
      .object({
        keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
        name: z.string().min(1).max(100),
        prefix: z.string().optional(),
        status: z.enum(['active', 'revoked']),
        scopes: z.array(z.string()).optional(),
        createdAt: z.string().datetime({ offset: true }),
        lastUsedAt: z.string().datetime({ offset: true }).optional(),
        expiresAt: z.string().datetime({ offset: true }).optional(),
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
const UserId = z.string();
const OperatorRole = z.enum(['admin', 'analyst', 'viewer', 'ops']);
const OperatorStatus = z.enum(['active', 'disabled']);
const TenantUser = z
  .object({
    userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
    email: z.string().email(),
    displayName: z.string().min(1).max(120),
    role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
    status: z.enum(['active', 'disabled']),
    createdAt: z.string().datetime({ offset: true }),
    updatedAt: z.string().datetime({ offset: true }),
    lastLoginAt: z.string().datetime({ offset: true }).optional(),
    disabledAt: z.string().datetime({ offset: true }).optional(),
  })
  .passthrough();
const TenantUserListData = z
  .object({
    items: z.array(
      z
        .object({
          userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
          email: z.string().email(),
          displayName: z.string().min(1).max(120),
          role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
          status: z.enum(['active', 'disabled']),
          createdAt: z.string().datetime({ offset: true }),
          updatedAt: z.string().datetime({ offset: true }),
          lastLoginAt: z.string().datetime({ offset: true }).optional(),
          disabledAt: z.string().datetime({ offset: true }).optional(),
        })
        .passthrough()
    ),
  })
  .passthrough();
const TenantUserListResponse = z
  .object({
    data: z
      .object({
        items: z.array(
          z
            .object({
              userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
              email: z.string().email(),
              displayName: z.string().min(1).max(120),
              role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
              status: z.enum(['active', 'disabled']),
              createdAt: z.string().datetime({ offset: true }),
              updatedAt: z.string().datetime({ offset: true }),
              lastLoginAt: z.string().datetime({ offset: true }).optional(),
              disabledAt: z.string().datetime({ offset: true }).optional(),
            })
            .passthrough()
        ),
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
const CreateTenantUserRequest = z
  .object({
    email: z.string().email(),
    displayName: z.string().min(1).max(120),
    role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
    password: z.string().min(8),
  })
  .passthrough();
const TenantUserResponse = z
  .object({
    data: z
      .object({
        userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
        email: z.string().email(),
        displayName: z.string().min(1).max(120),
        role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
        status: z.enum(['active', 'disabled']),
        createdAt: z.string().datetime({ offset: true }),
        updatedAt: z.string().datetime({ offset: true }),
        lastLoginAt: z.string().datetime({ offset: true }).optional(),
        disabledAt: z.string().datetime({ offset: true }).optional(),
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
const UpdateTenantUserRequest = z
  .object({
    displayName: z.string().min(1).max(120),
    role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
    password: z.string().min(8),
  })
  .partial()
  .passthrough();
const OperatorLoginRequest = z
  .object({ email: z.string().email(), password: z.string().min(8) })
  .passthrough();
const SessionOperator = z
  .object({
    userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
    email: z.string().email(),
    displayName: z.string().min(1).max(120),
    role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
  })
  .passthrough();
const AuthTokens = z
  .object({
    accessToken: z.string(),
    refreshToken: z.string(),
    tokenType: z.literal('Bearer').default('Bearer'),
    expiresIn: z.number().int(),
    operator: z
      .object({
        userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
        email: z.string().email(),
        displayName: z.string().min(1).max(120),
        role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
      })
      .passthrough(),
  })
  .passthrough();
const AuthTokensResponse = z
  .object({
    data: z
      .object({
        accessToken: z.string(),
        refreshToken: z.string(),
        tokenType: z.literal('Bearer').default('Bearer'),
        expiresIn: z.number().int(),
        operator: z
          .object({
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
          })
          .passthrough(),
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
const TenantId = z.string();
const SessionTenantSummary = z
  .object({
    tenantId: z.string().regex(/^tnt_[0-9A-HJKMNP-TV-Z]{26}$/),
    displayNameEn: z.string(),
    displayNameAr: z.string(),
  })
  .partial()
  .passthrough();
const OperatorSession = z
  .object({
    operator: z
      .object({
        userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
        email: z.string().email(),
        displayName: z.string().min(1).max(120),
        role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
      })
      .passthrough(),
    tenant: z
      .object({
        tenantId: z.string().regex(/^tnt_[0-9A-HJKMNP-TV-Z]{26}$/),
        displayNameEn: z.string(),
        displayNameAr: z.string(),
      })
      .partial()
      .passthrough()
      .optional(),
  })
  .passthrough();
const OperatorSessionResponse = z
  .object({
    data: z
      .object({
        operator: z
          .object({
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
          })
          .passthrough(),
        tenant: z
          .object({
            tenantId: z.string().regex(/^tnt_[0-9A-HJKMNP-TV-Z]{26}$/),
            displayNameEn: z.string(),
            displayNameAr: z.string(),
          })
          .partial()
          .passthrough()
          .optional(),
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
const UpdateOperatorMeRequest = z
  .object({ displayName: z.string().min(1).max(120) })
  .passthrough();
const RefreshTokenRequest = z
  .object({ refreshToken: z.string() })
  .passthrough();

export const schemas: any = {
  createTenantApiKey_Body,
  createTenantUser_Body,
  updateTenantUser_Body,
  operatorLogin_Body,
  Problem,
  ApiKeyId,
  ApiKey,
  ApiKeyListData,
  ResponseMeta,
  ApiKeyListResponse,
  ApiKeyCreateRequest,
  ApiKeyCreated,
  ApiKeyCreatedResponse,
  ApiKeyResponse,
  UserId,
  OperatorRole,
  OperatorStatus,
  TenantUser,
  TenantUserListData,
  TenantUserListResponse,
  CreateTenantUserRequest,
  TenantUserResponse,
  UpdateTenantUserRequest,
  OperatorLoginRequest,
  SessionOperator,
  AuthTokens,
  AuthTokensResponse,
  TenantId,
  SessionTenantSummary,
  OperatorSession,
  OperatorSessionResponse,
  UpdateOperatorMeRequest,
  RefreshTokenRequest,
};

const endpoints = makeApi([
  {
    method: 'post',
    path: '/v0/auth/login',
    alias: 'operatorLogin',
    description: `Future FI operator UI. Not Nafath. Marked stub. Returns tokens + operator summary.`,
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: operatorLogin_Body,
      },
    ],
    response: z
      .object({
        data: z
          .object({
            accessToken: z.string(),
            refreshToken: z.string(),
            tokenType: z.literal('Bearer').default('Bearer'),
            expiresIn: z.number().int(),
            operator: z
              .object({
                userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
                email: z.string().email(),
                displayName: z.string().min(1).max(120),
                role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
              })
              .passthrough(),
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
    path: '/v0/auth/logout',
    alias: 'operatorLogout',
    requestFormat: 'json',
    response: z.void(),
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
    path: '/v0/auth/me',
    alias: 'getOperatorMe',
    description: `Signed-in operator for My profile / account dropdown.
API-key sessions return a synthetic demo operator.
`,
    requestFormat: 'json',
    response: z
      .object({
        data: z
          .object({
            operator: z
              .object({
                userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
                email: z.string().email(),
                displayName: z.string().min(1).max(120),
                role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
              })
              .passthrough(),
            tenant: z
              .object({
                tenantId: z.string().regex(/^tnt_[0-9A-HJKMNP-TV-Z]{26}$/),
                displayNameEn: z.string(),
                displayNameAr: z.string(),
              })
              .partial()
              .passthrough()
              .optional(),
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
    method: 'patch',
    path: '/v0/auth/me',
    alias: 'updateOperatorMe',
    description: `Self-service. Email and role cannot be changed here.`,
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: z
          .object({ displayName: z.string().min(1).max(120) })
          .passthrough(),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            operator: z
              .object({
                userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
                email: z.string().email(),
                displayName: z.string().min(1).max(120),
                role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
              })
              .passthrough(),
            tenant: z
              .object({
                tenantId: z.string().regex(/^tnt_[0-9A-HJKMNP-TV-Z]{26}$/),
                displayNameEn: z.string(),
                displayNameAr: z.string(),
              })
              .partial()
              .passthrough()
              .optional(),
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
    method: 'post',
    path: '/v0/auth/refresh',
    alias: 'operatorRefresh',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: z.object({ refreshToken: z.string() }).passthrough(),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            accessToken: z.string(),
            refreshToken: z.string(),
            tokenType: z.literal('Bearer').default('Bearer'),
            expiresIn: z.number().int(),
            operator: z
              .object({
                userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
                email: z.string().email(),
                displayName: z.string().min(1).max(120),
                role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
              })
              .passthrough(),
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
    path: '/v0/tenants/me/api-keys',
    alias: 'listTenantApiKeys',
    requestFormat: 'json',
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
                  name: z.string().min(1).max(100),
                  prefix: z.string().optional(),
                  status: z.enum(['active', 'revoked']),
                  scopes: z.array(z.string()).optional(),
                  createdAt: z.string().datetime({ offset: true }),
                  lastUsedAt: z.string().datetime({ offset: true }).optional(),
                  expiresAt: z.string().datetime({ offset: true }).optional(),
                })
                .passthrough()
            ),
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
    path: '/v0/tenants/me/api-keys',
    alias: 'createTenantApiKey',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: createTenantApiKey_Body,
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
            keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
            name: z.string().min(1).max(100),
            prefix: z.string().optional(),
            status: z.enum(['active', 'revoked']),
            scopes: z.array(z.string()).optional(),
            createdAt: z.string().datetime({ offset: true }),
            lastUsedAt: z.string().datetime({ offset: true }).optional(),
            expiresAt: z.string().datetime({ offset: true }).optional(),
          })
          .passthrough()
          .and(z.object({ secret: z.string() }).passthrough()),
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
    path: '/v0/tenants/me/api-keys/:keyId',
    alias: 'getTenantApiKey',
    requestFormat: 'json',
    parameters: [
      {
        name: 'keyId',
        type: 'Path',
        schema: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            keyId: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
            name: z.string().min(1).max(100),
            prefix: z.string().optional(),
            status: z.enum(['active', 'revoked']),
            scopes: z.array(z.string()).optional(),
            createdAt: z.string().datetime({ offset: true }),
            lastUsedAt: z.string().datetime({ offset: true }).optional(),
            expiresAt: z.string().datetime({ offset: true }).optional(),
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
    path: '/v0/tenants/me/api-keys/:keyId',
    alias: 'revokeTenantApiKey',
    requestFormat: 'json',
    parameters: [
      {
        name: 'keyId',
        type: 'Path',
        schema: z.string().regex(/^key_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
      {
        name: 'Idempotency-Key',
        type: 'Header',
        schema: z.string().min(1).max(128),
      },
    ],
    response: z.void(),
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
    path: '/v0/tenants/me/users',
    alias: 'listTenantUsers',
    requestFormat: 'json',
    response: z
      .object({
        data: z
          .object({
            items: z.array(
              z
                .object({
                  userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
                  email: z.string().email(),
                  displayName: z.string().min(1).max(120),
                  role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
                  status: z.enum(['active', 'disabled']),
                  createdAt: z.string().datetime({ offset: true }),
                  updatedAt: z.string().datetime({ offset: true }),
                  lastLoginAt: z.string().datetime({ offset: true }).optional(),
                  disabledAt: z.string().datetime({ offset: true }).optional(),
                })
                .passthrough()
            ),
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
    path: '/v0/tenants/me/users',
    alias: 'createTenantUser',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: createTenantUser_Body,
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
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
            status: z.enum(['active', 'disabled']),
            createdAt: z.string().datetime({ offset: true }),
            updatedAt: z.string().datetime({ offset: true }),
            lastLoginAt: z.string().datetime({ offset: true }).optional(),
            disabledAt: z.string().datetime({ offset: true }).optional(),
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
    path: '/v0/tenants/me/users/:userId',
    alias: 'getTenantUser',
    requestFormat: 'json',
    parameters: [
      {
        name: 'userId',
        type: 'Path',
        schema: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
      },
    ],
    response: z
      .object({
        data: z
          .object({
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
            status: z.enum(['active', 'disabled']),
            createdAt: z.string().datetime({ offset: true }),
            updatedAt: z.string().datetime({ offset: true }),
            lastLoginAt: z.string().datetime({ offset: true }).optional(),
            disabledAt: z.string().datetime({ offset: true }).optional(),
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
    method: 'patch',
    path: '/v0/tenants/me/users/:userId',
    alias: 'updateTenantUser',
    requestFormat: 'json',
    parameters: [
      {
        name: 'body',
        type: 'Body',
        schema: updateTenantUser_Body,
      },
      {
        name: 'userId',
        type: 'Path',
        schema: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
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
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
            status: z.enum(['active', 'disabled']),
            createdAt: z.string().datetime({ offset: true }),
            updatedAt: z.string().datetime({ offset: true }),
            lastLoginAt: z.string().datetime({ offset: true }).optional(),
            disabledAt: z.string().datetime({ offset: true }).optional(),
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
    path: '/v0/tenants/me/users/:userId/disable',
    alias: 'disableTenantUser',
    requestFormat: 'json',
    parameters: [
      {
        name: 'userId',
        type: 'Path',
        schema: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
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
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
            status: z.enum(['active', 'disabled']),
            createdAt: z.string().datetime({ offset: true }),
            updatedAt: z.string().datetime({ offset: true }),
            lastLoginAt: z.string().datetime({ offset: true }).optional(),
            disabledAt: z.string().datetime({ offset: true }).optional(),
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
    path: '/v0/tenants/me/users/:userId/enable',
    alias: 'enableTenantUser',
    requestFormat: 'json',
    parameters: [
      {
        name: 'userId',
        type: 'Path',
        schema: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
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
            userId: z.string().regex(/^usr_[0-9A-HJKMNP-TV-Z]{26}$/),
            email: z.string().email(),
            displayName: z.string().min(1).max(120),
            role: z.enum(['admin', 'analyst', 'viewer', 'ops']),
            status: z.enum(['active', 'disabled']),
            createdAt: z.string().datetime({ offset: true }),
            updatedAt: z.string().datetime({ offset: true }),
            lastLoginAt: z.string().datetime({ offset: true }).optional(),
            disabledAt: z.string().datetime({ offset: true }).optional(),
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
