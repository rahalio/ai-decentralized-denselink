"""
Entity Generator - Generates domain entities

Per DDD: Entities belong in core layer (domain layer).
NO handlers, NO DTOs - only pure domain entities.
"""

from pathlib import Path
from typing import Dict, Any, List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations, extract_schemas
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory, remove_stale_domain_dirs
from ...utils.string import kebab_case, pascal_case


class EntityGenerator(BaseGenerator):
    """Generates domain entities"""

    @property
    def name(self) -> str:
        return "Entity Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "entity"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate entity files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory - entities go to models/{resource}/entity/ (clean when pipeline.clean)
        project_root = context.config.paths.project_root
        core_src = project_root / "packages" / "core" / "src"
        domain_dir = core_src / context.domain_name
        models_dir = domain_dir / "models"

        # Remove generated dirs for domains no longer in config (e.g. publishing)
        if not context.get_state("core_stale_domains_cleaned"):
            enabled = {d.name for d in context.config.domains if d.enabled}
            for name in remove_stale_domain_dirs(core_src, enabled, preserve={"_shared", "integration-events"}):
                context.logger.info(f"Removed stale core domain: {name}")
            context.set_state("core_stale_domains_cleaned", True)

        ensure_directory(models_dir)
        if context.config.pipeline.clean and models_dir.exists():
            clean_directory(models_dir)

        # Extract operations and group by resource
        operations = extract_operations(context.spec)
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

        # Generate entities for each resource
        schemas_dict = extract_schemas(context.spec)
        resource_dirs = {}  # Track resource directories for index generation

        for resource, ops in resource_operations.items():
            from ...utils.x_codegen_extensions import should_skip_persistence
            if all(should_skip_persistence(o.get("operation", {})) for o in ops):
                continue

            resource_kebab = kebab_case(resource)
            resource_pascal = pascal_case(resource)

            # Initialize resource_dirs structure (no resource_dir needed for flatter structure)
            resource_dirs[resource] = {
                "kebab": resource_kebab,
                "pascal": resource_pascal
            }

            # Find entity schema name from operations using EntityExtractor
            from ...generators.core.repositories.entity_extractor import EntityExtractor
            entity_schema_name = EntityExtractor.extract_entity_name_from_operations(context, resource)

            if not entity_schema_name:
                warnings.append(f"Could not find entity schema for resource: {resource}")
                continue

            # Check if this is a persisted entity (has x-dynamodb.entityType) or a value object
            entity_schema_def = schemas_dict.get(entity_schema_name) or {}
            is_persisted_entity = False
            is_value_object = False
            is_transport = False

            # Check for persisted entity (has x-dynamodb.entityType)
            if isinstance(entity_schema_def, dict):
                x_dynamodb = entity_schema_def.get("x-dynamodb")
                if isinstance(x_dynamodb, dict) and x_dynamodb.get("entityType"):
                    is_persisted_entity = True

            # Check for configuration entity (may not have x-dynamodb but should be persisted)
            from ...utils.schema_analyzer import SchemaAnalyzer
            is_config_entity = False
            if isinstance(entity_schema_def, dict):
                is_config_entity = SchemaAnalyzer.is_configuration_entity(entity_schema_name, entity_schema_def)
                if is_config_entity:
                    is_persisted_entity = True  # Configuration entities are persisted

            # Check for explicit x-value-object marker
            if isinstance(entity_schema_def, dict):
                if entity_schema_def.get("x-value-object") is True:
                    is_value_object = True
                    is_persisted_entity = False

            # Check if this is a transport wrapper (structural check)
            def _is_transport_wrapper(schema: dict) -> bool:
                """Return True if schema looks like a transport wrapper: { data: ..., meta?: ... }"""
                if not isinstance(schema, dict):
                    return False
                if schema.get("type") != "object":
                    return False
                props = schema.get("properties", {}) or {}
                # Check if it has 'data' property and only 'data' and optionally 'meta'
                if "data" in props:
                    prop_keys = set(props.keys())
                    if prop_keys.issubset({"data", "meta"}):
                        return True
                return False

            # Check if this is computed data (not an entity)
            is_computed_data = False
            if isinstance(entity_schema_def, dict):
                is_computed_data = SchemaAnalyzer.is_computed_data_schema(entity_schema_def, entity_schema_name)
                if is_computed_data:
                    is_transport = True  # Computed data is treated as transport DTO

            # Structural transport wrapper check (more reliable than name patterns)
            if _is_transport_wrapper(entity_schema_def):
                # But check if it wraps an entity first
                if not is_computed_data:
                    from ...generators.core.schemas.schema_resolver import SchemaResolver
                    wrapped_entity = SchemaResolver.extract_entity_from_response_schema(entity_schema_def, schemas_dict)
                    if wrapped_entity and not wrapped_entity.endswith("Response"):
                        # Check if wrapped entity is actually an entity
                        wrapped_schema = schemas_dict.get(wrapped_entity)
                        if wrapped_schema and SchemaAnalyzer.is_entity_schema(wrapped_schema, wrapped_entity, schemas_dict):
                            # Update entity_schema_name to the wrapped entity
                            entity_schema_name = wrapped_entity
                            entity_schema_def = wrapped_schema
                            # Re-check for persisted entity
                            x_dynamodb = entity_schema_def.get("x-dynamodb")
                            if isinstance(x_dynamodb, dict) and x_dynamodb.get("entityType"):
                                is_persisted_entity = True
                            is_config_entity = SchemaAnalyzer.is_configuration_entity(entity_schema_name, entity_schema_def)
                            if is_config_entity:
                                is_persisted_entity = True
                            is_transport = False  # Not a transport wrapper if it wraps an entity
                        else:
                            is_transport = True
                    else:
                        is_transport = True
                else:
                    is_transport = True
            # Also check name patterns as fallback (but only if not wrapping an entity)
            elif entity_schema_name.endswith(("Response", "Result", "Output")):
                # Check if Response wraps an entity
                if not is_computed_data:
                    from ...generators.core.schemas.schema_resolver import SchemaResolver
                    wrapped_entity = SchemaResolver.extract_entity_from_response_schema(entity_schema_def, schemas_dict)
                    if wrapped_entity and not wrapped_entity.endswith("Response"):
                        wrapped_schema = schemas_dict.get(wrapped_entity)
                        if wrapped_schema and SchemaAnalyzer.is_entity_schema(wrapped_schema, wrapped_entity, schemas_dict):
                            # Update to use wrapped entity
                            entity_schema_name = wrapped_entity
                            entity_schema_def = wrapped_schema
                            x_dynamodb = entity_schema_def.get("x-dynamodb")
                            if isinstance(x_dynamodb, dict) and x_dynamodb.get("entityType"):
                                is_persisted_entity = True
                            is_config_entity = SchemaAnalyzer.is_configuration_entity(entity_schema_name, entity_schema_def)
                            if is_config_entity:
                                is_persisted_entity = True
                            is_transport = False
                        else:
                            is_transport = True
                    else:
                        is_transport = True
                else:
                    is_transport = True

            # Core is driven by YAML operations only. x-dynamodb drives only DynamoDB adapter generation.
            # Classification: Value Object (explicit) → Transport/Computed (skip) → else Entity (from API response)
            if is_value_object:
                # Generate as Value Object (explicitly marked with x-value-object: true)
                value_objects_dir = domain_dir / "value-objects"
                ensure_directory(value_objects_dir)
                resource_dirs[resource]["value_object_dir"] = value_objects_dir
                domain_file = value_objects_dir / f"{resource_kebab}.value-object.ts"
                header = self.generate_header(
                    context,
                    f"{resource_pascal} Value Object - Domain model"
                )
                domain_type = "ValueObject"
                type_label = "Value Object (not persisted)"
            elif is_transport:
                # Skip transport DTOs / computed data — not domain concepts
                operation_ids = [op["operation_id"] for op in ops]
                warnings.append(
                    f"Skipping resource '{resource}': schema '{entity_schema_name}' looks like a transport wrapper "
                    f"or computed data. Operations: {', '.join(operation_ids)}"
                )
                continue
            else:
                # Generate as Entity — schema comes from operations (API response). x-dynamodb is for adapters only.
                domain_file = models_dir / f"{resource_kebab}.entity.ts"
                header = self.generate_header(
                    context,
                    f"{resource_pascal} Entity - Domain model"
                )
                domain_type = "Entity"
                type_label = "Persisted Entity (x-dynamodb)" if is_persisted_entity else "Domain Entity (API)"
                resource_dirs[resource]["entity_file"] = domain_file

            # Calculate import path to schemas
            if domain_type == "ValueObject":
                # Value objects are in domain/value-objects/, schemas are in domain/schemas/
                schemas_path = f"../schemas/{context.domain_name}.schemas.js"
            else:
                # Entities are in domain/models/, schemas are in domain/schemas/
                schemas_path = f"../schemas/{context.domain_name}.schemas.js"

            # Generate schema reference
            # IMPORTANT: Only generate value objects from schemas explicitly marked with x-value-object: true
            # Never generate VOs from transport wrapper data fields - those should be skipped entirely
            # The extractor should have already extracted the referenced schema (e.g., OAuthStartPayload)
            # from transport wrappers, so entity_schema_name should be the actual VO schema, not the wrapper
            # Use OpenAPI-derived types when schema is in components so we get proper typing; otherwise
            # fall back to z.infer (e.g. when schema exists in Zod output but not in OpenAPI components).
            schema_in_components = entity_schema_name in schemas_dict
            openapi_types_path = f"../openapi/{context.domain_name}.openapi.types.js"
            if schema_in_components:
                content = f"""{header}import type {{ components }} from "{openapi_types_path}";
import {{ schemas }} from "{schemas_path}";

/**
 * {domain_type}: {resource_pascal}{domain_type}
 * Description: Represents the {resource_pascal} domain model.
 * Source: schemas.{entity_schema_name}
 * Type: {type_label}
 */
export const {resource_pascal}{domain_type}Schema = schemas.{entity_schema_name};
export type {resource_pascal}{domain_type} = components["schemas"]["{entity_schema_name}"];
"""
            else:
                content = f"""{header}import {{ z }} from "zod";
import {{ schemas }} from "{schemas_path}";

/**
 * {domain_type}: {resource_pascal}{domain_type}
 * Description: Represents the {resource_pascal} domain model.
 * Source: schemas.{entity_schema_name}
 * Type: {type_label}
 */
export const {resource_pascal}{domain_type}Schema = schemas.{entity_schema_name};
export type {resource_pascal}{domain_type} = z.infer<typeof {resource_pascal}{domain_type}Schema>;
"""

            write_file(domain_file, content)
            files.append(domain_file)

            # Store domain type for later use
            resource_dirs[resource]["domain_type"] = domain_type
            resource_dirs[resource]["is_persisted"] = is_persisted_entity

        # Generate models/index.ts barrel export for all entities
        # Entities are now directly in models/ directory (flatter structure)
        # Value objects are in domain/value-objects/ (not in models/)

        # Generate index.ts for value-objects directory (if any value objects were generated)
        # Value objects are now directly under domain/, not under models/
        value_objects_dir = domain_dir / "value-objects"
        has_value_objects = False
        if value_objects_dir.exists():
            value_object_files = list(value_objects_dir.glob("*.value-object.ts"))
            if value_object_files:
                has_value_objects = True
                value_objects_index_file = value_objects_dir / "index.ts"
                value_objects_index_content = self._generate_value_objects_index(context, value_object_files, domain_dir)
                write_file(value_objects_index_file, value_objects_index_content)
                files.append(value_objects_index_file)

        # Generate index.ts for models directory (entities only, value objects are separate)
        # Only include resources that are actually entities (not value objects or skipped)
        models_index_file = models_dir / "index.ts"
        existing_entity_resources = [
            resource for resource, info in resource_dirs.items()
            if info.get("domain_type") == "Entity" and "entity_file" in info
        ]
        models_index_content = self._generate_models_index(context, existing_entity_resources, has_value_objects=False)
        write_file(models_index_file, models_index_content)
        files.append(models_index_file)

        context.logger.info(f"Generated {len(files)} entity/value-object files for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)


    def _generate_entity_index(
        self,
        context: GenerationContext,
        resource_kebab: str,
        resource_pascal: str
    ) -> str:
        """Generate index.ts for entity directory"""
        header = self.generate_header(context, f"{resource_pascal} entity exports")
        return f"""{header}export * from "./{resource_kebab}.entity.js";
"""

    def _generate_resource_index(
        self,
        context: GenerationContext,
        resource_kebab: str,
        resource_pascal: str,
        export_type: str = "entity"
    ) -> str:
        """Generate index.ts for resource directory"""
        header = self.generate_header(context, f"{resource_pascal} model exports")
        if export_type == "value-object":
            return f"""{header}export * from "./value-object/index.js";
"""
        else:
            return f"""{header}export * from "./entity/index.js";
"""

    def _generate_value_objects_index(
        self,
        context: GenerationContext,
        value_object_files: List[Path],
        domain_dir: Path
    ) -> str:
        """Generate index.ts for value-objects directory (now at domain level)"""
        header = self.generate_header(context, "Value Objects barrel export")
        exports = []
        for vo_file in sorted(value_object_files):
            # Get relative path from value-objects directory
            vo_name = vo_file.stem.replace(".value-object", "")
            exports.append(f'export * from "./{vo_name}.value-object.js";')

        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""

    def _generate_models_index(
        self,
        context: GenerationContext,
        resources: List[str],
        has_value_objects: bool = False
    ) -> str:
        """Generate index.ts for models directory - exports all entities directly"""
        header = self.generate_header(context, f"Models barrel export - All {pascal_case(context.domain_name)} entities")
        exports = []
        
        # Export all entities directly (flatter structure)
        for resource in sorted(resources):
            resource_kebab = kebab_case(resource)
            exports.append(f'export * from "./{resource_kebab}.entity.js";')

        # Note: Value objects are now in domain/value-objects/, not in models/
        # They should be imported separately: from "@ddd/core/{domain}/value-objects"

        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""
