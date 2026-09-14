---
name: ddd-identity
description: >-
  Shared identity/auth blueprint for DDD single-tenant (or tenant-keyed) apps:
  API keys, operator login/JWT, users enable/disable. Use when editing identity
  OpenAPI, auth middleware, or scaffolding login for a new codegen repo.
---

# Identity blueprint

Shipped as the **sample domain** every DDD codegen repo should start with.

## What it covers

| Concern | Surface |
|---------|---------|
| Tenant API keys | `GET/POST/DELETE /v0/tenants/me/api-keys` |
| Operator users | CRUD + enable/disable under `/v0/tenants/me/users` |
| Session auth | `POST /v0/auth/login`, `/refresh`, `/logout`, `GET/PATCH /v0/auth/me` |
| Middleware | `X-API-Key` **or** Bearer JWT → tenant context + scopes |
| Idempotency | `Idempotency-Key` on mutating POSTs |

## Files (starter)

| Layer | Path |
|-------|------|
| OpenAPI | `packages/openapi-core/src/identity.yaml` + `identity.schemas.yaml` |
| Core | `packages/core/src/identity/` |
| Services | `platform/services/src/identity/` |
| Adapters | `platform/adapters/src/identity/` (sandbox Maps) |
| API | `platform/api-server/src/domains/identity/` |
| Shared auth | `platform/api-server/src/lib/middleware/auth-prehandler.ts` (+ security chain) |
| JWT | `platform/services/src/_shared/services/token.service.ts` |

## Runtime seeds

- Demo API key: `denselink_demo_local_dev_key` (override with `SEED_API_KEY`)
- Demo tenant: `tnt_demo` (`SEED_TENANT_ID`)
- Demo operators: seeded in `sandbox-store` (`admin@demo.local` / `analyst@demo.local`)

## Rules for agents

1. Treat identity as **shared infrastructure**, not product IP — keep contracts stable when cloning.
2. Product scopes belong in API key `scopes[]`; do not hardcode product paths into auth middleware.
3. Login/me/logout/refresh routes must remain registered (see `domain-routes` exclude list for stub route names only).
4. After identity YAML edits: **core-only** regen + handwrite platform (Mode B), unless first-time scaffold.

## Extending for a product

- Add scopes (`orders:write`, …) in seed + OpenAPI descriptions.
- Keep PK patterns single-tenant unless the product is multi-org (`ORG#…`).
- Do not rename `/v0/auth/*` paths without a migration plan — webapps and middleware assume them.
