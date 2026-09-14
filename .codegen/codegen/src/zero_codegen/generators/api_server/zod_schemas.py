"""
Zod Schemas Generator - Generates Zod schemas from OpenAPI specs

Per DDD: Zod schemas belong in api-server layer (inbound layer).
These are runtime validation schemas extracted from OpenAPI specs.
"""

from pathlib import Path
from typing import List
import json

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...base.errors import GenerationError
from ...utils.file import ensure_directory, write_file, file_exists
from ...utils.string import pascal_case
import subprocess


class ZodSchemasGenerator(BaseGenerator):
    """
    Generates Zod schemas from bundled OpenAPI JSON files

    Uses openapi-zod-client to extract Zod schemas.
    Outputs to: platform/api-server/src/domains/{domain}/contracts/{domain}.zod.schema.ts
    """

    @property
    def name(self) -> str:
        return "Zod Schemas Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "zod_schemas"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate Zod schemas file"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get bundled spec path
        bundled_path = context.bundled_path.resolve() if not context.bundled_path.is_absolute() else context.bundled_path
        if not file_exists(bundled_path):
            warnings.append(f"Bundled OpenAPI spec not found: {bundled_path}")
            warnings.append("Skipping Zod schemas generation - ensure OpenAPI spec is bundled first")
            return GenerateResult(files=files, warnings=warnings)

        # Get output directory - Zod schemas go to api-server contracts
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "api-server" / "src" / "domains" / context.domain_name / "contracts"
        ensure_directory(output_dir)

        # Generate Zod schemas file
        schemas_file = output_dir / f"{context.domain_name}.zod.schema.ts"

        header = self.generate_header(
            context,
            f"{pascal_case(context.domain_name)} Zod Schemas - Runtime validation schemas"
        )

        context.logger.info(f"Extracting Zod schemas for {context.domain_name}...")

        # Run openapi-zod-client to extract schemas
        # Base URL from config or default
        base_url = getattr(context.config, 'base_url', None) or "https://api.ddd-codegen-starter.local"

        cmd = [
            "npx",
            "--yes",
            "openapi-zod-client@latest",
            str(bundled_path),
            "-o",
            str(schemas_file),
            "--baseUrl",
            base_url,
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=True,
            )

            if file_exists(schemas_file):
                # Read the generated file and prepend our header
                with open(schemas_file, "r") as f:
                    content = f.read()

                # Prepend header if not already present
                if "AUTO-GENERATED" not in content[:200]:
                    full_content = f"{header}{content}"
                    write_file(schemas_file, full_content)
                    content = full_content

                # Post-process to add type annotations
                self._add_type_annotations(schemas_file, content)
                # Post-process: enforce strict objects when OpenAPI says additionalProperties: false
                self._apply_strict_mode_from_openapi(schemas_file, bundled_path)

                files.append(schemas_file)
                context.logger.info(f"✅ Generated Zod schemas: {schemas_file}")
            else:
                warnings.append(f"Zod schemas file was not created: {schemas_file}")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to extract Zod schemas: {e.stderr or str(e)}"
            warnings.append(error_msg)
            context.logger.error(error_msg)
        except FileNotFoundError:
            warnings.append("npx not found - ensure Node.js is installed")
            context.logger.warn("npx not found - skipping Zod schemas generation")
        except Exception as e:
            warnings.append(f"Unexpected error generating Zod schemas: {str(e)}")
            context.logger.error(f"Unexpected error: {str(e)}")

        return GenerateResult(files=files, warnings=warnings)

    def _add_type_annotations(self, schemas_file: Path, content: str):
        """Add explicit type annotations to api, createApiClient, and schemas exports to fix TypeScript errors"""
        try:
            import re
            # Replace schemas export with type annotation
            # Pattern: export const schemas = {
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
            # First try multiline pattern
            content = re.sub(
                r'export function createApiClient\(([^)]+)\) \{\s+return new Zodios\(([^)]+)\);\s+\}',
                r'export function createApiClient(\1): any {\n  return new Zodios(\2);\n}',
                content,
                flags=re.MULTILINE | re.DOTALL
            )

            # Alternative pattern for createApiClient if the above doesn't match
            if 'export function createApiClient' in content:
                lines = content.split('\n')
                new_lines = []
                for i, line in enumerate(lines):
                    if line.strip().startswith('export function createApiClient') and ': any' not in line:
                        # Check if next line is opening brace
                        if i + 1 < len(lines) and lines[i + 1].strip() == '{':
                            new_lines.append(line.replace(') {', '): any {'))
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                content = '\n'.join(new_lines)

            write_file(schemas_file, content)
        except Exception as e:
            # Log warning but don't fail - the file was generated successfully
            import warnings
            warnings.warn(f"Failed to add type annotations to {schemas_file}: {e}")

    def _apply_strict_mode_from_openapi(self, schemas_file: Path, bundled_path: Path):
        """
        Replace `.passthrough()` with `.strict()` for Zod object schemas where the
        OpenAPI component schema has `additionalProperties: false`.

        Notes:
        - `openapi-zod-client` emits `.passthrough()` by default.
        - We enforce strictness only for schemas that are explicitly marked strict
          in OpenAPI to avoid breaking legacy schemas.
        """
        try:
            raw = Path(bundled_path).read_text(encoding="utf-8")
            spec = json.loads(raw)
            components = (spec or {}).get("components") or {}
            schemas = (components.get("schemas") or {})

            strict_schema_names: List[str] = []
            min_properties_by_name: dict[str, int] = {}
            for name, schema in schemas.items():
                if not isinstance(schema, dict):
                    continue
                if schema.get("additionalProperties") is False:
                    strict_schema_names.append(name)
                    if isinstance(schema.get("minProperties"), int):
                        min_properties_by_name[name] = int(schema["minProperties"])

            if not strict_schema_names:
                return

            import re
            content = schemas_file.read_text(encoding="utf-8")

            def _enforce_strict_on_const(ts: str, schema_name: str, min_props: int | None) -> str:
                """
                Ensure `const <schema_name> = z.object(...)[...].strict()[.refine(minProps)] ;`
                - If `.passthrough()` exists in the const expression, replace it with `.strict()`.
                - Else if `.strict()` is missing on the top-level schema expression, add it.
                - If OpenAPI specifies `minProperties`, append a `.refine(...)` enforcing it.
                """
                const_pattern = rf"(const\s+{re.escape(schema_name)}\s*=\s*)([\s\S]*?);"

                def _repl(match: re.Match) -> str:
                    prefix = match.group(1)
                    expr = match.group(2)
                    if not re.search(r"z\s*\.\s*object\(", expr):
                        return match.group(0)
                    # Strictness (top-level): avoid false positives from nested `.strict()` inside object properties.
                    tail = expr.rstrip()
                    if not re.search(r"\.strict\(\)\s*$", tail):
                        if re.search(r"\.passthrough\(\)\s*$", tail):
                            tail = re.sub(r"\.passthrough\(\)\s*$", ".strict()", tail, count=1)
                        elif ".superRefine(" in tail:
                            tail = tail.replace(".superRefine(", ".strict().superRefine(", 1)
                        elif ".refine(" in tail:
                            tail = tail.replace(".refine(", ".strict().refine(", 1)
                        else:
                            tail = f"{tail}.strict()"
                        expr = tail

                    # minProperties enforcement
                    if isinstance(min_props, int) and min_props > 0:
                        if ".refine(" not in expr and ".superRefine(" not in expr:
                            expr = (
                                f'{expr}.refine((v) => Object.keys(v).length >= {min_props}, '
                                f'{{ message: "At least {min_props} propert'
                                f'{"y" if min_props == 1 else "ies"} must be provided" }})'
                            )

                    return f"{prefix}{expr};"

                return re.sub(const_pattern, _repl, ts, count=1)

            for schema_name in strict_schema_names:
                content = _enforce_strict_on_const(content, schema_name, min_properties_by_name.get(schema_name))

            write_file(schemas_file, content)
        except Exception as e:
            import warnings
            warnings.warn(f"Failed to apply strict mode to {schemas_file}: {e}")
