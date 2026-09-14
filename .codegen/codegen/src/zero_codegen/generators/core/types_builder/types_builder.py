"""
Types Builder - Builds TypeScript type export file content
"""

from typing import Dict, Any, List, Set, Optional
from pathlib import Path
import os
from zero_codegen.base.context import GenerationContext
from zero_codegen.utils.openapi import (
    extract_schemas,
    extract_operations,
    get_request_body_schema_name,
    get_response_schema_name,
    get_shared_types_from_common_files,
    is_shared_type,
)
from zero_codegen.utils.string import pascal_case, extract_verb_from_operation_id, singularize
from zero_codegen.utils.naming import NamingConvention
from zero_codegen.utils.schema_analyzer import SchemaAnalyzer


class TypesBuilder:
    """Builds TypeScript type export file content"""

    @staticmethod
    def build_types_file_content(context: GenerationContext, version: str) -> str:
        """Build complete types file content"""
        header = TypesBuilder._generate_header(context, version)

        # Import statement - import from local openapi folder
        # Calculate relative path from packages/core/src/{domain}/types/index.ts
        # to packages/core/src/{domain}/openapi/{domain}.openapi.types.ts
        # From: packages/core/src/{domain}/types/index.ts
        # To: packages/core/src/{domain}/openapi/{domain}.openapi.types.ts
        # Relative: ../openapi/{domain}.openapi.types
        domain_name = context.domain_name

        # Simple relative path: from types/ to openapi/ in same domain directory
        import_path = f"../openapi/{domain_name}.openapi.types"

        import_stmt = f'import type {{ components, operations }} from "{import_path}";'

        # Re-export section
        re_export_section = TypesBuilder._generate_re_export_section()

        # Schema aliases
        schema_aliases = TypesBuilder._generate_schema_aliases(context)

        # Operation input types
        input_types = TypesBuilder._generate_operation_input_types(context)

        # Operation parameter types
        param_types = TypesBuilder._generate_operation_parameter_types(context)

        # Operation response types
        response_types = TypesBuilder._generate_operation_response_types(context, schema_aliases)

        return f"""{header}{import_stmt}

{re_export_section}
{schema_aliases}
{input_types}
{param_types}
{response_types}
"""

    @staticmethod
    def build_flat_types_file_content(context: GenerationContext, version: str) -> str:
        """Build flat types file content (excludes components/operations for main index exports)"""
        header = TypesBuilder._generate_header(context, version)

        # Import statement
        domain_name = context.domain_name
        import_path = f"../openapi/{domain_name}.openapi.types"
        import_stmt = f'import type {{ components, operations }} from "{import_path}";'

        # Schema aliases (domain-specific types only, excludes components/operations)
        schema_aliases = TypesBuilder._generate_schema_aliases(context)

        # Operation input types
        input_types = TypesBuilder._generate_operation_input_types(context)

        # Operation parameter types
        param_types = TypesBuilder._generate_operation_parameter_types(context)

        # Operation response types
        response_types = TypesBuilder._generate_operation_response_types(context, schema_aliases)

        return f"""{header}{import_stmt}

// ============================================================================
// Domain Types Export - Domain-specific types only (excludes components/operations)
// ============================================================================
// This file exports domain-specific types for use in main index.ts
// components and operations are NOT exported here to avoid duplicate export errors
// Access components/operations via namespace: domain.types.components

{schema_aliases}
{input_types}
{param_types}
{response_types}
"""

    @staticmethod
    def _generate_header(context: GenerationContext, version: str) -> str:
        """Generate file header"""
        domain_name = context.domain_name
        domain_title = domain_name.replace("-", " ").title()

        return f"""/**
 * {domain_title} Domain Types
 *
 * Auto-generated from OpenAPI spec
 * Generator: types-generator v{version}
 *
 * This file re-exports types from generated OpenAPI types and adds
 * convenient type aliases for handlers (response types, etc.)
 *
 * ⚠️ DO NOT EDIT MANUALLY - this file is auto-generated
 */

"""

    @staticmethod
    def _generate_re_export_section() -> str:
        """Generate re-export section"""
        return """// ============================================================================
// Re-export all generated types
// ============================================================================
// Note: components and operations are exported here but should be accessed via namespace
// in main index.ts to avoid duplicate export errors (e.g., blockchain.types.components)

export type { components, operations };

"""

    @staticmethod
    def _generate_schema_aliases(context: GenerationContext) -> str:
        """Generate schema type aliases, excluding shared types and names that clash with model entity types"""
        schemas = extract_schemas(context.spec)
        model_entity_type_names = TypesBuilder._get_model_entity_type_names(context)

        # Get openapi directory to detect shared types
        # openapi_dir might be openapi/ or openapi/src/, check both
        openapi_dir = context.config.paths.openapi_dir
        # If openapi_dir doesn't have src/, try adding it
        if not (openapi_dir / "common").exists():
            openapi_src_dir = openapi_dir / "src"
            if openapi_src_dir.exists():
                openapi_dir = openapi_src_dir

        # Filter schemas - exclude Request/Response/Envelope types
        exclude_patterns = ["Request", "Response", "Envelope", "RequestBody", "Meta", "Error", "Problem"]

        schema_aliases = []
        request_schemas = []

        for schema_name in sorted(schemas.keys()):
            if "-" in schema_name:
                continue
            if schema_name in model_entity_type_names:
                continue
            # Skip excluded patterns
            if any(pattern in schema_name for pattern in exclude_patterns):
                # But include Request schemas for convenience aliases
                if "Request" in schema_name:
                    request_schemas.append(schema_name)
                continue

            # Skip shared types - they should only be exported from shared/types
            if is_shared_type(schema_name, context.spec, openapi_dir):
                continue

            # Get schema definition
            schema_def = schemas[schema_name]
            
            if isinstance(schema_def, dict):
                # Include value objects in type aliases for convenience
                # (They are also exported from value-objects/, but having them in types/ makes them easier to use)
                # Skip schemas that are primary entities (have x-dynamodb or are config entities)
                # Base schemas like DomainEvent that multiple entities reference should still be in types
                has_dynamodb = schema_def.get("x-dynamodb") and isinstance(schema_def.get("x-dynamodb"), dict)
                is_config_entity = SchemaAnalyzer.is_configuration_entity(schema_name, schema_def)
                
                # Only exclude if it's a primary entity schema (has x-dynamodb or is config entity)
                # AND the schema name matches entity naming (ends with Entity, Settings, Config, Limits, Policies)
                # This excludes primary entities but keeps base schemas that entities reference
                if (has_dynamodb or is_config_entity):
                    entity_name_patterns = ["Entity", "Settings", "Config", "Limits", "Policies"]
                    if any(schema_name.endswith(pattern) for pattern in entity_name_patterns):
                        continue

            # Check if schema is a $ref alias
            if isinstance(schema_def, dict) and "$ref" in schema_def:
                # It's a $ref alias - resolve it
                ref_path = schema_def["$ref"]
                if ref_path.startswith("#/components/schemas/"):
                    ref_name = ref_path.split("/")[-1]
                    if ref_name in schemas and ref_name not in model_entity_type_names:
                        if not is_shared_type(ref_name, context.spec, openapi_dir):
                            ref_schema = schemas[ref_name]
                            if not (isinstance(ref_schema, dict) and SchemaAnalyzer.is_entity_schema(ref_schema, ref_name, schemas)):
                                schema_aliases.append(f'export type {schema_name} = components["schemas"]["{ref_name}"];')
                continue

            # Generate alias for direct schema (only if not an entity)
            schema_aliases.append(f'export type {schema_name} = components["schemas"]["{schema_name}"];')

        # Add request schemas (these are domain-specific even if they reference shared types)
        for schema_name in sorted(request_schemas):
            if "-" in schema_name:  # Skip invalid TS identifiers (bundler artifacts)
                continue
            schema_aliases.append(f'export type {schema_name} = components["schemas"]["{schema_name}"];')

        # Add entity aliases for response-only resources
        entity_aliases = TypesBuilder._generate_entity_aliases(context, schemas, schema_aliases)

        if not schema_aliases and not entity_aliases:
            return ""

        all_aliases = schema_aliases + entity_aliases
        return f"""// ============================================================================
// Convenient Type Aliases for Schemas
// ============================================================================

{chr(10).join(all_aliases)}

"""

    @staticmethod
    def _generate_entity_aliases(
        context: GenerationContext,
        schemas: Dict[str, Any],
        schema_aliases: List[str]
    ) -> List[str]:
        """Generate entity aliases for response-only resources, excluding shared types"""
        operations = extract_operations(context.spec)
        entity_aliases = []
        resource_entity_map = {}

        # Get openapi directory to detect shared types
        # openapi_dir might be openapi/ or openapi/src/, check both
        openapi_dir = context.config.paths.openapi_dir
        # If openapi_dir doesn't have src/, try adding it
        if not (openapi_dir / "common").exists():
            openapi_src_dir = openapi_dir / "src"
            if openapi_src_dir.exists():
                openapi_dir = openapi_src_dir

        # Build set of schema alias names once (to avoid duplicates)
        schema_alias_names_set = set()
        for alias in schema_aliases:
            if "export type" in alias and "=" in alias:
                type_name = alias.split("export type")[1].split("=")[0].strip()
                schema_alias_names_set.add(type_name)

        # Track entity aliases we've created to avoid duplicates
        created_entity_names = set()

        # Get model entity type names to avoid conflicts (models export {Resource}Entity)
        model_entity_type_names = TypesBuilder._get_model_entity_type_names(context)

        for op_data in operations:
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            # Get expected entity name
            entity_name = pascal_case(resource)

            # Skip shared types
            if is_shared_type(entity_name, context.spec, openapi_dir):
                continue

            # Skip if entity already exists as a direct schema (no alias needed)
            if entity_name in schemas:
                continue

            # Check if entity name already exists in schema_aliases or we've already created it (to avoid duplicates)
            if entity_name in schema_alias_names_set or entity_name in created_entity_names:
                continue

            # Skip if entity_name conflicts with a model entity type (e.g. EventEntity from models/event.entity.ts)
            if entity_name in model_entity_type_names:
                continue

            # Check if entity_name exists in OpenAPI spec (might be a $ref alias)
            entity_schema_def = schemas.get(entity_name)
            if entity_schema_def and isinstance(entity_schema_def, dict) and "$ref" in entity_schema_def:
                # Entity exists as $ref alias in spec
                ref_path = entity_schema_def["$ref"]
                if ref_path.startswith("#/components/schemas/"):
                    ref_name = ref_path.split("/")[-1]
                    if ref_name in schemas:
                        # Check if referenced type is shared
                        if not is_shared_type(ref_name, context.spec, openapi_dir):
                            entity_aliases.append(f'export type {entity_name} = components["schemas"]["{ref_name}"];')
                            resource_entity_map[resource] = entity_name
                            created_entity_names.add(entity_name)
                        continue

            # If entity schema doesn't exist but Response schema does, create alias
            if entity_name not in schemas:
                # Check for Response variant
                response_variant = f"{entity_name}Response"
                if response_variant in schemas:
                    entity_aliases.append(f'export type {entity_name} = components["schemas"]["{response_variant}"];')
                    resource_entity_map[resource] = entity_name
                    created_entity_names.add(entity_name)
                else:
                    # Try POST operation response patterns (e.g., PostEntitlementsEvaluateResponse, PostMetricsQueryResponse)
                    # Check for Post{Entity}Response or {Entity}EvaluateResponse patterns
                    entity_singular = singularize(entity_name)
                    # Also try removing trailing 's' for cases like EntitlementsEvaluate -> EntitlementEvaluate
                    entity_no_s = entity_name[:-1] if entity_name.endswith('s') and len(entity_name) > 1 else None
                    post_response_variants = [
                        f"Post{entity_name}Response",
                        f"{entity_name}Response",  # Direct match
                        f"{entity_singular}EvaluateResponse",  # For EntitlementEvaluateResponse
                        f"{entity_singular}QueryResponse",  # For MetricQueryResponse
                        f"{pascal_case(singularize(resource))}EvaluateResponse",  # Alternative pattern
                        f"{pascal_case(singularize(resource))}QueryResponse",  # Alternative pattern
                    ]
                    if entity_no_s:
                        post_response_variants.extend([
                            f"{entity_no_s}EvaluateResponse",  # For EntitlementEvaluateResponse (EntitlementsEvaluate -> EntitlementEvaluate)
                            f"{entity_no_s}QueryResponse",  # For MetricQueryResponse
                        ])

                    # Also try operation ID based patterns
                    op_pascal = pascal_case(operation_id)
                    if op_pascal.startswith("Post"):
                        # Extract resource from operation ID (e.g., PostEntitlementsEvaluate -> EntitlementsEvaluate)
                        op_resource = op_pascal.replace("Post", "")
                        post_response_variants.append(f"{op_resource}Response")
                        # Try singularized version
                        op_resource_singular = singularize(op_resource)
                        if op_resource_singular != op_resource:
                            post_response_variants.append(f"{op_resource_singular}Response")
                            # Also try with Evaluate/Query suffixes
                            post_response_variants.append(f"{op_resource_singular}EvaluateResponse")
                            post_response_variants.append(f"{op_resource_singular}QueryResponse")

                    # Also check the actual response schema name from the operation
                    op = op_data["operation"]
                    responses = op.get("responses", {})
                    actual_response_schema_name = None
                    for status_code in ["200", "201", "202"]:
                        if status_code in responses:
                            response = responses[status_code]
                            content = response.get("content", {}) if isinstance(response, dict) else {}
                            if "application/json" in content:
                                json_content = content["application/json"]
                                if isinstance(json_content, dict):
                                    # Check for $ref
                                    if "$ref" in json_content:
                                        ref_path = json_content["$ref"]
                                        if ref_path.startswith("#/components/schemas/"):
                                            actual_response_schema_name = ref_path.split("/")[-1]
                                            break
                                    # Check for schema property
                                    elif "schema" in json_content:
                                        schema_ref = json_content["schema"]
                                        if isinstance(schema_ref, dict) and "$ref" in schema_ref:
                                            ref_path = schema_ref["$ref"]
                                            if ref_path.startswith("#/components/schemas/"):
                                                actual_response_schema_name = ref_path.split("/")[-1]
                                                break

                    # Add actual response schema name to variants if not already there
                    if actual_response_schema_name and actual_response_schema_name not in post_response_variants:
                        post_response_variants.append(actual_response_schema_name)

                    entity_from_post_response = None
                    post_response_schema_name = None
                    for post_variant in post_response_variants:
                        if post_variant in schemas:
                            post_response_schema_name = post_variant
                            response_schema = schemas[post_variant]
                            # Extract entity from response's data property
                            entity_from_post_response = TypesBuilder._extract_entity_from_response_data(response_schema, schemas, openapi_dir)
                            if entity_from_post_response:
                                break

                    if entity_from_post_response:
                        # Check if extracted entity is shared
                        if not is_shared_type(entity_from_post_response, context.spec, openapi_dir):
                            entity_aliases.append(f'export type {entity_name} = components["schemas"]["{entity_from_post_response}"];')
                            resource_entity_map[resource] = entity_name
                            created_entity_names.add(entity_name)
                    elif post_response_schema_name:
                        # Response schema exists but data is inline - create alias from response's data property
                        # This handles cases like EntitlementEvaluateResponse where data is inline
                        # Try to find the status code (200, 201, or 202)
                        op = op_data["operation"]
                        responses = op.get("responses", {})
                        status_code = None
                        for code in ["200", "201", "202"]:
                            if code in responses:
                                response = responses[code]
                                content = response.get("content", {}) if isinstance(response, dict) else {}
                                if "application/json" in content:
                                    status_code = code
                                    break

                        if status_code:
                            # Create alias that extracts data from the response type
                            entity_aliases.append(f'export type {entity_name} = operations["{operation_id}"]["responses"]["{status_code}"]["content"]["application/json"]["data"];')
                            resource_entity_map[resource] = entity_name
                            created_entity_names.add(entity_name)
                    else:
                        # Try Get{Entity}Response pattern
                        get_response_variant = f"Get{entity_name}Response"
                        if get_response_variant in schemas:
                            response_schema = schemas[get_response_variant]
                            # Check if it's an allOf with data property
                            if isinstance(response_schema, dict) and "allOf" in response_schema:
                                for item in response_schema["allOf"]:
                                    if isinstance(item, dict) and "properties" in item:
                                        data_prop = item["properties"].get("data", {})
                                        if isinstance(data_prop, dict) and "$ref" in data_prop:
                                            ref_name = data_prop["$ref"].split("/")[-1]
                                            if ref_name in schemas:
                                                # Check if referenced type is shared
                                                if not is_shared_type(ref_name, context.spec, openapi_dir):
                                                    entity_aliases.append(f'export type {entity_name} = components["schemas"]["{ref_name}"];')
                                                    resource_entity_map[resource] = entity_name
                                                    created_entity_names.add(entity_name)
                                                break
                        else:
                            # Try List{Entity}Response pattern (for list-only resources)
                            list_response_variant = f"List{entity_name}Response"
                            if list_response_variant in schemas:
                                response_schema = schemas[list_response_variant]
                                # Extract entity from list response (data.data.items pattern)
                                entity_from_list = TypesBuilder._extract_entity_from_list_response(response_schema, schemas)
                                if entity_from_list:
                                    # Check if extracted entity is shared
                                    if not is_shared_type(entity_from_list, context.spec, openapi_dir):
                                        # Check if entity_name already exists in schema_aliases to avoid duplicates
                                        if entity_name not in schema_alias_names_set and entity_name not in created_entity_names:
                                            entity_aliases.append(f'export type {entity_name} = components["schemas"]["{entity_from_list}"];')
                                            resource_entity_map[resource] = entity_name
                                            created_entity_names.add(entity_name)
                            else:
                                # For list operations, try to create entity alias from response data
                                # But only if verb is "list" and entity_name doesn't conflict with existing aliases
                                # AND we haven't already created an alias for this entity_name
                                if verb == "list":
                                    # Only create alias if entity_name doesn't conflict with schema aliases or existing entity aliases
                                    if entity_name not in schema_alias_names_set and entity_name not in created_entity_names:
                                        # Check if we can extract entity from list response
                                        op = op_data["operation"]
                                        responses = op.get("responses", {})
                                        for status_code in ["200", "201", "202"]:
                                            if status_code in responses:
                                                response = responses[status_code]
                                                content = response.get("content", {}) if isinstance(response, dict) else {}
                                                if "application/json" in content:
                                                    entity_aliases.append(f'export type {entity_name} = operations["{operation_id}"]["responses"]["{status_code}"]["content"]["application/json"]["data"];')
                                                    resource_entity_map[resource] = entity_name
                                                    created_entity_names.add(entity_name)
                                                break

        # Remove duplicates
        entity_aliases = list(dict.fromkeys(entity_aliases))

        # Remove entity aliases that are already in schema_aliases
        schema_alias_names = set()
        for alias in schema_aliases:
            if "export type" in alias:
                type_name = alias.split("export type")[1].split("=")[0].strip()
                schema_alias_names.add(type_name)

        filtered_entity_aliases = []
        for alias in entity_aliases:
            if "export type" in alias:
                type_name = alias.split("export type")[1].split("=")[0].strip()
                if type_name not in schema_alias_names:
                    filtered_entity_aliases.append(alias)
            else:
                filtered_entity_aliases.append(alias)

        return filtered_entity_aliases

    @staticmethod
    def _get_model_entity_type_names(context: GenerationContext) -> Set[str]:
        """Get type names exported by model entity files to avoid duplicate export conflicts.
        Entity files at models/{resource}.entity.ts export {Resource}Entity."""
        from zero_codegen.utils.string import pascal_case
        project_root = context.config.paths.project_root
        models_dir = project_root / "packages" / "core" / "src" / context.domain_name / "models"
        if not models_dir.exists():
            return set()
        names = set()
        for path in models_dir.glob("*.entity.ts"):
            # {resource}.entity.ts -> ResourceEntity (e.g. event.entity.ts -> EventEntity)
            stem = path.stem.replace(".entity", "")
            # kebab-case to PascalCase: event-in-stream -> EventInStream
            parts = stem.replace("-", " ").split()
            resource_pascal = "".join(p.capitalize() for p in parts)
            names.add(f"{resource_pascal}Entity")
        return names

    @staticmethod
    def _extract_entity_from_response_data(
        response_schema: Dict[str, Any],
        schemas: Dict[str, Any],
        openapi_dir: Path
    ) -> Optional[str]:
        """Extract entity schema name from POST response schema's data property"""
        from zero_codegen.utils.openapi import extract_schema_name_from_ref

        if not isinstance(response_schema, dict):
            return None

        # Check if response has a data property
        if "properties" in response_schema:
            data_prop = response_schema["properties"].get("data", {})
            if isinstance(data_prop, dict):
                # Check if data is a direct $ref
                if "$ref" in data_prop:
                    ref_name = extract_schema_name_from_ref(data_prop["$ref"])
                    if ref_name and ref_name in schemas:
                        # Filter out Response/Request types
                        if not any(suffix in ref_name for suffix in ["Request", "Response", "Envelope"]):
                            return ref_name

                # Check if data has properties (inline schema)
                if "properties" in data_prop:
                    # This is an inline schema - use the response schema name as entity
                    # But we need to check if there's a better entity name
                    # For now, return None to let other patterns handle it
                    return None

        # Check allOf pattern
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data_prop = item["properties"].get("data", {})
                    if isinstance(data_prop, dict):
                        # Check if data is a $ref
                        if "$ref" in data_prop:
                            ref_name = extract_schema_name_from_ref(data_prop["$ref"])
                            if ref_name and ref_name in schemas:
                                if not any(suffix in ref_name for suffix in ["Request", "Response", "Envelope"]):
                                    return ref_name
                        # Check if data has properties (inline entity)
                        elif "properties" in data_prop:
                            # For inline schemas in data, we can't extract a named type
                            # Return None to indicate we need to create an alias from the response
                            return None

        return None

    @staticmethod
    def _extract_entity_from_list_response(response_schema: Dict[str, Any], schemas: Dict[str, Any]) -> Optional[str]:
        """Extract entity schema name from List{Entity}Response (handles data.data.items pattern)"""
        from zero_codegen.utils.openapi import extract_schema_name_from_ref

        if not isinstance(response_schema, dict):
            return None

        # Check allOf pattern
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data = item["properties"].get("data", {})
                    if isinstance(data, dict):
                        # Handle data.data.items pattern (nested data structure)
                        if "properties" in data and "data" in data["properties"]:
                            inner_data = data["properties"]["data"]
                            if isinstance(inner_data, dict) and "properties" in inner_data:
                                items = inner_data["properties"].get("items", {})
                                if isinstance(items, dict):
                                    # Check if items is array with $ref
                                    if items.get("type") == "array" and "items" in items:
                                        array_items = items["items"]
                                        if isinstance(array_items, dict) and "$ref" in array_items:
                                            ref_name = extract_schema_name_from_ref(array_items["$ref"])
                                            if ref_name and ref_name in schemas:
                                                return ref_name
                                    # Or items directly has $ref
                                    elif "$ref" in items:
                                        ref_name = extract_schema_name_from_ref(items["$ref"])
                                        if ref_name and ref_name in schemas:
                                            return ref_name
                        # Handle direct data.items pattern
                        elif "properties" in data and "items" in data["properties"]:
                            items = data["properties"]["items"]
                            if isinstance(items, dict):
                                if items.get("type") == "array" and "items" in items:
                                    array_items = items["items"]
                                    if isinstance(array_items, dict) and "$ref" in array_items:
                                        ref_name = extract_schema_name_from_ref(array_items["$ref"])
                                        if ref_name and ref_name in schemas:
                                            return ref_name

        return None

    @staticmethod
    def _generate_operation_input_types(context: GenerationContext) -> str:
        """Generate operation input types (request bodies)"""
        operations = extract_operations(context.spec)

        input_types = []
        # Track schema names to detect duplicates
        schema_name_counts = {}
        for op_data in operations:
            op = op_data["operation"]
            operation_id = op_data["operation_id"]

            # Generate RequestInput for any operation with a JSON body (not only create/update/patch)
            if not op.get("requestBody"):
                continue

            # Check if request body has application/json content
            request_body = op.get("requestBody", {})
            content = request_body.get("content", {}) if isinstance(request_body, dict) else {}

            # Only generate input type if application/json exists
            if "application/json" not in content:
                continue

            # Extract actual schema name from OpenAPI spec (use unbundled for $ref when bundled is dereferenced)
            schema_name = get_request_body_schema_name(
                op, context.spec, getattr(context, "unbundled_spec", None)
            )

            # Use operation_id-based naming to avoid duplicates when multiple operations use same schema
            # Format: {OperationId}RequestInput (e.g., CreatePolicyRequestInput, InviteOrgMemberRequestInput)
            type_name = f"{pascal_case(operation_id)}RequestInput"

            input_types.append(f'export type {type_name} = NonNullable<operations["{operation_id}"]["requestBody"]>["content"]["application/json"];')
            # Alias UpdateFooRequest → UpdateFooRequestInput unless OpenAPI already defines UpdateFooRequest
            if type_name.startswith("Update") and type_name.endswith("RequestInput"):
                alias = type_name[: -len("Input")]
                schemas = extract_schemas(context.spec)
                if alias not in schemas:
                    input_types.append(f"export type {alias} = {type_name};")

        if not input_types:
            return ""

        return f"""// ============================================================================
// Operation Input Types (Request Bodies)
// ============================================================================

// These types represent the input data for create/update operations

{chr(10).join(input_types)}

"""

    @staticmethod
    def _generate_operation_parameter_types(context: GenerationContext) -> str:
        """Generate operation parameter types ({operation_id}Params).

        Emits Params for any operation that has parameters (query or path).
        Aligns with get_input_schema_or_type_name - single source of truth for param-only inputs.
        """
        from zero_codegen.utils.openapi import _operation_has_parameters

        operations = extract_operations(context.spec)
        schemas = extract_schemas(context.spec)

        param_types = []
        for op_data in operations:
            op = op_data["operation"]
            operation_id = op_data["operation_id"]

            if not _operation_has_parameters(op):
                continue

            expected_schema_name = f"{pascal_case(operation_id)}Params"
            if expected_schema_name in schemas:
                continue

            parameters = op.get("parameters", [])
            has_query = any(p.get("in") == "query" for p in parameters if isinstance(p, dict))
            has_path = any(p.get("in") == "path" for p in parameters if isinstance(p, dict))

            if has_query:
                # NonNullable: OpenAPI types make parameters.query optional when all query params are optional; normalize to object for repository/handler use.
                param_types.append(f'export type {expected_schema_name} = NonNullable<operations["{operation_id}"]["parameters"]["query"]>;')
            elif has_path:
                param_types.append(f'export type {expected_schema_name} = operations["{operation_id}"]["parameters"]["path"];')

        if not param_types:
            return ""

        return f"""// ============================================================================
// Operation Parameter Types (Query/Path Parameters)
// ============================================================================

// These types represent parameters for operations without request bodies.
// Aligned with get_input_schema_or_type_name for consistent naming across generators.

{chr(10).join(param_types)}

"""

    @staticmethod
    def _generate_operation_response_types(
        context: GenerationContext,
        schema_aliases_section: str
    ) -> str:
        """Generate operation response types"""
        operations = extract_operations(context.spec)

        # Get schema alias names to avoid duplicates
        schema_alias_names = set()
        for line in schema_aliases_section.split("\n"):
            if "export type" in line and "=" in line:
                type_name = line.split("export type")[1].split("=")[0].strip()
                schema_alias_names.add(type_name)

        response_types = []
        for op_data in operations:
            op = op_data["operation"]
            operation_id = op_data["operation_id"]
            http_method = op_data.get("method", "").lower()
            verb = extract_verb_from_operation_id(operation_id)

            # Also check HTTP method and operation ID patterns
            # POST operations are typically create operations
            # VerbMapper already handles "complete" pattern, so no special case needed
            if http_method == "post" or operation_id.lower().startswith("post"):
                if verb != "create":
                    verb = "create"

            # Determine status code based on verb
            responses = op.get("responses", {})

            if verb == "create":
                if "201" in responses:
                    status_code = "201"
                elif "200" in responses:
                    status_code = "200"
                elif "202" in responses:
                    status_code = "202"
                else:
                    continue
            elif verb == "delete":
                if "204" in responses:
                    status_code = "204"
                elif "200" in responses:
                    status_code = "200"
                else:
                    continue
            else:
                if "200" in responses:
                    status_code = "200"
                elif "204" in responses:
                    status_code = "204"
                else:
                    continue

            # Check if response has application/json content
            response = responses.get(status_code, {})
            content = response.get("content", {}) if isinstance(response, dict) else {}

            # Only generate response type if application/json exists
            if "application/json" not in content:
                continue

            # Generate response type name
            response_type_name = f"{pascal_case(operation_id)}Response"

            # Skip if this type already exists as a schema alias
            if response_type_name in schema_alias_names:
                continue

            # Handle 204 (No Content) responses
            if status_code == "204":
                response_204 = responses.get("204", {})
                response_ref = response_204.get("$ref", "")
                response_schema_name = get_response_schema_name(op, context.spec, status_code)

                if "NoContentResponse" in response_ref or response_schema_name == "NoContentResponse":
                    if not any("export type NoContentResponse" in rt for rt in response_types):
                        response_types.insert(0, 'export type NoContentResponse = { data: { success: boolean }, meta: { correlationId: string, timestamp: string } };')
                    type_name = f"{pascal_case(operation_id)}Response"
                    response_types.append(f'export type {type_name} = NoContentResponse;')
                else:
                    type_name = f"{pascal_case(operation_id)}Response"
                    response_types.append(f'export type {type_name} = {{ data: {{ success: boolean }}, meta: {{ correlationId: string, timestamp: string }} }};')
            else:
                # Always generate response type alias - even if the underlying schema is aliased
                # Schema aliases are for entities, response types are for full response structures
                response_types.append(f'export type {response_type_name} = operations["{operation_id}"]["responses"]["{status_code}"]["content"]["application/json"];')

        if not response_types:
            return ""

        return f"""// ============================================================================
// Operation Response Types
// ============================================================================

// These types are used by handlers for type-safe response envelopes

{chr(10).join(response_types)}

"""
