"""
Types Generator - Generates TypeScript type exports

Per DDD: Types belong in core layer (domain layer).
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import write_file
from ...utils.generator_setup import GeneratorSetup
from .types_builder.types_builder import TypesBuilder


class TypesGenerator(BaseGenerator):
    """Generates TypeScript type exports from OpenAPI types"""
    
    @property
    def name(self) -> str:
        return "Types Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "types"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate types file"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory using GeneratorSetup helper (clean when pipeline.clean)
        output_dir = GeneratorSetup.get_output_directory(
            context, generator_type="types", layer="core", clean=context.config.pipeline.clean
        )
        
        # Generate types file at types/index.ts
        types_file = output_dir / "index.ts"
        
        # Remove old types.ts file at domain root if it exists (legacy)
        project_root = context.config.paths.project_root
        domain_dir = project_root / "packages" / "core" / "src" / context.domain_name
        legacy_types_file = domain_dir / "types.ts"
        if legacy_types_file.exists():
            legacy_types_file.unlink()
        
        content = TypesBuilder.build_types_file_content(context, self.version)
        write_file(types_file, content)
        files.append(types_file)
        
        # Also generate a domain types export file that excludes components/operations for main index.ts
        domain_types_file = output_dir / f"{context.domain_name}.domain.types.ts"
        domain_content = TypesBuilder.build_flat_types_file_content(context, self.version)
        write_file(domain_types_file, domain_content)
        files.append(domain_types_file)
        
        return GenerateResult(files=files, warnings=warnings)
