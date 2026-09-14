"""
Services Main Index Generator - Generates platform/services/src/index.ts barrel export

This generator creates the main barrel export file for the entire services package,
aggregating all domain exports and providing namespace exports.
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file
from ...utils.string import pascal_case, camel_case


class ServicesMainIndexGenerator(BaseGenerator):
    """Generates main platform/services/src/index.ts barrel export file"""
    
    @property
    def name(self) -> str:
        return "Services Main Index Generator"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def type(self) -> str:
        return "services_main_index"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate main platform/services/src/index.ts file"""
        # Main index doesn't need OpenAPI spec, so we skip validation
        # self.validate_context(context)  # Skip - spec not needed for main index
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        services_src_dir = project_root / "platform" / "services" / "src"
        ensure_directory(services_src_dir)
        
        # Generate main index.ts
        index_file = services_src_dir / "index.ts"
        
        # Get all enabled domains from config
        enabled_domains = [
            domain.name for domain in context.config.domains
            if domain.enabled
        ]
        enabled_domains.sort()  # Sort alphabetically for consistency
        
        header = self.generate_header(
            context,
            "Main Services Package Index"
        )
        
        # Generate namespace imports
        namespace_imports = []
        namespace_exports = []
        
        # Add all domains — camelCase vars so hyphenated domain names are valid JS identifiers
        for domain in enabled_domains:
            domain_export = camel_case(domain)
            domain_var = f"_{domain_export}"
            namespace_imports.append(f'import * as {domain_var} from "./{domain}/index.js";')
            namespace_exports.append(f'export const {domain_export} = {domain_var};')
        
        content = f"""{header}/**
 * Services Package - Main Barrel Export
 *
 * Central export point for all application services (use cases, ports, DTOs, policies, errors)
 * Organized by domain for easy importing
 *
 * Usage:
 *   // Namespace imports (recommended)
 *   import {{ activity, ai, conversation }} from "@ddd/services";
 *   const {{ usecases, dto, ports }} = activity;
 *
 *   // Direct imports from domain
 *   import {{ ExecuteCreateEventUseCase }} from "@ddd/services/activity";
 *   
 *   // Shared services
 *   import {{ executionContextService }} from "@ddd/services";
 */

// ============================================================================
// SHARED SERVICES EXPORTS
// ============================================================================
export {{ executionContextService }} from "./_shared/index.js";

// ============================================================================
// DOMAIN EXPORTS (using namespace to avoid duplicate type conflicts)
// ============================================================================
// Export domains as namespaces to prevent TS2308 errors from duplicate exports
// of shared types across domains

{chr(10).join(namespace_imports)}

// Export as namespaces
{chr(10).join(namespace_exports)}
"""
        
        write_file(index_file, content)
        files.append(index_file)
        
        context.logger.info(f"Generated services main index.ts with {len(enabled_domains)} domains")
        
        return GenerateResult(files=files, warnings=warnings)
