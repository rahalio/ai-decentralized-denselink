"""
Schema Field Extractor - Extract field names and properties from OpenAPI schemas

This module provides utilities to extract field names, required fields, and field types
from OpenAPI schemas for use in code generation.
"""

from typing import Dict, Any, List, Optional, Set
from .openapi import (
    get_request_body_schema,
    get_response_schema,
    resolve_ref,
    extract_schemas
)


class SchemaFieldExtractor:
    """Extract field names and properties from OpenAPI schemas"""
    
    @staticmethod
    def extract_field_names(schema: Dict[str, Any], spec: Dict[str, Any]) -> List[str]:
        """
        Extract all field names from a schema.
        
        Args:
            schema: OpenAPI schema dictionary
            spec: Full OpenAPI spec (for resolving $ref)
        
        Returns:
            List of field names (property keys)
        """
        if not schema:
            return []
        
        # Resolve $ref if present
        if "$ref" in schema:
            resolved = resolve_ref(spec, schema["$ref"])
            if resolved:
                schema = resolved
            else:
                return []
        
        # Handle allOf, anyOf, oneOf by merging properties
        if "allOf" in schema:
            fields = set()
            for sub_schema in schema["allOf"]:
                fields.update(SchemaFieldExtractor.extract_field_names(sub_schema, spec))
            return sorted(fields)
        
        if "anyOf" in schema or "oneOf" in schema:
            # For anyOf/oneOf, use first option's fields
            options = schema.get("anyOf", []) or schema.get("oneOf", [])
            if options:
                return SchemaFieldExtractor.extract_field_names(options[0], spec)
            return []
        
        # Extract properties
        properties = schema.get("properties", {})
        if not properties:
            return []
        
        return sorted(properties.keys())
    
    @staticmethod
    def extract_required_fields(schema: Dict[str, Any], spec: Dict[str, Any]) -> Set[str]:
        """
        Extract required field names from a schema.
        
        Args:
            schema: OpenAPI schema dictionary
            spec: Full OpenAPI spec (for resolving $ref)
        
        Returns:
            Set of required field names
        """
        if not schema:
            return set()
        
        # Resolve $ref if present
        if "$ref" in schema:
            resolved = resolve_ref(spec, schema["$ref"])
            if resolved:
                schema = resolved
            else:
                return set()
        
        # Handle allOf, anyOf, oneOf
        if "allOf" in schema:
            required = set()
            for sub_schema in schema["allOf"]:
                required.update(SchemaFieldExtractor.extract_required_fields(sub_schema, spec))
            # Also check top-level required
            required.update(schema.get("required", []))
            return required
        
        if "anyOf" in schema or "oneOf" in schema:
            # For anyOf/oneOf, use first option's required fields
            options = schema.get("anyOf", []) or schema.get("oneOf", [])
            if options:
                return SchemaFieldExtractor.extract_required_fields(options[0], spec)
            return set()
        
        # Extract required array
        required = schema.get("required", [])
        return set(required) if isinstance(required, list) else set()
    
    @staticmethod
    def extract_field_type(schema: Dict[str, Any], field_name: str, spec: Dict[str, Any]) -> Optional[str]:
        """
        Extract the type of a specific field from a schema.
        
        Args:
            schema: OpenAPI schema dictionary
            field_name: Name of the field
            spec: Full OpenAPI spec (for resolving $ref)
        
        Returns:
            TypeScript type string or None
        """
        if not schema:
            return None
        
        # Resolve $ref if present
        if "$ref" in schema:
            resolved = resolve_ref(spec, schema["$ref"])
            if resolved:
                schema = resolved
            else:
                return None
        
        # Handle allOf - check all schemas
        if "allOf" in schema:
            for sub_schema in schema["allOf"]:
                field_type = SchemaFieldExtractor.extract_field_type(sub_schema, field_name, spec)
                if field_type:
                    return field_type
            return None
        
        # Get properties
        properties = schema.get("properties", {})
        if field_name not in properties:
            return None
        
        field_schema = properties[field_name]
        
        # Resolve field schema $ref
        if "$ref" in field_schema:
            ref_name = field_schema["$ref"].split("/")[-1]
            return ref_name
        
        # Extract type
        field_type = field_schema.get("type", "any")
        
        # Handle array types
        if field_type == "array":
            items = field_schema.get("items", {})
            if "$ref" in items:
                item_type = items["$ref"].split("/")[-1]
                return f"{item_type}[]"
            item_type = items.get("type", "any")
            return f"{item_type}[]"
        
        return field_type
    
    @staticmethod
    def get_request_fields(operation: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract field information from operation request body.
        
        Args:
            operation: OpenAPI operation dictionary
            spec: Full OpenAPI spec
        
        Returns:
            Dictionary with:
            - fields: List of field names
            - required: Set of required field names
            - schema: The request body schema
        """
        schema = get_request_body_schema(operation, spec)
        if not schema:
            return {
                "fields": [],
                "required": set(),
                "schema": None
            }
        
        return {
            "fields": SchemaFieldExtractor.extract_field_names(schema, spec),
            "required": SchemaFieldExtractor.extract_required_fields(schema, spec),
            "schema": schema
        }
    
    @staticmethod
    def get_response_fields(operation: Dict[str, Any], spec: Dict[str, Any], status_code: str = "200") -> Dict[str, Any]:
        """
        Extract field information from operation response.
        
        Args:
            operation: OpenAPI operation dictionary
            spec: Full OpenAPI spec
            status_code: HTTP status code (default: "200")
        
        Returns:
            Dictionary with:
            - fields: List of field names
            - required: Set of required field names
            - schema: The response schema
        """
        schema = get_response_schema(operation, spec, status_code)
        if not schema:
            return {
                "fields": [],
                "required": set(),
                "schema": None
            }
        
        return {
            "fields": SchemaFieldExtractor.extract_field_names(schema, spec),
            "required": SchemaFieldExtractor.extract_required_fields(schema, spec),
            "schema": schema
        }
    
    # Actor/tenant stamps — never the entity primary key (Team.teamId vs createdByActorId).
    _NON_ENTITY_ID_FIELDS = frozenset(
        {
            "orgId",
            "organizationId",
            "createdByActorId",
            "updatedByActorId",
            "userId",
            "actorId",
            "ownerUserId",
            "ownerActorId",
        }
    )

    @staticmethod
    def find_id_field(schema: Dict[str, Any], spec: Dict[str, Any]) -> Optional[str]:
        """
        Find the ID field name in a schema (common patterns: id, _id, uuid, etc.)
        
        Args:
            schema: OpenAPI schema dictionary
            spec: Full OpenAPI spec
        
        Returns:
            ID field name or None
        """
        fields = SchemaFieldExtractor.extract_field_names(schema, spec)
        
        # Common ID field patterns
        id_patterns = ["id", "_id", "uuid", "identifier", "key"]
        
        for field in fields:
            field_lower = field.lower()
            if field_lower in id_patterns:
                return field
        
        id_suffix_fields = [
            field
            for field in fields
            if (field.endswith("Id") or field.endswith("ID"))
            and field not in SchemaFieldExtractor._NON_ENTITY_ID_FIELDS
        ]
        if not id_suffix_fields:
            return None

        # Prefer required *Id fields so alphabetical order does not pick a
        # secondary FK (e.g. accountId before personId on Person).
        required = set(SchemaFieldExtractor.extract_required_fields(schema, spec) or [])
        required_ids = [field for field in id_suffix_fields if field in required]

        # Prefer primary key shaped like {SchemaName}Id (Mission → missionId).
        schema_name = ""
        if isinstance(schema, dict):
            schema_name = str(schema.get("x-schema-name") or schema.get("title") or "")
        # Callers often pass unresolved component schemas; try common title casing.
        if not schema_name and isinstance(spec, dict):
            components = (spec.get("components") or {}).get("schemas") or {}
            for name, candidate in components.items():
                if candidate is schema:
                    schema_name = name
                    break
        if schema_name:
            expected = schema_name[:1].lower() + schema_name[1:] + "Id"
            # AgentEnrollment → enrollmentId (drop leading Agent when present)
            alt = None
            if schema_name.startswith("Agent") and len(schema_name) > 5:
                rest = schema_name[5:]
                alt = rest[:1].lower() + rest[1:] + "Id"
            for candidate in (expected, alt):
                if candidate and candidate in required_ids:
                    return candidate
                if candidate and candidate in id_suffix_fields:
                    return candidate

        if required_ids:
            return required_ids[0]

        return id_suffix_fields[0]
    
    @staticmethod
    def find_org_id_field(schema: Dict[str, Any], spec: Dict[str, Any]) -> Optional[str]:
        """
        Find the organization ID field name in a schema.
        
        Args:
            schema: OpenAPI schema dictionary
            spec: Full OpenAPI spec
        
        Returns:
            Organization ID field name or None
        """
        fields = SchemaFieldExtractor.extract_field_names(schema, spec)
        
        # Common org ID patterns
        org_patterns = ["orgId", "organizationId", "org_id", "organization_id", "tenantId", "tenant_id"]
        
        for field in fields:
            if field in org_patterns:
                return field
        
        return None
