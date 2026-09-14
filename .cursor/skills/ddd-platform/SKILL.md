---
name: ddd-platform
description: >-
  Generic OpenAPI-first DDD platform conventions for zero-codegen monorepos:
  layered architecture (core, services, adapters, api-server, tests, postman,
  webapp skeleton), response envelopes, OpenAPI extensions, and anti-drift rules.
  Use when working on OpenAPI, DDD layers, codegen, Fastify domains, Vitest,
  Postman collections, or any repo that follows this starter pattern.
---

# OpenAPI-first DDD Platform

Reusable conventions for monorepos that generate TypeScript DDD layers from OpenAPI via **zero-codegen**. Discover product-specific names in the **current** repo; do not assume ZATCA or any one product.

## HARD RULE — After OpenAPI YAML edits

**Regenerate `core` only. Handwrite services, adapters, api-server, tests, postman, and webapp.**

1. Edit YAML → bundle.
2. Regenerate **core** for the domain.
3. Preserve handwritten core patches if any.
4. Hand-update ports/use cases/adapters/routes/handlers to match.

Full-layer regen only when the user explicitly asks, or when scaffolding a **brand-new** domain (Mode A).

## Canonical layout

```
{repo}/
  packages/
    openapi-core/     # OpenAPI YAML (+ .bundled JSON)
    core/             # Domain models, types, Zod, repository interfaces + _shared/
  platform/
    services/         # Use cases, ports, DTOs, policies + _shared/
    adapters/         # DynamoDB / sandbox repos + _shared/ (ddb helpers, messaging)
    api-server/       # Fastify routes, handlers, DI + lib/middleware/
    tests/            # Vitest + optional postman/
  .codegen/           # zero-codegen tool + JSON config
```

Dependency direction (never invert):

```
webapp → api-server → services → adapters → core
              ↑           ↑
         ports in    implementations
         services    in adapters
```

OpenAPI is the **source of truth** for HTTP paths, schemas, and response shapes.

## Shared scaffolds (copy into every tenant app)

| Area | Path | Purpose |
|------|------|---------|
| Core shared | `packages/core/src/_shared/` | ID contracts, repo base types, event envelope |
| OpenAPI common | `packages/openapi-core/src/common/` | Envelopes, Problem, security, parameters, primitives |
| Services shared | `platform/services/src/_shared/` | Execution context, JWT token, API-key lookup ports, RLS |
| Adapters shared | `platform/adapters/src/_shared/` | Dynamo helpers, sandbox store, messaging/outbox |
| API middleware | `platform/api-server/src/lib/middleware/` | Auth, tenant context, idempotency, envelopes |
| Identity sample | `**/identity/**` + `identity.yaml` | Tenant API keys + operator login blueprint |

## Response contracts (envelopes)

| Kind | Schema | Body |
|------|--------|------|
| Success | `DataEnvelope` | `{ data: T, meta: ResponseMeta }` |
| List | `ListResponseEnvelope` / paged | `{ data: { items: T[] }, meta }` |
| Error | Problem / `ErrorEnvelope` | RFC7807-style |
| No content | — | `204` |

Handlers stay pass-through: `reply.code(n).send(result)`.

## OpenAPI conventions

- Files: `{domain}.yaml` + optional `{domain}.schemas.yaml`; shared under `common/`
- `operationId`: camelCase
- Extensions: `x-repository`, `x-dynamodb` (see **ddd-codegen** skill)
- Security: `X-API-Key` and/or Bearer JWT (identity)

## Anti-drift

1. Change OpenAPI first; then bundle → generate core → handwrite below.
2. Do not strip envelopes to “fix” clients.
3. Nested DI: `deps.useCases.{repo}.{verb}.execute`.
4. Document product regen commands in the repo README, not only in skills.

## Build order

```text
openapi bundle → generate core → (handwrite or generate lower layers)
→ build: core → services → adapters → api-server
```
