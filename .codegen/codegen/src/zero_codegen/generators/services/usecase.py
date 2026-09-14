"""
Use Case Generator - Generates application use cases

Per DDD: Use cases belong in services layer (application layer).
Use cases orchestrate business flows using ports.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations, get_request_body_schema, get_response_schema_name
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory, remove_stale_domain_dirs
from ...utils.string import kebab_case, pascal_case, camel_case, dto_input_type_name, dto_output_type_name, extract_verb_from_operation_id
from ...utils.port_determination import PortDetermination
from ...utils.schema_field_extractor import SchemaFieldExtractor
from ...utils.x_codegen_extensions import should_skip_usecase


class UseCaseGenerator(BaseGenerator):
    """
    Generates use case classes

    Pattern: class ExecutePublishContent {
      constructor(private readonly publisher: ProviderPublisher, ...) {}
      async execute(input: PublishContentInput): Promise<PublishContentOutput> {
        // orchestration logic
      }
    }
    """

    @property
    def name(self) -> str:
        return "Use Case Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "usecase"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate use case files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory
        project_root = context.config.paths.project_root
        services_src = project_root / "platform" / "services" / "src"
        output_dir = services_src / context.domain_name / "usecases"

        # Remove generated dirs for domains no longer in config (e.g. publishing)
        if not context.get_state("services_stale_domains_cleaned"):
            enabled = {d.name for d in context.config.domains if d.enabled}
            for name in remove_stale_domain_dirs(services_src, enabled, preserve={"_shared"}):
                context.logger.info(f"Removed stale services domain: {name}")
            context.set_state("services_stale_domains_cleaned", True)

        # Clean when pipeline.clean to remove stale use case files (e.g. from old operation_id naming)
        if context.config.pipeline.clean and output_dir.exists():
            clean_directory(output_dir)
        ensure_directory(output_dir)

        # Extract operations
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)

        # Identify all ports first (needed for dependency determination)
        identified_ports: Dict[str, str] = {}
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            if should_skip_usecase(operation):
                continue
            port_name = PortDetermination.determine_port_name(
                operation_id, operation, context, path=op_data.get("path")
            )
            if port_name not in identified_ports:
                adapter_name = PortDetermination.determine_adapter_name(port_name)
                identified_ports[port_name] = adapter_name

        # Generate use case for each operation (skip aliased - they delegate to another use case)
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            if self._resolve_operation_alias(context, operation_id, operation):
                continue
            if should_skip_usecase(operation):
                continue
            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            # Generate use case class name: Execute{OperationId in PascalCase}
            # Use full operation_id to ensure uniqueness (e.g., ExecuteGetProviderAccount vs ExecuteValidateProviderAccount)
            use_case_name = f"Execute{pascal_case(operation_id)}"
            # File name should be kebab-case ending with .usecase.ts (e.g., execute-list-provider-catalog.usecase.ts)
            use_case_file_name = kebab_case(use_case_name)
            use_case_file = output_dir / f"{use_case_file_name}.usecase.ts"

            # Determine dependencies (ports) needed using shared utility
            dependencies = PortDetermination.determine_use_case_dependencies(
                operation_id, operation, resource, verb, identified_ports
            )

            # Generate use case content
            header = self.generate_header(
                context,
                f"{use_case_name} - Application use case"
            )

            use_case_content = self._generate_use_case_content(
                context,
                use_case_name,
                operation_id,
                operation,
                verb,
                resource,
                dependencies,
                header
            )

            write_file(use_case_file, use_case_content)
            files.append(use_case_file)

        # Generate use cases index (only non-aliased use cases have files to export)
        index_file = output_dir / "index.ts"
        use_case_exports = []
        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data.get("operation", {})
            if self._resolve_operation_alias(context, operation_id, operation):
                continue
            if should_skip_usecase(operation):
                continue
            # Use full operation_id to ensure uniqueness
            use_case_name = f"Execute{pascal_case(operation_id)}"
            # File name should be kebab-case ending with .usecase.ts for export path
            use_case_file_name = kebab_case(use_case_name)
            use_case_exports.append((use_case_name, use_case_file_name))
        index_content = self._generate_index(context, use_case_exports)
        write_file(index_file, index_content)
        files.append(index_file)

        context.logger.info(f"Generated {len(files)} use case files for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _resolve_operation_alias(
        self,
        context: GenerationContext,
        operation_id: str,
        operation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Resolve operation alias - aliased ops delegate to another use case, no own file."""
        aliases = getattr(context.domain, "operation_aliases", None) or {}
        alias_cfg = aliases.get(operation_id)
        if alias_cfg:
            return {"delegate_to": alias_cfg.delegate_to, "input_merge": alias_cfg.input_merge or {}}
        x_codegen = operation.get("x-codegen") or {}
        if isinstance(x_codegen, dict) and x_codegen.get("delegateTo"):
            return {"delegate_to": x_codegen["delegateTo"], "input_merge": x_codegen.get("inputMerge") or {}}
        return None

    def _extract_entity_name_from_schema(self, operation: Dict[str, Any], context: GenerationContext) -> Optional[str]:
        """
        Extract entity name from operation response schema.

        Args:
            operation: OpenAPI operation dictionary
            context: Generation context

        Returns:
            Entity name from schema or None
        """
        from ...utils.openapi import get_response_schema_name
        from ...generators.core.repositories.entity_extractor import EntityExtractor

        # Try to get entity name from response schema
        response_schema_name = get_response_schema_name(operation, context.spec, "200")
        if not response_schema_name:
            response_schema_name = get_response_schema_name(operation, context.spec, "201")

        if response_schema_name:
            # Remove common suffixes
            entity_name = response_schema_name.replace("Response", "").replace("Result", "").replace("Output", "")
            return entity_name

        return None

    def _extract_request_field_names(self, operation: Dict[str, Any], context: GenerationContext) -> List[str]:
        """
        Extract field names from operation request body schema.

        Args:
            operation: OpenAPI operation dictionary
            context: Generation context

        Returns:
            List of field names from request schema
        """
        request_info = SchemaFieldExtractor.get_request_fields(operation, context.spec)
        return request_info.get("fields", [])

    def _extract_response_field_names(self, operation: Dict[str, Any], context: GenerationContext, status_code: str = "200") -> List[str]:
        """
        Extract field names from operation response schema.

        Args:
            operation: OpenAPI operation dictionary
            context: Generation context
            status_code: HTTP status code

        Returns:
            List of field names from response schema
        """
        response_info = SchemaFieldExtractor.get_response_fields(operation, context.spec, status_code)
        return response_info.get("fields", [])

    def _extract_path_parameters(self, operation: Dict[str, Any], context: GenerationContext, path: Optional[str] = None) -> List[str]:
        """
        Extract path parameter names from operation.

        Args:
            operation: OpenAPI operation dictionary
            context: Generation context
            path: Optional path string (e.g., "/v1/orgs/{orgId}/providers/{providerAccountId}")

        Returns:
            List of path parameter names (excluding common org-scoped parameters like orgId)
        """
        path_params = []

        # Always exclude tenant orgId. Path-item params are often only on the path string
        # (not copied onto the operation), so we cannot rely solely on operation.parameters
        # to discover OrgIdPath refs — otherwise orgId stays in the list and
        # `_find_id_field_in_request` picks it because "id" is a substring of "orgId".
        common_org_params = {"orgId"}
        parameters = operation.get("parameters", []) or []
        for param in parameters:
            if isinstance(param, dict):
                param_ref = param.get("$ref", "")
                param_name = param.get("name", "")
                # Check if it references OrgId parameter component
                if "#/components/parameters/OrgId" in param_ref or param_name == "orgId":
                    common_org_params.add("orgId")
            elif isinstance(param, str) and param.startswith("#"):
                # It's a $ref - check if it's OrgId
                if "#/components/parameters/OrgId" in param or "OrgId" in param:
                    common_org_params.add("orgId")

        # Extract from path string if available (most reliable)
        if path:
            import re
            # Find all {paramName} patterns in path
            matches = re.findall(r'\{([^}]+)\}', path)
            for param_name in matches:
                # Exclude common org-scoped parameters (derived from OpenAPI, not hardcoded!)
                if param_name not in common_org_params:
                    path_params.append(param_name)

        # Also check operation parameters (for completeness)
        for param in parameters:
            if isinstance(param, dict):
                param_in = param.get("in")
                if param_in == "path":
                    param_name = param.get("name")
                    param_ref = param.get("$ref", "")
                    # Exclude if it's a common org parameter or references OrgId
                    is_org_param = (
                        param_name in common_org_params or
                        "#/components/parameters/OrgId" in param_ref
                    )
                    if param_name and not is_org_param and param_name not in path_params:
                        path_params.append(param_name)
            elif isinstance(param, str) and param.startswith("#"):
                # It's a $ref - resolve it
                from ...utils.openapi import resolve_ref
                resolved = resolve_ref(context.spec, param)
                if resolved and resolved.get("in") == "path":
                    param_name = resolved.get("name")
                    param_ref = param if isinstance(param, str) else ""
                    # Exclude if it references OrgId
                    is_org_param = (
                        param_name in common_org_params or
                        "#/components/parameters/OrgId" in param_ref or
                        "OrgId" in param_ref
                    )
                    if param_name and not is_org_param and param_name not in path_params:
                        path_params.append(param_name)

        return path_params

    def _find_create_method_for_resource(self, operation_id: str, context: GenerationContext) -> Optional[str]:
        """
        Find the create method name for the same resource.

        Args:
            operation_id: Current operation ID
            context: Generation context

        Returns:
            Create method name or None
        """
        from ...utils.openapi import extract_operations
        from ...utils.naming import NamingConvention

        current_resource = NamingConvention.resource_for_grouping(operation_id)
        operations = extract_operations(context.spec)

        for op_data in operations:
            op_id = op_data["operation_id"]
            op_resource = NamingConvention.resource_for_grouping(
                op_id, op_data.get("path")
            )
            op_verb = extract_verb_from_operation_id(op_id)

            if op_resource == current_resource and op_verb == "create":
                return camel_case(op_id)

        return None

    def _find_get_method_for_resource(self, operation_id: str, context: GenerationContext) -> Optional[str]:
        """
        Find the get method name for the same resource.

        Args:
            operation_id: Current operation ID
            context: Generation context

        Returns:
            Get method name or None
        """
        from ...utils.openapi import extract_operations
        from ...utils.naming import NamingConvention

        current_resource = NamingConvention.resource_for_grouping(operation_id)
        operations = extract_operations(context.spec)

        for op_data in operations:
            op_id = op_data["operation_id"]
            op_resource = NamingConvention.resource_for_grouping(
                op_id, op_data.get("path")
            )
            op_verb = extract_verb_from_operation_id(op_id)

            if op_resource == current_resource and op_verb == "get":
                return camel_case(op_id)

        return None

    def _find_list_method_for_resource(self, operation_id: str, context: GenerationContext) -> Optional[str]:
        """
        Find the list method name for the same resource (fallback when get doesn't exist).

        Returns:
            List method name or None
        """
        from ...utils.openapi import extract_operations
        from ...utils.naming import NamingConvention

        current_resource = NamingConvention.resource_for_grouping(operation_id)
        operations = extract_operations(context.spec)

        for op_data in operations:
            op_id = op_data["operation_id"]
            op_resource = NamingConvention.resource_for_grouping(
                op_id, op_data.get("path")
            )
            op_verb = extract_verb_from_operation_id(op_id)

            if op_resource == current_resource and op_verb == "list":
                return camel_case(op_id)

        return None

    def _resolve_fetch_method_for_resource(
        self, operation_id: str, resource_var: str, context: GenerationContext
    ) -> Optional[tuple]:
        """
        Resolve the method to fetch an entity by id. Returns (method_name, use_list_find_pattern)
        or None when neither get nor list exists (caller should skip pre-fetch).
        """
        get_method = self._find_get_method_for_resource(operation_id, context) if operation_id and context else None
        if get_method:
            return (get_method, False)

        list_method = self._find_list_method_for_resource(operation_id, context) if operation_id and context else None
        if list_method:
            return (list_method, True)

        return None

    def _find_id_field_in_request(self, operation: Dict[str, Any], context: GenerationContext, path: Optional[str] = None) -> Optional[str]:
        """
        Find the ID field name in request schema (for lookups).
        Checks path parameters first, then request body fields.

        Args:
            operation: OpenAPI operation dictionary
            context: Generation context
            path: Optional path string

        Returns:
            ID field name or None
        """
        # Actor/tenant stamps — never treat as the resource primary key.
        non_entity = SchemaFieldExtractor._NON_ENTITY_ID_FIELDS

        # First check path parameters (most common for ID fields).
        # Prefer *Id resource params; never treat orgId as the entity id.
        path_params = self._extract_path_parameters(operation, context, path)
        for param in path_params:
            if param.endswith("Id") and param not in non_entity:
                return param
        for param in path_params:
            pl = param.lower()
            if param not in non_entity and ("id" in pl or "account" in pl):
                return param

        # Then check request body fields (skip actor/tenant stamps).
        request_fields = self._extract_request_field_names(operation, context)
        for field in request_fields:
            if field in non_entity:
                continue
            if field.endswith("Id") or field.endswith("ID") or field.lower() in ("id", "_id", "uuid", "key"):
                return field

        return None

    def _generate_field_access_code(self, field_name: str, prefix: str = "input") -> str:
        """
        Generate TypeScript field access code.

        Args:
            field_name: Field name from schema
            prefix: Prefix (default: "input")

        Returns:
            TypeScript code to access the field
        """
        return f"{prefix}.{field_name}"

    def _generate_field_validation_code(self, field_name: str, field_type: str = "string") -> str:
        """
        Generate TypeScript validation code for a required field.

        Args:
            field_name: Field name from schema
            field_type: Field type (for appropriate validation)

        Returns:
            TypeScript validation code
        """
        if field_type == "string":
            return f"""    if (!input.{field_name}) {{
      throw new ValidationError("{field_name} is required");
    }}"""
        else:
            return f"""    if (input.{field_name} === undefined || input.{field_name} === null) {{
      throw new ValidationError("{field_name} is required");
    }}"""

    def _generate_token_extraction_code(self, token_fields: List[str], request_fields: List[str]) -> str:
        """
        Generate code to extract token/credential values from entity or input.
        Completely generic - works for any token/credential field names.

        Args:
            token_fields: List of token-related field names
            request_fields: All request field names

        Returns:
            TypeScript code to extract token value
        """
        if not token_fields:
            # Try to find sensitive fields from OpenAPI schema properties
            # Check for fields with format: password or x-sensitive extensions
            # Fallback: use field name patterns as heuristic (should ideally come from schema)
            # TODO: Derive from OpenAPI schema properties (format: password, x-sensitive: true, etc.)
            token_patterns = ["token", "refresh", "credential", "password", "secret"]
            for field in request_fields:
                if any(pattern in field.lower() for pattern in token_patterns):
                    token_fields.append(field)

        if not token_fields:
            return "input.token || entity.token || (entity as any).tokenSet?.token"

        # Generate extraction code for all token fields
        extraction_parts = []
        for field in token_fields:
            extraction_parts.append(f"input.{field}")
            extraction_parts.append(f"entity.{field}")
            extraction_parts.append(f"(entity as any).{field}")
            # Also check nested structures
            extraction_parts.append(f"(entity as any).tokenSet?.{field}")
            extraction_parts.append(f"(entity as any).credentials?.{field}")

        return " || ".join(extraction_parts) if extraction_parts else "null"

    def _derive_variable_name_from_port(self, port_name: str) -> str:
        """
        Derive variable name from port name generically.

        Uses PortDetermination.derive_variable_name() for consistency.
        No special cases - fully generic.

        Args:
            port_name: Port interface name (e.g., "ProviderAccountRepository", "ContentPublisher")

        Returns:
            Variable name in camelCase (e.g., "providerAccountRepository", "contentPublisher")
        """
        # Use shared utility for consistency - no special cases
        return PortDetermination.derive_variable_name(port_name)

    def _build_dep_to_var_map(self, dependencies: List[str]) -> Dict[str, str]:
        """
        Build mapping from port name to constructor variable name, with deduplication.
        When multiple ports derive to same base (e.g. PromptTemplateRepository + PromptTemplatePublisher),
        append port-type suffix: promptTemplateRepository, promptTemplatePublisher.
        Mirrors port_adapter.py logic (lines 284-322).
        """
        base_name_counts: Dict[str, int] = {}
        for dep in dependencies:
            base = self._derive_variable_name_from_port(dep)
            base_name_counts[base] = base_name_counts.get(base, 0) + 1
        dep_to_var: Dict[str, str] = {}
        used_var_names: set[str] = set()
        for dep in dependencies:
            dep_var = self._derive_variable_name_from_port(dep)
            if base_name_counts.get(dep_var, 0) > 1:
                port_suffix = ""
                if dep.endswith("Repository"):
                    port_suffix = "Repository"
                elif dep.endswith("Publisher"):
                    port_suffix = "Publisher"
                elif dep.endswith("Client"):
                    port_suffix = "Client"
                elif dep.endswith("Refresher"):
                    port_suffix = "Refresher"
                dep_var = f"{dep_var}{port_suffix}" if port_suffix else f"{dep_var}Port"
            if dep_var in used_var_names:
                dep_var = f"{dep_var}{len(used_var_names)}"
            used_var_names.add(dep_var)
            dep_to_var[dep] = dep_var
        return dep_to_var

    def _get_domain_id_method(self, context: GenerationContext) -> str:
        """
        Get the IdGeneratorService method name from OpenAPI spec info.x-domain.
        Example: x-domain "act" -> "actId", "chn" -> "chnId"
        """
        from ...utils.openapi import get_domain_id_method
        return get_domain_id_method(context.spec, context.domain_name)

    def _generate_use_case_content(
        self,
        context: GenerationContext,
        use_case_name: str,
        operation_id: str,
        operation: Dict[str, Any],
        verb: str,
        resource: str,
        dependencies: List[str],
        header: str
    ) -> str:
        """Generate use case class content"""
        # Use canonical DTO type naming (matches DTO and port generators)
        input_type = dto_input_type_name(operation_id)
        output_type = dto_output_type_name(operation_id)

        # Generate constructor parameters and dep->var mapping (for body generation)
        dep_to_var = self._build_dep_to_var_map(dependencies)
        constructor_params = []
        constructor_params.append("    private readonly context: ExecutionContextService")
        constructor_params.append("    private readonly idGenerator: IdGeneratorService")
        for dep, dep_var in dep_to_var.items():
            constructor_params.append(f"    private readonly {dep_var}: {dep}")

        constructor_params_str = ",\n".join(constructor_params)

        # Generate imports
        port_imports = ", ".join(sorted(set(dependencies))) if dependencies else ""
        dto_imports = f"{input_type}, {output_type}"

        # Determine repo_var for method generation (use deduplicated names)
        repo_var_for_body = None
        for dep in dependencies:
            if dep.endswith("Repository") and repo_var_for_body is None:
                repo_var_for_body = dep_to_var.get(dep)

        # Generate use case body based on verb
        # Pass path from op_data if available (for path parameter extraction)
        path = None
        for op_data in extract_operations(context.spec):
            if op_data["operation_id"] == operation_id:
                path = op_data.get("path")
                break

        # Determine policy name first (before generating body, so we can pass it to body generation)
        policy_name = None
        if verb in ["publish", "create", "update", "delete"]:
            policy_name = f"Can{pascal_case(verb)}"
        
        use_case_body = self._generate_use_case_body(verb, resource, dependencies, dep_to_var, input_type, output_type, operation_id, operation, context, path, repo_var_for_body, context.domain_name, policy_name)

        # Determine error imports needed - scan the generated body for actual error usage
        error_imports = self._determine_error_imports(operation, operation_id, use_case_body)

        # Determine policy imports needed - scan the generated body for actual policy usage
        policy_imports = self._determine_policy_imports(verb, use_case_body)

        # Only include port import if there are dependencies
        port_import_line = f"import type {{ {port_imports} }} from \"../ports\";\n" if port_imports else ""

        # Get domain ID method name for correlation ID generation
        domain_id_method = self._get_domain_id_method(context)

        return f"""{header}/**
 * {use_case_name} Use Case
 *
 * DDD: Application use case for {verb} {resource}.
 * Orchestrates the business flow using ports (interfaces).
 */

import type {{ {dto_imports} }} from "../dto/{kebab_case(resource)}.dto";
import type {{ ExecutionContextService, IdGeneratorService }} from "@ddd/services/_shared/index.js";
{port_import_line}{f"import {{ {error_imports} }} from \"../errors\";\n" if error_imports else ""}{policy_imports}
export class {use_case_name} {{
  constructor(
{constructor_params_str}
  ) {{}}

  async execute(input: {input_type}): Promise<{output_type}> {{
    // Generate correlation ID for this request (domain-prefixed format: {{domain_prefix}}_{{ulid}})
    const correlationId = this.idGenerator.{domain_id_method}();

{use_case_body}
  }}
}}
"""

    def _generate_use_case_body(
        self,
        verb: str,
        resource: str,
        dependencies: List[str],
        dep_to_var: Dict[str, str],
        input_type: str,
        output_type: str,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: Optional[str] = None,
        repo_var: Optional[str] = None,
        domain_name: Optional[str] = None,
        policy_name: Optional[str] = None
    ) -> str:
        """Generate use case method body based on verb"""
        operation_id_lower = operation_id.lower()
        resource_var = camel_case(resource)

        # Find port variables using dep_to_var (handles deduplication for same-base ports)
        repo_var = None
        publisher_var = None
        client_var = None
        refresher_var = None

        for dep in dependencies:
            dep_var = dep_to_var.get(dep) or self._derive_variable_name_from_port(dep)

            # Categorize dependencies by suffix pattern only (no hardcoded domain-specific checks)
            if dep.endswith("Repository"):
                if repo_var is None:
                    repo_var = dep_var  # Use first repository found
            elif dep.endswith("Publisher"):
                publisher_var = dep_var
            elif dep.endswith("Client"):
                client_var = dep_var
            elif dep.endswith("Refresher"):
                refresher_var = dep_var

        # Determine port types from dependencies (generic, not hardcoded domain-specific names)
        has_publisher = publisher_var is not None
        has_refresher = refresher_var is not None
        has_client = client_var is not None
        has_repository = repo_var is not None

        # Generate body based on verb + port types (completely generic - no hardcoded operation names)
        if verb == "create":
            # Check if this create operation uses a port (determined from OpenAPI tags/patterns)
            if has_publisher:
                # Create operation that uses a publisher port (generic - works for any publisher)
                return self._generate_create_with_port_body(
                    repo_var, publisher_var, resource_var, output_type, operation, context, path, "Publisher", domain_name
                )
            elif has_client:
                # Create operation that uses a client port (generic - works for any client)
                return self._generate_create_with_port_body(
                    repo_var, client_var, resource_var, output_type, operation, context, path, "Client", domain_name
                )
            else:
                # Standard create operation
                return self._generate_create_body(repo_var, resource_var, output_type, operation_id, operation, context, path, domain_name, policy_name)
        elif verb == "update":
            if has_refresher:
                return self._generate_update_with_port_body(
                    repo_var, refresher_var, resource_var, output_type, operation, context, path, "Refresher", domain_name
                )
            # Refresh* operations (e.g. RefreshOrgIdentitySession) use a single repo method; delegate, don't do get+update
            if operation_id_lower.startswith("refresh") and has_repository and repo_var:
                return self._generate_repository_delegate_body(repo_var, operation_id, output_type, path)
            # Operation-scoped repo (e.g. EnableEventRuleRepository) has only one method; use delegate, not get+policy+update
            repo_port_name = next((d for d in dependencies if d.endswith("Repository")), None)
            if (
                repo_port_name
                and repo_var
                and PortDetermination.normalize_port_name_to_resource_scoped(repo_port_name) != repo_port_name
            ):
                return self._generate_repository_delegate_body(repo_var, operation_id, output_type, path)
            # Standard update operation (resource-scoped repo with get + update)
            return self._generate_update_body(repo_var, resource_var, output_type, operation_id, operation, context, path, domain_name, policy_name)
        elif verb == "delete":
            return self._generate_delete_body(repo_var, resource_var, output_type, operation_id, operation, context, path, domain_name, policy_name)
        elif verb == "get":
            return self._generate_get_body(repo_var, resource_var, output_type, operation_id, operation, context, path, domain_name)
        elif verb == "list":
            return self._generate_list_body(repo_var, resource_var, output_type, operation_id, operation, context, path, domain_name)
        elif has_repository and repo_var:
            # Non-CRUD verb with repository (export, enable, disable, test, cancel, etc.): delegate to port
            return self._generate_repository_delegate_body(
                repo_var, operation_id, output_type, path
            )
        else:
            return self._generate_generic_body(verb, resource_var, output_type, domain_name)

    def _generate_create_with_port_body(
        self,
        repo_var: Optional[str],
        port_var: str,
        resource_var: str,
        output_type: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: Optional[str],
        port_type: str,
        domain_name: Optional[str] = None
    ) -> str:
        """
        Generate create use case body that uses a port (Publisher, Client, etc.).
        Completely generic - works for any port type determined from OpenAPI tags/patterns.
        Handles two patterns:
        1. Load entity first, then call port (e.g., Publisher pattern)
        2. Call port first, then create entity (e.g., Client callback pattern)
        """
        if not port_var:
            return """    // TODO: Implement create logic with port
    throw new Error("Use case not yet implemented");"""

        # Extract entity name from schema for error messages
        entity_name = self._extract_entity_name_from_schema(operation, context) or "Entity"

        # Extract path parameters
        path_params = self._extract_path_parameters(operation, context, path)
        id_field = self._find_id_field_in_request(operation, context, path) or (path_params[0] if path_params else "id")

        # Extract request field names from schema
        request_info = SchemaFieldExtractor.get_request_fields(operation, context.spec)
        request_fields = request_info.get("fields", [])
        required_fields = request_info.get("required", set())

        # Extract response field names from schema
        response_info = SchemaFieldExtractor.get_response_fields(operation, context.spec, "200")
        if not response_info.get("fields"):
            response_info = SchemaFieldExtractor.get_response_fields(operation, context.spec, "201")
        response_fields = response_info.get("fields", [])

        # Extract method names from operation IDs
        operation_id = operation.get("operationId", "")
        port_method = camel_case(operation_id) if operation_id else f"create{pascal_case(resource_var)}"

        # Determine pattern: check if response contains entity fields (suggests entity creation after port call)
        # vs. if path has ID param (suggests loading entity before port call)
        has_id_in_path = bool(path_params)
        response_has_entity_fields = any(field in response_fields for field in ["account", "entity", "user", "tokenSet"])

        # Pattern 1: Load entity first, then call port (Publisher pattern)
        fetch_result = self._resolve_fetch_method_for_resource(
            operation_id or "", resource_var, context
        ) if (has_id_in_path and repo_var) else None
        if has_id_in_path and repo_var and fetch_result:
            fetch_method, use_list_find = fetch_result
            id_access = self._generate_field_access_code(id_field)
            entity_var = "entity"
            id_var = f"{id_field.replace('Id', '').lower()}Id" if id_field.endswith('Id') else f"{id_field}Value"

            if use_list_find:
                list_input = "{ orgId: this.context.getOrgId(), correlationId } as any"
                find_pred = f"(item: any) => (item?.id ?? item?.['{id_field}']) == {id_var}"
                entity_load_code = f"""    const {id_var} = (input as any).{id_field};
    const listResult = await this.{repo_var}.{fetch_method}({list_input});
    const {entity_var} = (Array.isArray((listResult as any)?.data?.items) ? (listResult as any).data.items : (Array.isArray((listResult as any)?.data) ? (listResult as any).data : [])).find({find_pred});
    if (!{entity_var}) {{
      throw new NotFoundError("{entity_name} not found");
    }}

"""
            else:
                entity_load_code = f"""    // Load entity from repository (pass correlation ID for response meta)
    const {entity_var} = await this.{repo_var}.{fetch_method}({{ {id_field}: {id_access}, correlationId }} as any);
    if (!{entity_var}) {{
      throw new NotFoundError("{entity_name} not found");
    }}

"""

            # Build request object dynamically from extracted fields
            request_obj_fields = []
            for field in request_fields:
                if field not in path_params:  # Don't include path params in request body
                    request_obj_fields.append(f"      {field}: input.{field},")
            request_obj_fields.append(f"      {entity_var}: {entity_var},")
            request_obj = "\n".join(request_obj_fields) if request_obj_fields else "      // No additional fields"

            # Build response object dynamically from extracted fields
            response_obj_fields = []
            for field in response_fields:
                if field not in ["data", "meta"]:  # Skip envelope fields
                    response_obj_fields.append(f"      {field}: result.{field},")
            response_obj = "\n".join(response_obj_fields) if response_obj_fields else "      // Response fields"

            # Generate validation for required fields
            validation_code = []
            for field in required_fields:
                validation_code.append(self._generate_field_validation_code(field))
            validation_str = "\n".join(validation_code) if validation_code else ""

            return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
{entity_load_code}{validation_str}
    const result = await this.{port_var}.{port_method}({{
{request_obj}
    }});

    return {{
{response_obj}
    }};"""

        # Pattern 2: Call port first, then create entity (Client callback pattern)
        elif response_has_entity_fields and repo_var:
            create_method = self._find_create_method_for_resource(operation_id, context) or f"create{pascal_case(resource_var)}"

            # Build port request object dynamically from extracted fields
            port_request_fields = []
            for field in request_fields:
                if field not in path_params:
                    port_request_fields.append(f"      {field}: input.{field},")
            port_request_obj = "\n".join(port_request_fields) if port_request_fields else "      // No request fields"

            # Generate validation for required fields
            validation_code = []
            for field in required_fields:
                validation_code.append(self._generate_field_validation_code(field))
            validation_str = "\n".join(validation_code) if validation_code else ""

            # Find token/entity fields in response to build entity creation object
            token_fields = []
            entity_fields = []
            for field in response_fields:
                # Check for sensitive fields (heuristic - should ideally come from OpenAPI schema properties)
                # TODO: Derive from OpenAPI schema properties (format: password, x-sensitive: true, etc.)
                if any(keyword in field.lower() for keyword in ["token", "credential", "access", "refresh"]):
                    token_fields.append(field)
                elif field not in ["data", "meta"]:
                    entity_fields.append(field)

            # Build entity creation object dynamically
            entity_create_fields = []
            if token_fields:
                token_obj_fields = []
                for field in token_fields:
                    token_obj_fields.append(f"        {field}: portResult.{field},")
                entity_create_fields.append(f"      tokenSet: {{\n{chr(10).join(token_obj_fields)}      }},")
            for field in entity_fields:
                if field not in token_fields:
                    entity_create_fields.append(f"      {field}: portResult.{field},")
            entity_create_obj = "\n".join(entity_create_fields) if entity_create_fields else "      // Entity fields"

            return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
{validation_str}

    const portResult = await this.{port_var}.{port_method}({{
{port_request_obj}
    }});

    // Create entity from port result (extract field names from response schema)
    const entity = await this.{repo_var}.{create_method}({{
{entity_create_obj}
    }} as any);

    return {{
      entity: entity as any,
      meta: {{
        correlationId,
        timestamp: new Date().toISOString()
      }}
    }};"""

        # Pattern 3: Just call port, no entity loading/creation
        else:
            # Build request object dynamically from extracted fields
            request_obj_fields = []
            for field in request_fields:
                if field not in path_params:
                    request_obj_fields.append(f"      {field}: input.{field},")
            request_obj = "\n".join(request_obj_fields) if request_obj_fields else "      // No additional fields"

            # Build response object dynamically from extracted fields
            response_obj_fields = []
            for field in response_fields:
                if field not in ["data", "meta"]:  # Skip envelope fields
                    response_obj_fields.append(f"      {field}: result.{field},")
            response_obj = "\n".join(response_obj_fields) if response_obj_fields else "      // Response fields"

            # Generate validation for required fields
            validation_code = []
            for field in required_fields:
                validation_code.append(self._generate_field_validation_code(field))
            validation_str = "\n".join(validation_code) if validation_code else ""

            return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
{validation_str}

    const result = await this.{port_var}.{port_method}({{
{request_obj}
    }});

    return {{
{response_obj}
    }};"""

    def _generate_update_with_port_body(
        self,
        repo_var: str,
        port_var: str,
        resource_var: str,
        output_type: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: Optional[str],
        port_type: str,
        domain_name: Optional[str] = None
    ) -> str:
        """
        Generate update use case body that uses a port (Refresher, etc.).
        Completely generic - works for any port type determined from OpenAPI tags/patterns.
        """
        if not repo_var or not port_var:
            return """    // TODO: Implement update logic with port
    throw new Error("Use case not yet implemented");"""

        # Extract entity name from schema for error messages
        entity_name = self._extract_entity_name_from_schema(operation, context) or "Entity"

        # Extract path parameters
        path_params = self._extract_path_parameters(operation, context, path)
        id_field = self._find_id_field_in_request(operation, context, path) or (path_params[0] if path_params else "id")
        id_access = self._generate_field_access_code(id_field)

        # Extract request field names from schema
        request_info = SchemaFieldExtractor.get_request_fields(operation, context.spec)
        request_fields = request_info.get("fields", [])

        # Extract response field names from schema
        response_info = SchemaFieldExtractor.get_response_fields(operation, context.spec, "200")
        response_fields = response_info.get("fields", [])

        # Extract method names from operation IDs
        operation_id = operation.get("operationId", "")
        fetch_result = self._resolve_fetch_method_for_resource(
            operation_id or "", resource_var, context
        )
        port_method = camel_case(operation_id) if operation_id else f"update{pascal_case(resource_var)}"

        # When no get/list exists, cannot load entity - call port directly (e.g. patch without pre-fetch)
        if not fetch_result:
            return f"""    // No get/list for this resource - call port directly
    const result = await this.{port_var}.{port_method}({{ ...input, correlationId }} as any);
    return result as {output_type};"""

        fetch_method, use_list_find = fetch_result

        # Find token/refresh field names from request schema
        token_fields = []
        for field in request_fields:
            # Check for sensitive fields (heuristic - should ideally come from OpenAPI schema properties)
            # TODO: Derive from OpenAPI schema properties (format: password, x-sensitive: true, etc.)
            if any(keyword in field.lower() for keyword in ["token", "refresh", "credential"]):
                token_fields.append(field)

        # Build port request object dynamically
        port_request_fields = []
        for field in request_fields:
            if field not in path_params:
                port_request_fields.append(f"      {field}: input.{field},")
        port_request_obj = "\n".join(port_request_fields) if port_request_fields else "      // No additional fields"

        # Generate token extraction code
        token_extraction_code = self._generate_token_extraction_code(token_fields, request_fields)

        id_var = f"{id_field.replace('Id', '').lower()}Id" if id_field.endswith('Id') else f"{id_field}Value"
        if use_list_find:
            list_input = "{ orgId: this.context.getOrgId(), correlationId } as any"
            find_pred = f"(item: any) => (item?.id ?? item?.['{id_field}']) == {id_var}"
            entity_load = f"""    const {id_var} = (input as any).{id_field};
    const listResult = await this.{repo_var}.{fetch_method}({list_input});
    const entity = (Array.isArray((listResult as any)?.data?.items) ? (listResult as any).data.items : (Array.isArray((listResult as any)?.data) ? (listResult as any).data : [])).find({find_pred});"""
        else:
            entity_load = f"    const entity = await this.{repo_var}.{fetch_method}({{ {id_field}: {id_access}, correlationId }} as any);"

        return f"""    // All field names extracted from OpenAPI spec
{entity_load}
    if (!entity) {{
      throw new NotFoundError(`{entity_name} not found: ${{{id_var if use_list_find else id_access}}}`);
    }}

    // Extract token/credential fields from entity or input (field names from schema)
    const entityData = entity as any;
    const tokenValue = {token_extraction_code}

    if (!tokenValue) {{
      throw new ValidationError(`Token/credential not available for {entity_name.lower()} ${{{id_access}}}`);
    }}

    const result = await this.{port_var}.{port_method}({{
{port_request_obj}
    }});

    // Update entity with result (extract field names from response schema, pass correlation ID)
    await this.{repo_var}.update({{ {id_field}: {id_access}, correlationId }}, {{
      ...entity,
      ...result
    }} as any);

    return {{
      entity: {{
        ...entity,
        ...result
      }} as any,
      meta: {{
        correlationId,
        timestamp: new Date().toISOString()
      }}
    }};"""


    def _generate_create_body(self, repo_var: str, resource_var: str, output_type: str, operation_id: str = "", operation: Optional[Dict[str, Any]] = None, context: Optional[GenerationContext] = None, path: Optional[str] = None, domain_name: Optional[str] = None, policy_name: Optional[str] = None) -> str:
        """Generate create use case body - extracts field names from OpenAPI spec"""
        if not repo_var or not operation or not context:
            return """    // TODO: Implement create logic
    throw new Error("Use case not yet implemented");"""

        # Extract request field names and required fields from schema
        request_info = SchemaFieldExtractor.get_request_fields(operation, context.spec)
        request_fields = request_info.get("fields", [])
        required_fields = request_info.get("required", set())

        # Extract method name from operation_id
        method_name = camel_case(operation_id) if operation_id else f"create{pascal_case(resource_var)}"

        # Generate validation code for required fields dynamically
        validation_code = []
        for field in required_fields:
            validation_code.append(self._generate_field_validation_code(field))
        validation_str = "\n".join(validation_code) if validation_code else "    // No required field validations"

        # Check if path contains orgId (indicates org-scoped resource)
        needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)
        
        # Get domain ID method for entity ID generation (from spec info.x-domain)
        domain_id_method = self._get_domain_id_method(context) if context else "actId"
        
        # Generate entity ID in services layer using IdGeneratorService
        domain_label = context.domain_name if context else (domain_name or "activity")
        entity_id_generation = f"""    // Generate entity ID in services layer using IdGeneratorService ({domain_label} domain)
    const entityId = this.idGenerator.{domain_id_method}();"""
        
        # Add orgId, entity ID, actor stamp, and correlationId from context if needed.
        # Always pass both `id` and resource-shaped ids so adapters that key on
        # teamId/jobId/etc. still receive the generated entity id (P6 actor inject).
        actor_stamp = (
            "createdByActorId: (input as any).createdByActorId ?? this.context.getUserId(), "
            "createdByActorType: (input as any).createdByActorType ?? \"human\", "
        )
        resource_id_assign = ""
        try:
            entity_name = self._extract_entity_name_from_schema(operation, context) if operation else None
            schemas = ((context.spec or {}).get("components") or {}).get("schemas") or {}
            if entity_name and entity_name in schemas:
                id_field = SchemaFieldExtractor.find_id_field(schemas[entity_name], context.spec)
                if id_field and id_field != "id":
                    resource_id_assign = f"{id_field}: entityId, "
        except Exception:
            resource_id_assign = ""
        create_input = (
            "{ ...input, id: entityId, "
            + resource_id_assign
            + actor_stamp
            + "correlationId } as any"
        )
        if needs_org_id:
            create_input = (
                "{ ...input, id: entityId, "
                + resource_id_assign
                + actor_stamp
                + "orgId: this.context.getOrgId(), correlationId } as any"
            )

        # Generate policy check if policy is available
        policy_check = ""
        if policy_name:
            policy_check = f"""    // Check policy
    if (!{policy_name}.allow({{}} as any, "")) {{
      throw new PermissionDeniedError("Operation not allowed");
    }}

"""
        
        return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
    // Validate input
    if (!input) {{
      throw new ValidationError("Input is required");
    }}
{validation_str}{policy_check}{entity_id_generation}

    // Create entity via repository (pass ID and correlation ID for response meta)
    const entity = await this.{repo_var}.{method_name}({create_input});

    return entity as {output_type};"""

    def _generate_update_body(self, repo_var: str, resource_var: str, output_type: str, operation_id: str = "", operation: Optional[Dict[str, Any]] = None, context: Optional[GenerationContext] = None, path: Optional[str] = None, domain_name: Optional[str] = None, policy_name: Optional[str] = None) -> str:
        """Generate update use case body - extracts field names from OpenAPI spec"""
        if not repo_var or not operation or not context:
            return """    // TODO: Implement update logic
    throw new Error("Use case not yet implemented");"""

        # Prefer entity schema primary key (policyId) over incidental FKs in the
        # request body (enrollmentId) — request field order is not authoritative.
        entity_id = None
        try:
            schemas = ((context.spec or {}).get("components") or {}).get("schemas") or {}
            candidates = []
            entity_name = self._extract_entity_name_from_schema(operation, context)
            if entity_name:
                candidates.append(entity_name)
            # Resource-scoped port name (CapacityPolicy) is more reliable for put*
            if resource_var:
                from ...utils.naming import pascal_case
                candidates.append(pascal_case(resource_var))
                candidates.append(pascal_case(resource_var).replace("Policy", "") + "Policy")
            for name in candidates:
                if name and name in schemas:
                    entity_id = SchemaFieldExtractor.find_id_field(schemas[name], context.spec)
                    if entity_id:
                        break
        except Exception:
            entity_id = None
        path_params = self._extract_path_parameters(operation, context, path)
        id_field = (
            entity_id
            or self._find_id_field_in_request(operation, context, path)
            or (path_params[0] if path_params else "id")
        )
        id_access = self._generate_field_access_code(id_field)

        # Extract entity name from schema for error messages
        entity_name = self._extract_entity_name_from_schema(operation, context) or "Entity"

        # Generate method names from operation_id
        update_method = camel_case(operation_id) if operation_id else f"update{pascal_case(resource_var)}"

        # Resolve fetch method: getX if exists, else listX+find, or None when neither exists
        fetch_result = self._resolve_fetch_method_for_resource(
            operation_id or "", resource_var, context
        )

        # Check if path contains orgId (indicates org-scoped resource)
        needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)

        # Extract ID to variable after validation to help TypeScript type narrowing
        id_var = f"{id_field.replace('Id', '').lower()}Id" if id_field.endswith('Id') else f"{id_field}Value"

        if fetch_result:
            fetch_method, use_list_find = fetch_result
            if use_list_find:
                list_input = "{ orgId: this.context.getOrgId(), correlationId } as any"
                find_predicate = f"(item: any) => (item?.id ?? item?.['{id_field}']) == {id_var}"
                # List envelopes use data.items (not data as an array).
                fetch_code = f"""    const listResult = await this.{repo_var}.{fetch_method}({list_input});
    const listItems = Array.isArray((listResult as any)?.data?.items)
      ? (listResult as any).data.items
      : (Array.isArray((listResult as any)?.data) ? (listResult as any).data : []);
    const existing = listItems.find({find_predicate});"""
            else:
                get_params = f"{{ {id_field}: {id_var}, orgId: this.context.getOrgId(), correlationId }} as any"
                fetch_code = f"    const existing = await this.{repo_var}.{fetch_method}({get_params});"
            # put* ops are upserts — missing row is OK; create path runs in the adapter.
            is_put_upsert = bool(operation_id and operation_id.startswith("put"))
            if is_put_upsert:
                fetch_block = f"""
    // Load existing entity (optional for put upsert)
{fetch_code}
"""
            else:
                fetch_block = f"""
    // Load existing entity
{fetch_code}
    if (!existing) {{
      throw new NotFoundError(`{entity_name} not found: ${{{id_var}}}`);
    }}
"""
        else:
            # No get/list for this resource - skip pre-fetch, call update directly
            fetch_block = "    // No get/list operation for this resource - call update directly\n"
            is_put_upsert = bool(operation_id and operation_id.startswith("put"))

        # Build repository call parameters for update (include correlationId)
        update_input = "{ ...input, correlationId } as any"
        if needs_org_id:
            update_input = "{ ...input, orgId: this.context.getOrgId(), correlationId } as any"
        # P6: stamp actor on put upserts when body omits it
        if operation_id and operation_id.startswith("put"):
            update_input = (
                "{ ...input, orgId: this.context.getOrgId(), "
                "createdByActorId: (input as any).createdByActorId ?? this.context.getUserId(), "
                "createdByActorType: (input as any).createdByActorType ?? \"human\", "
                "correlationId } as any"
                if needs_org_id
                else "{ ...input, "
                "createdByActorId: (input as any).createdByActorId ?? this.context.getUserId(), "
                "createdByActorType: (input as any).createdByActorType ?? \"human\", "
                "correlationId } as any"
            )

        # Generate policy check if policy is available
        policy_check = ""
        if policy_name:
            policy_check = f"""    // Check policy
    if (!{policy_name}.allow({{}} as any, "")) {{
      throw new PermissionDeniedError("Operation not allowed");
    }}

"""

        # putCapacityPolicy may omit policyId (server generates); don't hard-require when put*
        id_required_block = ""
        if not (operation_id and operation_id.startswith("put") and id_field in ("policyId", "providerId")):
            id_required_block = f"""    if (!(input as any).{id_field}) {{
      throw new ValidationError("{id_field} is required");
    }}
    const {id_var} = (input as any).{id_field};
"""
        else:
            id_required_block = f"""    const {id_var} = (input as any).{id_field} ?? this.idGenerator.{self._get_domain_id_method(context) if context else "actId"}();
    (input as any).{id_field} = {id_var};
"""

        return f"""    // All field names extracted from OpenAPI spec
    // Validate input
    if (!input) {{
      throw new ValidationError("Input is required");
    }}
{id_required_block}{fetch_block}{policy_check}    // Update entity via repository (pass correlation ID for response meta)
    const updated = await this.{repo_var}.{update_method}({update_input});

    return updated as {output_type};"""

    def _generate_delete_body(self, repo_var: str, resource_var: str, output_type: str, operation_id: str = "", operation: Optional[Dict[str, Any]] = None, context: Optional[GenerationContext] = None, path: Optional[str] = None, domain_name: Optional[str] = None, policy_name: Optional[str] = None) -> str:
        """Generate delete use case body - extracts field names from OpenAPI spec"""
        if not repo_var or not operation or not context:
            return """    // TODO: Implement delete logic
    throw new Error("Use case not yet implemented");"""

        # Extract path parameters to find ID field
        path_params = self._extract_path_parameters(operation, context, path)
        id_field = self._find_id_field_in_request(operation, context, path) or (path_params[0] if path_params else "id")
        id_access = self._generate_field_access_code(id_field)

        # Extract entity name from schema for error messages
        entity_name = self._extract_entity_name_from_schema(operation, context) or "Entity"

        # Generate method names from operation_id
        delete_method = camel_case(operation_id) if operation_id else f"delete{pascal_case(resource_var)}"

        # Resolve fetch method: getX if exists, else listX+find, or None when neither exists
        fetch_result = self._resolve_fetch_method_for_resource(
            operation_id or "", resource_var, context
        )

        # Check if path contains orgId (indicates org-scoped resource)
        needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)

        # Extract ID to variable after validation to help TypeScript type narrowing
        id_var = f"{id_field.replace('Id', '').lower()}Id" if id_field.endswith('Id') else f"{id_field}Value"

        if fetch_result:
            fetch_method, use_list_find = fetch_result
            if use_list_find:
                list_input = "{ orgId: this.context.getOrgId(), correlationId } as any"
                find_predicate = f"(item: any) => (item?.id ?? item?.['{id_field}']) == {id_var}"
                fetch_code = f"""    const listResult = await this.{repo_var}.{fetch_method}({list_input});
    const existing = (Array.isArray((listResult as any)?.data?.items) ? (listResult as any).data.items : (Array.isArray((listResult as any)?.data) ? (listResult as any).data : [])).find({find_predicate});"""
            else:
                get_params = f"{{ {id_field}: {id_var}, orgId: this.context.getOrgId(), correlationId }} as any"
                fetch_code = f"    const existing = await this.{repo_var}.{fetch_method}({get_params});"
            fetch_block = f"""
    // Load existing entity
{fetch_code}
    if (!existing) {{
      throw new NotFoundError(`{entity_name} not found: ${{{id_var}}}`);
    }}
"""
        else:
            # No get/list for this resource - skip pre-fetch, call delete directly
            fetch_block = "    // No get/list operation for this resource - call delete directly\n"

        # Build repository call parameters for delete (use extracted ID variable)
        if needs_org_id:
            delete_params = f"{{ {id_field}: {id_var}, orgId: this.context.getOrgId(), correlationId }} as any"
        else:
            delete_params = f"{{ {id_field}: {id_var}, correlationId }} as any"

        # Generate policy check if policy is available
        policy_check = ""
        if policy_name:
            policy_check = f"""    // Check policy
    if (!{policy_name}.allow({{}} as any, "")) {{
      throw new PermissionDeniedError("Operation not allowed");
    }}

"""

        return f"""    // All field names extracted from OpenAPI spec
    // Validate input
    if (!input) {{
      throw new ValidationError("Input is required");
    }}
    if (!(input as any).{id_field}) {{
      throw new ValidationError("{id_field} is required");
    }}
    const {id_var} = (input as any).{id_field};
{fetch_block}{policy_check}    // Delete entity via repository (pass correlation ID for response meta)
    await this.{repo_var}.{delete_method}({delete_params});

    return {{}} as {output_type};"""

    def _generate_get_body(self, repo_var: str, resource_var: str, output_type: str, operation_id: str = "", operation: Optional[Dict[str, Any]] = None, context: Optional[GenerationContext] = None, path: Optional[str] = None, domain_name: Optional[str] = None) -> str:
        """Generate get use case body - extracts field names from OpenAPI spec"""
        if not repo_var or not operation or not context:
            return """    // TODO: Implement get logic
    throw new Error("Use case not yet implemented");"""

        # Extract path parameters to find ID field
        path_params = self._extract_path_parameters(operation, context, path)
        id_field = self._find_id_field_in_request(operation, context, path) or (path_params[0] if path_params else None)

        # Extract request field names from schema
        request_info = SchemaFieldExtractor.get_request_fields(operation, context.spec)
        request_fields = request_info.get("fields", [])

        # Determine method name from operation_id
        method_name = camel_case(operation_id) if operation_id else f"get{pascal_case(resource_var)}"

        # Extract entity name from schema for error messages
        entity_name = self._extract_entity_name_from_schema(operation, context) or "Entity"

        # Check if path contains orgId (indicates org-scoped resource that needs orgId)
        needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)
        
        # If there's an ID field (from path or request), validate and use it
        if id_field:
            id_access = self._generate_field_access_code(id_field)
            # Extract ID to variable after validation to help TypeScript type narrowing
            id_var = f"{id_field.replace('Id', '').lower()}Id" if id_field.endswith('Id') else f"{id_field}Value"
            # Build repository call parameters (use extracted ID variable)
            if needs_org_id:
                repo_params = f"{{ {id_field}: {id_var}, orgId: this.context.getOrgId(), correlationId }} as any"
            else:
                repo_params = f"{{ {id_field}: {id_var}, correlationId }} as any"
            
            return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
    // Validate input
    if (!input) {{
      throw new ValidationError("Input is required");
    }}
    if (!(input as any).{id_field}) {{
      throw new ValidationError("{id_field} is required");
    }}
    const {id_var} = (input as any).{id_field};

    // Load entity via repository (pass correlation ID for response meta)
    const entity = await this.{repo_var}.{method_name}({repo_params});
    if (!entity) {{
      throw new NotFoundError(`{entity_name} not found: ${{{id_var}}}`);
    }}

    return entity as {output_type};"""
        else:
            # No ID field - check if orgId is needed from path
            needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)
            repo_params = "{ ...input, correlationId } as any"
            if needs_org_id:
                repo_params = "{ ...input, orgId: this.context.getOrgId(), correlationId } as any"
            
            return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
    // Load entity via repository (no ID field - uses input directly, pass correlation ID for response meta)
    const entity = await this.{repo_var}.{method_name}({repo_params});
    if (!entity) {{
      throw new NotFoundError(`{entity_name} not found`);
    }}

    return entity as {output_type};"""

    def _generate_list_body(self, repo_var: str, resource_var: str, output_type: str, operation_id: str = "", operation: Optional[Dict[str, Any]] = None, context: Optional[GenerationContext] = None, path: Optional[str] = None, domain_name: Optional[str] = None) -> str:
        """Generate list use case body - extracts field names from OpenAPI spec"""
        if not repo_var or not operation or not context:
            return """    // TODO: Implement list logic
    throw new Error("Use case not yet implemented");"""

        # Extract request field names from schema (for filtering/pagination)
        request_info = SchemaFieldExtractor.get_request_fields(operation, context.spec)
        request_fields = request_info.get("fields", [])

        # Generate method name from operation_id
        method_name = camel_case(operation_id) if operation_id else f"list{pascal_case(resource_var)}"

        # Check if path contains orgId (indicates org-scoped resource)
        needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)
        list_input = "{ ...input, correlationId } as any"
        if needs_org_id:
            list_input = "{ ...input, orgId: this.context.getOrgId(), correlationId } as any"

        return f"""    // All field names extracted from OpenAPI spec: {', '.join(request_fields) if request_fields else 'none'}
    // List entities via repository
    const result = await this.{repo_var}.{method_name}({list_input});

    return result as {output_type};"""

    def _generate_repository_delegate_body(
        self,
        repo_var: str,
        operation_id: str,
        output_type: str,
        path: Optional[str] = None
    ) -> str:
        """Generate use case body that delegates to repository port (for export, enable, disable, test, cancel, etc.)."""
        method_name = camel_case(operation_id)
        needs_org_id = True  # ALS org; path {orgId} is validation-only (directory routes have no path orgId)
        call_input = "{ ...input, correlationId } as any"
        if needs_org_id:
            call_input = "{ ...input, orgId: this.context.getOrgId(), correlationId } as any"
        return f"""    // Delegate to repository port
    const result = await this.{repo_var}.{method_name}({call_input});
    return result as {output_type};"""

    def _generate_generic_body(self, verb: str, resource_var: str, output_type: str, domain_name: Optional[str] = None) -> str:
        """Generate generic use case body"""
        return f"""    // TODO: Implement {verb} logic for {resource_var}
    // 1. Validate input
    // 2. Load entities via repositories if needed
    // 3. Apply business rules/policies
    // 4. Call ports (adapters) for side effects
    // 5. Return output

    throw new Error("Use case not yet implemented");"""

    def _determine_error_imports(self, operation: Dict[str, Any], operation_id: str, use_case_body: str) -> str:
        """Determine which error classes to import by scanning the generated use case body for actual usage"""
        # List of all possible error types
        all_errors = ["ValidationError", "NotFoundError", "BadRequestError", "PermissionDeniedError", "ConflictError"]
        
        # Scan the generated body for which errors are actually used
        used_errors = []
        for error_type in all_errors:
            # Check if the error is used in the body (look for "throw new ErrorType" or "ErrorType(")
            if f"throw new {error_type}" in use_case_body or f"{error_type}(" in use_case_body:
                used_errors.append(error_type)
        
        # Only return errors that are actually used - don't default to anything
        # If no errors are used (e.g., list operations), return empty string
        if not used_errors:
            return ""
        
        return ", ".join(sorted(set(used_errors)))

    def _determine_policy_imports(self, verb: str, use_case_body: str) -> str:
        """Determine which policy classes to import by scanning the generated use case body for actual usage"""
        # Generic pattern for all verbs that need policies
        # Policy generator creates policies for: publish, create, update, delete
        # Policy files use kebab-case ending with .policy.ts (e.g., can-create.policy.ts)
        if verb in ["publish", "create", "update", "delete"]:
            policy_name = f"Can{pascal_case(verb)}"
            # Check if the policy is actually used in the body
            if f"{policy_name}.allow" in use_case_body or f"new {policy_name}" in use_case_body:
                policy_file_name = kebab_case(policy_name)
                return f'import {{ {policy_name} }} from "../policies/{policy_file_name}.policy";'
        return ""

    def _generate_index(self, context: GenerationContext, use_case_exports: List[tuple[str, str]]) -> str:
        """Generate use cases index file"""
        # Deduplicate use case exports by file name
        unique_exports = {}
        for use_case_name, file_name in use_case_exports:
            if file_name not in unique_exports:
                unique_exports[file_name] = use_case_name

        # Sort by file name
        sorted_exports = sorted(unique_exports.items())
        exports = "\n".join([f"export * from \"./{file_name}.usecase.js\";" for file_name, _ in sorted_exports])
        if not exports.strip():
            exports = "export {};"

        return f"""/**
 * {pascal_case(context.domain_name)} Use Cases
 *
 * DDD: Application use cases for {context.domain_name} domain.
 */

{exports}
"""
