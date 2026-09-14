# Denselink

Mesh developer density console for MeshPort allocation, license keys, venue coverage analytics, developer incentive grants, and density modelling.

OpenAPI-first DDD monorepo based on the zero-apps codegen scaffold. Package scope: **`@denselink/*`**.

## Product specs

- [PRODUCT.md](./PRODUCT.md)
- [USER_STORIES.md](./USER_STORIES.md)
- [WEBAPP.md](./WEBAPP.md)

## Layout

```
packages/openapi-core  →  packages/core  →  platform/services  →  platform/adapters  →  platform/api-server
         ↑ OpenAPI source of truth                              ports↑        impl↑              HTTP↑
platform/webapp  → API clients + UI
```

## Quick start

```bash
pnpm install
pnpm lint:openapi && pnpm bundle:openapi
pnpm codegen:paths
pnpm build
pnpm dev:api
# Health: curl http://127.0.0.1:4000/health
# Demo key: X-API-Key: denselink_demo_local_dev_key
```

Optional Dynamo Local:

```bash
docker compose up -d
TABLE_NAME=denselink-core-local AWS_ENDPOINT_URL=http://localhost:8000 node scripts/ensure-dynamo-table.mjs
```

## Codegen rules (agents)

1. **New domain** → full multi-layer generate once (Mode A).
2. **YAML edit on existing domain** → regenerate **core only**, handwrite below (Mode B).
3. Keep envelopes (`{ data, meta }`), nested DI, and identity middleware intact.

See `.cursor/skills/` and `docs/CODEGEN.md`.

## Domains

| Domain | Purpose |
|--------|---------|
| `identity` | API keys + operator auth (scaffold blueprint) |
| `meshports` | MeshPort allocation and collision prevention |
| `licenses` | SDK license keys and encryption attestation |
| `density` | Density models and piggyback discovery |
| `venues` | Venue programmes and always-on campaigns |
| `grants` | Density milestone grants |
| `telemetry` | Node telemetry aggregate ingest |
| `reports` | Contribution, coverage, and ROI reports |
