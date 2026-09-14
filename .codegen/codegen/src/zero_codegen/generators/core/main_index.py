"""
Main Index Generator - Generates packages/core/src/index.ts barrel export

This generator creates the main barrel export file for the entire core package,
aggregating all domain exports and providing both namespace and flat exports.

Domains are discovered by rescanning packages/core/src: only subdirectories that
contain both index.ts and schemas/{domain}.schemas.ts are included. This avoids
exporting domains that failed to generate (e.g. missing spec) or were disabled.
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file
from ...utils.string import pascal_case, camel_case


def _discover_domains(core_src_dir: Path) -> List[str]:
    """
    Rescan core/src for domain directories that were actually generated.
    A domain is included only if it has both index.ts and schemas/{domain}.schemas.ts.
    """
    domains: List[str] = []
    if not core_src_dir.is_dir():
        return domains
    for path in sorted(core_src_dir.iterdir()):
        if not path.is_dir() or path.name.startswith(".") or path.name == "_shared":
            continue
        domain = path.name
        index_ts = path / "index.ts"
        schemas_ts = path / "schemas" / f"{domain}.schemas.ts"
        if index_ts.is_file() and schemas_ts.is_file():
            domains.append(domain)
    return sorted(domains)


class MainIndexGenerator(BaseGenerator):
    """Generates main packages/core/src/index.ts barrel export file"""
    
    @property
    def name(self) -> str:
        return "Main Index Builder Generator"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def type(self) -> str:
        return "main_index"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate main packages/core/src/index.ts file"""
        # Main index doesn't need OpenAPI spec, so we skip validation
        # self.validate_context(context)  # Skip - spec not needed for main index
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        core_src_dir = project_root / "packages" / "core" / "src"
        ensure_directory(core_src_dir)
        
        # Generate main index.ts
        index_file = core_src_dir / "index.ts"
        
        # Rescan core/src for domains that were actually generated (don't use config list)
        enabled_domains = _discover_domains(core_src_dir)
        
        header = self.generate_header(
            context,
            "Main Core Package Index"
        )
        
        # Generate namespace imports
        namespace_imports = []
        namespace_exports = []
        
        # Add _shared first
        namespace_imports.append('import * as __shared from "./_shared/index.js";')
        namespace_exports.append('export const _shared = __shared;')
        
        # Add all domains — camelCase vars so hyphenated domain names are valid JS identifiers
        for domain in enabled_domains:
            domain_export = camel_case(domain)
            domain_var = f"_{domain_export}"
            namespace_imports.append(f'import * as {domain_var} from "./{domain}/index.js";')
            namespace_exports.append(f'export const {domain_export} = {domain_var};')
        
        # Generate schema exports
        schema_exports_lines = []
        for domain in enabled_domains:
            domain_pascal = pascal_case(domain)
            schema_exports_lines.append(f'// {domain_pascal} Service')
            schema_exports_lines.append(
                f'export {{ schemas as {domain_pascal}Schemas }} from "./{domain}/schemas/{domain}.schemas.js";'
            )
            schema_exports_lines.append('')  # Empty line between domains
        
        content = f"""{header}/**
 * @ddd/core - Main Barrel Export
 *
 * Central export point for all core business logic, entities, repositories, and types
 * Organized by domain for easy importing
 *
 * Usage:
 *   // Namespace imports (recommended for new code)
 *   import {{ activity, ai }} from "@ddd/core";
 *   const {{ repositories, types }} = activity;
 *
 *   // Direct domain imports (via package.json exports)
 *   import {{ ActivityRepository }} from "@ddd/core/activity/repositories/index.js";
 *   import {{ ActivityEntity }} from "@ddd/core/activity/models/index.js";
 *   import {{ ActivitySchemas }} from "@ddd/core/activity/schemas/index.js";
 *
 *   // Flat schema imports
 *   import {{ ActivitySchemas, AiSchemas }} from "@ddd/core";
 */

// ============================================================================
// DOMAIN EXPORTS (using namespace to avoid duplicate shared type conflicts)
// ============================================================================
// Export domains as namespaces to prevent TS2308 errors from duplicate exports
// of shared types (AccountId, OrgId, PageInfo, components, operations)
// NOTE: _shared is NOT a domain and is exported separately

{chr(10).join(namespace_imports)}

// Export as namespaces
{chr(10).join(namespace_exports)}

// ============================================================================
// FLAT EXPORTS (for direct imports)
// ============================================================================
// Export schemas from each domain for convenience
// NOTE: Types, repositories, models, and value-objects are available via:
//   - Namespace exports: import {{ activity }} from "@ddd/core"; activity.types.*
//   - Direct exports: import * from "@ddd/core/activity/types/index.js"
//   - Direct exports: import * from "@ddd/core/activity/repositories/index.js"
//   - Direct exports: import * from "@ddd/core/activity/models/index.js"
//   - Direct exports: import * from "@ddd/core/activity/value-objects/index.js"

// Shared utilities and helpers
// These exports are required by platform/api-server and platform/services
export {{
  DOMAIN_PREFIX_MAP,
  isValidDomainId,
  extractDomainFromId,
}} from "./_shared/index.js";
export type {{ DomainCode, DomainPrefix }} from "./_shared/index.js";

{chr(10).join(schema_exports_lines)}
"""
        
        write_file(index_file, content)
        files.append(index_file)
        
        context.logger.info(f"Generated main index.ts with {len(enabled_domains)} domains (rescan)")
        
        return GenerateResult(files=files, warnings=warnings)
