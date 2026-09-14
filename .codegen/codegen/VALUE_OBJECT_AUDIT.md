# Value Object Audit - Channel Domain

## Value Objects Marked in YAML

### ✅ Explicitly Marked Value Objects (`x-value-object: true`)

1. **ProviderCapability**
   - **Location:** `components/schemas/ProviderCapability`
   - **Marked:** `x-value-object: true`
   - **Usage:** Referenced in `ProviderType.capabilities` array
   - **Reason:** Domain concept representing a capability (key, description, supported flag). No identity, not persisted.
   - **Status:** ✅ Correctly marked

2. **OAuthStartPayload**
   - **Location:** `components/schemas/OAuthStartPayload`
   - **Marked:** `x-value-object: true`
   - **Usage:** Referenced in `OAuthStartResponse.data`
   - **Reason:** Ephemeral OAuth flow state (`authorizationUrl`, `state`). Not persisted, domain concept.
   - **Status:** ✅ Correctly marked and extracted from transport wrapper

3. **ProviderConnectionValidation**
   - **Location:** `components/schemas/ProviderConnectionValidation`
   - **Marked:** `x-value-object: true`
   - **Usage:** Referenced in `ProviderAccountValidationResponse.data`
   - **Reason:** Validation result (isValid, status, tokenExpiresAt, etc.). Not persisted, represents validation outcome.
   - **Status:** ✅ Correctly marked and extracted from transport wrapper

## Value Objects Generated

Currently, only value objects that are the **primary schema** for a resource (extracted from operations) are generated as separate files:

- `provider-connection-improved.value-object.ts` - Generated from `OAuthStartResponse.data` (inline object)

## Value Objects NOT Generated (But Correctly Marked)

These value objects are marked in YAML but not generated as separate files because they're **not primary schemas** for any resource:

- `ProviderCapability` - Used as array items in `ProviderType` and `ProviderAccount`
- `OAuthStartPayload` - Referenced in `OAuthStartResponse.data`
- `ProviderConnectionValidation` - Referenced in `ProviderAccountValidationResponse.data`

**Note:** These are still available through the schemas and can be used in generated code, but won't have dedicated value object files unless they become primary schemas for resources.

## Recommendations

1. ✅ **ProviderCapability** - Correctly marked. Used as embedded value object in entities.
2. ✅ **OAuthStartPayload** - Correctly marked. Extracted from transport wrapper.
3. ✅ **ProviderConnectionValidation** - Correctly marked. Extracted from transport wrapper.

All value objects are now explicitly marked - no guessing. The generator will use these markings when determining classification.
