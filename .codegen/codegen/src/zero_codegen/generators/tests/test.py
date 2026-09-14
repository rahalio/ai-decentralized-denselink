"""
Test Generator - Generates test utilities

Generates:
- Entity factories
- DTO factories
- Mock repositories
- Test setup files
- Faker helpers
- Index files
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations, extract_schemas, get_domain_prefix
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory, remove_stale_domain_dirs
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id


class TestGenerator(BaseGenerator):
    """
    Generates test utilities for domains

    Output structure:
    platform/tests/src/{domain}/
    ├── factories/
    │   ├── {resource}/
    │   │   ├── entity/{resource}.entity.factory.ts
    │   │   └── dto/{verb}-{resource}.dto.factory.ts
    │   ├── faker-helpers.ts
    │   └── shared/faker-helpers.ts
    ├── mocks/
    │   └── index.ts
    ├── __setup__/
    │   ├── vitest.setup.ts
    │   └── test-db.setup.ts
    ├── e2e/
    │   └── setup.ts
    └── index.ts
    """

    @property
    def name(self) -> str:
        return "Test Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "test"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate test utility files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory (clean when pipeline.clean to remove stale test factories)
        project_root = context.config.paths.project_root
        tests_src = project_root / "platform" / "tests" / "src"
        output_dir = tests_src / context.domain_name
        ensure_directory(output_dir)

        # Remove test dirs for domains no longer in config (e.g. publishing after removal)
        if not context.get_state("tests_stale_domains_cleaned"):
            enabled = {d.name for d in context.config.domains if d.enabled}
            for name in remove_stale_domain_dirs(tests_src, enabled, preserve={"_shared", "smoke"}):
                context.logger.info(f"Removed stale test domain: {name}")
            context.set_state("tests_stale_domains_cleaned", True)

        if context.config.pipeline.clean:
            clean_directory(output_dir)

        # Extract operations and schemas
        operations = extract_operations(context.spec)
        schemas_dict = extract_schemas(context.spec)

        # Expand with aliased operations so we generate factories for delegated ops
        operations = self._expand_operations_with_aliases(context, operations)

        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)

        # Group operations by resource
        resource_operations: Dict[str, List[Dict[str, Any]]] = {}
        for op_data in operations:
            operation_id = op_data["operation_id"]
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            if resource not in resource_operations:
                resource_operations[resource] = []
            resource_operations[resource].append(op_data)

        # Generate factories
        factory_files = self._generate_factories(context, output_dir, resource_operations, schemas_dict)
        files.extend(factory_files)

        # Mock repositories are not needed - we use shared createMockDependencies
        # mock_files = self._generate_mocks(context, output_dir, resource_operations, schemas_dict)
        # files.extend(mock_files)

        # Generate setup files
        setup_files = self._generate_setup_files(context, output_dir)
        files.extend(setup_files)

        # Generate index file with factory exports
        index_file = self._generate_index(context, output_dir, resource_operations)
        files.append(index_file)
        
        # Generate factories index file (barrel export for all factories)
        factories_index_file = self._generate_factories_index(context, output_dir, resource_operations)
        files.append(factories_index_file)

        # Generate test files for domain components (handlers, use cases, etc.)
        component_test_files = self._generate_component_tests(context, resource_operations)
        files.extend(component_test_files)

        context.logger.info(f"Generated {len(files)} test utility files for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _expand_operations_with_aliases(
        self, context: GenerationContext, operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add synthetic operations for aliased ops so we generate factories for them."""
        aliases = getattr(context.domain, "operation_aliases", None) or {}
        if not aliases:
            return operations

        op_by_id = {op["operation_id"]: op for op in operations}
        expanded = list(operations)
        for alias_op_id, alias_cfg in aliases.items():
            if alias_op_id in op_by_id:
                continue  # Already in spec
            delegate_to = getattr(alias_cfg, "delegate_to", None)
            if not delegate_to or delegate_to not in op_by_id:
                continue
            delegate_op = op_by_id[delegate_to]
            expanded.append({
                "operation_id": alias_op_id,
                "path": delegate_op.get("path", ""),
                "method": delegate_op.get("method", "GET"),
                "operation": delegate_op.get("operation", {}),
            })
        return expanded

    def _generate_factories(
        self,
        context: GenerationContext,
        output_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]],
        schemas_dict: Dict[str, Any]
    ) -> List[Path]:
        """Generate entity and DTO factories"""
        files: List[Path] = []
        project_root = context.config.paths.project_root
        factories_dir = output_dir / "factories"
        ensure_directory(factories_dir)

        # Skip generating faker helpers - now in shared location
        # Faker helpers are in platform/tests/src/_shared/factories/faker-helpers.ts

        # Generate factories for each resource
        for resource, ops in resource_operations.items():
            resource_kebab = kebab_case(resource)
            resource_pascal = pascal_case(resource)

            resource_factory_dir = factories_dir / resource_kebab
            ensure_directory(resource_factory_dir)

            # Only generate entity factory when the entity file exists in core
            entity_file = project_root / "packages" / "core" / "src" / context.domain_name / "models" / f"{resource_kebab}.entity.ts"
            entity_factory_file = resource_factory_dir / "entity" / f"{resource_kebab}.entity.factory.ts"
            if entity_file.exists():
                entity_dir = resource_factory_dir / "entity"
                ensure_directory(entity_dir)
                entity_content = self._generate_entity_factory(context, resource, resource_pascal, schemas_dict)
                write_file(entity_factory_file, entity_content)
                files.append(entity_factory_file)
            elif entity_factory_file.exists():
                # Remove orphaned entity factory (entity was removed from core)
                entity_factory_file.unlink()

            # Generate DTO factories for each operation
            dto_dir = resource_factory_dir / "dto"
            ensure_directory(dto_dir)
            generated_dto_names = set()

            for op_data in ops:
                operation_id = op_data["operation_id"]
                operation = op_data.get("operation", {})
                http_method = op_data.get("method", "").lower()
                verb = extract_verb_from_operation_id(operation_id, http_method)
                dto_factory_file = dto_dir / f"{verb}-{resource_kebab}.dto.factory.ts"
                dto_content = self._generate_dto_factory(context, resource, resource_pascal, verb, operation_id, schemas_dict, operation)
                if dto_content is not None:
                    write_file(dto_factory_file, dto_content)
                    files.append(dto_factory_file)
                    generated_dto_names.add(dto_factory_file.name)
                elif dto_factory_file.exists():
                    dto_factory_file.unlink()

            # Remove orphaned DTO factories (ops removed from OpenAPI)
            for path in dto_dir.iterdir():
                if path.is_file() and path.suffix == ".ts" and path.name not in generated_dto_names:
                    path.unlink()

        return files

    def _generate_mocks(
        self,
        context: GenerationContext,
        output_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]],
        schemas_dict: Dict[str, Any]
    ) -> List[Path]:
        """Generate mock repositories"""
        files: List[Path] = []
        mocks_dir = output_dir / "mocks"
        ensure_directory(mocks_dir)

        # Extract repository names from operations
        repositories = set()
        for ops in resource_operations.values():
            for op_data in ops:
                resource = NamingConvention.resource_for_grouping(
                    op_data["operation_id"], op_data.get("path")
                )
                repo_name = f"{pascal_case(resource)}Repository"
                repositories.add(repo_name)

        # Generate mocks index
        mocks_index_file = mocks_dir / "index.ts"
        mocks_content = self._generate_mocks_index(context, repositories)
        write_file(mocks_index_file, mocks_content)
        files.append(mocks_index_file)

        return files

    def _generate_setup_files(self, context: GenerationContext, output_dir: Path) -> List[Path]:
        """Generate test setup files"""
        files: List[Path] = []

        # Skip generating setup files - now in shared location
        # Setup files are in platform/tests/src/_shared/__setup__/ and platform/tests/src/_shared/e2e/
        # - vitest.setup.ts -> platform/tests/src/_shared/__setup__/vitest.setup.ts
        # - test-db.setup.ts -> platform/tests/src/_shared/__setup__/test-db.setup.ts
        # - e2e/setup.ts -> platform/tests/src/_shared/e2e/setup.ts

        return files

    def _generate_faker_value_for_field(
        self,
        field_name: str,
        field_type: Optional[str],
        field_props: Dict[str, Any],
        context: GenerationContext = None
    ) -> str:
        """Generate faker value for a field based on name and type"""
        field_name_lower = field_name.lower()
        
        # Email fields
        if "email" in field_name_lower:
            return "faker.internet.email()"
        
        # Name fields
        if field_name_lower in ["name", "displayname", "display_name"]:
            return "faker.person.fullName()"
        if field_name_lower in ["firstname", "first_name"]:
            return "faker.person.firstName()"
        if field_name_lower in ["lastname", "last_name"]:
            return "faker.person.lastName()"
        
        # URL fields
        if "url" in field_name_lower or "uri" in field_name_lower:
            return "faker.internet.url()"
        
        # Slug fields
        if "slug" in field_name_lower:
            return "faker.lorem.slug()"
        
        # Description fields
        if "description" in field_name_lower or "desc" in field_name_lower:
            return "faker.lorem.sentence()"
        
        # Title fields
        if "title" in field_name_lower:
            return "faker.lorem.sentence()"
        
        # Text/Content fields
        if field_name_lower in ["text", "content", "body", "message"]:
            return "faker.lorem.paragraph()"
        
        # Status/enum fields
        if field_name_lower == "status":
            # Check if it's an enum
            if "enum" in field_props:
                enum_values = field_props.get("enum", [])
                if enum_values:
                    # Use first enum value as default
                    return f'"{enum_values[0]}"'
            # Default status values for common enums
            return '"active"'
        
        # Enum fields (check for enum property)
        if "enum" in field_props:
            enum_values = field_props.get("enum", [])
            if enum_values:
                # Use first enum value as default
                return f'"{enum_values[0]}"'
        
        # ID fields (orgId, userId, connectionId, etc.) - but not the main "id" field
        if field_name_lower.endswith("id") and field_name_lower != "id":
            # Check if it has a regex pattern (e.g. ^con_, ^chn_, ^idt_)
            pattern = field_props.get("pattern", "")
            if pattern:
                import re
                # Multi-segment prefix e.g. ^soc_dlv_[0-9a-hjkmnp-tv-z]{26}$
                match = re.match(r'\^(.+?)_\[0-9a-hjkmnp-tv-z\]\{26\}\$', pattern)
                if match:
                    prefix = match.group(1) + "_"
                    return f'`{prefix}${{ulid().toLowerCase()}}`'
                # Single-segment prefix e.g. ^idt_ or ^con_[0-9a-hjkmnp-tv-z]{26}$
                match = re.match(r'\^([a-z]+)_', pattern)
                if match:
                    prefix = match.group(1)
                    return f'`{prefix}_${{ulid().toLowerCase()}}`'
            return "faker.string.uuid()"
        
        # Date fields
        if "date" in field_name_lower or "time" in field_name_lower:
            return "new Date().toISOString()"
        
        # Object types - must check before other types
        if field_type == "object" or field_props.get("type") == "object" or "properties" in field_props:
            # Check if it's a simple object with properties
            if "properties" in field_props:
                props = field_props.get("properties", {})
                # Generate a minimal object with default values for properties
                obj_fields = []
                for prop_name, prop_schema in props.items():
                    if isinstance(prop_schema, dict) and "$ref" in prop_schema and context and context.spec:
                        from ...utils.openapi import resolve_ref
                        resolved = resolve_ref(context.spec, prop_schema["$ref"])
                        if resolved:
                            prop_schema = resolved
                    # Only include properties with defaults or simple types
                    if isinstance(prop_schema, dict) and prop_schema.get("default") is not None:
                        default_val = prop_schema.get("default")
                        if isinstance(default_val, bool):
                            obj_fields.append(f'      {prop_name}: {str(default_val).lower()}')
                        elif isinstance(default_val, (int, float)):
                            obj_fields.append(f'      {prop_name}: {default_val}')
                        else:
                            obj_fields.append(f'      {prop_name}: "{default_val}"')
                    elif prop_schema.get("type") == "boolean":
                        obj_fields.append(f'      {prop_name}: false')
                    elif prop_schema.get("type") == "number":
                        obj_fields.append(f'      {prop_name}: 0')
                    elif prop_schema.get("type") == "string":
                        if "enum" in prop_schema and prop_schema.get("enum"):
                            obj_fields.append(f'      {prop_name}: "{prop_schema["enum"][0]}"')
                        elif prop_schema.get("format") in ("uri", "url"):
                            obj_fields.append(f'      {prop_name}: faker.internet.url()')
                        else:
                            obj_fields.append(f'      {prop_name}: ""')
                
                if obj_fields:
                    return "{\n" + ",\n".join(obj_fields) + "\n    }"
            # Default to empty object for complex objects (passthrough allows any properties)
            return "{}"
        
        # Boolean fields
        if field_type == "boolean" or field_props.get("type") == "boolean":
            return "faker.datatype.boolean()"
        
        # Number fields
        if field_type == "number" or field_type == "integer" or field_props.get("type") in ["number", "integer"]:
            if "limit" in field_name_lower or "count" in field_name_lower:
                return "faker.number.int({ min: 1, max: 100 })"
            return "faker.number.int()"
        
        # Array fields
        if field_type and field_type.endswith("[]") or field_props.get("type") == "array":
            return "[]"
        
        # String fields with format
        format_type = field_props.get("format", "")
        if format_type == "email":
            return "faker.internet.email()"
        if format_type == "uri" or format_type == "url":
            return "faker.internet.url()"
        if format_type == "date-time":
            return "new Date().toISOString()"
        if format_type == "date":
            return "faker.date.anytime().toISOString().split('T')[0]"
        
        # Default: string
        return f'faker.lorem.word()'

    def _generate_faker_helpers(self, context: GenerationContext) -> str:
        """Generate faker helpers file"""
        header = self.generate_header(context, "Faker Helpers for Deterministic Test Data")

        return f"""{header}/**
 * Faker Helpers
 *
 * Provides deterministic faker instance with seeding support.
 */

import {{ faker }} from "@faker-js/faker";

let fakerInstance: typeof faker | null = null;

/**
 * Seeds the faker instance for deterministic test data.
 *
 * @param seed - Seed value (default: 99999)
 */
export function seedFaker(seed: number = 99999): void {{
  faker.seed(seed);
  fakerInstance = faker;
}}

/**
 * Gets the seeded faker instance.
 * If not seeded, seeds with default value.
 *
 * @returns Faker instance
 */
export function getFaker(): typeof faker {{
  if (!fakerInstance) {{
    seedFaker();
  }}
  return fakerInstance!;
}}
"""

    def _generate_entity_factory(
        self,
        context: GenerationContext,
        resource: str,
        resource_pascal: str,
        schemas_dict: Dict[str, Any]
    ) -> str:
        """Generate entity factory"""
        header = self.generate_header(context, f"{resource_pascal} Entity Factory")
        resource_kebab = kebab_case(resource)
        domain_pascal = pascal_case(context.domain_name)

        # Try to find the correct schema name by reading the entity file
        entity_schema_name = self._find_entity_schema_name(context, resource, resource_pascal, schemas_dict)

        # Extract required fields from the entity schema (resolve $ref if needed)
        entity_schema = schemas_dict.get(entity_schema_name, {})
        if entity_schema and "$ref" in entity_schema:
            from ...utils.openapi import resolve_ref
            resolved = resolve_ref(context.spec, entity_schema["$ref"])
            if resolved:
                entity_schema = resolved
        from ...utils.schema_field_extractor import SchemaFieldExtractor
        required_fields = SchemaFieldExtractor.extract_required_fields(entity_schema, context.spec)
        
        # Generate default values for required fields (excluding id, createdAt, updatedAt which we handle separately)
        default_values = []
        for field_name in sorted(required_fields):
            if field_name in ["id", "createdAt", "updatedAt"]:
                continue
            
            # Get field type to generate appropriate faker value
            field_type = SchemaFieldExtractor.extract_field_type(entity_schema, field_name, context.spec)
            field_props = entity_schema.get("properties", {}).get(field_name, {})
            
            # Resolve $ref if present
            if "$ref" in field_props:
                from ...utils.openapi import resolve_ref
                resolved = resolve_ref(context.spec, field_props["$ref"])
                if resolved:
                    field_props = resolved
            
            # Generate faker value based on field name and type
            faker_value = self._generate_faker_value_for_field(field_name, field_type, field_props, context)
            default_values.append(f"    {field_name}: overrides.{field_name} ?? {faker_value},")
        
        default_values_str = "\n".join(default_values) + "\n" if default_values else ""

        # Extract domain prefix from OpenAPI spec (info.x-domain or info.x-domain-prefix)
        domain_prefix = get_domain_prefix(context.spec, context.domain_name)
        domain_prefix_str = f'"{domain_prefix}"' if domain_prefix else '""'
        
        # Check if id field has a pattern that requires a specific prefix (e.g. idt_, soc_dlv_)
        id_prefix = ""
        id_field_props = entity_schema.get("properties", {}).get("id", {})
        if id_field_props and "$ref" in id_field_props:
            from ...utils.openapi import resolve_ref
            resolved = resolve_ref(context.spec, id_field_props["$ref"])
            if resolved:
                id_field_props = resolved
        if id_field_props and "pattern" in id_field_props:
            pattern = id_field_props["pattern"]
            import re
            # Match ^prefix_[0-9a-hjkmnp-tv-z]{26}$ to support single (idt_) and multi-segment (soc_dlv_) prefixes
            match = re.match(r'\^(.+?)_\[0-9a-hjkmnp-tv-z\]\{26\}\$', pattern)
            if match:
                id_prefix = match.group(1) + "_"
            else:
                # Fallback: single segment like ^idt_
                match = re.match(r'\^([a-z]+)_', pattern)
                if match:
                    id_prefix = match.group(1) + "_"
        # Generate ID format based on pattern
        if id_prefix:
            id_generation = f'`{id_prefix}${{ulid().toLowerCase()}}`'
        else:
            id_generation = f'`${{DOMAIN_PREFIX}}_${{ulid().toLowerCase()}}`'
        
        # Check if faker is needed (if any default values use faker)
        needs_faker = any("faker." in val for val in default_values) if default_values else False
        
        # Generate imports
        imports = []
        if needs_faker:
            imports.append('import { faker } from "@faker-js/faker";')
        imports.append(f'import type {{ {resource_pascal}Entity }} from "@ddd/core/{context.domain_name}/models/index.js";')
        domain_schemas_name = f"{camel_case(context.domain_name)}Schemas"  # e.g., activitySchemas
        imports.append(f'import {{ {domain_schemas_name} }} from "@ddd/core/{context.domain_name}";')
        imports.append('import { ulid } from "ulid";')
        imports_str = "\n".join(imports)
        
        return f"""{header}
{imports_str}

// Domain prefix from OpenAPI spec info.x-domain
const DOMAIN_PREFIX = {domain_prefix_str};

export function create{resource_pascal}(overrides: Partial<{resource_pascal}Entity> = {{}}) {{
  const raw = {{
    id: overrides.id ?? {id_generation},
    createdAt: overrides.createdAt ?? new Date().toISOString(),
    updatedAt: overrides.updatedAt ?? new Date().toISOString(),
{default_values_str}    ...overrides,
  }};

  return {domain_schemas_name}.{entity_schema_name}.parse(raw);
}}

export function {camel_case(resource)}Batch(n = 3, overrides = {{}}) {{
  return Array.from({{ length: n }}, () => create{resource_pascal}(overrides));
}}
"""

    def _find_entity_schema_name(
        self,
        context: GenerationContext,
        resource: str,
        resource_pascal: str,
        schemas_dict: Dict[str, Any]
    ) -> str:
        """Find the correct schema name for an entity by reading the entity file"""
        resource_kebab = kebab_case(resource)
        project_root = context.config.paths.project_root
        entity_file = project_root / "packages" / "core" / "src" / context.domain_name / "models" / f"{resource_kebab}.entity.ts"
        
        # Try to read the entity file to find the schema name (trust core export over spec dict)
        if entity_file.exists():
            try:
                with open(entity_file, "r") as f:
                    content = f.read()
                import re
                # Prefer the assignment line (EntitySchema = schemas.X) so we don't match "schemas.js" from import path
                assign_match = re.search(r'Schema\s*=\s*schemas\.(\w+)', content)
                if assign_match:
                    schema_name = assign_match.group(1)
                    if schema_name != "js" and (schema_name in schemas_dict or schema_name[0:1].isupper()):
                        return schema_name
                # Else look for schemas.SchemaName but exclude path artifacts (e.g. "js" from .schemas.js)
                matches = re.findall(r'schemas\.(\w+)', content)
                for name in matches:
                    if name != "js" and (name in schemas_dict or (len(name) > 1 and name[0:1].isupper())):
                        return name
            except Exception:
                pass  # Fall through to default patterns
        
        # Fallback: try common patterns
        patterns = [
            f"{resource_pascal}Entity",
            resource_pascal,
            f"{resource_pascal}Settings",
            f"{resource_pascal}Config",
        ]
        
        # Domain-specific fallbacks
        if context.domain_name == "identity":
            if resource_pascal == "Org":
                patterns.insert(0, "User")
            elif resource_pascal in ["UserOnboarding", "OrgOnboarding"]:
                patterns.insert(0, "OnboardingStatus")
            elif resource_pascal in ["UserOnboardingStep", "OrgOnboardingStep"]:
                patterns.insert(0, "OnboardingStep")
            elif resource_pascal == "AuthSession":
                patterns.insert(0, "LoginPayload")
            elif resource_pascal == "AuthSignup":
                patterns.insert(0, "SignUpPayload")
            elif resource_pascal == "SSOSetting":
                patterns.insert(0, "SSOSettings")
            elif resource_pascal == "SSOProvider":
                patterns.insert(0, "SSOProvider")
        elif context.domain_name == "ai":
            # AI domain entities that use Model schema
            if resource_pascal in ["UsageByModel", "UsageByProvider", "Model"]:
                patterns.insert(0, "Model")
            # AI domain entities that use specific schemas
            elif resource_pascal == "AIModel":
                patterns.insert(0, "AIBaseModel")
            elif resource_pascal == "AIGateway":
                patterns.insert(0, "AIGateway")
            elif resource_pascal == "AIProvider":
                patterns.insert(0, "AIProvider")
            elif resource_pascal == "Prompt":
                patterns.insert(0, "PromptTemplate")
            elif resource_pascal == "Rerank":
                patterns.insert(0, "RerankResult")
            elif resource_pascal == "Usage":
                patterns.insert(0, "UsageResponse")
        elif context.domain_name == "social":
            # Social domain: Account entity uses OrgChannel (see account.entity.ts)
            if resource_pascal == "Account":
                patterns.insert(0, "OrgChannel")
            # Channel, Provider, etc. use PlatformProvider in core
            elif resource_pascal in ["Channel", "ChannelAccount"]:
                patterns.insert(0, "PlatformProvider")
            elif resource_pascal == "ProviderCatalog":
                patterns.insert(0, "ProviderType")
            elif resource_pascal == "Provider":
                patterns.insert(0, "PlatformProvider")
            elif resource_pascal == "ProviderWebhook":
                patterns.insert(0, "PlatformProvider")
        
        for pattern in patterns:
            if pattern in schemas_dict:
                return pattern
        
        # Last resort: return the first pattern (will fail at runtime but at least compiles)
        return patterns[0]

    def _get_dto_field_props(
        self,
        dto_schema: Dict[str, Any],
        field_name: str,
        context: GenerationContext
    ) -> Dict[str, Any]:
        """Get field properties from a DTO schema, resolving allOf so properties inside allOf are found."""
        if not dto_schema:
            return {}
        schema = dto_schema
        if "$ref" in schema:
            from ...utils.openapi import resolve_ref
            resolved = resolve_ref(context.spec, schema["$ref"])
            if resolved:
                return self._get_dto_field_props(resolved, field_name, context)
            return {}
        if "allOf" in schema:
            for sub in schema["allOf"]:
                props = self._get_dto_field_props(sub, field_name, context)
                if props:
                    return props
            return {}
        return schema.get("properties", {}).get(field_name, {})

    def _generate_dto_factory(
        self,
        context: GenerationContext,
        resource: str,
        resource_pascal: str,
        verb: str,
        operation_id: str,
        schemas_dict: Dict[str, Any],
        operation: Dict[str, Any] = None
    ) -> str:
        """Generate DTO factory"""
        header = self.generate_header(context, f"{pascal_case(verb)}{resource_pascal} DTO Factory")
        resource_kebab = kebab_case(resource)
        domain_pascal = pascal_case(context.domain_name)
        verb_pascal = pascal_case(verb)

        # Use get_input_schema_or_type_name - single source of truth (no speculative fallbacks)
        # For aliased ops, use delegate's operation_id so we get the correct Params type
        dto_schema_name = None
        is_params_type = False
        if operation:
            from ...utils.openapi import get_input_schema_or_type_name
            aliases = getattr(context.domain, "operation_aliases", None) or {}
            alias_cfg = aliases.get(operation_id)
            effective_op_id = operation_id
            if alias_cfg:
                effective_op_id = getattr(alias_cfg, "delegate_to", None) or (alias_cfg.get("delegateTo") if isinstance(alias_cfg, dict) else None) or operation_id
            input_type_name = get_input_schema_or_type_name(
                operation, context.spec, effective_op_id, getattr(context, "unbundled_spec", None)
            )
            if input_type_name:
                # Schema validation: request body schemas must exist in OpenAPI
                if input_type_name in schemas_dict:
                    dto_schema_name = input_type_name
                # Params types: emitted by types builder, no Zod schema
                elif input_type_name.endswith("Params"):
                    dto_schema_name = input_type_name
                    is_params_type = True

        # Skip factory if no valid input type (per recommendation: no speculative fallbacks)
        if not dto_schema_name:
            return None

        # Extract required fields (request body schemas have Zod; Params are type-only)
        dto_schema = schemas_dict.get(dto_schema_name, {}) if not is_params_type else {}
        if dto_schema and "$ref" in dto_schema:
            from ...utils.openapi import resolve_ref
            resolved = resolve_ref(context.spec, dto_schema["$ref"])
            if resolved:
                dto_schema = resolved
        from ...utils.schema_field_extractor import SchemaFieldExtractor
        required_fields = SchemaFieldExtractor.extract_required_fields(dto_schema, context.spec)
        
        # Generate default values for required fields
        default_values = []
        for field_name in sorted(required_fields):
            if field_name == "id":
                continue  # Skip id, we handle it separately
            
            # Get field type to generate appropriate faker value
            field_type = SchemaFieldExtractor.extract_field_type(dto_schema, field_name, context.spec)
            field_props = self._get_dto_field_props(dto_schema, field_name, context)
            
            # Resolve $ref if present
            if field_props and "$ref" in field_props:
                from ...utils.openapi import resolve_ref
                resolved = resolve_ref(context.spec, field_props["$ref"])
                if resolved:
                    field_props = resolved
            
            # Generate faker value based on field name and type
            faker_value = self._generate_faker_value_for_field(field_name, field_type, field_props, context)
            default_values.append(f"    {field_name}: overrides.{field_name} ?? {faker_value},")
        
        default_values_str = "\n".join(default_values) + "\n" if default_values else ""

        # Extract domain prefix from OpenAPI spec (info.x-domain or info.x-domain-prefix)
        domain_prefix = get_domain_prefix(context.spec, context.domain_name)
        domain_prefix_str = f'"{domain_prefix}"' if domain_prefix else '""'
        
        # Check if faker is needed (if any default values use faker)
        needs_faker = any("faker." in val for val in default_values) if default_values else False
        # Check if ulid is needed (if any default values use ulid)
        needs_ulid = any("ulid()" in val for val in default_values) if default_values else False
        
        # Generate imports
        imports = []
        if needs_faker:
            imports.append('import { faker } from "@faker-js/faker";')
        if needs_ulid:
            imports.append('import { ulid } from "ulid";')
        domain_schemas_name = f"{camel_case(context.domain_name)}Schemas"
        if is_params_type:
            imports.append(f'import type {{ {dto_schema_name} }} from "@ddd/core/{context.domain_name}";')
            type_annotation = dto_schema_name
            return_stmt = "return raw;"
        elif dto_schema_name and dto_schema_name in schemas_dict:
            imports.append(f'import type {{ {dto_schema_name} }} from "@ddd/core/{context.domain_name}";')
            imports.append(f'import {{ {domain_schemas_name} }} from "@ddd/core/{context.domain_name}";')
            type_annotation = dto_schema_name
            return_stmt = f"return {domain_schemas_name}.{dto_schema_name}.parse(raw);"
        else:
            type_annotation = "Record<string, unknown>"
            return_stmt = "return raw;"
        imports_str = "\n".join(imports)
        
        domain_prefix_comment = f"\n// Domain prefix from OpenAPI spec info.x-domain\nconst DOMAIN_PREFIX = {domain_prefix_str};" if needs_ulid else ""
        
        return f"""{header}
{imports_str}{domain_prefix_comment}

export function create{verb_pascal}{resource_pascal}Request(overrides: Partial<{type_annotation}> = {{}}) {{
  const raw = {{
{default_values_str}    ...overrides,
  }};

  {return_stmt}
}}
"""

    def _generate_mocks_index(
        self,
        context: GenerationContext,
        repositories: set
    ) -> str:
        """Generate mocks index file"""
        header = self.generate_header(context, "Mock Repositories for Testing")
        domain_pascal = pascal_case(context.domain_name)

        # Generate mock class declarations
        mock_classes = []
        for repo_name in sorted(repositories):
            mock_name = f"Mock{repo_name}"
            mock_classes.append(f"export class {mock_name} implements {repo_name} {{")
            mock_classes.append(f"  private {camel_case(repo_name.replace('Repository', ''))}s: any[] = [];")
            mock_classes.append(f"  private idCounter = 1;")
            mock_classes.append("")
            mock_classes.append("  reset(): void {")
            mock_classes.append(f"    this.{camel_case(repo_name.replace('Repository', ''))}s = [];")
            mock_classes.append("    this.idCounter = 1;")
            mock_classes.append("  }")
            mock_classes.append("")
            mock_classes.append(f"  async list(orgId: string, params?: any): Promise<any> {{")
            mock_classes.append(f"    let items = this.{camel_case(repo_name.replace('Repository', ''))}s.filter((item) => item.orgId === orgId);")
            mock_classes.append("    const limit = params?.limit ?? 50;")
            mock_classes.append("    if (limit) {")
            mock_classes.append("      items = items.slice(0, limit);")
            mock_classes.append("    }")
            mock_classes.append("    return {")
            mock_classes.append("      items,")
            mock_classes.append("      nextCursor: items.length === limit ? items[items.length - 1]?.id : undefined,")
            mock_classes.append("      prevCursor: undefined,")
            mock_classes.append("    };")
            mock_classes.append("  }")
            mock_classes.append("")
            mock_classes.append(f"  async findById(orgId: string, id: string): Promise<any | null> {{")
            mock_classes.append(f"    return this.{camel_case(repo_name.replace('Repository', ''))}s.find((item) => item.id === id && item.orgId === orgId) || null;")
            mock_classes.append("  }")
            mock_classes.append("")
            mock_classes.append(f"  async get(orgId: string, id: string): Promise<any | null> {{")
            mock_classes.append("    return this.findById(orgId, id);")
            mock_classes.append("  }")
            mock_classes.append("")
            mock_classes.append(f"  async create(orgId: string, data: any): Promise<any> {{")
            mock_classes.append(f"    const newItem = {{ ...data, id: data.id ?? `${{this.idCounter++}}`, orgId }};")
            mock_classes.append(f"    this.{camel_case(repo_name.replace('Repository', ''))}s.push(newItem);")
            mock_classes.append("    return newItem;")
            mock_classes.append("  }")
            mock_classes.append("")
            mock_classes.append(f"  async update(orgId: string, id: string, data: Partial<any>): Promise<any> {{")
            mock_classes.append(f"    const index = this.{camel_case(repo_name.replace('Repository', ''))}s.findIndex((item) => item.id === id && item.orgId === orgId);")
            mock_classes.append("    if (index === -1) {")
            mock_classes.append("      throw new Error(`Item not found: ${{id}}`);")
            mock_classes.append("    }")
            mock_classes.append(f"    this.{camel_case(repo_name.replace('Repository', ''))}s[index] = {{ ...this.{camel_case(repo_name.replace('Repository', ''))}s[index], ...data }};")
            mock_classes.append(f"    return this.{camel_case(repo_name.replace('Repository', ''))}s[index];")
            mock_classes.append("  }")
            mock_classes.append("")
            mock_classes.append(f"  async delete(orgId: string, id: string): Promise<void> {{")
            mock_classes.append(f"    const index = this.{camel_case(repo_name.replace('Repository', ''))}s.findIndex((item) => item.id === id && item.orgId === orgId);")
            mock_classes.append("    if (index !== -1) {")
            mock_classes.append(f"      this.{camel_case(repo_name.replace('Repository', ''))}s.splice(index, 1);")
            mock_classes.append("    }")
            mock_classes.append("  }")
            mock_classes.append("}")
            mock_classes.append("")

        # Generate imports
        repo_imports = ", ".join(sorted(repositories))

        return f"""{header}
import type {{
  {repo_imports}
}} from "@ddd/core/{context.domain_name}/repositories/index.js";
import type {{
  PaginationParams,
  PaginatedResult,
}} from "@ddd/core/_shared/index.js";

{chr(10).join(mock_classes)}
"""

    def _generate_vitest_setup(self, context: GenerationContext) -> str:
        """Generate vitest setup file"""
        header = self.generate_header(context, "Vitest global setup")

        return f"""{header}
/**
 * Vitest Global Setup
 *
 * Configures test environment with:
 * - DynamoDB Local connection
 * - Frozen time
 * - Seeded faker
 * - Baseline data
 */

import {{ beforeAll, afterAll, beforeEach, afterEach, vi }} from "vitest";
import {{ startTestDb, stopTestDb, getDynamoClient }} from "./test-db.setup.js";

// Set required environment variables
process.env.TZ = "UTC";
process.env.TEST_FIXED_DATE = "2025-01-01T00:00:00Z";
process.env.TEST_FAKER_SEED = "12345";

/**
 * Global setup - runs once per worker
 */
beforeAll(async () => {{
  console.log("🚀 Starting test environment...");

  // Connect to DynamoDB Local (assumes it's already running via docker-compose)
  const client = await startTestDb();

  // Make DynamoDB client available globally
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).dynamoClient = client;

  console.log("✅ Test environment ready");
}}, 10000); // 10s timeout

/**
 * Global teardown - runs once per worker
 */
afterAll(async () => {{
  await stopTestDb();
}});

/**
 * Per-test setup
 */
beforeEach(() => {{
  // ⚠️ DO NOT use fake timers globally - breaks Fastify async operations!
  // Tests that need frozen time should opt-in explicitly with:
  //   vi.useFakeTimers(); vi.setSystemTime(new Date("2025-01-01"));
}});

/**
 * Per-test teardown
 */
afterEach(() => {{
  // Ensure real timers are restored (in case test used fake timers)
  vi.useRealTimers();
}});
"""

    def _generate_test_db_setup(self, context: GenerationContext) -> str:
        """Generate test database setup file for DynamoDB"""
        header = self.generate_header(context, "Test database setup")

        return f"""{header}
/**
 * Test Database Setup
 *
 * Manages DynamoDB Local for integration/E2E tests
 * 
 * DynamoDB Local should be started via docker-compose before running tests:
 *   docker-compose up -d dynamodb-local
 * 
 * Or use the helper script:
 *   ./scripts/dynamodb-start.sh
 */

import {{ DynamoDBClient }} from "@aws-sdk/client-dynamodb";

let dynamoClient: DynamoDBClient | null = null;

/**
 * Get DynamoDB client instance
 */
export function getDynamoClient(): DynamoDBClient {{
  if (!dynamoClient) {{
    throw new Error("DynamoDB client not initialized. Call startTestDb() first.");
  }}
  return dynamoClient;
}}

/**
 * Start test database (DynamoDB Local)
 * 
 * Assumes DynamoDB Local is already running via docker-compose.
 * Sets up environment variables and creates DynamoDB client.
 */
export async function startTestDb(): Promise<DynamoDBClient> {{
  if (dynamoClient) {{
    return getDynamoClient();
  }}

  console.log("🚀 Connecting to DynamoDB Local...");

  // Set DynamoDB Local endpoint if not already set
  const endpoint = process.env.AWS_ENDPOINT_URL || "http://localhost:8000";
  const region = process.env.AWS_REGION || "us-east-1";
  
  // Set default credentials if not provided
  if (!process.env.AWS_ACCESS_KEY_ID) {{
    process.env.AWS_ACCESS_KEY_ID = "test";
  }}
  if (!process.env.AWS_SECRET_ACCESS_KEY) {{
    process.env.AWS_SECRET_ACCESS_KEY = "test";
  }}

  // Set table names if not already set
  if (!process.env.TABLE_NAME && !process.env.DYNAMODB_CORE_TABLE_NAME) {{
    process.env.TABLE_NAME = "ddd-codegen-starter-core-test";
    process.env.DYNAMODB_CORE_TABLE_NAME = "ddd-codegen-starter-core-test";
  }}
  if (!process.env.BASE_TABLE_NAME && !process.env.DYNAMODB_BASE_TABLE_NAME) {{
    process.env.BASE_TABLE_NAME = "ddd-codegen-starter-base-test";
    process.env.DYNAMODB_BASE_TABLE_NAME = "ddd-codegen-starter-base-test";
  }}
  if (!process.env.ANALYTICS_TABLE_NAME && !process.env.DYNAMODB_ANALYTICS_TABLE_NAME) {{
    process.env.ANALYTICS_TABLE_NAME = "ddd-codegen-starter-analytics-test";
    process.env.DYNAMODB_ANALYTICS_TABLE_NAME = "ddd-codegen-starter-analytics-test";
  }}

  // Initialize DynamoDB client
  dynamoClient = new DynamoDBClient({{
    endpoint,
    region,
    credentials: {{
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    }},
  }});

  console.log("✅ DynamoDB Local ready");
  console.log(`   Endpoint: ${{endpoint}}`);
  console.log(`   Core Table: ${{process.env.TABLE_NAME || process.env.DYNAMODB_CORE_TABLE_NAME}}`);

  return dynamoClient;
}}

/**
 * Stop test database (cleanup DynamoDB client)
 */
export async function stopTestDb(): Promise<void> {{
  if (dynamoClient) {{
    dynamoClient.destroy();
    dynamoClient = null;
    console.log("🛑 DynamoDB client stopped");
  }}
}}
"""

    def _generate_e2e_setup(self, context: GenerationContext) -> str:
        """Generate E2E test setup file"""
        header = self.generate_header(context, "E2E test setup")
        domain_pascal = pascal_case(context.domain_name)

        return f"""{header}
/**
 * E2E Test Setup - Shared Configuration and Utilities
 */

import jwt from "jsonwebtoken";

// Test Configuration
export const TEST_JWT_SECRET = "test-secret-key-for-e2e-testing";
// Test IDs - using identity domain prefix (ID_) as these are org/account IDs
// These are generic test constants, not domain-specific
export const TEST_ORG_ID = "idt_01hqzx3k8pqrs7vn6m9tw1abjz"; // Identity domain format
export const TEST_ACCOUNT_ID = "idt_01hqzx3k8pqrs7vn6m9tw1abjz"; // Identity domain format
export const TEST_USER_EMAIL = "test@example.com";

// Set JWT_SECRET for auth middleware
process.env.JWT_SECRET = TEST_JWT_SECRET;

/**
 * Generate a valid JWT token for testing
 */
export function generateAuthToken(
  orgId: string = TEST_ORG_ID,
  email: string = TEST_USER_EMAIL
): string {{
  return jwt.sign(
    {{
      accountId: TEST_ACCOUNT_ID,
      orgIds: [orgId],
      email,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600,
    }},
    TEST_JWT_SECRET
  );
}}

/**
 * Helper to parse JSON response
 */
export function parseJsonResponse(body: string) {{
  try {{
    return JSON.parse(body);
  }} catch {{
    return null;
  }}
}}
"""

    def _generate_index(
        self, 
        context: GenerationContext, 
        output_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]] = None
    ) -> Path:
        """Generate test utilities index file with factory barrel exports"""
        header = self.generate_header(context, "Test utilities barrel export")
        domain_pascal = pascal_case(context.domain_name)

        index_file = output_dir / "index.ts"
        
        # Generate factory exports if resource operations provided
        factory_exports = []
        project_root = context.config.paths.project_root
        if resource_operations:
            for resource, ops in resource_operations.items():
                resource_kebab = kebab_case(resource)
                resource_pascal = pascal_case(resource)
                entity_file = project_root / "packages" / "core" / "src" / context.domain_name / "models" / f"{resource_kebab}.entity.ts"
                if entity_file.exists():
                    factory_exports.append(f'export {{ create{resource_pascal} }} from "./factories/{resource_kebab}/entity/{resource_kebab}.entity.factory.js";')
                
                # Export DTO factories for each operation
                for op_data in ops:
                    operation_id = op_data["operation_id"]
                    operation = op_data.get("operation", {})
                    http_method = op_data.get("method", "").lower()
                    verb = extract_verb_from_operation_id(operation_id, http_method)
                    
                    if verb in ["create", "update", "patch"]:
                        verb_pascal = pascal_case(verb)
                        dto_factory_name = f"create{verb_pascal}{resource_pascal}Request"
                        factory_exports.append(f'export {{ {dto_factory_name} }} from "./factories/{resource_kebab}/dto/{verb}-{resource_kebab}.dto.factory.js";')
        
        factory_exports_str = "\n".join(sorted(set(factory_exports))) if factory_exports else ""
        index_content = f"""{header}
/**
 * {domain_pascal} Service Test Utilities
 *
 * Barrel export for factories, mock repositories, and test helpers.
 * Import these in {domain_pascal.lower()} service tests for consistent mocking.
 */

// Factories (entity and DTO factories) - use barrel export
{f"export * from \"./factories/index.js\";" if factory_exports_str else "// No factories generated"}

// Mock repositories are not needed - use createMockDependencies from @ddd/tests/shared
// export * from "./mocks/index.js";

// Test setup helpers (now in shared, but keeping for backward compatibility)
export {{
  TEST_JWT_SECRET,
  TEST_ORG_ID,
  TEST_ACCOUNT_ID,
  TEST_USER_EMAIL,
  generateAuthToken,
  parseJsonResponse,
}} from "@ddd/tests/shared";
"""
        write_file(index_file, index_content)
        return index_file

    def _generate_factories_index(
        self,
        context: GenerationContext,
        output_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> Path:
        """Generate factories index file (barrel export for all factories)"""
        header = self.generate_header(context, "Factories barrel export")
        factories_dir = output_dir / "factories"
        ensure_directory(factories_dir)
        project_root = context.config.paths.project_root
        
        factory_exports = []
        for resource, ops in resource_operations.items():
            resource_kebab = kebab_case(resource)
            resource_pascal = pascal_case(resource)
            entity_file = project_root / "packages" / "core" / "src" / context.domain_name / "models" / f"{resource_kebab}.entity.ts"
            entity_factory_path = factories_dir / resource_kebab / "entity" / f"{resource_kebab}.entity.factory.ts"
            if entity_file.exists() and entity_factory_path.exists():
                factory_exports.append(f'export {{ create{resource_pascal} }} from "./{resource_kebab}/entity/{resource_kebab}.entity.factory.js";')
            
            # Export DTO factories for each operation
            for op_data in ops:
                operation_id = op_data["operation_id"]
                operation = op_data.get("operation", {})
                http_method = op_data.get("method", "").lower()
                verb = extract_verb_from_operation_id(operation_id, http_method)
                
                if verb in ["create", "update", "patch"]:
                    verb_pascal = pascal_case(verb)
                    dto_factory_name = f"create{verb_pascal}{resource_pascal}Request"
                    dto_factory_path = factories_dir / resource_kebab / "dto" / f"{verb}-{resource_kebab}.dto.factory.ts"
                    if dto_factory_path.exists():
                        factory_exports.append(f'export {{ {dto_factory_name} }} from "./{resource_kebab}/dto/{verb}-{resource_kebab}.dto.factory.js";')
        
        factories_index_file = factories_dir / "index.ts"
        factory_exports_sorted = sorted(set(factory_exports))
        factories_index_content = f"""{header}
/**
 * Factories Barrel Export
 *
 * Exports all entity and DTO factories for the {context.domain_name} domain.
 * Use these factories in tests to create test data.
 */

{chr(10).join(factory_exports_sorted) if factory_exports_sorted else "// No factories generated"}
"""
        write_file(factories_index_file, factories_index_content)
        return factories_index_file

    def _generate_component_tests(
        self,
        context: GenerationContext,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> List[Path]:
        """Generate test files for handlers, use cases, and other domain components"""
        files: List[Path] = []
        project_root = context.config.paths.project_root
        tests_dir = project_root / "platform" / "tests" / "src" / context.domain_name
        api_server_dir = project_root / "platform" / "api-server" / "src" / "domains" / context.domain_name
        services_dir = project_root / "platform" / "services" / "src" / context.domain_name

        # Generate handler tests (in tests directory, referencing api-server)
        handler_test_files = self._generate_handler_tests(context, tests_dir, api_server_dir, resource_operations)
        files.extend(handler_test_files)

        # Generate use case tests (in tests directory, referencing services)
        usecase_test_files = self._generate_usecase_tests(context, tests_dir, services_dir, resource_operations)
        files.extend(usecase_test_files)

        # Generate index.ts files for test directories
        if handler_test_files:
            handlers_index_file = tests_dir / "handlers" / "index.ts"
            handlers_index_content = self._generate_handlers_test_index(context, resource_operations)
            write_file(handlers_index_file, handlers_index_content)
            files.append(handlers_index_file)

        if usecase_test_files:
            usecases_index_file = tests_dir / "usecases" / "index.ts"
            usecases_index_content = self._generate_usecases_test_index(context, resource_operations)
            write_file(usecases_index_file, usecases_index_content)
            files.append(usecases_index_file)

        return files

    def _generate_handler_tests(
        self,
        context: GenerationContext,
        tests_dir: Path,
        api_server_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> List[Path]:
        """Generate test files for handlers (api-server layer)"""
        files: List[Path] = []
        project_root = context.config.paths.project_root
        handlers_dir = api_server_dir / "handlers"
        tests_handlers_dir = tests_dir / "handlers"

        if not handlers_dir.exists():
            return files

        ensure_directory(tests_handlers_dir)

        # Generate use case lists for handlers (handler factories are now in shared location)
        use_case_list_files = self._generate_handler_use_case_lists(context, tests_dir, resource_operations)
        files.extend(use_case_list_files)

        # Group operations by resource
        for resource, ops in resource_operations.items():
            resource_kebab = kebab_case(resource)
            handler_file = handlers_dir / f"{resource_kebab}.handlers.ts"
            resource_tests_dir = tests_handlers_dir / resource_kebab

            # Only generate tests if handler file exists
            if not handler_file.exists():
                continue

            ensure_directory(resource_tests_dir)

            test_filenames = []
            factories_dir = tests_dir / "factories"
            # Generate test file for each handler in the resource file
            entity_file = project_root / "packages" / "core" / "src" / context.domain_name / "models" / f"{resource_kebab}.entity.ts"
            has_entity_factory = entity_file.exists()
            for op_data in ops:
                operation_id = op_data["operation_id"]
                handler_name = camel_case(operation_id)
                handler_kebab = kebab_case(handler_name)
                verb = extract_verb_from_operation_id(operation_id, http_method=op_data.get("method", "").lower())
                dto_factory_path = factories_dir / resource_kebab / "dto" / f"{verb}-{resource_kebab}.dto.factory.ts"
                has_dto_factory = verb in ["create", "update", "patch"] and dto_factory_path.exists()
                test_filename = f"{handler_kebab}.handler.test.ts"
                test_file = resource_tests_dir / test_filename
                test_content = self._generate_handler_test_content(
                    context, operation_id, handler_name, resource, op_data, api_server_dir, has_entity_factory, has_dto_factory
                )
                write_file(test_file, test_content)
                files.append(test_file)
                test_filenames.append(test_filename)

            # Generate index.ts for resource test directory
            if test_filenames:
                resource_test_index_file = resource_tests_dir / "index.ts"
                resource_test_index_content = self._generate_resource_handler_test_index(context, test_filenames)
                write_file(resource_test_index_file, resource_test_index_content)
                files.append(resource_test_index_file)

        return files

    def _generate_handler_use_case_lists(
        self,
        context: GenerationContext,
        tests_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> List[Path]:
        """Generate use case lists for handlers (handler factories are now in shared location)"""
        files: List[Path] = []
        factories_dir = tests_dir / "handlers" / "__factories__"
        ensure_directory(factories_dir)

        # Extract all use case names from operations
        use_case_names = set()
        for ops in resource_operations.values():
            for op_data in ops:
                operation_id = op_data["operation_id"]
                use_case_name = f"Execute{pascal_case(operation_id)}"
                use_case_var = camel_case(use_case_name)
                use_case_names.add(use_case_var)

        # Generate use case list file
        use_case_list_file = factories_dir / "use-cases.ts"
        use_case_list_content = self._generate_use_case_list_content(context, sorted(use_case_names))
        write_file(use_case_list_file, use_case_list_content)
        files.append(use_case_list_file)

        return files

    def _generate_use_case_list_content(
        self,
        context: GenerationContext,
        use_case_names: List[str]
    ) -> str:
        """Generate use case list content"""
        header = self.generate_header(context, "Use Case List")
        domain_pascal = pascal_case(context.domain_name)
        
        # Generate use case names list
        use_case_names_str = ",\n  ".join([f'"{name}"' for name in use_case_names])

        return f"""{header}
/**
 * {domain_pascal} Domain Use Cases
 * 
 * List of all use case names for the {context.domain_name} domain.
 * Used by createMockDependencies() to pre-create mocks.
 */

export const {domain_pascal.upper()}_USE_CASES = [
  {use_case_names_str}
] as const;
"""

    def _generate_handler_test_factory_content(
        self,
        context: GenerationContext,
        use_case_names: List[str]
    ) -> str:
        """Generate test factory content for handlers"""
        header = self.generate_header(context, "Handler test factories")
        domain_pascal = pascal_case(context.domain_name)
        
        # Generate use case names list
        use_case_names_str = ",\n    ".join([f'"{name}"' for name in use_case_names])

        return f"""{header}
/**
 * Test Factories for Handlers
 *
 * Provides factories for creating mock FastifyRequest, FastifyReply, and Dependencies
 * for testing api-server handlers.
 */

import type {{ FastifyRequest, FastifyReply }} from "fastify";
import {{ vi }} from "vitest";

/**
 * Extended FastifyRequest type for testing with effectiveOrgId
 */
interface TestFastifyRequest extends Partial<FastifyRequest> {{
  effectiveOrgId?: string;
  params?: Record<string, string>;
  query?: Record<string, string | string[]>;
  body?: unknown;
}}

/**
 * Creates a mock FastifyRequest for testing
 */
export function createMockRequest(overrides: Partial<TestFastifyRequest> = {{}}): TestFastifyRequest {{
  const orgId = overrides?.effectiveOrgId ?? "test-org-id";
  
  return {{
    params: {{}},
    query: {{}},
    body: {{}},
    headers: {{}},
    effectiveOrgId: orgId,
    ...overrides,
  }};
}}

/**
 * Creates a mock FastifyReply for testing
 */
export function createMockReply(overrides: Partial<FastifyReply> = {{}}): Partial<FastifyReply> {{
  const send = vi.fn().mockReturnThis();
  const code = vi.fn().mockReturnThis();
  const status = vi.fn().mockReturnThis();
  
  return {{
    send,
    code,
    status,
    ...overrides,
  }} as Partial<FastifyReply>;
}}

/**
 * Creates a mock Dependencies object for testing
 * 
 * @template T - The dependencies type (e.g., {domain_pascal}DDDDependencies)
 */
export function createMockDependencies<T extends Record<string, {{ execute: ReturnType<typeof vi.fn> }}>>(
  overrides: Partial<T> = {{}}
): T {{
  const mockDeps: Record<string, {{ execute: ReturnType<typeof vi.fn> }}> = {{}};
  
  // Pre-create all use case mocks so vi.spyOn can find them
  const useCaseNames = [
    {use_case_names_str}
  ];
  
  for (const name of useCaseNames) {{
    mockDeps[name] = {{
      execute: vi.fn(),
    }};
  }}
  
  // Apply overrides
  Object.assign(mockDeps, overrides);
  
  return mockDeps as T;
}}
"""

    def _generate_resource_handler_test_index(
        self,
        context: GenerationContext,
        test_filenames: List[str]
    ) -> str:
        """Generate index.ts for resource handler test directory"""
        header = self.generate_header(context, "Handler tests barrel export")
        exports = []
        for filename in sorted(test_filenames):
            import_name = filename.replace(".ts", "")
            exports.append(f'export * from "./{import_name}.js";')

        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""

    def _generate_usecase_tests(
        self,
        context: GenerationContext,
        tests_dir: Path,
        services_dir: Path,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> List[Path]:
        """Generate test files for use cases"""
        files: List[Path] = []
        usecases_dir = services_dir / "usecases"
        tests_usecases_dir = tests_dir / "usecases"

        if not usecases_dir.exists():
            return files

        ensure_directory(tests_usecases_dir)

        # Generate test file for each use case
        for resource, ops in resource_operations.items():
            for op_data in ops:
                operation_id = op_data["operation_id"]
                usecase_name = f"Execute{pascal_case(operation_id)}"
                usecase_file = usecases_dir / f"{usecase_name}.ts"

                # Only generate test if use case file exists
                if usecase_file.exists():
                    # Use kebab-case filename with -usecase suffix
                    usecase_file_name = kebab_case(usecase_name)
                    test_file = tests_usecases_dir / f"{usecase_file_name}-usecase.test.ts"
                    test_content = self._generate_usecase_test_content(
                        context, operation_id, usecase_name, resource, op_data, services_dir
                    )
                    write_file(test_file, test_content)
                    files.append(test_file)

        return files

    def _generate_handler_test_content(
        self,
        context: GenerationContext,
        operation_id: str,
        handler_name: str,
        resource: str,
        op_data: Dict[str, Any],
        api_server_dir: Path,
        has_entity_factory: bool = True,
        has_dto_factory: bool = True
    ) -> str:
        """Generate test content for a handler (api-server layer)"""
        header = self.generate_header(context, f"{pascal_case(operation_id)} handler tests")
        handler_pascal = pascal_case(handler_name)
        resource_pascal = pascal_case(resource)
        resource_kebab = kebab_case(resource)
        operation = op_data.get("operation", {})
        http_method = op_data.get("method", "").lower()
        verb = extract_verb_from_operation_id(operation_id, http_method=http_method)
        domain_pascal = pascal_case(context.domain_name)

        # Get expected status code from operation
        expected_status = self._get_expected_status_code(verb, operation) if operation else (201 if verb == "create" else 204 if verb == "delete" else 200)

        # Build test cases based on verb (handlers pass orgId into use case input)
        test_cases = self._build_handler_test_cases(
            verb, operation_id, handler_name, resource, resource_kebab, resource_pascal,
            context, operation, op_data, expected_status, has_entity_factory, has_dto_factory
        )

        # Import handler from api-server using barrel export
        handler_import_path = f"@ddd/api-server/domains/{context.domain_name}/handlers"

        # DTO factory import only when the DTO factory file exists (barrel may not export it)
        dto_factory_import = ""
        if has_dto_factory and verb in ["create", "update", "patch"]:
            verb_pascal = pascal_case(verb)
            dto_factory_name = f"create{verb_pascal}{resource_pascal}Request"
            dto_factory_import = f'import {{ {dto_factory_name} }} from "@ddd/factories/{context.domain_name}";\n'

        # Import test factories from shared location (using barrel exports)
        test_factory_import = f'import {{ createMockRequest, createMockReply, createMockDependencies, TEST_ORG_ID }} from "@ddd/tests/shared";\n'
        # Import use case list
        use_case_list_import = f'import {{ {domain_pascal.upper()}_USE_CASES }} from "../__factories__/use-cases.js";\n'
        # Import entity factory only when core has entity file for this resource
        entity_factory_import = f'import {{ create{resource_pascal} as create{resource_pascal}Entity }} from "@ddd/factories/{context.domain_name}";\n' if has_entity_factory else ""

        return f"""{header}
import {{ describe, it, expect, beforeEach, vi }} from "vitest";
import {{ {handler_name} }} from "{handler_import_path}";
import type {{ {domain_pascal}DDDDependencies }} from "@ddd/api-server/domains/{context.domain_name}";
{entity_factory_import}{dto_factory_import}{test_factory_import}{use_case_list_import}
describe("{handler_pascal}", () => {{
  let mockRequest: ReturnType<typeof createMockRequest>;
  let mockReply: ReturnType<typeof createMockReply>;
  let mockDeps: {domain_pascal}DDDDependencies;
  const orgId = TEST_ORG_ID;

  beforeEach(() => {{
    mockRequest = createMockRequest({{ orgId }});
    mockReply = createMockReply();
    mockDeps = createMockDependencies<{domain_pascal}DDDDependencies>(
      {domain_pascal.upper()}_USE_CASES,
      {{
        // Mock use case dependencies here
      }}
    );
  }});

{test_cases}
}});
"""

    def _get_expected_status_code(
        self,
        verb: str,
        operation: Dict[str, Any]
    ) -> int:
        """Get expected HTTP status code from operation responses"""
        if not operation:
            # Default based on verb
            if verb == "create":
                return 201
            elif verb == "delete":
                return 204
            else:
                return 200
        
        responses = operation.get("responses", {})
        
        # For create operations, prefer 201, fallback to 200
        if verb == "create":
            if "201" in responses:
                return 201
            elif "200" in responses:
                return 200
            else:
                return 201
        
        # For delete operations, prefer 204, fallback to 200
        elif verb == "delete":
            if "204" in responses:
                return 204
            elif "200" in responses:
                return 200
            else:
                return 204
        
        # For other operations, use 200
        else:
            return 200

    def _build_handler_test_cases(
        self,
        verb: str,
        operation_id: str,
        handler_name: str,
        resource: str,
        resource_kebab: str = None,
        resource_pascal: str = None,
        context: GenerationContext = None,
        operation: Dict[str, Any] = None,
        op_data: Dict[str, Any] = None,
        expected_status: int = 200,
        has_entity_factory: bool = True,
        has_dto_factory: bool = True
    ) -> str:
        """Build test cases for a handler based on verb (api-server layer).
        When has_entity_factory is False, use inline entity mock (no createXEntity).
        When has_dto_factory is False for create/update/patch, use {} as any for body input.
        Handlers pass orgId (and params/body) into use case, so expectations use expect.objectContaining.
        """
        if resource_pascal is None:
            resource_pascal = pascal_case(resource)
        if resource_kebab is None:
            resource_kebab = kebab_case(resource)
        handler_pascal = pascal_case(handler_name)

        # Entity declaration: factory or inline mock for resources without core entity file
        if has_entity_factory:
            entity_line = f"const entity = create{resource_pascal}Entity({{ orgId }});"
            entities_list_lines = f"""      create{resource_pascal}Entity({{ orgId }}),
      create{resource_pascal}Entity({{ orgId }}),"""
        else:
            entity_line = "const entity = { id: 'mock-id', orgId } as any;"
            entities_list_lines = """      { id: 'mock-1', orgId } as any,
      { id: 'mock-2', orgId } as any,"""

        # Generate DTO factory name for create/update operations (used only when has_dto_factory)
        verb_pascal = pascal_case(verb)
        dto_factory_name = f"create{verb_pascal}{resource_pascal}Request"
        input_line = f"const input = {dto_factory_name}();" if has_dto_factory else "const input = {} as any;"

        # Extract path parameters
        path_params = []
        if operation and "parameters" in operation:
            for param in operation["parameters"]:
                if param.get("in") == "path":
                    path_params.append(param.get("name", ""))

        # Check if handler has id parameter (for get operations)
        has_id_param = len(path_params) > 0
        # Entity id param is the last path param (e.g. postId in /orgs/:orgId/.../posts/:postId), not orgId
        entity_id_param = path_params[-1] if path_params else "id"

        # Use case name pattern: Execute{OperationId} (camelCase for property access)
        # Dependencies use: execute{OperationId} (e.g., executePostOrgs, executeGetOrg)
        # Operation ID is camelCase (e.g., "postOrgs"), dependency property is "execute" + capitalize first letter
        use_case_prop = "execute" + (operation_id[0].upper() + operation_id[1:] if operation_id else "")

        # Org-scoped handlers pass orgId into use case; platform-scoped (e.g. listPlatformSocialProviders) pass {{}} or params only
        is_org_scoped = operation_id and "Org" in operation_id

        if verb == "get":
            if has_id_param:
                param_name = entity_id_param
                expect_arg = f"expect.objectContaining({{ orgId, {param_name}: entity.id }})" if is_org_scoped else f"expect.objectContaining({{ {param_name}: entity.id }})"
                return f"""  it("should return 200 with entity when found", async () => {{
    {entity_line}
    const useCaseResult = {{ data: entity, meta: {{ correlationId: "test", timestamp: new Date().toISOString() }} }};
    
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(useCaseResult);
    mockRequest.params = {{ {param_name}: entity.id }};

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockDeps.{use_case_prop}.execute).toHaveBeenCalledWith({expect_arg});
    expect(mockReply.code).toHaveBeenCalledWith(200);
    expect(mockReply.send).toHaveBeenCalledWith(useCaseResult);
  }});

  it("should return error when entity not found", async () => {{
    const nonExistentId = "non-existent-id";
    mockRequest.params = {{ {param_name}: nonExistentId }};
    
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockRejectedValue(
      new Error("Entity not found")
    );

    await expect(
      {handler_name}(mockRequest, mockReply, mockDeps)
    ).rejects.toThrow();
  }});
"""
            else:
                expect_arg = "expect.objectContaining({ orgId })" if is_org_scoped else "expect.anything()"
                return f"""  it("should return 200 with entity", async () => {{
    {entity_line}
    const useCaseResult = {{ data: entity, meta: {{ correlationId: "test", timestamp: new Date().toISOString() }} }};
    
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(useCaseResult);

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockDeps.{use_case_prop}.execute).toHaveBeenCalledWith({expect_arg});
    expect(mockReply.code).toHaveBeenCalledWith(200);
    expect(mockReply.send).toHaveBeenCalledWith(useCaseResult);
  }});
"""
        elif verb == "create":
            # Create is typically org-scoped
            expect_arg = "expect.objectContaining({ orgId })" if is_org_scoped else "expect.anything()"
            return f"""  it("should return 201 with created entity", async () => {{
    {input_line}
    {entity_line}
    const useCaseResult = {{ data: entity, meta: {{ correlationId: "test", timestamp: new Date().toISOString() }} }};
    
    mockRequest.body = input;
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(useCaseResult);

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockDeps.{use_case_prop}.execute).toHaveBeenCalledWith({expect_arg});
    expect(mockReply.code).toHaveBeenCalledWith({expected_status});
    expect(mockReply.send).toHaveBeenCalledWith(useCaseResult);
  }});
"""
        elif verb in ["update", "patch"]:
            param_name = entity_id_param
            expect_arg = f"expect.objectContaining({{ orgId, {param_name}: entity.id }})" if is_org_scoped else f"expect.objectContaining({{ {param_name}: entity.id }})"
            return f"""  it("should return {expected_status} with updated entity", async () => {{
    {entity_line}
    {input_line}
    const updatedEntity = {{ ...entity, ...input }};
    const useCaseResult = {{ data: updatedEntity, meta: {{ correlationId: "test", timestamp: new Date().toISOString() }} }};
    
    mockRequest.params = {{ {param_name}: entity.id }};
    mockRequest.body = input;
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(useCaseResult);

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockDeps.{use_case_prop}.execute).toHaveBeenCalledWith({expect_arg});
    expect(mockReply.code).toHaveBeenCalledWith({expected_status});
    expect(mockReply.send).toHaveBeenCalledWith(useCaseResult);
  }});
"""
        elif verb == "delete":
            param_name = entity_id_param
            expect_arg = f"expect.objectContaining({{ orgId, {param_name}: entity.id }})" if is_org_scoped else f"expect.objectContaining({{ {param_name}: entity.id }})"
            return f"""  it("should return {expected_status} on successful deletion", async () => {{
    {entity_line}
    mockRequest.params = {{ {param_name}: entity.id }};
    
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(undefined);

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockDeps.{use_case_prop}.execute).toHaveBeenCalledWith({expect_arg});
    expect(mockReply.code).toHaveBeenCalledWith({expected_status});
  }});
"""
        elif verb == "list":
            expect_arg = "expect.objectContaining({ orgId })" if is_org_scoped else "expect.anything()"
            return f"""  it("should return 200 with list of entities", async () => {{
    const entities = [
{entities_list_lines}
    ];
    const useCaseResult = {{
      data: {{ items: entities, nextCursor: undefined, prevCursor: undefined }},
      meta: {{ correlationId: "test", timestamp: new Date().toISOString(), pagination: {{}} }}
    }};
    
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(useCaseResult);

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockDeps.{use_case_prop}.execute).toHaveBeenCalledWith({expect_arg});
    expect(mockReply.code).toHaveBeenCalledWith(200);
    expect(mockReply.send).toHaveBeenCalledWith(useCaseResult);
  }});
"""
        else:
            # For unknown verbs, try to call handler with minimal parameters
            return f"""  it("should execute handler successfully", async () => {{
    // Generic test for {verb} operation - handler may have custom signature
    const useCaseResult = {{ data: {{}}, meta: {{ correlationId: "test", timestamp: new Date().toISOString() }} }};
    vi.spyOn(mockDeps.{use_case_prop}, "execute").mockResolvedValue(useCaseResult);

    await {handler_name}(mockRequest, mockReply, mockDeps);

    expect(mockReply.code).toHaveBeenCalled();
    expect(mockReply.send).toHaveBeenCalled();
  }});
"""

    def _generate_handlers_test_index(
        self,
        context: GenerationContext,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Generate index.ts for handlers test directory"""
        header = self.generate_header(context, "Handler tests barrel export")
        exports = []
        for resource, ops in sorted(resource_operations.items()):
            resource_kebab = kebab_case(resource)
            exports.append(f'export * from "./{resource_kebab}/index.js";')

        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""

    def _generate_usecases_test_index(
        self,
        context: GenerationContext,
        resource_operations: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Generate index.ts for usecases test directory"""
        header = self.generate_header(context, "Use case tests barrel export")
        exports = []
        seen_usecases = set()
        for resource, ops in resource_operations.items():
            for op_data in ops:
                operation_id = op_data["operation_id"]
                usecase_name = f"Execute{pascal_case(operation_id)}"
                if usecase_name not in seen_usecases:
                    seen_usecases.add(usecase_name)
                    # Use kebab-case filename with -usecase suffix
                    usecase_file_name = kebab_case(usecase_name)
                    exports.append(f'export * from "./{usecase_file_name}-usecase.test.js";')

        exports_str = "\n".join(sorted(exports))
        return f"""{header}{exports_str}
"""

    def _generate_usecase_test_content(
        self,
        context: GenerationContext,
        operation_id: str,
        usecase_name: str,
        resource: str,
        op_data: Dict[str, Any],
        services_dir: Path
    ) -> str:
        """Generate test content for a use case"""
        header = self.generate_header(context, f"{usecase_name} tests")
        resource_pascal = pascal_case(resource)
        resource_kebab = kebab_case(resource)
        operation = op_data.get("operation", {})
        http_method = op_data.get("method", "").lower()
        verb = extract_verb_from_operation_id(operation_id, http_method=http_method)

        repo_name = f"{resource_pascal}Repository"
        mock_repo_name = f"Mock{repo_name}"

        # Determine DTO factory name for input creation
        verb_pascal = pascal_case(verb)
        dto_factory_name = f"create{verb_pascal}{resource_pascal}Request"
        needs_dto_factory = verb in ["create", "update", "patch"]
        dto_factory_import = ""
        input_creation = "{} as any"
        if needs_dto_factory:
            dto_factory_import = f'import {{ {dto_factory_name} }} from "@ddd/factories/{context.domain_name}/factories/{resource_kebab}/dto/{verb}-{resource_kebab}.dto.factory.js";\n'
            input_creation = f"{dto_factory_name}()"

        # Calculate relative import path from tests to services
        # tests/src/{domain}/usecases/ -> services/src/{domain}/usecases/
        # Use kebab-case filename with -usecase suffix
        usecase_file_name = kebab_case(usecase_name)
        relative_path = f"@ddd/services/{context.domain_name}/usecases/{usecase_file_name}-usecase.js"

        return f"""{header}
import {{ describe, it, expect, beforeEach, vi }} from "vitest";
import {{ {usecase_name} }} from "{relative_path}";
import {{ {mock_repo_name} }} from "@ddd/factories/{context.domain_name}/mocks/index.js";
import {{ create{resource_pascal} as create{resource_pascal}Entity }} from "@ddd/factories/{context.domain_name}/factories/{resource_kebab}/entity/{resource_kebab}.entity.factory.js";
{dto_factory_import}import {{ TEST_ORG_ID }} from "@ddd/factories/{context.domain_name}/e2e/setup.js";

describe("{usecase_name}", () => {{
  let useCase: {usecase_name};
  let mockRepo: {mock_repo_name};
  const orgId = TEST_ORG_ID;

  beforeEach(() => {{
    mockRepo = new {mock_repo_name}();
    mockRepo.reset();
    useCase = new {usecase_name}(mockRepo);
  }});

  it("should execute use case successfully", async () => {{
    // Use DTO factory for input if available, otherwise use empty object
    const input = {input_creation};

    const result = await useCase.execute(input);

    expect(result).toBeDefined();
  }});
}});
"""
