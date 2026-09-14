"""
OpenAPI TypeScript Extractor - Extracts TypeScript types from bundled OpenAPI JSON files

Uses openapi-typescript to extract TypeScript types from bundled OpenAPI JSON files.
Outputs to: packages/core/src/{domain}/openapi/{domain}.openapi.types.ts

This extractor is modular and standalone - can be invoked directly or via pipeline.
"""

from pathlib import Path
from typing import List
import subprocess

from zero_codegen.base.generator import BaseGenerator, GenerateResult
from zero_codegen.base.context import GenerationContext
from zero_codegen.base.errors import GenerationError
from zero_codegen.base.folder_structure import FolderStructureConfig
from zero_codegen.utils.file import ensure_directory, file_exists, clean_directory


class OpenApiTypeScriptExtractor(BaseGenerator):
    """Extracts TypeScript types from bundled OpenAPI JSON files using openapi-typescript"""

    @property
    def name(self) -> str:
        return "OpenAPI TypeScript Extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "openapi_typescript_extractor"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Extract TypeScript types from bundled JSON file"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get bundled spec path (resolve to absolute path)
        bundled_path = context.bundled_path.resolve() if not context.bundled_path.is_absolute() else context.bundled_path
        if not file_exists(bundled_path):
            raise GenerationError(
                f"Bundled OpenAPI spec not found: {bundled_path}",
                context.domain_name,
                self.type,
            )

        # Determine output path - always use core layer for core generation
        project_root = context.config.paths.project_root.resolve()
        
        # Core layer: packages/core/src/{domain}/openapi/{domain}.openapi.types.ts
        domain_dir = project_root / "packages" / "core" / "src" / context.domain_name
        output_dir = domain_dir / "openapi"
        ensure_directory(output_dir)
        if context.config.pipeline.clean:
            clean_directory(output_dir)
        types_file = output_dir / f"{context.domain_name}.openapi.types.ts"

        # Ensure types_file is absolute
        types_file = types_file.resolve()

        context.logger.info(f"Extracting TypeScript types for {context.domain_name}...")

        # Run openapi-typescript
        cmd = [
            "npx",
            "--yes",
            "openapi-typescript@latest",
            str(bundled_path),
            "-o",
            str(types_file),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(context.config.paths.project_root),
                capture_output=True,
                text=True,
                check=True,
            )
            if file_exists(types_file):
                files.append(types_file)
                context.logger.info(f"✅ Extracted TypeScript types: {types_file}")
            else:
                warnings.append(f"TypeScript types file was not created: {types_file}")
        except subprocess.CalledProcessError as e:
            raise GenerationError(
                f"Failed to extract TypeScript types: {e.stderr}",
                context.domain_name,
                self.type,
            )

        return GenerateResult(files=files, warnings=warnings)
