"""
Schemas Generator - Generates schemas/{domain}.schemas.ts from Zod schemas

Per DDD: Schemas belong in core layer (domain layer).
This generator creates a barrel export file that re-exports schemas from the zod schema file.
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file, file_exists
from ...utils.string import pascal_case


class SchemasGenerator(BaseGenerator):
    """Generates schemas barrel export file from Zod schemas"""
    
    @property
    def name(self) -> str:
        return "Schemas Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "schemas"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate schemas barrel export file"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        domain_dir = project_root / "packages" / "core" / "src" / context.domain_name
        schemas_dir = domain_dir / "schemas"
        ensure_directory(schemas_dir)
        
        # Check if zod schema file exists
        openapi_dir = domain_dir / "openapi"
        zod_schema_file = openapi_dir / f"{context.domain_name}.zod.schema.ts"
        
        if not file_exists(zod_schema_file):
            warnings.append(f"Zod schema file not found: {zod_schema_file}")
            warnings.append("Schemas barrel export will not be generated")
            return GenerateResult(files=files, warnings=warnings)
        
        # Generate schemas barrel export file
        schemas_file = schemas_dir / f"{context.domain_name}.schemas.ts"
        
        header = self.generate_header(
            context,
            f"{pascal_case(context.domain_name)} Schemas - Domain schemas barrel export"
        )
        
        # Read the zod schema file to extract schema names
        # The zod schema file exports individual schemas, we need to re-export them
        # Import path from schemas/ to openapi/ (Node ESM requires .js extension)
        import_path = f"../openapi/{context.domain_name}.zod.schema.js"

        content = f"""{header}import {{ schemas }} from "{import_path}";

export {{ schemas }};
"""
        
        write_file(schemas_file, content)
        files.append(schemas_file)
        
        context.logger.info(f"Generated schemas barrel export for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
