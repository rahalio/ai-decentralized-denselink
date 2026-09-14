#!/usr/bin/env node
/**
 * Rewrite .codegen/.zero-codegen-merged.json paths to absolute (cwd = repo root).
 * Usage: node scripts/sync-codegen-paths.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const configPath = join(root, '.codegen', '.zero-codegen-merged.json');
const cfg = JSON.parse(readFileSync(configPath, 'utf8'));

cfg.paths = {
  ...cfg.paths,
  project_root: root,
  openapi_dir: join(root, 'packages', 'openapi-core', 'src'),
  bundled_dir: join(root, 'packages', 'openapi-core', 'src', '.bundled'),
};

writeFileSync(configPath, JSON.stringify(cfg, null, 2) + '\n');
console.log('Updated codegen paths for', root);
