"""
Repository Builder - Builds repository interface content
"""

from typing import Dict, Any, List, Tuple, Optional

from zero_codegen.base.context import GenerationContext
from zero_codegen.base.folder_structure import FolderStructureConfig
from zero_codegen.utils.openapi import extract_operations, get_request_body_schema_name, is_shared_type
from zero_codegen.utils.string import extract_verb_from_operation_id, pascal_case, kebab_case
from zero_codegen.utils.naming import NamingConvention
from zero_codegen.generators.core.repositories.repository_config import RepositoryConfig, DEFAULT_CONFIG, DOMAIN_CONFIGS


class RepositoryBuilder:
    """Builds repository interface content"""

    @staticmethod
    def _get_config(context: GenerationContext) -> RepositoryConfig:
        """Get repository configuration for the domain"""
        return DOMAIN_CONFIGS.get(context.domain_name, DEFAULT_CONFIG)

    @staticmethod
    def build_repository_content(
        context: GenerationContext,
        resource: str,
        entity_name: str,
        header: str
    ) -> str:
        """Build repository interface content for base layer"""
        repo_name = NamingConvention.repository_type_name(resource)
        return RepositoryBuilder._build_base_repository(
            context, resource, entity_name, repo_name, header
        )

    @staticmethod
    def _build_base_repository(
        context: GenerationContext,
        resource: str,
        entity_name: str,
        repo_name: str,
        header: str
    ) -> str:
        """Build base layer repository interface"""
        operations = extract_operations(context.spec)
        resource_operations = RepositoryBuilder._get_resource_operations(operations, resource)

        # Get configuration for this domain
        config = RepositoryBuilder._get_config(context)

        # Detect schema mismatches between GET and LIST operations
        schema_mismatch_warning = RepositoryBuilder._detect_schema_mismatch(
            context, resource_operations, entity_name
        )

        # Determine operation combination
        repo_type, create_type, update_type, list_params_type = RepositoryBuilder._analyze_operations(
            context, resource_operations, entity_name, config
        )

        # Get import paths
        project_root = context.config.paths.project_root
        shared_repos_path = FolderStructureConfig.get_layer_shared_import_path(
            layer="core",
            generator_type="repository",
            shared_type="repositories"
        )
        types_path = FolderStructureConfig.get_layer_import_path(
            project_root,
            layer="core",
            from_generator="repository",
            to_generator="types",
            domain_name=context.domain_name
        )
        shared_types_path = FolderStructureConfig.get_layer_shared_import_path(
            layer="core",
            generator_type="repository",
            shared_type="types"
        )

        # Build entity import path and type name
        # Entity should be imported from models/{resource}.entity.ts (flatter structure)
        resource_kebab = kebab_case(resource)
        resource_pascal = pascal_case(resource)
        entity_type_name = f"{resource_pascal}Entity"
        entity_import_path = f"../models/{resource_kebab}.entity.js"

        # Build types import list (excluding entity - it has its own import)
        types_to_import = RepositoryBuilder._build_types_import_list(
            entity_name, list_params_type, create_type, update_type, config, exclude_entity=True
        )

        # Separate shared types from domain-specific types
        openapi_dir = context.config.paths.openapi_dir
        # If openapi_dir doesn't have src/, try adding it
        if not (openapi_dir / "common").exists():
            openapi_src_dir = openapi_dir / "src"
            if openapi_src_dir.exists():
                openapi_dir = openapi_src_dir

        shared_types = []
        domain_types = []
        for type_name in types_to_import:
            if is_shared_type(type_name, context.spec, openapi_dir):
                shared_types.append(type_name)
            else:
                domain_types.append(type_name)

        # Build import statements
        import_statements = []
        # Entity import (always domain-specific, from entity file)
        import_statements.append(f'import type {{\n  {entity_type_name}\n}} from "{entity_import_path}";')
        # Other types (request DTOs, etc.) from types/index.js
        if domain_types:
            domain_imports = ",\n  ".join(domain_types)
            import_statements.append(f'import type {{\n  {domain_imports}\n}} from "{types_path}";')
        if shared_types:
            shared_imports = ",\n  ".join(shared_types)
            import_statements.append(f'import type {{\n  {shared_imports}\n}} from "{shared_types_path}";')

        types_import = "\n".join(import_statements) if import_statements else ""

        list_params_in_interface = list_params_type if list_params_type.startswith("Record<") else list_params_type

        # Detect schema mismatches between GET and LIST operations
        schema_mismatch_warning = RepositoryBuilder._detect_schema_mismatch(
            context, resource_operations, entity_name
        )

        # Build repository interface based on type
        # Use entity type name (e.g., ProviderConnectionImprovedEntity) instead of schema name
        return RepositoryBuilder._build_repository_interface(
            repo_type, repo_name, entity_type_name, create_type, update_type,
            list_params_in_interface, shared_repos_path, types_import, header, config, schema_mismatch_warning
        )

    @staticmethod
    def _get_resource_operations(
        operations: List[Dict[str, Any]],
        resource: str
    ) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Get all operations for a resource"""
        resource_operations = []
        for op_data in operations:
            op = op_data["operation"]
            operation_id = op_data["operation_id"]
            op_resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            # Use centralized VerbMapper for consistent verb extraction
            http_method = op_data.get("method", "").lower()

            # Extract verb from operation ID
            op_verb = extract_verb_from_operation_id(
                operation_id,
                http_method=http_method,
                response_has_items=False
            )

            if op_resource == resource:
                resource_operations.append((op_verb, operation_id, op))
        return resource_operations

    @staticmethod
    def _analyze_operations(
        context: GenerationContext,
        resource_operations: List[Tuple[str, str, Dict[str, Any]]],
        entity_name: str,
        config: RepositoryConfig
    ) -> Tuple[str, str, str, str]:
        """Analyze operations to determine repository type and types"""
        has_create = any(verb in config.create_verbs for verb, _, _ in resource_operations)
        has_update = any(verb in config.update_verbs for verb, _, _ in resource_operations)
        has_delete = any(verb in config.delete_verbs for verb, _, _ in resource_operations)

        # Determine repository type
        repo_type = config.get_repository_type(has_create, has_update, has_delete)

        # Extract list params type
        list_params_type = RepositoryBuilder._extract_list_params_type(resource_operations, config)

        # Extract create type
        create_type = RepositoryBuilder._extract_create_type(
            context, resource_operations, entity_name, has_create, config
        )

        # Extract update type
        update_type = RepositoryBuilder._extract_update_type(
            context, resource_operations, entity_name, has_update, config
        )

        return repo_type, create_type, update_type, list_params_type

    @staticmethod
    def _determine_repo_type(has_create: bool, has_update: bool, has_delete: bool, config: RepositoryConfig) -> str:
        """Determine repository type based on operations"""
        return config.get_repository_type(has_create, has_update, has_delete)

    @staticmethod
    def _extract_list_params_type(
        resource_operations: List[Tuple[str, str, Dict[str, Any]]],
        config: RepositoryConfig
    ) -> str:
        """Extract list params type from list operation or GET operations with query params"""
        for verb, operation_id, op in resource_operations:
            parameters = op.get("parameters", [])
            has_query = any(p.get("in") == "query" for p in parameters if isinstance(p, dict))

            # Generate params type for list operations
            if verb in config.list_verbs and has_query:
                return f"{pascal_case(operation_id)}Params"

            # Also check for GET operations with query params (they might be list-like)
            # The types generator will have generated the params type if it's a list response
            if verb in config.get_verbs and has_query:
                return f"{pascal_case(operation_id)}Params"
        return config.default_list_params_type

    @staticmethod
    def _extract_create_type(
        context: GenerationContext,
        resource_operations: List[Tuple[str, str, Dict[str, Any]]],
        entity_name: str,
        has_create: bool,
        config: RepositoryConfig
    ) -> Optional[str]:
        """Extract create type from create operation that returns the entity"""
        if not has_create:
            return None

        from zero_codegen.utils.openapi import get_response_schema_name, get_response_schema
        from zero_codegen.generators.core.schemas.schema_resolver import SchemaResolver
        from zero_codegen.utils.openapi import extract_schemas

        schemas_dict = extract_schemas(context.spec)
        entity_lower = entity_name.lower()

        # Prefer create operations that return the entity
        preferred_op = None
        for verb, operation_id, op in resource_operations:
            if verb in config.create_verbs:
                # Check if this operation returns the entity
                for status_code in config.create_status_codes:
                    response_schema_name = get_response_schema_name(op, context.spec, status_code)
                    response_schema = None

                    if response_schema_name:
                        response_schema = schemas_dict.get(response_schema_name)
                    else:
                        response_schema = get_response_schema(op, context.spec, status_code)

                    if response_schema and isinstance(response_schema, dict):
                        # Extract entity from response
                        entity_from_response = SchemaResolver.extract_entity_from_response_schema(
                            response_schema, schemas_dict
                        )
                        if entity_from_response and entity_from_response.lower() == entity_lower:
                            preferred_op = (verb, operation_id, op)
                            break

                if preferred_op:
                    break

        # Use preferred op if found, otherwise use first create op
        target_op = preferred_op if preferred_op else None
        if not target_op:
            for verb, operation_id, op in resource_operations:
                if verb in config.create_verbs:
                    target_op = (verb, operation_id, op)
                    break

        if target_op:
            _, _, op = target_op
            schema_name = get_request_body_schema_name(
                op, context.spec, getattr(context, "unbundled_spec", None)
            )
            return schema_name if schema_name else entity_name

        return None

    @staticmethod
    def _extract_update_type(
        context: GenerationContext,
        resource_operations: List[Tuple[str, str, Dict[str, Any]]],
        entity_name: str,
        has_update: bool,
        config: RepositoryConfig
    ) -> Optional[str]:
        """Extract update type from update operation"""
        if not has_update:
            return None

        # Prefer operations that match the entity name
        preferred_op = None
        entity_lower = entity_name.lower()

        for verb, operation_id, op in resource_operations:
            if verb in config.update_verbs:
                operation_id_lower = operation_id.lower()
                # Remove all update verbs to get resource part
                resource_part = operation_id_lower
                for update_verb in config.update_verbs:
                    resource_part = resource_part.replace(update_verb, "").strip()
                if resource_part == entity_lower:
                    preferred_op = (verb, operation_id, op)
                    break

        if not preferred_op:
            for verb, operation_id, op in resource_operations:
                if verb in config.update_verbs:
                    preferred_op = (verb, operation_id, op)
                    break

        if preferred_op:
            verb, operation_id, op = preferred_op
            request_body = op.get("requestBody")
            if request_body:
                content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
                has_content = any(ct in content for ct in config.request_body_content_types)
                if not has_content:
                    return config.default_list_params_type
                # Prefer operation RequestInput (types builder always emits these)
                return f"{pascal_case(operation_id)}RequestInput"
            return entity_name

        return None

    @staticmethod
    def _build_types_import_list(
        entity_name: str,
        list_params_type: str,
        create_type: Optional[str],
        update_type: Optional[str],
        config: RepositoryConfig,
        exclude_entity: bool = False
    ) -> List[str]:
        """Build list of types to import (excluding entity if exclude_entity=True)"""
        types_to_import = []
        
        # Entity is imported separately from entity file, not from types/index.js
        if not exclude_entity:
            types_to_import.append(entity_name)

        if not config.is_builtin_type(list_params_type):
            if list_params_type not in types_to_import:
                types_to_import.append(list_params_type)

        if create_type and create_type not in types_to_import and not config.is_builtin_type(create_type):
            types_to_import.append(create_type)
        if update_type and update_type != create_type and update_type not in types_to_import and not config.is_builtin_type(update_type):
            types_to_import.append(update_type)

        return types_to_import

    @staticmethod
    def _detect_schema_mismatch(
        context: GenerationContext,
        resource_operations: List[Tuple[str, str, Dict[str, Any]]],
        entity_name: str
    ) -> Optional[str]:
        """Detect schema mismatches between GET and LIST operations"""
        from zero_codegen.utils.openapi import get_response_schema, extract_schemas
        from zero_codegen.generators.core.schemas.schema_resolver import SchemaResolver

        schemas_dict = extract_schemas(context.spec)
        get_entity = None
        list_entity = None

        # Extract entity from GET operations
        for verb, operation_id, op in resource_operations:
            if verb == "get":
                response_schema = get_response_schema(op, context.spec, "200")
                if response_schema and isinstance(response_schema, dict):
                    entity = SchemaResolver.extract_entity_from_response_schema(response_schema, schemas_dict)
                    if entity and not any(suffix in entity for suffix in ["Request", "Response", "Envelope"]):
                        get_entity = entity
                        break

        # Extract entity from LIST operations
        for verb, operation_id, op in resource_operations:
            if verb == "list":
                response_schema = get_response_schema(op, context.spec, "200")
                if response_schema and isinstance(response_schema, dict):
                    entity = SchemaResolver.extract_entity_from_response_schema(response_schema, schemas_dict)
                    if entity and not any(suffix in entity for suffix in ["Request", "Response", "Envelope"]):
                        list_entity = entity
                        break

        # Check for mismatch
        if get_entity and list_entity and get_entity != list_entity:
            return f"Schema mismatch detected: GET operations return '{get_entity}' but LIST operations return '{list_entity}'. Using '{get_entity}' from GET operations. TODO: Fix schema mismatch in API - listSchedules should return Schedule[] not Job[]"

        return None

    @staticmethod
    def _build_repository_interface(
        repo_type: str,
        repo_name: str,
        entity_name: str,
        create_type: Optional[str],
        update_type: Optional[str],
        list_params_in_interface: str,
        shared_repos_path: str,
        types_import: str,
        header: str,
        config: RepositoryConfig,
        schema_mismatch_warning: Optional[str] = None
    ) -> str:
        """Build repository interface based on type"""
        # Add TODO comment if schema mismatch detected
        todo_comment = ""
        if schema_mismatch_warning:
            todo_comment = f"\n/**\n * TODO: {schema_mismatch_warning}\n */\n"

        repo_interfaces = {
            "CrudRepository": f"""import type {{
  CrudRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends CrudRepository<{entity_name}, {create_type}, {update_type}, string, {list_params_in_interface}> {{

}}
""",
            "CreateUpdateReadRepository": f"""import type {{
  CreateUpdateReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends CreateUpdateReadRepository<{entity_name}, {create_type}, {update_type}, string, {list_params_in_interface}> {{

}}
""",
            "CreateDeleteReadRepository": f"""import type {{
  CreateDeleteReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends CreateDeleteReadRepository<{entity_name}, {create_type}, string, {list_params_in_interface}> {{

}}
""",
            "UpdateDeleteReadRepository": f"""import type {{
  UpdateDeleteReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends UpdateDeleteReadRepository<{entity_name}, {update_type}, string, {list_params_in_interface}> {{

}}
""",
            "CreateReadRepository": f"""import type {{
  CreateReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends CreateReadRepository<{entity_name}, {create_type}, string, {list_params_in_interface}> {{

}}
""",
            "UpdateReadRepository": f"""import type {{
  UpdateReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends UpdateReadRepository<{entity_name}, {update_type}, string, {list_params_in_interface}> {{

}}
""",
            "DeleteReadRepository": f"""import type {{
  DeleteReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends DeleteReadRepository<{entity_name}, string, {list_params_in_interface}> {{

}}
""",
            "ReadRepository": f"""import type {{
  ReadRepository,
}} from "{shared_repos_path}";

{types_import}
{todo_comment}/**
 * {repo_name} Interface
 */
export interface {repo_name} extends ReadRepository<{entity_name}, string, {list_params_in_interface}> {{

}}
""",
        }

        return header + repo_interfaces.get(repo_type, repo_interfaces["ReadRepository"])
