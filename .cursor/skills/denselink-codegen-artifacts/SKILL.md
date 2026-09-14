---
name: denselink-codegen-artifacts
description: >-
  Denselink rule: commit the .codegen toolchain; never commit or push generated
  OpenAPI bundles, Postman generated collections, or Python caches. Use when
  committing, pushing, reviewing git status, or cleaning codegen outputs.
---

# Denselink — codegen artifacts vs toolchain

## Commit the toolchain

**Do commit** the `.codegen/` directory that ships with this repo:

- `.codegen/codegen/` — Python `zero_codegen` tool
- `.codegen/.zero-codegen-merged.json` and `.codegen/zero-codegen.json`
- `.codegen/openapi-examples/` and lint templates

These are required for `pnpm codegen:*` and Mode A/B generation. Do **not** add a blanket `.codegen/` entry to `.gitignore`.

## Never commit or push generated artifacts

**Do not** commit, stage, or push:

| Artifact | Path |
|----------|------|
| Bundled OpenAPI | `packages/openapi-core/src/.bundled/` |
| Postman generated | `platform/tests/postman/generated/` |
| Integration-event generated dumps | `**/integration-events/generated/` (except hand-maintained `integration-event.types.ts`) |
| Python caches | `.codegen/**/__pycache__/`, `*.pyc` |

Regenerate bundles with `pnpm bundle:openapi`. Regenerate core with `pnpm codegen:core` after YAML edits (Mode B).

## Agent checklist before `git add` / push

1. Confirm `.codegen/` tool/config changes are intentional and included.
2. Confirm `.bundled/`, Postman generated, and `__pycache__` are **not** staged.
3. If git status shows those paths, unstage them and rely on `.gitignore`.
