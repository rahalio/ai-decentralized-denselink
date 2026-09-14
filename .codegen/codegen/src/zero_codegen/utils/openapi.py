"""
OpenAPI specification parsing and manipulation utilities
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Union
import yaml
import json

from zero_codegen.base.errors import OpenAPIError


COMMON_QUERY_PARAMS_REF_PREFIX = "common/query-params.yaml#/components/schemas/"


def _dereference_common_refs_recursive(
    obj: Union[dict, list, Any],
    common_schemas: Dict[str, Any],
) -> Any:
    """Recursively replace $ref to common/query-params.yaml with inline schemas."""
    if isinstance(obj, dict):
        if "$ref" in obj and obj["$ref"].startswith(COMMON_QUERY_PARAMS_REF_PREFIX):
            schema_name = obj["$ref"].split("/")[-1]
            if schema_name in common_schemas:
                return dict(common_schemas[schema_name])
        return {
            k: _dereference_common_refs_recursive(v, common_schemas)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_dereference_common_refs_recursive(item, common_schemas) for item in obj]
    return obj


def dereference_common_query_params(bundled_path: Path, openapi_dir: Path) -> bool:
    """
    Inline $ref to common/query-params.yaml in bundled JSON so downstream tools
    (openapi-zod-client, openapi-typescript) don't need to resolve external refs.

    Returns True if any refs were dereferenced and file was updated.
    """
    common_path = openapi_dir / "common" / "query-params.yaml"
    if not common_path.exists():
        return False

    common_spec = load_openapi_spec(common_path)
    common_schemas = common_spec.get("components", {}).get("schemas", {})
    if not common_schemas:
        return False

    content = bundled_path.read_text(encoding="utf-8")
    spec = json.loads(content)

    # Check if any common refs exist
    spec_str = json.dumps(spec)
    if COMMON_QUERY_PARAMS_REF_PREFIX not in spec_str:
        return False

    dereferenced = _dereference_common_refs_recursive(spec, common_schemas)
    bundled_path.write_text(json.dumps(dereferenced, indent=2), encoding="utf-8")
    return True


def load_openapi_spec(path: Path) -> Dict[str, Any]:
    """Load OpenAPI specification from file"""
    if not path.exists():
        # Provide helpful error message
        parent_dir = path.parent
        available_files = []

        if parent_dir.exists():
            # Look for similar files
            available_files = [
                f.name for f in parent_dir.glob("*.json")[:5]
            ] + [
                f.name for f in parent_dir.glob("*.yaml")[:5]
            ]

        error_msg = f"""
❌ OpenAPI spec file not found: {path}
"""
        if available_files:
            try:
                cwd = Path.cwd()
                if parent_dir.is_relative_to(cwd):
                    rel_path = parent_dir.relative_to(cwd)
                    restore_path = str(rel_path).replace("\\", "/")
                else:
                    restore_path = str(parent_dir)
            except (ValueError, AttributeError):
                restore_path = str(parent_dir)

            error_msg += f"""
💡 Found these files in {parent_dir}:
   {', '.join(available_files[:5])}

💡 To restore from main branch:
   git checkout main -- {restore_path}/
"""
        else:
            error_msg += f"""
💡 The directory {parent_dir} exists but contains no spec files.

💡 To restore OpenAPI files from main branch:
   git checkout main -- openapi/
"""

        raise OpenAPIError(error_msg.strip())

    try:
        content = path.read_text(encoding="utf-8")

        # Try YAML first
        if path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(content)

        # Try JSON
        if path.suffix == ".json":
            return json.loads(content)

        # Default to YAML
        return yaml.safe_load(content)

    except yaml.YAMLError as e:
        raise OpenAPIError(f"Failed to parse YAML: {e}")
    except json.JSONDecodeError as e:
        raise OpenAPIError(f"Failed to parse JSON: {e}")
    except Exception as e:
        raise OpenAPIError(f"Failed to load OpenAPI spec: {e}")


def get_domain_prefix(spec: Dict[str, Any], domain_name: str = "") -> str:
    """
    Get domain prefix from OpenAPI spec info.
    Used for correlation IDs and entity IDs (format: {prefix}_{ulid}).

    Precedence:
      x-zatca-domain-prefix (zatca) >
      x-domain / x-domain-prefix (legacy) >
      fallback from domain_name[:3].

    Args:
        spec: OpenAPI spec dict
        domain_name: Domain name for fallback (e.g. "activity", "social")

    Returns:
        Domain prefix string (e.g. "act", "chn", "prd") — lowercased.
    """
    info = spec.get("info", {}) or {}
    prefix = (
        info.get("x-zatca-domain-prefix")
        or info.get("x-domain")
        or info.get("x-domain-prefix")
        or ""
    )
    if prefix and isinstance(prefix, str) and prefix.strip():
        return str(prefix).strip().lower()
    if domain_name:
        return (domain_name[:3] if len(domain_name) >= 3 else domain_name).lower()
    return "unk"


def get_domain_id_method(spec: Dict[str, Any], domain_name: str = "") -> str:
    """
    Get IdGeneratorService method name from OpenAPI spec.
    Derived from info.x-domain: "act" -> "actId", "chn" -> "chnId".

    Args:
        spec: OpenAPI spec dict
        domain_name: Domain name for fallback

    Returns:
        Method name (e.g. "actId", "chnId", "prdId")
    """
    prefix = get_domain_prefix(spec, domain_name)
    if not prefix:
        return "actId"
    return f"{prefix}Id"


def _resolve_parameter(spec: Dict[str, Any], param: Any) -> Optional[Dict[str, Any]]:
    """Resolve a parameter object or $ref to a parameter dict."""
    if not isinstance(param, dict):
        return None
    if "$ref" in param:
        return resolve_ref(spec, param["$ref"])
    return param


def _merge_path_item_parameters(
    spec: Dict[str, Any],
    path_item: Dict[str, Any],
    operation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Return an operation dict with path-item parameters merged in.

    OpenAPI path-item `parameters` apply to all methods; generators must see them
    on the operation to emit Params / non-empty Input DTOs.
    Operation-level parameters win on (name, in).
    """
    path_params = path_item.get("parameters") or []
    if not path_params:
        return operation

    op_params = list(operation.get("parameters") or [])
    existing: set = set()
    for p in op_params:
        resolved = _resolve_parameter(spec, p)
        if resolved and isinstance(resolved, dict):
            existing.add((resolved.get("name"), resolved.get("in")))

    merged = list(op_params)
    for p in path_params:
        resolved = _resolve_parameter(spec, p)
        if resolved and isinstance(resolved, dict):
            key = (resolved.get("name"), resolved.get("in"))
            if key in existing:
                continue
            # Prefer storing the resolved shape so `in`/`name` are visible without $ref.
            merged.append(resolved)
            existing.add(key)
        elif p not in merged:
            merged.append(p)

    if merged == op_params:
        return operation
    return {**operation, "parameters": merged}


def extract_operations(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all operations from OpenAPI spec (with path-item parameters merged)."""
    operations = []

    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "patch", "delete", "head", "options"]:
                continue
            if not isinstance(operation, dict):
                continue
            merged_operation = _merge_path_item_parameters(spec, path_item, operation)
            operation_data = {
                "path": path,
                "method": method.upper(),
                "operation": merged_operation,
                "operation_id": merged_operation.get("operationId", f"{method}_{path}"),
            }
            operations.append(operation_data)

    return operations


def extract_schemas(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all schemas from OpenAPI spec"""
    components = spec.get("components", {})
    return components.get("schemas", {})


def get_operation_by_id(spec: Dict[str, Any], operation_id: str) -> Optional[Dict[str, Any]]:
    """Get operation by operationId"""
    operations = extract_operations(spec)
    for op in operations:
        if op["operation_id"] == operation_id:
            return op["operation"]
    return None


def resolve_ref(spec: Dict[str, Any], ref: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a $ref reference in OpenAPI spec

    Supports:
    - #/components/schemas/Name
    - #/components/parameters/Name
    - #/components/responses/Name
    - #/components/requestBodies/Name
    - ./file.yaml#/components/schemas/Name (not fully supported)
    """
    if not ref.startswith("#/"):
        # External reference - not fully supported
        return None

    parts = ref[2:].split("/")
    # parts = ["components", "schemas", "SchemaName"] or ["components", "requestBodies", "RequestBodyName"]
    if len(parts) < 3:
        return None

    component_type = parts[0]  # "components"
    component_name = parts[1]  # "schemas", "requestBodies", "parameters", etc.
    # Schema/component name is the last part
    schema_name = parts[2] if len(parts) >= 3 else None

    components = spec.get("components", {})
    component = components.get(component_name, {})

    if schema_name:
        return component.get(schema_name)

    return component


def extract_schema_name_from_ref(ref: str) -> Optional[str]:
    """
    Extract schema name from a $ref string

    Examples:
    - "#/components/schemas/CreateChainRequest" -> "CreateChainRequest"
    - "#/components/requestBodies/CreateChainRequestBody" -> "CreateChainRequestBody"
    """
    if not ref or not isinstance(ref, str):
        return None

    if not ref.startswith("#/"):
        return None

    parts = ref[2:].split("/")
    # parts = ["components", "schemas", "SchemaName"] or ["components", "requestBodies", "RequestBodyName"]
    if len(parts) >= 3 and parts[0] == "components":
        # Schema/component name is the last part
        return parts[-1]

    return None


def _operation_has_parameters(operation: Dict[str, Any], spec: Optional[Dict[str, Any]] = None) -> bool:
    """Check if operation has any parameters (query, path, header). Resolves $ref when spec given."""
    parameters = operation.get("parameters", [])
    if not parameters:
        return False
    for p in parameters:
        if not isinstance(p, dict):
            continue
        resolved = p
        if "$ref" in p and spec is not None:
            resolved = resolve_ref(spec, p["$ref"]) or {}
        if isinstance(resolved, dict) and resolved.get("in") in ("query", "path"):
            return True
    return False


def get_input_schema_or_type_name(
    operation: Dict[str, Any],
    spec: Dict[str, Any],
    operation_id: str,
    fallback_spec: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Unified input type name for an operation. Single source of truth for all generators.

    - Request body exists: returns schema name from get_request_body_schema_name (validate in schemas)
    - Params only (query/path): returns {operation_id}Params (PascalCase, emitted by types builder)
    - No input: returns None

    Schema validation: callers should verify request body names exist in extract_schemas(spec).
    Params types are emitted by the types builder for operations with parameters.
    """
    from zero_codegen.utils.string import pascal_case

    # 1. Request body - use schema name (caller validates against schemas)
    schema_name = get_request_body_schema_name(operation, spec, fallback_spec)
    if schema_name:
        return schema_name

    # 1b. Request body present but schema name unresolved (e.g. bundled spec with inline schema).
    #     Core types builder emits {OperationId}RequestInput for any verb with a JSON body.
    op_pascal = pascal_case(operation_id)
    request_body = operation.get("requestBody")
    if request_body:
        content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
        if content.get("application/json"):
            return f"{op_pascal}RequestInput"

    # 2. Params only - use {operation_id}Params (types builder emits these)
    if _operation_has_parameters(operation, spec):
        return f"{pascal_case(operation_id)}Params"

    return None


def get_request_body_schema_name(
    operation: Dict[str, Any],
    spec: Dict[str, Any],
    fallback_spec: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Extract the actual schema name from requestBody.

    When spec is dereferenced (bundled), schema has no $ref. Use fallback_spec
    (unbundled YAML) which retains $refs for resolution.
    """
    result = _get_request_body_schema_name_impl(operation, spec)
    if result is not None:
        return result

    if fallback_spec is not None:
        operation_id = operation.get("operationId")
        if operation_id:
            unbundled_op = get_operation_by_id(fallback_spec, operation_id)
            if unbundled_op:
                return _get_request_body_schema_name_impl(unbundled_op, fallback_spec)

    return None


def _get_request_body_schema_name_impl(operation: Dict[str, Any], spec: Dict[str, Any]) -> Optional[str]:
    """Internal implementation: extract schema name when spec has $refs."""
    request_body = operation.get("requestBody")
    if not request_body:
        return None

    # Check for direct $ref to requestBodies component
    if "$ref" in request_body:
        ref = request_body["$ref"]
        schema_name = extract_schema_name_from_ref(ref)
        if schema_name:
            # If it's a requestBody reference, resolve it and get the schema
            if "#/components/requestBodies/" in ref:
                resolved = resolve_ref(spec, ref)
                if resolved:
                    content = resolved.get("content", {})
                    json_content = content.get("application/json", {})
                    schema = json_content.get("schema")
                    if schema and "$ref" in schema:
                        return extract_schema_name_from_ref(schema["$ref"])
            else:
                return schema_name

    # Check content -> application/json -> schema -> $ref
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema")

    if schema and "$ref" in schema:
        return extract_schema_name_from_ref(schema["$ref"])

    return None


def get_response_schema_name(operation: Dict[str, Any], spec: Dict[str, Any], status_code: str = "200") -> Optional[str]:
    """Extract the actual schema name from response"""
    responses = operation.get("responses", {})
    response = responses.get(status_code)

    if not response:
        # Try 200 as fallback
        if status_code != "200" and "200" in responses:
            response = responses["200"]
        else:
            return None

    # Check for direct $ref (e.g., #/components/responses/NoContentResponse)
    if "$ref" in response:
        ref = response["$ref"]
        schema_name = extract_schema_name_from_ref(ref)
        # For 204 responses, if it references NoContentResponse, return it
        if status_code == "204" and "NoContentResponse" in ref:
            return "NoContentResponse"
        if schema_name:
            return schema_name

    # Check content -> application/json -> schema -> $ref
    content = response.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema")

    if schema and "$ref" in schema:
        return extract_schema_name_from_ref(schema["$ref"])

    return None


def get_schema(spec: Dict[str, Any], schema_name: str) -> Optional[Dict[str, Any]]:
    """Get schema by name"""
    schemas = extract_schemas(spec)
    return schemas.get(schema_name)


def get_request_body_schema(operation: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get request body schema from operation"""
    request_body = operation.get("requestBody")
    if not request_body:
        return None

    # Handle $ref
    if "$ref" in request_body:
        resolved = resolve_ref(spec, request_body["$ref"])
        if resolved:
            request_body = resolved

    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema")

    if not schema:
        return None

    # Resolve schema ref if needed
    if "$ref" in schema:
        return resolve_ref(spec, schema["$ref"])

    return schema


def get_response_schema(operation: Dict[str, Any], spec: Dict[str, Any], status_code: str = "200") -> Optional[Dict[str, Any]]:
    """Get response schema from operation"""
    responses = operation.get("responses", {})
    response = responses.get(status_code)

    if not response:
        return None

    # Handle $ref
    if "$ref" in response:
        resolved = resolve_ref(spec, response["$ref"])
        if resolved:
            response = resolved

    content = response.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema")

    if not schema:
        return None

    # Resolve schema ref if needed
    if "$ref" in schema:
        return resolve_ref(spec, schema["$ref"])

    return schema


def is_crud_operation(operation_id: str) -> bool:
    """Check if operation is a CRUD operation"""
    verbs = ["create", "update", "delete", "get", "list", "patch"]
    return any(operation_id.lower().startswith(verb) for verb in verbs)


def has_path_parameter(path: str, param_name: str) -> bool:
    """Check if path has a specific parameter"""
    return f"{{{param_name}}}" in path or f"{{{{{param_name}}}}}" in path


def get_shared_types_from_common_files(openapi_dir: Path) -> Set[str]:
    """
    Dynamically detect shared types by loading common YAML files.

    Shared types are defined in openapi/src/common/*.yaml files.
    This function loads all common files and extracts schema names.

    Args:
        openapi_dir: Path to openapi directory (e.g., project_root / "openapi" / "src")

    Returns:
        Set of shared type names found in common files
    """
    shared_types: Set[str] = set()
    common_dir = openapi_dir / "common"

    if not common_dir.exists():
        return shared_types

    # Load all YAML files in common directory
    for yaml_file in common_dir.glob("*.yaml"):
        try:
            spec = load_openapi_spec(yaml_file)
            schemas = spec.get("components", {}).get("schemas", {})

            # Add all schema names from common files
            for schema_name in schemas.keys():
                shared_types.add(schema_name)

        except Exception:
            # Skip files that can't be loaded
            continue

    return shared_types


def is_shared_type(type_name: str, spec: Dict[str, Any], openapi_dir: Path) -> bool:
    """
    Check if a type is a shared type by examining $ref references in the spec.

    A type is shared if:
    1. It's defined in a common/*.yaml file (detected via $ref)
    2. It's explicitly listed in common files

    Args:
        type_name: Name of the type to check
        spec: OpenAPI specification dict
        openapi_dir: Path to openapi directory

    Returns:
        True if type is shared, False otherwise
    """
    # First check if it's in common files directly
    shared_types = get_shared_types_from_common_files(openapi_dir)
    if type_name in shared_types:
        return True

    # Check if this type is referenced via $ref to common files
    schemas = spec.get("components", {}).get("schemas", {})
    type_def = schemas.get(type_name)

    if isinstance(type_def, dict):
        # Check if it's a $ref to a common file
        ref = type_def.get("$ref", "")
        if ref and "common/" in ref:
            return True

        # Check allOf, anyOf, oneOf for common refs
        for key in ["allOf", "anyOf", "oneOf"]:
            if key in type_def:
                for item in type_def[key]:
                    if isinstance(item, dict):
                        item_ref = item.get("$ref", "")
                        if item_ref and "common/" in item_ref:
                            return True

    return False


def get_shared_types_from_common_files(openapi_dir: Path) -> Set[str]:
    """
    Dynamically detect shared types by loading common YAML files.

    Shared types are defined in openapi/src/common/*.yaml files.
    This function loads all common files and extracts schema names.

    Args:
        openapi_dir: Path to openapi/src directory

    Returns:
        Set of shared type names found in common files
    """
    shared_types: Set[str] = set()
    common_dir = openapi_dir / "common"

    if not common_dir.exists():
        return shared_types

    # Load all YAML files in common directory
    for yaml_file in common_dir.glob("*.yaml"):
        try:
            spec = load_openapi_spec(yaml_file)
            schemas = spec.get("components", {}).get("schemas", {})

            # Add all schema names from common files
            for schema_name in schemas.keys():
                shared_types.add(schema_name)

        except Exception:
            # Skip files that can't be loaded - allows codegen to work even if some files are missing
            continue

    # Always add these as they're always shared (re-exported from generated types)
    shared_types.add("components")
    shared_types.add("operations")

    return shared_types


def is_shared_type(type_name: str, spec: Dict[str, Any], openapi_dir: Path) -> bool:
    """
    Check if a type is a shared type by examining $ref references in the spec.

    A type is shared if:
    1. It's defined in a common/*.yaml file (detected via $ref)
    2. It's explicitly listed in common files

    Args:
        type_name: Name of the type to check
        spec: OpenAPI specification dict
        openapi_dir: Path to openapi/src directory

    Returns:
        True if type is shared, False otherwise
    """
    # First check if it's in common files directly
    shared_types = get_shared_types_from_common_files(openapi_dir)
    if type_name in shared_types:
        return True

    # Check if this type is referenced via $ref to common files
    schemas = spec.get("components", {}).get("schemas", {})
    type_def = schemas.get(type_name)

    if isinstance(type_def, dict):
        # Check if it's a $ref to a common file
        ref = type_def.get("$ref", "")
        if ref and "common/" in ref:
            return True

        # Check allOf, anyOf, oneOf for common refs
        for key in ["allOf", "anyOf", "oneOf"]:
            if key in type_def:
                for item in type_def[key]:
                    if isinstance(item, dict):
                        item_ref = item.get("$ref", "")
                        if item_ref and "common/" in item_ref:
                            return True

    return False
