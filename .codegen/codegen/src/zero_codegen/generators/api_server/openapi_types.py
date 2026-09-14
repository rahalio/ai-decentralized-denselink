"""
OpenAPI Types Generator - Generates OpenAPI TypeScript types

Per DDD: OpenAPI types belong in api-server layer (inbound layer).
These are contract types extracted from OpenAPI specs.
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file, clean_directory
from ...utils.string import pascal_case


class OpenAPITypesGenerator(BaseGenerator):
    """
    Generates OpenAPI TypeScript types

    Uses OpenAPI TypeScript extractor to generate types from OpenAPI spec.
    """

    @property
    def name(self) -> str:
        return "OpenAPI Types Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "openapi_types"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate OpenAPI types"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory (clean contracts/ when pipeline.clean - openapi_types runs before zod_schemas)
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "api-server" / "src" / "domains" / context.domain_name / "contracts"
        ensure_directory(output_dir)
        if context.config.pipeline.clean:
            clean_directory(output_dir)

        # Use OpenAPI TypeScript extractor
        from ...extractors.openapi_typescript_extractor import OpenApiTypeScriptExtractor

        extractor = OpenApiTypeScriptExtractor()

        # Generate types file
        types_file = output_dir / f"{context.domain_name}.openapi.types.ts"

        header = self.generate_header(
            context,
            f"{pascal_case(context.domain_name)} OpenAPI Types - Contract types"
        )

        # Extract types from spec
        try:
            types_content = extractor.extract(context.spec, context.domain_name)
            full_content = f"{header}{types_content}"
            write_file(types_file, full_content)
            files.append(types_file)
        except Exception as e:
            warnings.append(f"Failed to extract OpenAPI types: {str(e)}")

        context.logger.info(f"Generated OpenAPI types file for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)
