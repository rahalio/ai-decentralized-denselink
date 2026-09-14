"""
Schema Resolver - Resolves schema references and extracts entities from response schemas
"""

from typing import Dict, Any, Optional
from zero_codegen.utils.openapi import extract_schema_name_from_ref, extract_schemas


class SchemaResolver:
    """Resolves schema references and extracts entities"""

    @staticmethod
    def resolve_allof_alias(schema_name: str, schemas_dict: Dict[str, Any]) -> Optional[str]:
        """
        Resolve an allOf alias schema to its actual schema name.

        Example: AuthSessionToken (allOf: [AuthSession]) -> AuthSession
        This is needed because openapi-zod-client doesn't export allOf aliases.
        """
        if schema_name not in schemas_dict:
            return None

        schema = schemas_dict[schema_name]
        if not isinstance(schema, dict):
            return None

        # Check if this is an allOf alias (single allOf item with a $ref)
        if "allOf" in schema:
            allof_items = schema["allOf"]
            if isinstance(allof_items, list) and len(allof_items) == 1:
                item = allof_items[0]
                if isinstance(item, dict) and "$ref" in item:
                    # Extract the referenced schema name
                    ref_name = extract_schema_name_from_ref(item["$ref"])
                    if ref_name and ref_name in schemas_dict:
                        # Recursively resolve if the referenced schema is also an allOf alias
                        return SchemaResolver.resolve_allof_alias(ref_name, schemas_dict) or ref_name

        return None

    @staticmethod
    def extract_entity_from_response_schema(
        schema: Dict[str, Any],
        schemas_dict: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract entity schema name from response schema.

        Handles multiple patterns:
        1. allOf with DataEnvelope pattern (data.$ref)
        2. Direct properties with data.$ref
        3. Inline object schemas in data (for cases like RegisterResponse)
        4. Array items in list responses (data.items.items.$ref)
        5. oneOf schemas (extract from first option)
        """
        if not isinstance(schema, dict):
            return None

        # Handle oneOf - extract from first option
        if "oneOf" in schema:
            one_of_items = schema["oneOf"]
            if isinstance(one_of_items, list) and len(one_of_items) > 0:
                first_item = one_of_items[0]
                if isinstance(first_item, dict) and "$ref" in first_item:
                    ref_name = extract_schema_name_from_ref(first_item["$ref"])
                    if ref_name and ref_name in schemas_dict:
                        # Recursively extract from the referenced schema
                        ref_schema = schemas_dict.get(ref_name)
                        if ref_schema:
                            return SchemaResolver.extract_entity_from_response_schema(ref_schema, schemas_dict) or ref_name

        # Check for allOf with DataEnvelope pattern
        if "allOf" in schema:
            for item in schema["allOf"]:
                if isinstance(item, dict):
                    # Check for data property with $ref
                    if "properties" in item and "data" in item["properties"]:
                        data_schema = item["properties"]["data"]
                        if isinstance(data_schema, dict):
                            # Handle $ref in data
                            if "$ref" in data_schema:
                                ref_name = extract_schema_name_from_ref(data_schema["$ref"])
                                if ref_name and ref_name in schemas_dict:
                                    return ref_name
                            # Handle array in data (list responses)
                            elif data_schema.get("type") == "array":
                                items = data_schema.get("items", {})
                                if isinstance(items, dict) and "$ref" in items:
                                    ref_name = extract_schema_name_from_ref(items["$ref"])
                                    if ref_name and ref_name in schemas_dict:
                                        return ref_name
                            # Handle nested object with items array (e.g., ListShareholderRegistriesResponse: data.items.items.$ref)
                            # This must come after array check but handles object with nested items
                            if data_schema.get("type") == "object" and "properties" in data_schema:
                                items_prop = data_schema["properties"].get("items", {})
                                if isinstance(items_prop, dict):
                                    # Check if items is an array with nested items
                                    if items_prop.get("type") == "array" and "items" in items_prop:
                                        array_items = items_prop.get("items", {})
                                        if isinstance(array_items, dict) and "$ref" in array_items:
                                            ref_name = extract_schema_name_from_ref(array_items["$ref"])
                                            if ref_name and ref_name in schemas_dict:
                                                return ref_name
                                    # Also check if items directly has $ref (for simpler patterns)
                                    elif "$ref" in items_prop:
                                        ref_name = extract_schema_name_from_ref(items_prop["$ref"])
                                        if ref_name and ref_name in schemas_dict:
                                            return ref_name
                                # Handle inline object schema in data (e.g., CompletionResponse: data.properties.id, output, tokensUsed)
                                # Check if this inline object is an entity or computed data
                                if "$ref" not in data_schema and "properties" in data_schema:
                                    # Check if this is computed data (should not be treated as entity)
                                    from zero_codegen.utils.schema_analyzer import SchemaAnalyzer
                                    if SchemaAnalyzer.is_computed_data_schema(data_schema):
                                        return None  # Computed data, not an entity
                                    
                                    # Check if this inline object is a configuration entity
                                    # For inline objects in Response schemas, derive name from Response name
                                    # This handles cases like LimitsResponse with inline data object
                                    if "properties" in data_schema:
                                        props = data_schema["properties"]
                                        # Check for configuration entity patterns in properties
                                        has_config_pattern = any(
                                            pattern in str(props.keys()).lower() 
                                            for pattern in SchemaAnalyzer.CONFIGURATION_ENTITY_PATTERNS
                                        )
                                        # Check for entity indicators
                                        has_entity_indicators = any(
                                            indicator in props for indicator in SchemaAnalyzer.ENTITY_INDICATORS
                                        )
                                        
                                        # If it has entity indicators or config patterns, it might be an entity
                                        # Return None to let the caller handle it (will use response schema name)
                                        if has_entity_indicators or has_config_pattern:
                                            return None  # Inline entity - will be handled by entity extractor
                                    
                                    # Default: inline object schema - return None to use response schema as entity
                                    return None
                    # Check for direct $ref (skip DataEnvelope)
                    if "$ref" in item:
                        ref_name = extract_schema_name_from_ref(item["$ref"])
                        if ref_name and ref_name != "DataEnvelope" and ref_name in schemas_dict:
                            # Check if it's not a Request/Response type
                            if not any(suffix in ref_name for suffix in ["Request", "Response", "Envelope"]):
                                return ref_name

        # Check for direct properties with data field
        if "properties" in schema:
            data_prop = schema["properties"].get("data")
            if isinstance(data_prop, dict):
                # Handle $ref in data
                if "$ref" in data_prop:
                    ref_name = extract_schema_name_from_ref(data_prop["$ref"])
                    if ref_name and ref_name in schemas_dict:
                        return ref_name
                # Handle array in data (list responses like ListTransferRequestsResponse)
                elif data_prop.get("type") == "object" and "properties" in data_prop:
                    items_prop = data_prop["properties"].get("items", {})
                    if isinstance(items_prop, dict):
                        # Check if items is an array
                        if items_prop.get("type") == "array":
                            array_items = items_prop.get("items", {})
                            if isinstance(array_items, dict) and "$ref" in array_items:
                                ref_name = extract_schema_name_from_ref(array_items["$ref"])
                                if ref_name and ref_name in schemas_dict:
                                    return ref_name
                        # Or items might directly be a $ref
                        elif "$ref" in items_prop:
                            ref_name = extract_schema_name_from_ref(items_prop["$ref"])
                            if ref_name and ref_name in schemas_dict:
                                return ref_name

        return None
