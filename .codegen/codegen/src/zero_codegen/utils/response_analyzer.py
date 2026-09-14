"""
Response Analyzer - Analyzes OpenAPI response schemas to determine response patterns
"""

from typing import Dict, Any, Optional
from zero_codegen.base.context import GenerationContext
from zero_codegen.utils.openapi import get_response_schema_name, extract_schemas


class ResponseAnalyzer:
    """Analyzes response schemas to determine response patterns"""

    @staticmethod
    def is_202_task_response(operation: Dict[str, Any], context: GenerationContext) -> bool:
        """Check if response is a 202 task response with taskId/status"""
        responses = operation.get("responses", {})
        if "202" not in responses:
            return False

        response_202_schema_name = get_response_schema_name(operation, context.spec, "202")
        if not response_202_schema_name:
            return False

        schemas_dict = extract_schemas(context.spec)
        response_202_schema = schemas_dict.get(response_202_schema_name)
        if not response_202_schema or not isinstance(response_202_schema, dict):
            return False

        # Check for taskId or status in data properties
        if "allOf" in response_202_schema:
            for item in response_202_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data = item["properties"].get("data", {})
                    if isinstance(data, dict) and "properties" in data:
                        if "taskId" in data["properties"] or "status" in data["properties"]:
                            return True
        elif "properties" in response_202_schema:
            data = response_202_schema["properties"].get("data", {})
            if isinstance(data, dict) and "properties" in data:
                if "taskId" in data["properties"] or "status" in data["properties"]:
                    return True

        return False

    @staticmethod
    def uses_operation_success(operation: Dict[str, Any], context: GenerationContext, status_code: str) -> bool:
        """Check if response uses OperationSuccessResponse"""
        response_schema_name = get_response_schema_name(operation, context.spec, status_code)
        if not response_schema_name:
            return False

        schemas_dict = extract_schemas(context.spec)
        response_schema = schemas_dict.get(response_schema_name)
        if not response_schema or not isinstance(response_schema, dict):
            return False

        # Check if response contains OperationSuccessResponse
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data = item["properties"].get("data", {})
                    if isinstance(data, dict) and "$ref" in data:
                        ref_name = data["$ref"].split("/")[-1]
                        if ref_name == "OperationSuccessResponse":
                            return True

        return False

    @staticmethod
    def is_empty_data_response(operation: Dict[str, Any], context: GenerationContext, status_code: str) -> bool:
        """Check if response has empty data object (Record<string, never>)"""
        response_schema_name = get_response_schema_name(operation, context.spec, status_code)
        if not response_schema_name:
            return False

        schemas_dict = extract_schemas(context.spec)
        response_schema = schemas_dict.get(response_schema_name)
        if not response_schema or not isinstance(response_schema, dict):
            return False

        # Check if data is an empty object (Record<string, never>)
        # This can be represented as:
        # 1. data: { type: "object", properties: {} } or no properties
        # 2. data: { type: "object" } with no properties
        # 3. data with additionalProperties: false and no properties
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data = item["properties"].get("data", {})
                    if isinstance(data, dict):
                        # Check for empty object type
                        if data.get("type") == "object":
                            props = data.get("properties", {})
                            # Empty object if no properties or properties is empty dict
                            if not props or len(props) == 0:
                                # Also check if additionalProperties is false (strict empty)
                                if data.get("additionalProperties") is False:
                                    return True
                                # Or if it's explicitly an empty object
                                if not data.get("additionalProperties"):
                                    return True
                        # Check for $ref to Record<string, never> pattern
                        if "$ref" in data:
                            ref_name = data["$ref"].split("/")[-1]
                            # Some schemas might reference an empty object schema
                            if ref_name and "empty" in ref_name.lower():
                                return True

        return False

    @staticmethod
    def is_array_response(operation: Dict[str, Any], context: GenerationContext, status_code: str) -> bool:
        """Check if response data is an array"""
        response_schema_name = get_response_schema_name(operation, context.spec, status_code)
        if not response_schema_name:
            return False

        schemas_dict = extract_schemas(context.spec)
        response_schema = schemas_dict.get(response_schema_name)
        if not response_schema or not isinstance(response_schema, dict):
            return False

        # Check if response contains array data
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data = item["properties"].get("data", {})
                    if isinstance(data, dict) and data.get("type") == "array":
                        return True
        elif "properties" in response_schema:
            data = response_schema["properties"].get("data", {})
            if isinstance(data, dict) and data.get("type") == "array":
                return True

        return False

    @staticmethod
    def is_items_response(operation: Dict[str, Any], context: GenerationContext, status_code: str) -> bool:
        """Check if response has data.items structure (list-like response)"""
        response_schema_name = get_response_schema_name(operation, context.spec, status_code)
        if not response_schema_name:
            return False

        schemas_dict = extract_schemas(context.spec)
        response_schema = schemas_dict.get(response_schema_name)
        if not response_schema or not isinstance(response_schema, dict):
            return False

        # Check if response has data.items structure
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    data = item["properties"].get("data", {})
                    if isinstance(data, dict) and "properties" in data:
                        if "items" in data["properties"]:
                            items_schema = data["properties"]["items"]
                            if isinstance(items_schema, dict) and items_schema.get("type") == "array":
                                return True
        elif "properties" in response_schema:
            data = response_schema["properties"].get("data", {})
            if isinstance(data, dict) and "properties" in data:
                if "items" in data["properties"]:
                    items_schema = data["properties"]["items"]
                    if isinstance(items_schema, dict) and items_schema.get("type") == "array":
                        return True

        return False

    @staticmethod
    def get_response_schema_name_for_verb(
        operation: Dict[str, Any],
        context: GenerationContext,
        verb: str
    ) -> Optional[str]:
        """Get response schema name based on verb"""
        responses = operation.get("responses", {})

        if verb == "create":
            # Prefer 201, then 200, then 202
            for status_code in ["201", "200", "202"]:
                schema_name = get_response_schema_name(operation, context.spec, status_code)
                if schema_name:
                    return schema_name
        elif verb == "delete":
            # Prefer 204, then 200
            for status_code in ["204", "200"]:
                schema_name = get_response_schema_name(operation, context.spec, status_code)
                if schema_name:
                    return schema_name
        else:
            # Prefer 200, then 204
            for status_code in ["200", "204"]:
                schema_name = get_response_schema_name(operation, context.spec, status_code)
                if schema_name:
                    return schema_name

        return None

    @staticmethod
    def is_full_response_structure(operation: Dict[str, Any], context: GenerationContext, status_code: str) -> bool:
        """
        Determine if response schema is already a full response structure (repository returns it directly)
        vs a wrapped response (handler needs to wrap the entity).

        A full response structure has:
        - Both `data` and `meta` properties at the top level
        - `data` is an inline object schema (not a $ref to an entity)

        A wrapped response has:
        - Both `data` and `meta` properties at the top level
        - `data` is a $ref to an entity schema (handler wraps the entity)

        Returns:
            True if repository returns full response structure (handler returns directly)
            False if handler needs to wrap the entity
        """
        response_schema_name = get_response_schema_name(operation, context.spec, status_code)
        if not response_schema_name:
            return False

        schemas_dict = extract_schemas(context.spec)
        response_schema = schemas_dict.get(response_schema_name)
        if not response_schema or not isinstance(response_schema, dict):
            return False

        # Must have both data and meta properties
        has_data = False
        has_meta = False
        data_schema = None

        # Check for allOf pattern (common in OpenAPI)
        if "allOf" in response_schema:
            for item in response_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    props = item["properties"]
                    if "data" in props:
                        has_data = True
                        data_schema = props["data"]
                    if "meta" in props:
                        has_meta = True
        # Check direct properties
        elif "properties" in response_schema:
            props = response_schema["properties"]
            if "data" in props:
                has_data = True
                data_schema = props["data"]
            if "meta" in props:
                has_meta = True

        # Must have both data and meta
        if not (has_data and has_meta):
            return False

        # Now check if data is an inline object (full response) vs $ref to entity (needs wrapping)
        if not isinstance(data_schema, dict):
            return False

        # If data has a $ref, it's referencing an entity schema - needs wrapping
        if "$ref" in data_schema:
            return False

        # If data is an inline object with properties, it's a full response structure
        # This means the repository returns the complete response object
        if data_schema.get("type") == "object" and "properties" in data_schema:
            return True

        # If data is an array, it's not a full response structure (needs wrapping)
        if data_schema.get("type") == "array":
            return False

        # Default: if we can't determine, assume it needs wrapping (safer)
        return False
