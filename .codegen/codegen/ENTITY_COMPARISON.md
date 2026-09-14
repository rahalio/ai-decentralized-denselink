# Channel Domain: Generated Entities vs YAML Schemas

## Generated Entities (6 total)

| Resource Name                  | Entity File                              | Schema Used                        | Status                                         |
| ------------------------------ | ---------------------------------------- | ---------------------------------- | ---------------------------------------------- |
| `provider`                     | `provider.entity.ts`                     | `ProviderAccount`                  | ✅ Correct (from listProviders/createProvider) |
| `provider-account`             | `provider-account.entity.ts`             | `ProviderAccount`                  | ✅ Correct                                     |
| `provider-account-token`       | `provider-account-token.entity.ts`       | `ProviderAccount`                  | ❌ **WRONG** - Should be `ProviderTokenSet`    |
| `provider-catalog`             | `provider-catalog.entity.ts`             | `ProviderType`                     | ✅ Correct                                     |
| `provider-webhook`             | `provider-webhook.entity.ts`             | `WebhookAcknowledgment`            | ✅ Correct                                     |
| `provider-connection-improved` | `provider-connection-improved.entity.ts` | `OAuthStartResponse.data` (inline) | ✅ Correct (extracts inline object)            |

## Schemas Available in YAML (15 total)

### Entity Schemas (should map to entities):

1. ✅ `ProviderAccount` - Used by: provider, provider-account
2. ✅ `ProviderType` - Used by: provider-catalog
3. ❌ `ProviderTokenSet` - **NOT USED** - Should be used by provider-account-token
4. ✅ `WebhookAcknowledgment` - Used by: provider-webhook
5. ✅ `ProviderCapability` - Supporting schema (not an entity)

### Response Schemas (wrappers, not entities):

6. `ProviderAccountListResponse` - Response wrapper
7. `ProviderCatalogResponse` - Response wrapper
8. `OAuthStartResponse` - Response wrapper (data extracted for provider-connection-improved)
9. `ProviderAccountValidationResponse` - Response wrapper

### Request Schemas (not entities):

10. `ProviderAccountCreateRequest` - Request DTO
11. `ProviderAccountUpdateRequest` - Request DTO
12. `ProviderTypeCreateRequest` - Request DTO
13. `ProviderTypeUpdateRequest` - Request DTO
14. `OAuthStartRequest` - Request DTO
15. `OAuthCallbackRequest` - Request DTO

## Issues Found

### ❌ `provider-account-token` Entity Issue

- **Current**: Uses `ProviderAccount` schema
- **Expected**: Should use `ProviderTokenSet` schema
- **Reason**: The resource name suggests it should represent token sets, and `ProviderTokenSet` exists in the YAML with proper DynamoDB metadata
- **Operations**: `refreshProviderAccountToken` returns `ProviderAccount`, but the entity should represent the token set itself

## Summary

- **Generated**: 6 entities
- **Correct**: 5 entities ✅
- **Incorrect**: 1 entity ❌ (`provider-account-token`)
- **Unused Schemas**: `ProviderTokenSet` (should be used)
