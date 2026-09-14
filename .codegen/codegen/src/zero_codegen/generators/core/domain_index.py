"""
Domain Index Generator - Generates {domain}/index.ts barrel export

Per DDD: Domain root index belongs in core layer (domain layer).
This generator creates the main barrel export file for the domain.
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file
from ...utils.string import pascal_case


class DomainIndexGenerator(BaseGenerator):
    """Generates domain root index.ts barrel export file"""
    
    @property
    def name(self) -> str:
        return "Domain Index Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "domain_index"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate domain root index.ts file"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        domain_dir = project_root / "packages" / "core" / "src" / context.domain_name
        ensure_directory(domain_dir)
        
        # Generate domain root index.ts
        index_file = domain_dir / "index.ts"
        
        header = self.generate_header(
            context,
            f"{pascal_case(context.domain_name)} Component - Core Export"
        )
        
        domain_pascal = pascal_case(context.domain_name)
        
        # Check if value-objects directory exists
        value_objects_dir = domain_dir / "value-objects"
        has_value_objects = value_objects_dir.exists() and any(value_objects_dir.glob("*.value-object.ts"))
        
        value_objects_export = ""
        if has_value_objects:
            value_objects_export = "\n// Value Objects (domain value objects, not persisted)\nexport * from \"./value-objects/index.js\";\n"
        
        # Check if models directory exists
        models_dir = domain_dir / "models"
        has_models = models_dir.exists() and any(models_dir.glob("*.entity.ts"))
        
        models_export = ""
        if has_models:
            models_export = "\n// Entities (domain entities, persisted)\nexport * from \"./models/index.js\";\n"
        
        content = f"""{header}// Types (Domain layer with Date objects + API operation types)
export * from "./types/index.js";

// Repository Interfaces (only if domain has repositories)
export * from "./repositories/index.js";
{models_export}{value_objects_export}
// ❌ Handlers removed from core per DDD principles
// Handlers are application/inbound concerns and belong in services or api-server
// Handler interfaces should be defined locally in handler implementations or replaced with use cases

// ❌ Converters removed from core per DDD principles
// Converters are application layer concerns and belong in services layer

// Schemas (Zod schemas from OpenAPI) - domain-specific export name
export {{ schemas as {domain_pascal.lower()}Schemas }} from "./schemas/{context.domain_name}.schemas.js";
"""
        
        write_file(index_file, content)
        files.append(index_file)
        
        context.logger.info(f"Generated domain root index for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
