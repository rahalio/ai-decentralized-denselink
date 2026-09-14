"""
OpenAPI Zod Client Extractor - Extracts Zod schemas from bundled OpenAPI JSON files

Uses openapi-zod-client to extract Zod schemas from bundled OpenAPI JSON files.
Outputs to: packages/core/src/{domain}/openapi/{domain}.zod.schema.ts

This extractor is modular and standalone - can be invoked directly or via pipeline.
"""

from pathlib import Path
from typing import List
import subprocess

from zero_codegen.base.generator import BaseGenerator, GenerateResult
from zero_codegen.base.context import GenerationContext
from zero_codegen.base.errors import GenerationError
from zero_codegen.base.folder_structure import FolderStructureConfig
from zero_codegen.utils.file import ensure_directory, file_exists


class OpenApiZodClientExtractor(BaseGenerator):
    """Extracts Zod schemas from bundled OpenAPI JSON files using openapi-zod-client"""

    @property
    def name(self) -> str:
        return "OpenAPI Zod Client Extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "openapi_zod_client_extractor"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Extract Zod schemas from bundled JSON file"""
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

        # Core layer: packages/core/src/{domain}/openapi/{domain}.zod.schema.ts
        domain_dir = project_root / "packages" / "core" / "src" / context.domain_name
        output_dir = domain_dir / "openapi"
        ensure_directory(output_dir)
        schemas_file = output_dir / f"{context.domain_name}.zod.schema.ts"
        schemas_file = schemas_file.resolve()

        # Base URL - use SDK config if available, otherwise default
        sdk_config = getattr(context.config.layers, 'sdk', None)
        base_url = sdk_config.base_url if sdk_config and sdk_config.base_url else "https://api.ddd-codegen-starter.local/v1"

        context.logger.info(f"Extracting Zod schemas for {context.domain_name}...")

        # Run openapi-zod-client (--export-schemas ensures component schemas are included even with empty paths)
        cmd = [
            "npx",
            "--yes",
            "openapi-zod-client@latest",
            str(bundled_path),
            "-o",
            str(schemas_file),
            "--baseUrl",
            base_url,
            "--export-schemas",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(context.config.paths.project_root),
                capture_output=True,
                text=True,
                check=True,
            )
            if file_exists(schemas_file):
                # Post-process the generated file to add type annotations
                self._add_type_annotations(schemas_file)
                files.append(schemas_file)
                context.logger.info(f"✅ Extracted Zod schemas: {schemas_file}")
            else:
                warnings.append(f"Zod schemas file was not created: {schemas_file}")
        except subprocess.CalledProcessError as e:
            raise GenerationError(
                f"Failed to extract Zod schemas: {e.stderr}",
                context.domain_name,
                self.type,
            )

        return GenerateResult(files=files, warnings=warnings)

    def _add_type_annotations(self, schemas_file: Path):
        """Add explicit type annotations to api, createApiClient, and schemas exports to fix TypeScript errors"""
        try:
            content = schemas_file.read_text(encoding="utf-8")

            import re
            # Type schemas as any to avoid TS7056 (inferred type exceeds max length) in large zod files.
            # Entity/value-object types use OpenAPI components when schema is in spec; fallback to z.infer otherwise.
            content = re.sub(
                r'export const schemas = \{',
                'export const schemas: any = {',
                content
            )

            # Replace api export with type annotation
            # Pattern: export const api = new Zodios(...)
            content = re.sub(
                r'export const api = new Zodios\(',
                'export const api: any = new Zodios(',
                content
            )

            # Pattern: export function createApiClient(...) { return new Zodios(...) }
            content = re.sub(
                r'export function createApiClient\(([^)]+)\) \{\s+return new Zodios\(([^)]+)\);\s+\}',
                r'export function createApiClient(\1): any {\n  return new Zodios(\2);\n}',
                content,
                flags=re.MULTILINE | re.DOTALL
            )

            # Alternative pattern for createApiClient if the above doesn't match
            if 'export function createApiClient' in content and ': any' not in content.split('export function createApiClient')[1].split('\n')[0]:
                content = re.sub(
                    r'(export function createApiClient\([^)]+\)) \{',
                    r'\1: any {',
                    content
                )

            schemas_file.write_text(content, encoding="utf-8")
        except Exception as e:
            # Log warning but don't fail - the file was generated successfully
            import warnings
            warnings.warn(f"Failed to add type annotations to {schemas_file}: {e}")
