# @denselink/openapi-core

OpenAPI contracts for the **DDD codegen starter**: shared `common/` components plus the **identity** sample domain.

**Rule:** Every domain YAML maps to DDD layers (`core` → `services` → `adapters` → `api-server`). After routine YAML edits, regenerate **core only** and handwrite lower layers (see `ddd-codegen` skill). Bootstrap of a missing domain may use full multi-layer generate when explicitly requested.

## Domains

| API | Entry | Role |
| ----- | ----- | ----- |
| `identity` | `src/identity.yaml` | Tenant API keys + operator auth (shared blueprint) |

Shared fragments live under `src/common/` (envelopes, Problem, security, parameters, primitives).

## Commands

```bash
pnpm install
pnpm lint:domains
pnpm bundle:domains
```

Bundles land in `src/.bundled/` (YAML + JSON for codegen).
