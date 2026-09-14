"""
Schema Analyzer - Intelligently analyzes OpenAPI schemas to determine their nature

This module provides semantic analysis of schemas to determine:
- Whether a schema is an Entity (has identity, lifecycle) vs Response DTO (computed/derived)
- Whether an operation needs repository access (reads entities to compute result)
"""

from typing import Dict, Any, Optional, Set
from zero_codegen.utils.openapi import extract_schemas, get_response_schema


class SchemaAnalyzer:
    """Analyzes schemas semantically to determine their nature"""

    # Entity indicators - properties that suggest this is a domain entity
    ENTITY_INDICATORS: Set[str] = {
        "id",  # Primary identifier
        "orgId",  # Multi-tenant scoping
        "createdAt",  # Lifecycle timestamp
        "updatedAt",  # Lifecycle timestamp
        "created_at",  # Alternative naming
        "updated_at",  # Alternative naming
    }

    # Response DTO indicators - properties that suggest this is a computed/derived response
    RESPONSE_DTO_INDICATORS: Set[str] = {
        "allowed",  # Permission/evaluation result
        "isValid",  # Validation result
        "canRefresh",  # Capability indicator
        "status",  # When combined with other DTO indicators
        "reason",  # Explanation/result
        "remaining",  # Computed value
        "hardLimit",  # Constraint indicator
        "accessToken",  # Authentication token
        "refreshToken",  # Authentication token
        "token",  # Generic token
        "metricKey",  # Query result indicator
        "series",  # Query result indicator
    }

    # Computed data indicators - properties that indicate aggregated/computed data (not entities)
    COMPUTED_DATA_INDICATORS: Set[str] = {
        "totalTokens",  # Aggregated metrics
        "totalRequests",  # Aggregated metrics
        "totalCost",  # Aggregated metrics
        "date",  # Time-based aggregations
        "month",  # Time-based aggregations
        "period",  # Time-based aggregations
        "series",  # Query result arrays
        "items",  # Query result arrays (when in computed context)
    }

    # Configuration entity patterns - names that suggest configuration entities
    CONFIGURATION_ENTITY_PATTERNS: Set[str] = {
        "limits",  # Rate limits, quotas
        "policies",  # Access policies, rules
        "settings",  # Configuration settings
        "config",  # Configuration
        "preferences",  # User preferences
    }

    # Operation patterns that need repository access (read entities to compute result)
    REPO_ACCESS_OPERATION_PATTERNS: Set[str] = {
        "evaluate",  # Evaluate permissions/entitlements
        "query",  # Query/aggregate data
        "search",  # Search through entities
        "validate",  # Validate against entities
        "check",  # Check status/state
        "verify",  # Verify against entities
    }

    @staticmethod
    def is_computed_data_schema(schema: Dict[str, Any], schema_name: Optional[str] = None) -> bool:
        """
        Check if schema represents computed/aggregated data (not an entity)
        
        Computed data schemas have:
        - x-computed-data: true marker (explicit indicator)
        - Aggregated metrics (totalTokens, totalRequests, totalCost)
        - Time-based aggregations (date, month, period)
        - Query result arrays (series, items in computed context)
        - No entity indicators (id, orgId, createdAt, updatedAt)
        """
        if not isinstance(schema, dict):
            return False
        
        # Check for explicit x-computed-data marker (highest priority)
        if schema.get("x-computed-data") is True:
            return True
        
        # Check for computed data indicators in properties
        props = schema.get("properties", {})
        if isinstance(props, dict):
            has_computed_indicators = any(
                indicator in props for indicator in SchemaAnalyzer.COMPUTED_DATA_INDICATORS
            )
            
            # Check for aggregation patterns (date ranges, totals, etc.)
            has_aggregation = any(
                prop_name in ["since", "until", "from", "to"] 
                for prop_name in props.keys()
            )
            
            # If it has computed indicators and no entity indicators, it's computed data
            if has_computed_indicators or has_aggregation:
                has_entity_indicators = any(
                    indicator in props for indicator in SchemaAnalyzer.ENTITY_INDICATORS
                )
                if not has_entity_indicators:
                    return True
        
        return False

    @staticmethod
    def is_configuration_entity(schema_name: Optional[str], schema: Dict[str, Any]) -> bool:
        """
        Check if this is a configuration entity that should be persisted
        
        Configuration entities:
        - Have names matching configuration patterns (limits, policies, settings, config, preferences)
        - May have x-config-entity marker
        - Are persisted but may not have x-dynamodb metadata
        """
        if not schema_name:
            return False
        
        schema_lower = schema_name.lower()
        
        # Check name patterns
        if any(pattern in schema_lower for pattern in SchemaAnalyzer.CONFIGURATION_ENTITY_PATTERNS):
            return True
        
        # Check for x-config-entity marker
        if isinstance(schema, dict) and schema.get("x-config-entity") is True:
            return True
        
        return False

    @staticmethod
    def is_entity_schema(schema: Dict[str, Any], schema_name: Optional[str] = None, schemas_dict: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if a schema represents a domain entity (vs Response DTO)

        Entities have:
        - Identity properties (id, orgId)
        - Lifecycle properties (createdAt, updatedAt)
        - Domain properties
        - OR are configuration entities (limits, policies, settings)

        Response DTOs have:
        - Computed/derived properties (allowed, isValid, reason)
        - Computed/aggregated data (totalTokens, totalRequests)
        - No identity or lifecycle properties
        """
        if not isinstance(schema, dict):
            return False

        # Check if this is a configuration entity
        if SchemaAnalyzer.is_configuration_entity(schema_name, schema):
            return True

        # Check if this is computed data (not an entity)
        if SchemaAnalyzer.is_computed_data_schema(schema, schema_name):
            return False

        # Check if schema has x-dynamodb metadata (definitely an entity)
        if schema.get("x-dynamodb") and isinstance(schema.get("x-dynamodb"), dict):
            if schema["x-dynamodb"].get("entityType"):
                return True

        if "properties" not in schema:
            return False

        props = schema["properties"]
        if not isinstance(props, dict):
            return False

        # Check for entity indicators
        has_entity_indicators = any(indicator in props for indicator in SchemaAnalyzer.ENTITY_INDICATORS)

        # Check for response DTO indicators
        has_dto_indicators = any(indicator in props for indicator in SchemaAnalyzer.RESPONSE_DTO_INDICATORS)

        # If it has entity indicators and no DTO indicators, it's an entity
        if has_entity_indicators and not has_dto_indicators:
            return True

        # If it has DTO indicators and no entity indicators, it's a Response DTO
        if has_dto_indicators and not has_entity_indicators:
            return False

        # If it has both, check the ratio - entities typically have more entity indicators
        entity_count = sum(1 for indicator in SchemaAnalyzer.ENTITY_INDICATORS if indicator in props)
        dto_count = sum(1 for indicator in SchemaAnalyzer.RESPONSE_DTO_INDICATORS if indicator in props)

        # If entity indicators outnumber DTO indicators, it's likely an entity
        if entity_count > dto_count:
            return True

        # Check if Response schema wraps an entity (smarter detection)
        if schema_name and schema_name.endswith("Response"):
            # Check if this Response wraps an entity schema
            if schemas_dict:
                from zero_codegen.generators.core.schemas.schema_resolver import SchemaResolver
                wrapped_entity = SchemaResolver.extract_entity_from_response_schema(schema, schemas_dict)
                if wrapped_entity:
                    # Check if the wrapped schema is an entity
                    wrapped_schema = schemas_dict.get(wrapped_entity)
                    if wrapped_schema and SchemaAnalyzer.is_entity_schema(wrapped_schema, wrapped_entity, schemas_dict):
                        return True  # Response wraps an entity, so treat as entity
            # Default: Response schemas are DTOs
            return False

        # Default: if we can't determine, assume entity (safer for repository generation)
        return True

    @staticmethod
    def is_response_dto_schema(
        schema: Dict[str, Any],
        schema_name: Optional[str] = None,
        schemas_dict: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if a schema represents a Response DTO (computed/derived response)

        This is the inverse of is_entity_schema
        """
        return not SchemaAnalyzer.is_entity_schema(schema, schema_name, schemas_dict)

    @staticmethod
    def operation_needs_repository_access(operation_id: Optional[str]) -> bool:
        """
        Determine if an operation needs repository access despite returning a Response DTO

        Some operations return Response DTOs but need to read entities to compute the result:
        - Evaluation operations (evaluate entitlements, permissions)
        - Query operations (aggregate/query data)
        - Validation operations (validate against entities)
        """
        if not operation_id:
            return False

        operation_id_lower = operation_id.lower()

        # Check if operation ID contains patterns that indicate it needs repository access
        return any(
            pattern in operation_id_lower
            for pattern in SchemaAnalyzer.REPO_ACCESS_OPERATION_PATTERNS
        )

    @staticmethod
    def should_skip_repository_generation(
        operation: Dict[str, Any],
        context_spec: Dict[str, Any],
        operation_id: Optional[str] = None
    ) -> bool:
        """
        Determine if repository generation should be skipped for this operation

        Returns True if:
        1. Operation returns a Response DTO (not an entity)
        2. Operation doesn't need repository access (doesn't read entities)
        """
        from zero_codegen.utils.openapi import get_response_schema_name, get_response_schema, extract_schema_name_from_ref

        # Get response schema
        response_schema_name = get_response_schema_name(operation, context_spec, "200")
        if not response_schema_name:
            response_schema_name = get_response_schema_name(operation, context_spec, "201")

        if not response_schema_name:
            return False  # No response schema means we can't determine - don't skip

        # Get the actual schema object
        schemas_dict = extract_schemas(context_spec)
        response_schema = schemas_dict.get(response_schema_name)

        if not response_schema:
            # Try to get from response directly
            response_schema = get_response_schema(operation, context_spec, "200")
            if not response_schema:
                response_schema = get_response_schema(operation, context_spec, "201")

        # Check if wrapped in data property
        inner_schema_name = None
        if response_schema and isinstance(response_schema, dict):
            # Handle allOf pattern (e.g., GetMetricsResponse with allOf + data.$ref)
            if "allOf" in response_schema:
                for item in response_schema["allOf"]:
                    if isinstance(item, dict) and "properties" in item:
                        data_prop = item["properties"].get("data")
                        if data_prop and "$ref" in data_prop:
                            inner_schema_name = extract_schema_name_from_ref(data_prop["$ref"])
                            break
                        elif data_prop and isinstance(data_prop, dict) and "properties" in data_prop:
                            # Inline data schema in allOf - analyze it directly
                            if SchemaAnalyzer.is_response_dto_schema(data_prop, response_schema_name, schemas_dict):
                                # Check if operation needs repository access
                                if SchemaAnalyzer.operation_needs_repository_access(operation_id):
                                    return False  # Don't skip - needs repository access
                                return True  # Skip - Response DTO without repo access needs
            elif "properties" in response_schema:
                data_prop = response_schema["properties"].get("data")
                if data_prop and "$ref" in data_prop:
                    inner_schema_name = extract_schema_name_from_ref(data_prop["$ref"])
                elif data_prop and isinstance(data_prop, dict) and "properties" in data_prop:
                    # Inline data schema - analyze it directly
                    if SchemaAnalyzer.is_response_dto_schema(data_prop, response_schema_name, schemas_dict):
                        # Check if operation needs repository access
                        if SchemaAnalyzer.operation_needs_repository_access(operation_id):
                            return False  # Don't skip - needs repository access
                        return True  # Skip - Response DTO without repo access needs

        # Check inner schema if wrapped
        schema_to_check = inner_schema_name or response_schema_name
        if schema_to_check and schema_to_check in schemas_dict:
            schema_to_inspect = schemas_dict[schema_to_check]
            if SchemaAnalyzer.is_response_dto_schema(schema_to_inspect, schema_to_check, schemas_dict):
                # Check if operation needs repository access
                if SchemaAnalyzer.operation_needs_repository_access(operation_id):
                    return False  # Don't skip - needs repository access
                return True  # Skip - Response DTO without repo access needs

        # If we can't determine, don't skip (safer to generate repository)
        return False

    @staticmethod
    def is_response_dto_operation(
        operation: Dict[str, Any],
        context_spec: Dict[str, Any],
        operation_id: Optional[str] = None
    ) -> bool:
        """
        Determine if an operation returns a Response DTO (regardless of whether it needs repo access)

        This is different from should_skip_repository_generation because some operations
        need repository access but still return Response DTOs (e.g., validate, evaluate, query)
        """
        from zero_codegen.utils.openapi import get_response_schema_name, get_response_schema, extract_schema_name_from_ref, extract_schemas

        # Get response schema
        response_schema_name = get_response_schema_name(operation, context_spec, "200")
        if not response_schema_name:
            response_schema_name = get_response_schema_name(operation, context_spec, "201")

        if not response_schema_name:
            return False  # No response schema means we can't determine

        # Get the actual schema object
        schemas_dict = extract_schemas(context_spec)
        response_schema = schemas_dict.get(response_schema_name)

        if not response_schema:
            # Try to get from response directly
            response_schema = get_response_schema(operation, context_spec, "200")
            if not response_schema:
                response_schema = get_response_schema(operation, context_spec, "201")

        # Check if wrapped in data property
        inner_schema_name = None
        if response_schema and isinstance(response_schema, dict):
            # Handle allOf pattern
            if "allOf" in response_schema:
                for item in response_schema["allOf"]:
                    if isinstance(item, dict) and "properties" in item:
                        data_prop = item["properties"].get("data")
                        if data_prop and "$ref" in data_prop:
                            inner_schema_name = extract_schema_name_from_ref(data_prop["$ref"])
                            break
                        elif data_prop and isinstance(data_prop, dict) and "properties" in data_prop:
                            # Inline data schema - analyze it directly
                            if SchemaAnalyzer.is_response_dto_schema(data_prop, response_schema_name, schemas_dict):
                                return True
            elif "properties" in response_schema:
                data_prop = response_schema["properties"].get("data")
                if data_prop and "$ref" in data_prop:
                    inner_schema_name = extract_schema_name_from_ref(data_prop["$ref"])
                elif data_prop and isinstance(data_prop, dict) and "properties" in data_prop:
                    # Inline data schema - analyze it directly
                    if SchemaAnalyzer.is_response_dto_schema(data_prop, response_schema_name, schemas_dict):
                        return True

        # Check inner schema if wrapped
        schema_to_check = inner_schema_name or response_schema_name
        if schema_to_check and schema_to_check in schemas_dict:
            schema_to_inspect = schemas_dict[schema_to_check]
            if SchemaAnalyzer.is_response_dto_schema(schema_to_inspect, schema_to_check, schemas_dict):
                return True

        return False
