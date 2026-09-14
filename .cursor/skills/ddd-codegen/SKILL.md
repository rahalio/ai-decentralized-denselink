---
name: ddd-codegen
description: >-
  Orchestrate the DDD codegen pipeline in this starter (and clones): OpenAPI
  through core/services/adapters/api-server. Use when running zero-codegen,
  bundling OpenAPI, regenerating packages/core, or scaffolding a new domain.
---

# DDD Codegen Pipeline (starter)

Tool: `.codegen/codegen/` (`zero_codegen` Python package).  
Config: `.codegen/.zero-codegen-merged.json` (run `pnpm codegen:paths` first).  
Package scope: `@denselink` (override via `package_scope` in config when cloning).

## Two modes

### Mode A — NEW domain (first scaffold)

1. Author `packages/openapi-core/src/{domain}.yaml` (+ schemas).
2. Register domain in `.codegen/.zero-codegen-merged.json`, `.codegen/zero-codegen.json`, and `packages/openapi-core/.redocly.yaml`.
3. `pnpm lint:openapi && pnpm bundle:openapi`
4. Full multi-layer generate for **that domain only** (omit `--layers` or pass all layers).
5. Build packages in order; then hand-fit platform (sandbox, DI, `domain-routes`).

### Mode B — EXISTING domain YAML edit (default)

1. Lint + bundle.
2. `pnpm codegen:core` (or `--domain X --layers core`).
3. **Handwrite** services → adapters → api-server deltas.
4. Never routine `generate` without `--layers core`.

## Commands

```bash
pnpm codegen:paths          # absolute paths into merged config
pnpm lint:openapi
pnpm bundle:openapi
pnpm codegen:core           # all enabled domains, core only
pnpm codegen:identity       # full scaffold for identity (starter sample)

# Manual
PYTHONPATH=.codegen/codegen/src python3 -m zero_codegen.cli.main generate \
  --domain identity --layers core \
  --config .codegen/.zero-codegen-merged.json --skip-build
```

## Layers

| # | Layer | Output |
|---|-------|--------|
| 1 | openapi (bundle) | `packages/openapi-core/src/.bundled/` |
| 2 | core | `packages/core/src/{domain}/` |
| 3 | services | `platform/services/src/{domain}/` |
| 4 | adapters | `platform/adapters/src/{domain}/` |
| 5 | api_server | `platform/api-server/src/domains/{domain}/` |

## Key OpenAPI extensions

```yaml
x-repository: Wallet       # or none
x-dynamodb:
  entityType: "WALLET"
  pkPatternTemplate: "WALLET#${walletId}"
  skPatternTemplate: "METADATA"
  pkPattern: "entity"      # entity | org | template
```

## Cloning for a new product

1. Copy this repo (or its `packages/` + `platform/` + `.codegen/`).
2. Set `package_scope` (e.g. `@acme`) and rename `@denselink/*` packages.
3. Keep `common/` + `identity`; add product domains under OpenAPI.
4. Extend `_shared` ID prefix maps and event catalogs — do not fork middleware.

See also: **ddd-platform**, **ddd-identity**.
