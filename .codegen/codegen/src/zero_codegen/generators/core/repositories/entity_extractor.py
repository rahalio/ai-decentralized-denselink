"""
Entity Extractor - Extracts entity names from operations for repository generation
"""

from typing import Dict, Any, List, Optional

from zero_codegen.base.context import GenerationContext
from zero_codegen.utils.openapi import extract_schemas, extract_operations, get_response_schema_name, get_domain_prefix as openapi_get_domain_prefix
from zero_codegen.utils.string import pascal_case, singularize, pluralize_resource_name
from zero_codegen.utils.naming import NamingConvention
from zero_codegen.generators.core.schemas.schema_resolver import SchemaResolver


class EntityExtractor:
    """
    Extracts entity names from operations.
    
    DOMAIN_PREFIXES can be overridden via domain config or extracted from OpenAPI metadata.
    This is a fallback for legacy domains that may have prefixed entity names.
    """
    
    @staticmethod
    def get_domain_prefix(domain_name: str, context: Optional[Any] = None) -> str:
        """
        Get domain prefix for entity name resolution.
        
        Priority:
        1. Extract from OpenAPI spec info.x-domain or info.x-domain-prefix
        2. Domain config override (if available)
        3. Empty string (no prefix)
        
        Args:
            domain_name: Domain name
            context: Optional generation context (for config access)
        
        Returns:
            Domain prefix string (empty if no prefix needed)
        """
        # Extract from OpenAPI spec (info.x-domain or info.x-domain-prefix)
        if context and hasattr(context, 'spec'):
            prefix = openapi_get_domain_prefix(context.spec, domain_name)
            if prefix:
                return prefix
        
        # Check context.config for domain-specific prefix override
        if context and hasattr(context, 'config'):
            # Look for domain config in config.domains list
            if hasattr(context.config, 'domains'):
                for domain_config in context.config.domains:
                    if hasattr(domain_config, 'name') and domain_config.name == domain_name:
                        # Check if domain config has entity_prefix attribute
                        if hasattr(domain_config, 'entity_prefix'):
                            return domain_config.entity_prefix
        
        # No prefix by default
        return ""

    @staticmethod
    def extract_entity_name_from_operations(
        context: GenerationContext,
        resource: str
    ) -> Optional[str]:
        """Extract actual entity schema name from response schemas"""
        operations = extract_operations(context.spec)
        schemas_dict = extract_schemas(context.spec)
        resource_pascal = pascal_case(resource)

        # 0. CONFIG: Per-domain overrides (preserve manual schema choices after regen)
        if hasattr(context, "domain") and context.domain:
            overrides = getattr(context.domain, "entity_schema_overrides", None)
            if overrides and isinstance(overrides, dict):
                schema_name = overrides.get(resource) or overrides.get(resource_pascal)
                if schema_name and schema_name in schemas_dict:
                    return schema_name

        # Find all operations for this resource
        resource_operations = []
        for op_data in operations:
            operation_id = op_data["operation_id"]
            op_resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )
            if op_resource == resource:
                resource_operations.append(op_data)

        # 1. PRIORITY: Traverse YAML to find entity schemas with x-dynamodb.entityType
        # Match resource name to entityType, then find the corresponding schema name
        # This is the most reliable - uses OpenAPI metadata, not operation responses
        # Only use this for exact or very close matches to avoid false positives
        entity_schema_from_metadata = EntityExtractor._find_entity_by_metadata(
            context, resource, resource_pascal, schemas_dict, require_exact_match=True
        )
        if entity_schema_from_metadata:
            return entity_schema_from_metadata

        # 2. Try to extract from response schemas (what operations actually return)
        # Filter out transport wrappers - only return actual entities or explicitly marked value objects
        entity_from_response = EntityExtractor._extract_from_response_schemas(
            context, resource_operations, schemas_dict
        )
        if entity_from_response:
            # Check if the extracted schema is a transport wrapper - if so, try to extract the referenced schema from data.$ref
            response_schema_def = schemas_dict.get(entity_from_response, {})
            if EntityExtractor._is_transport_wrapper(response_schema_def):
                # Operations-first: payload schema from response (data.$ref or inline). x-dynamodb is for adapters only.
                data_ref_schema = EntityExtractor._extract_data_ref_schema(response_schema_def, schemas_dict)
                if data_ref_schema:
                    ref_schema_def = schemas_dict.get(data_ref_schema, {})
                    if isinstance(ref_schema_def, dict):
                        from zero_codegen.utils.schema_analyzer import SchemaAnalyzer
                        if SchemaAnalyzer.is_computed_data_schema(ref_schema_def, data_ref_schema):
                            return None
                        return data_ref_schema
                    return data_ref_schema
                return None
            # Not a transport wrapper - return the extracted entity
            return entity_from_response

        # 3. Try exact match (but filter out transport wrappers)
        if resource_pascal in schemas_dict:
            schema_def = schemas_dict[resource_pascal]
            if not EntityExtractor._is_transport_wrapper(schema_def):
                return resource_pascal

        # 4. Try case-insensitive match (but filter out transport wrappers)
        for schema_name in schemas_dict.keys():
            if schema_name.lower() == resource_pascal.lower():
                schema_def = schemas_dict[schema_name]
                if not EntityExtractor._is_transport_wrapper(schema_def):
                    return schema_name

        # 5. Try domain-prefixed variations
        domain_prefix = EntityExtractor.get_domain_prefix(context.domain_name, context)
        if domain_prefix:
            prefixed_name = f"{domain_prefix}{resource_pascal}"
            if prefixed_name in schemas_dict:
                return prefixed_name

        # 6. Try singular/plural variations
        singular_resource = singularize(resource_pascal)
        if singular_resource != resource_pascal and singular_resource in schemas_dict:
            return singular_resource
        plural_resource = pluralize_resource_name(resource_pascal)
        if plural_resource != resource_pascal and plural_resource in schemas_dict:
            return plural_resource

        # 7. Try domain-prefixed singular/plural
        domain_prefix = EntityExtractor.get_domain_prefix(context.domain_name, context)
        if domain_prefix:
            prefixed_singular = f"{domain_prefix}{singular_resource}"
            if prefixed_singular != prefixed_name and prefixed_singular in schemas_dict:
                return prefixed_singular

        # 8. Try to resolve allOf aliases
        resolved = SchemaResolver.resolve_allof_alias(resource_pascal, schemas_dict)
        if resolved:
            return resolved

        return None

    @staticmethod
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

    @staticmethod
    def _extract_data_ref_schema(wrapper_schema: dict, schemas_dict: Dict[str, Any]) -> Optional[str]:
        """Extract the entity schema name from a transport wrapper: data.$ref or inline data with x-dynamodb (e.g. after bundling)."""
        if not isinstance(wrapper_schema, dict):
            return None
        from zero_codegen.utils.openapi import extract_schema_name_from_ref

        def collect_data_schemas(schema: dict, out: list) -> None:
            if not isinstance(schema, dict):
                return
            props = schema.get("properties", {}) or {}
            data_prop = props.get("data")
            if isinstance(data_prop, dict):
                out.append(data_prop)
            for item in schema.get("allOf", []):
                if isinstance(item, dict):
                    collect_data_schemas(item, out)

        data_schemas = []
        collect_data_schemas(wrapper_schema, data_schemas)
        for data_schema in data_schemas:
            if not isinstance(data_schema, dict):
                continue
            if "$ref" in data_schema:
                ref_name = extract_schema_name_from_ref(data_schema["$ref"])
                if ref_name and ref_name in schemas_dict:
                    return ref_name
            x_dynamodb = data_schema.get("x-dynamodb")
            if isinstance(x_dynamodb, dict) and x_dynamodb.get("entityType"):
                entity_type = x_dynamodb["entityType"]
                for name, defn in schemas_dict.items():
                    if isinstance(defn, dict):
                        x = defn.get("x-dynamodb")
                        if isinstance(x, dict) and x.get("entityType") == entity_type:
                            return name
        return None

    @staticmethod
    def _find_entity_by_metadata(
        context: GenerationContext,
        resource: str,
        resource_pascal: str,
        schemas_dict: Dict[str, Any],
        require_exact_match: bool = False
    ) -> Optional[str]:
        """
        Find entity schema by traversing OpenAPI YAML and matching resource name to x-dynamodb.entityType.
        
        This is the definitive way to map resources to entities - uses OpenAPI metadata, not guessing.
        """
        # Build a map of entityType -> schema_name by traversing all schemas
        entity_type_to_schema = {}
        
        for schema_name, schema_def in schemas_dict.items():
            if isinstance(schema_def, dict):
                x_dynamodb = schema_def.get("x-dynamodb")
                if x_dynamodb and isinstance(x_dynamodb, dict):
                    entity_type = x_dynamodb.get("entityType")
                    if entity_type:
                        entity_type_to_schema[entity_type] = schema_name
        
        # Try to match resource name to entityType
        # Convert resource name to entityType format (e.g., "ProviderAccountToken" -> "PROVIDER_ACCOUNT_TOKEN")
        resource_upper = resource_pascal.upper()
        # Insert underscores before capital letters (except first)
        import re
        entity_type_candidate = re.sub(r'(?<!^)(?=[A-Z])', '_', resource_pascal).upper()
        
        # Try exact match
        if entity_type_candidate in entity_type_to_schema:
            return entity_type_to_schema[entity_type_candidate]
        
        # Try matching by word similarity
        # e.g., "PROVIDER_ACCOUNT_TOKEN" should match "PROVIDER_TOKEN_SET" (both contain PROVIDER and TOKEN)
        # Extract key words from resource name (split camelCase)
        resource_words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', resource_pascal)
        resource_words_upper = [w.upper() for w in resource_words]
        
        # Find entityTypes that contain the key words from resource name
        best_match = None
        best_score = 0
        
        for entity_type, schema_name in entity_type_to_schema.items():
            entity_type_upper = entity_type.upper()
            # Split entityType by underscores
            entity_type_words = entity_type_upper.split('_')
            
            # Count how many resource words appear in entityType
            matches = sum(1 for word in resource_words_upper if word in entity_type_words)
            # Prefer matches on last words (more specific)
            score = matches * 2
            if resource_words_upper and resource_words_upper[-1] in entity_type_words:
                score += 20  # High bonus for matching last word
            
            # Prefer exact substring matches (e.g., "TOKEN" in "PROVIDER_TOKEN_SET")
            for word in resource_words_upper:
                if word in entity_type_upper:
                    score += 5
            
            if score > best_score and score > 0:
                best_score = score
                best_match = schema_name
        
        # If require_exact_match is True, only return if match is very close (high score)
        if require_exact_match and best_match:
            # Require at least 2 word matches or exact entityType match for high confidence
            # Also require that the match isn't just a partial word match (e.g., "PROVIDER" matching "PROVIDER_TYPE")
            # The score should be high enough to indicate a real match
            if best_score < 20:  # Higher threshold - require strong match
                return None
            # Additional check: if resource is a single word and entityType has multiple words,
            # require that the resource word matches the first word AND there's a strong overall match
            if len(resource_words_upper) == 1 and '_' in entity_type_upper:
                # Single word resource matching multi-word entityType - be more strict
                # Only match if it's a very strong match (score > 25)
                if best_score < 25:
                    return None
        
        return best_match

    @staticmethod
    def _extract_from_response_schemas(
        context: GenerationContext,
        resource_operations: List[Dict[str, Any]],
        schemas_dict: Dict[str, Any]
    ) -> Optional[str]:
        """Extract entity from response schemas, prioritizing GET operations over LIST operations"""
        from zero_codegen.utils.openapi import get_response_schema
        from zero_codegen.utils.string import extract_verb_from_operation_id

        # Separate operations by verb - prioritize GET/create/update over LIST
        get_ops = []
        list_ops = []
        other_ops = []

        for op_data in resource_operations:
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            if verb == "get":
                get_ops.append(op_data)
            elif verb == "list":
                list_ops.append(op_data)
            else:
                other_ops.append(op_data)

        # Try GET operations first (they represent single entities)
        entity_from_get = EntityExtractor._extract_entity_from_operation_list(
            context, get_ops, schemas_dict
        )
        if entity_from_get:
            return entity_from_get

        # Try create/update operations (they also represent single entities)
        entity_from_other = EntityExtractor._extract_entity_from_operation_list(
            context, other_ops, schemas_dict
        )
        if entity_from_other:
            return entity_from_other

        # Finally try LIST operations (they represent list items)
        entity_from_list = EntityExtractor._extract_entity_from_operation_list(
            context, list_ops, schemas_dict
        )
        return entity_from_list

    @staticmethod
    def _extract_entity_from_operation_list(
        context: GenerationContext,
        operations: List[Dict[str, Any]],
        schemas_dict: Dict[str, Any]
    ) -> Optional[str]:
        """Extract entity from a list of operations"""
        from zero_codegen.utils.openapi import get_response_schema

        for op_data in operations:
            op = op_data["operation"]
            for status_code in ["200", "201", "202"]:
                # Try to get named schema first
                response_schema_name = get_response_schema_name(op, context.spec, status_code)
                response_schema = None

                if response_schema_name:
                    # Named schema exists
                    response_schema = schemas_dict.get(response_schema_name)
                else:
                    # Try to get inline schema
                    response_schema = get_response_schema(op, context.spec, status_code)

                if response_schema and isinstance(response_schema, dict):
                    entity_from_response = SchemaResolver.extract_entity_from_response_schema(
                        response_schema, schemas_dict
                    )
                    if entity_from_response:
                        # Smarter handling: Check if Response schema wraps an entity
                        if entity_from_response.endswith("Response"):
                            # Check if this Response wraps an entity schema
                            response_schema_def = schemas_dict.get(entity_from_response)
                            if response_schema_def and isinstance(response_schema_def, dict):
                                # Try to extract entity from the Response wrapper
                                wrapped_entity = SchemaResolver.extract_entity_from_response_schema(
                                    response_schema_def, schemas_dict
                                )
                                if wrapped_entity and not wrapped_entity.endswith("Response"):
                                    # Check if wrapped entity is actually an entity (not computed data)
                                    from zero_codegen.utils.schema_analyzer import SchemaAnalyzer
                                    wrapped_schema = schemas_dict.get(wrapped_entity)
                                    if wrapped_schema:
                                        # Check if it's computed data (should skip)
                                        if SchemaAnalyzer.is_computed_data_schema(wrapped_schema, wrapped_entity):
                                            continue
                                        # Check if it's a configuration entity or regular entity
                                        if (SchemaAnalyzer.is_configuration_entity(wrapped_entity, wrapped_schema) or
                                            SchemaAnalyzer.is_entity_schema(wrapped_schema, wrapped_entity, schemas_dict)):
                                            return wrapped_entity
                            # If Response doesn't wrap an entity, skip it
                            continue
                        
                        # Filter out Request/Envelope types (but allow Response if it wraps entity - handled above)
                        if any(suffix in entity_from_response for suffix in ["Request", "Envelope"]):
                            continue
                        
                        # Resolve allOf aliases
                        resolved = SchemaResolver.resolve_allof_alias(entity_from_response, schemas_dict)
                        if resolved:
                            # Check if resolved is a Response that wraps an entity
                            if resolved.endswith("Response"):
                                resolved_schema = schemas_dict.get(resolved)
                                if resolved_schema:
                                    wrapped = SchemaResolver.extract_entity_from_response_schema(resolved_schema, schemas_dict)
                                    if wrapped and not wrapped.endswith("Response"):
                                        from zero_codegen.utils.schema_analyzer import SchemaAnalyzer
                                        wrapped_schema = schemas_dict.get(wrapped)
                                        if wrapped_schema and not SchemaAnalyzer.is_computed_data_schema(wrapped_schema, wrapped):
                                            return wrapped
                                continue
                            if not any(suffix in resolved for suffix in ["Request", "Response", "Envelope"]):
                                return resolved
                        
                        # Return the entity if it's not a Request/Envelope
                        if not any(suffix in entity_from_response for suffix in ["Request", "Envelope"]):
                            return entity_from_response
                    # Resolver returned None — try wrapper with data.$ref or inline data (e.g. bundled allOf with inlined entity)
                    if not entity_from_response and response_schema and isinstance(response_schema, dict):
                        from zero_codegen.utils.schema_analyzer import SchemaAnalyzer
                        data_entity = EntityExtractor._extract_data_ref_schema(response_schema, schemas_dict)
                        if data_entity and data_entity in schemas_dict:
                            ref_def = schemas_dict.get(data_entity, {})
                            if isinstance(ref_def, dict) and not SchemaAnalyzer.is_computed_data_schema(ref_def, data_entity):
                                return data_entity
                    # Legacy: inline data at top-level properties
                    elif response_schema_name and response_schema_name in schemas_dict:
                        response_wrapper = schemas_dict[response_schema_name]
                        if isinstance(response_wrapper, dict) and "properties" in response_wrapper:
                            data_prop = response_wrapper["properties"].get("data")
                            if isinstance(data_prop, dict) and "$ref" not in data_prop and "properties" in data_prop:
                                return response_schema_name
        return None
