# Strict Naming Schema: operationId from Path Resource

Codegen derives **grouping** (ports, handlers, repositories) from the **path resource**, not from ad-hoc operationId parsing. This document defines how operationIds must be formed so that grouping is deterministic and the generator needs no domain-specific hardcoding.

## Rule: operationId = Verb + Scope + PathResource

- **Verb** – From HTTP method or path action: `List`, `Get`, `Create`, `Update`, `Patch`, `Delete`, `Run`, `Provision`, etc.
- **Scope** – Optional, from path prefix:
  - Path starts with `/platform/` → scope `Platform` + domain (e.g. `PlatformAi`).
  - Path under `/orgs/{orgId}/` → scope `Org` + domain (e.g. `OrgAi`) for org-scoped config; execution resources may omit scope or use `Org`.
- **PathResource** – **Exactly** the path resource in PascalCase (see below). No extra qualifiers (no `Flat`, `ByGateway`, `ById`, etc.).

## Path → PathResource

1. Take the path template (e.g. `/orgs/{orgId}/ai/base-models`, `/orgs/{orgId}/ai/evals/{evalId}/run`).
2. Split on `/` and drop path parameters (segments matching `{...}`).
3. **Path resource** = last remaining segment (the noun that identifies the entity).
   - `/orgs/{orgId}/ai/base-models` → `base-models` → **BaseModels**
   - `/orgs/{orgId}/ai/evals` → `evals` → **Evals**
   - `/orgs/{orgId}/ai/gateways/{gatewayId}/models` → `models` (under gateways) → use **GatewayModels** (parent + segment) when the segment is a generic plural like `models`; otherwise last segment only.
4. Convert kebab-case to PascalCase. Use **plural** for List, **singular** for Get/Create/Update/Patch/Delete/Run/Provision in the operationId.

## Examples (path → operationId)

| Path | Method | operationId |
|------|--------|-------------|
| `/platform/ai/providers` | GET | `ListPlatformAiProviders` |
| `/platform/ai/providers/{providerId}` | GET | `GetPlatformAiProvider` |
| `/orgs/{orgId}/ai/base-models` | GET | `ListOrgAiBaseModels` |
| `/orgs/{orgId}/ai/base-models/{baseModelId}` | GET | `GetOrgAiBaseModel` |
| `/orgs/{orgId}/ai/prompts` | GET | `ListOrgAiPrompts` |
| `/orgs/{orgId}/ai/prompts` | POST | `CreateOrgAiPrompt` |
| `/orgs/{orgId}/ai/prompts/provision` | POST | `ProvisionOrgAiPrompt` |
| `/orgs/{orgId}/ai/evals` | GET | `ListOrgAiEvals` |
| `/orgs/{orgId}/ai/evals/{evalId}/run` | POST | `RunOrgAiEval` |
| `/orgs/{orgId}/ai/gateway-models` | GET | `ListOrgAiGatewayModels` |
| `/orgs/{orgId}/ai/gateway-models/{gatewayModelId}` | GET | `GetOrgAiGatewayModel` |
| `/orgs/{orgId}/ai/gateways/{gatewayId}/models/{modelId}` | PATCH | `PatchOrgAiGatewayModel` |

## What the generator does (no hardcoding)

1. **Grouping key** – Derived from the **path** when available:
   - Path → last non-parameter segment(s) → PascalCase → singularized → grouping key.
2. **Fallback** (when path not passed) – From operationId only:
   - Strip one **verb** prefix (from a single verb list).
   - Strip one **scope** prefix (e.g. `Org`, `Platform`, `OrgAi`, `PlatformAi` – configurable list, no domain-specific names).
   - Singularize remainder → grouping key.
3. **No** stripping of qualifier suffixes (`Flat`, `ByGateway`, `ById`, etc.) or special-case mappings (`AvailableChannel` → `PlatformChannel`, etc.). If the spec follows this schema, those do not appear in operationIds.

## Summary

- **Path** is the source of truth for the resource; **operationId** must mirror it as `Verb + Scope + PathResource`.
- Codegen uses **path** to compute the grouping key when path is available; otherwise it uses operationId with only **verb** and **scope** stripping plus singularization.
- This keeps grouping consistent and removes the need for hardcoded suffix/prefix or domain-specific rules in the generator.
