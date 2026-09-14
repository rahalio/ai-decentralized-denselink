# Entity Classification Audit - Channel Domain

## Expected Classification (per OpenAPI spec analysis)

### ✅ Persisted Entities (should be generated)

1. **ProviderType** (`entityType: PROVIDER_TYPE`)
   - Resource: `provider-catalog`
   - File: `models/provider-catalog/entity/provider-catalog.entity.ts`
   - Schema: `schemas.ProviderType` ✅ CORRECT

2. **ProviderTokenSet** (`entityType: PROVIDER_TOKEN_SET`)
   - Resource: `provider-account-token`
   - File: `models/provider-account-token/entity/provider-account-token.entity.ts`
   - Schema: `schemas.ProviderTokenSet` ❌ **WRONG** - Currently using `schemas.ProviderAccount`

3. **ProviderAccount** (`entityType: PROVIDER_ACCOUNT`)
   - Resource: `provider`
   - File: `models/provider/entity/provider.entity.ts`
   - Schema: `schemas.ProviderAccount` ✅ CORRECT

4. **WebhookAcknowledgment** (`entityType: WEBHOOK_ACKNOWLEDGMENT`)
   - Resource: `provider-webhook`
   - File: `models/provider-webhook/entity/provider-webhook.entity.ts`
   - Schema: `schemas.WebhookAcknowledgment` ✅ CORRECT

### ❌ Transport Wrappers (should be SKIPPED)

1. **ProviderAccountListResponse** - `{ data: { items: [...] }, meta }`
2. **ProviderCatalogResponse** - `{ data: { items: [...] }, meta }`
3. **OAuthStartResponse** - `{ data: { authorizationUrl, state }, meta }`
4. **ProviderAccountValidationResponse** - `{ data: { isValid, ... }, meta }`

**Expected behavior:** These should be detected by `_is_transport_wrapper()` and skipped with warnings.

### ⚠️ Value Objects (should only be generated if explicitly marked)

Currently generated:

- **ProviderConnectionImproved** (`OAuthStartResponse.shape.data`)
  - File: `models/value-objects/provider-connection-improved.value-object.ts`
  - **Issue:** This is being generated from a transport wrapper's `data` field
  - **Expected:** Should be skipped unless `OAuthStartPayload` schema is defined with `x-value-object: true`

## Current Issues

### Issue 1: `provider-account-token` using wrong schema

- **Current:** `schemas.ProviderAccount`
- **Expected:** `schemas.ProviderTokenSet`
- **Root cause:** `refreshProviderAccountToken` operation returns `ProviderAccount`, but the resource should map to `PROVIDER_TOKEN_SET` entityType via metadata matching

### Issue 2: Transport wrappers not being skipped

- **Current:** `OAuthStartResponse` is being used to generate a value object
- **Expected:** `OAuthStartResponse` should be skipped entirely
- **Root cause:** The extractor is returning `OAuthStartResponse` as the entity schema, and the generator is treating it as a value object instead of detecting it as a transport wrapper first

### Issue 3: Missing transport wrapper detection

- Transport wrappers should be detected BEFORE entity extraction or value object generation
- The `_is_transport_wrapper()` function exists but may not be catching all cases

## Recommended Fixes

1. **Prioritize metadata matching over response extraction** for resources that have clear entityType mappings
2. **Skip transport wrappers at extraction time** - if a schema is detected as a transport wrapper, don't use it as an entity schema
3. **Only generate value objects from explicit `x-value-object: true` schemas** - don't derive VOs from transport wrapper `data` fields

## Verification Checklist

- [ ] `provider-account-token` uses `ProviderTokenSet` schema
- [ ] All transport wrappers are skipped with warnings
- [ ] No value objects generated from transport wrapper `data` fields
- [ ] Only 4 entity files generated (ProviderType, ProviderTokenSet, ProviderAccount, WebhookAcknowledgment)
- [ ] Warnings logged for skipped transport wrappers with operation IDs
