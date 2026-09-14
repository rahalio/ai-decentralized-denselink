# List methods: GSI-first rule

## Rule

List methods must **prefer Query on a GSI** when the entity has any GSI enabled and the request allows building a valid GSI partition key. Use **Scan** only when no GSI key can be built (avoids full table scan).

## Branch order

When building the list implementation, try in order:

1. **GSI3** (e.g. status in PK) — when the API provides a filter that matches GSI3 PK (e.g. `status`).
2. **GSI1** (e.g. status, kind, or type in PK) — when the API provides a filter that matches GSI1 PK.
3. **GSI2** (orgId only) — when there is no status/kind/type filter; a single partition per org covers all items, ordered by `updatedAt` in the sort key.
4. **Scan** — only when no GSI partition key can be built (e.g. no GSI2 and no filter).

Use `buildGsiPartitionKeyForQuery(entityType, gsiIndex, queryKey)` from `platform/adapters/src/_shared/gsi-key-builder.js`. The `queryKey` object should include `orgId` and, when applicable: `status`, `kind`, or `type`. See `.docs/database/DYNAMODB-GSI-CONFIG.md` for key shapes per entity.

## Reference implementations

- **content-entry-repository.ddb.ts** — Full pattern: GSI3 (status) → GSI1 (kind) → GSI2 (all) → scan. Includes in-memory sort when `sortBy !== updatedAt`, and `includeTotal` via GSI or scan count.
- **campaign-repository.ddb.ts** — GSI1 (status) → GSI3 (type) → scan. Same pagination and totalCount pattern.
- **product-repository.ddb.ts** — GSI1 (lifecycleState) → scan.

## GET by id

GET operations use main-table Query (`PK = :pk AND begins_with(SK, :skPrefix)`). No change; no "GSI first" choice for GETs.
