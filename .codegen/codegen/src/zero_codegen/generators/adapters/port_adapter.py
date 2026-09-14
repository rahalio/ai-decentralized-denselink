"""
Port Adapter Generator - Generates port adapter implementations

Per DDD: Adapters implement ports from services layer.
These adapters handle infrastructure concerns (HTTP, database, external APIs).
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations, get_request_body_schema_name, get_response_schema_name
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id
from ...utils.port_determination import PortDetermination


class PortAdapterGenerator(BaseGenerator):
    """
    Generates port adapter implementations

    Pattern: Adapter implements port from services layer
    export class GenericProviderPublisherAdapter implements ProviderPublisher {
      async publishContent(params: PublishContentParams): Promise<PublishContentResult> {
        // implementation
      }
    }
    """

    @property
    def name(self) -> str:
        return "Port Adapter Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "port_adapter"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate port adapter files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "adapters" / "src" / context.domain_name
        
        # DynamoDB generator cleans the directory first, so we don't need to clean again
        # Just ensure directory exists
        ensure_directory(output_dir)

        # Extract operations to identify ports
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)

        # Get DDB repositories from spec (same logic as DynamoDB generator - no file reading)
        from ...generators.adapters.dynamodb_repository import DynamoDBRepositoryGenerator
        ddb_generator = DynamoDBRepositoryGenerator()
        ddb_repositories = ddb_generator._identify_repositories(operations, context)
        operation_to_ddb_repo = {}
        for repo_name, repo_info in ddb_repositories.items():
            for op_data in repo_info.get("operations", []):
                op_id = op_data.get("operation_id", "")
                if op_id:
                    operation_to_ddb_repo[op_id] = repo_name

        # Identify ports that need adapters
        ports = self._identify_ports(operations, context)

        # Generate adapter for each port
        adapter_filenames = []
        for port_name, port_info in ports.items():
            adapter_name = self._determine_adapter_name(port_name)
            adapter_filename = f"{kebab_case(adapter_name.replace('Adapter', ''))}.adapter.ts"
            adapter_file = output_dir / adapter_filename

            if (
                context.domain_name == "organization"
                and adapter_filename == "org-repository.adapter.ts"
            ):
                context.logger.info(
                    "Skipping generated org-repository.adapter.ts "
                    "(hand-maintained id===orgId normalization)"
                )
                adapter_filenames.append((port_name, adapter_filename))
                continue

            header = self.generate_header(
                context,
                f"{adapter_name} - Port Adapter Implementation"
            )

            adapter_content = self._generate_adapter_content(
                context,
                port_name,
                adapter_name,
                port_info,
                header,
                output_dir,
                operation_to_ddb_repo,
                ddb_repositories
            )

            write_file(adapter_file, adapter_content)
            files.append(adapter_file)
            adapter_filenames.append((port_name, adapter_filename))

        # Generate index.ts - only export DDB files that exist (avoids phantom exports when DDB gen skips)
        if adapter_filenames:
            index_file = output_dir / "index.ts"
            index_content = self._generate_adapters_index_from_spec(
                context, ddb_repositories, adapter_filenames, output_dir
            )
            write_file(index_file, index_content)
            files.append(index_file)

        context.logger.info(f"Generated {len(files)} port adapters for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _generate_adapters_index_from_spec(
        self,
        context: GenerationContext,
        ddb_repositories: Dict[str, Any],
        adapter_filenames: List[tuple],
        output_dir: Path
    ) -> str:
        """Generate full index.ts from spec. Only exports DDB files that exist (avoids phantom exports when DDB gen skips)."""
        header = self.generate_header(context, "DynamoDB repository adapters barrel export")
        exports = []
        # DDB exports: only include files that exist (port_adapter runs after DDB gen, so we can check)
        for repo_name in sorted(ddb_repositories.keys()):
            import_name = f"{kebab_case(repo_name.replace('Repository', ''))}-repository.ddb"
            ddb_path = output_dir / f"{import_name}.ts"
            if ddb_path.exists():
                exports.append(f'export * from "./{import_name}.js";')
        # Port adapter exports
        for port_name, filename in sorted(adapter_filenames):
            import_name = filename.replace(".ts", "")
            exports.append(f'export * from "./{import_name}.js";')
        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""

    def _identify_ports(
        self,
        operations: List[Dict[str, Any]],
        context: GenerationContext
    ) -> Dict[str, Dict[str, Any]]:
        """Identify ports that need adapters"""
        ports = {}

        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data["operation"]

            port_name = self._determine_port_name(
                operation_id, operation, context, path=op_data.get("path")
            )

            if port_name not in ports:
                ports[port_name] = {
                    "operations": [],
                }

            ports[port_name]["operations"].append(op_data)

        return ports

    def _determine_port_name(
        self,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: Optional[str] = None,
    ) -> str:
        """Determine port name from operation using shared utility"""
        return PortDetermination.determine_port_name(
            operation_id, operation, context, path=path
        )

    def _determine_adapter_name(self, port_name: str) -> str:
        """Determine adapter class name from port name using shared utility"""
        return PortDetermination.determine_adapter_name(port_name)

    def _generate_adapter_content(
        self,
        context: GenerationContext,
        port_name: str,
        adapter_name: str,
        port_info: Dict[str, Any],
        header: str,
        output_dir: Path,
        operation_to_ddb_repo: Dict[str, str],
        ddb_repositories: Dict[str, Any]
    ) -> str:
        """Generate port adapter content. Uses spec-based lookup for DDB repos (no file reading)."""
        operations = port_info["operations"]

        # Adapters should NOT import DTOs from services/dto
        # DTOs are application layer types. Adapters should only import:
        # 1. Port interfaces from services/ports
        # 2. Domain types from core (if needed for implementation)
        # 3. Infrastructure utilities from adapters/shared
        # The port interface signature already includes DTO types, so adapters don't need separate imports
        dto_imports = []

        # Build local dependency imports (DynamoDB repositories, HttpClient, etc.)
        # These are infrastructure imports, not services imports
        local_dependency_imports = []

        # Get ALL operations in the domain to find related ports
        from ...utils.openapi import extract_operations
        all_operations = extract_operations(context.spec)

        # Identify all ports in the domain from OpenAPI operations
        all_ports = {}
        for op_data in all_operations:
            op_id = op_data["operation_id"]
            op = op_data["operation"]
            identified_port_name = PortDetermination.determine_port_name(
                op_id, op, context, path=op_data.get("path")
            )
            if identified_port_name not in all_ports:
                all_ports[identified_port_name] = {
                    "operations": [],
                    "port_name": identified_port_name
                }
            all_ports[identified_port_name]["operations"].append(op_data)

        # Derive dependencies from port relationships (not hardcoded operation patterns!)
        # Only include dependencies that are actually needed, not all ports in the domain
        dependency_ports = []

        # Publishers typically need HttpClient for external API calls
        # Check if this port is a Publisher type
        needs_http = port_name.endswith("Publisher")

        # NOTE: We don't automatically add all repository/client/refresher ports as dependencies
        # because most adapters don't need them. Dependencies should only be added when:
        # 1. They're explicitly referenced in method implementations (future enhancement)
        # 2. They're needed for specific port types (e.g., Publishers need HttpClient)
        # 3. They're determined from OpenAPI schema relationships (future enhancement)
        
        # For now, only add dependencies that are explicitly needed:
        # - Publishers need HttpClient (handled above)
        # - Repository adapters only need their DDB repository (handled below)
        # - Other dependencies should be added only when method implementations require them

        # Collect all dependency port names for a single barrel import
        # Services now use barrel exports, so we can import all ports from the domain index
        dependency_port_names = [dep_port["port_name"] for dep_port in dependency_ports]

        # Generate constructor parameters from dependency ports
        constructor_params = []
        if needs_http:
            constructor_params.append("    private readonly http: HttpClient,")

        # Add dynamoClient as dependency if this port maps to a DDB repo.
        # Adapter encapsulates Ddb creation internally - api-server only imports adapter and passes dynamoClient.
        ddb_repo_var = None
        ddb_repo_class: Optional[str] = None
        if port_name.endswith("Repository") and operations:
            # Find DDB repo from operation->repo mapping (same source of truth as DynamoDB generator)
            repo_name = None
            for op_data in operations:
                op_id = op_data.get("operation_id", "")
                if op_id in operation_to_ddb_repo:
                    repo_name = operation_to_ddb_repo[op_id]
                    break
            if not repo_name and port_name in ddb_repositories:
                repo_name = port_name
            if not repo_name:
                normalized_port = PortDetermination.normalize_port_name_to_resource_scoped(port_name)
                if normalized_port in ddb_repositories:
                    repo_name = normalized_port
            if repo_name:
                resource_base = repo_name.replace("Repository", "")
                ddb_repo_class = f"{repo_name}Ddb"
                ddb_repo_var = "ddb"  # Internal field; adapter creates Ddb from dynamoClient
                ddb_repo_path = f"./{kebab_case(resource_base)}-repository.ddb.js"
                local_dependency_imports.append(f"import type {{ AdapterDynamoDBClient }} from \"../_shared/dynamodb-client-types.js\";")
                local_dependency_imports.append(f"import {{ {ddb_repo_class} }} from \"{ddb_repo_path}\";")
                constructor_params.append(f"    private readonly dynamoClient: AdapterDynamoDBClient,")

        # Add constructor params for all identified dependency ports
        # Track variable names to avoid duplicates
        used_var_names = set()
        for dep_port in dependency_ports:
            dep_port_name = dep_port["port_name"]
            # Derive variable name generically from port name (not hardcoded!)
            dep_var = PortDetermination.derive_variable_name(dep_port_name)
            # Handle reserved words (e.g., "eval" -> "evalRepository")
            if dep_var == "eval":
                dep_var = "evalRepository"
            # Ensure unique variable names by appending port type suffix if duplicate
            original_var = dep_var
            counter = 1
            while dep_var in used_var_names:
                # Append port type suffix to make it unique (Repository, Client, Publisher, Refresher)
                port_suffix = ""
                if dep_port_name.endswith("Repository"):
                    port_suffix = "Repository"
                elif dep_port_name.endswith("Client"):
                    port_suffix = "Client"
                elif dep_port_name.endswith("Publisher"):
                    port_suffix = "Publisher"
                elif dep_port_name.endswith("Refresher"):
                    port_suffix = "Refresher"
                if port_suffix:
                    dep_var = f"{original_var}{port_suffix}"
                else:
                    dep_var = f"{original_var}{counter}"
                    counter += 1
            used_var_names.add(dep_var)
            constructor_params.append(f"    private readonly {dep_var}: {dep_port_name},")

        # Join parameters with newlines (each param already has trailing comma)
        # Remove trailing comma from last parameter if present
        # Also ensure no double commas exist (safety check)
        if constructor_params:
            # Remove any double commas first
            constructor_params = [param.replace(",,", ",") for param in constructor_params]
            # Remove comma from last parameter
            if constructor_params and constructor_params[-1].endswith(","):
                constructor_params[-1] = constructor_params[-1].rstrip(",")
            constructor_params_str = "\n".join(constructor_params)
        else:
            constructor_params_str = ""

        # Port imports now use barrel exports from services domain index
        # No need to determine port suffix since we import from domain barrel export

        # Generate method implementations
        # Use DTO types from services/dto to match port interface signatures
        methods = []
        dto_input_types = set()
        dto_output_types = set()
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            method_name = camel_case(operation_id)
            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            # Generate DTO type names matching the pattern used in DTO generator
            operation_name = operation_id.replace(verb, "", 1) if operation_id.lower().startswith(verb.lower()) else operation_id
            operation_name_pascal = pascal_case(operation_name)

            if operation_name_pascal == pascal_case(resource):
                input_dto_type = f"{pascal_case(verb)}{pascal_case(resource)}Input"
                output_dto_type = f"{pascal_case(verb)}{pascal_case(resource)}Output"
            else:
                input_dto_type = f"{operation_name_pascal}Input"
                output_dto_type = f"{operation_name_pascal}Output"

            dto_input_types.add(input_dto_type)
            dto_output_types.add(output_dto_type)

            # Pass dependency ports to method body generation (derived from OpenAPI, not hardcoded!)
            method_body = self._generate_method_body(
                port_name, operation_id, operation, context, input_dto_type, dependency_ports, verb, resource, ddb_repo_var
            )

            # Use TypeScript utility types to extract types from port interface
            # This avoids needing to import DTOs separately since they're already in the port interface
            # Use Awaited<> to unwrap Promise since port methods return Promise<T> and async functions also return Promise<T>
            input_type = f"Parameters<{port_name}['{method_name}']>[0]"
            output_type = f"Awaited<ReturnType<{port_name}['{method_name}']>>"

            methods.append(f"""  async {method_name}(input: {input_type}): Promise<{output_type}> {{
{method_body}
  }}""")

        methods_str = "\n\n".join(methods)

        # Add local infrastructure imports (HttpClient, DynamoDB repositories, etc.)
        # Port imports are handled separately and combined with main port import
        local_imports_str = ""
        if needs_http:
            local_imports_str += "import type { HttpClient } from \"../_shared/http-client.js\";\n"
        if local_dependency_imports:
            if local_imports_str:
                local_imports_str += "\n"
            local_imports_str += "\n".join(local_dependency_imports)
        
        # Local infrastructure imports only (ports are combined with main port import)
        dependency_imports_str = local_imports_str

        # Also import core types for request/response schemas used in method implementations
        core_type_imports = []
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]

            # Get core types for request bodies and responses (used in implementations)
            input_core_type, output_core_type = self._map_dto_to_core_types(
                operation_id, operation, context
            )
            # Only add core types that are actual schemas (not inline types or void)
            if not (input_core_type.startswith("{") and input_core_type.endswith("}")) and input_core_type != "Record<string, never>":
                core_type_imports.append(input_core_type)
            if not (output_core_type.startswith("{") and output_core_type.endswith("}")) and output_core_type != "Record<string, never>" and output_core_type != "void":
                core_type_imports.append(output_core_type)

        # Adapters should NOT import core types - they should only depend on ports
        # Core types are infrastructure concerns that should be handled internally
        core_imports_str = ""

        # Combine main port and dependency ports into a single import from the same source
        all_port_names = [port_name]
        if dependency_port_names:
            all_port_names.extend(dependency_port_names)
        
        # Sort and deduplicate all port names
        all_port_names_sorted = sorted(set(all_port_names))
        ports_list = ",\n  ".join(all_port_names_sorted)
        port_import = f"import type {{\n  {ports_list},\n}} from \"@ddd/services/{context.domain_name}\";\n"

        # When adapter encapsulates Ddb, add constructor body to create Ddb from dynamoClient
        constructor_body = ""
        if ddb_repo_class:
            constructor_body = f" {{\n    this.ddb = new {ddb_repo_class}(this.dynamoClient);\n  }}"
        else:
            constructor_body = " {}"

        # Add private ddb field when adapter creates Ddb internally
        ddb_field = f"  private readonly ddb: {ddb_repo_class};\n\n" if ddb_repo_class else ""

        return f"""{header}/**
 * {adapter_name}
 *
 * DDD: Infrastructure adapter that implements {port_name} port.
 * Handles infrastructure concerns (HTTP, database, external APIs).
 * Encapsulates Ddb creation - api-server passes dynamoClient only.
 */

{port_import}{core_imports_str}{dependency_imports_str}

/**
 * {adapter_name}
 *
 * Implements {port_name} port for infrastructure layer.
 */
export class {adapter_name} implements {port_name} {{
{ddb_field}  constructor(
{constructor_params_str}
  ){constructor_body}

{methods_str}
}}
"""

    def _generate_dto_types(
        self,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext
    ) -> tuple[str, str]:
        """Generate DTO type names (Input and Output) - same logic as port generator"""
        # Extract resource and verb (no path in this context; uses operation_id fallback)
        verb = extract_verb_from_operation_id(operation_id)
        resource = NamingConvention.resource_for_grouping(operation_id)

        # Use operation ID to ensure uniqueness when multiple operations share verb+resource
        # Extract the full operation name (without verb) for uniqueness
        operation_name = operation_id.replace(verb, "", 1) if operation_id.lower().startswith(verb.lower()) else operation_id
        operation_name_pascal = pascal_case(operation_name)

        # If operation name is just the resource, use standard naming
        if operation_name_pascal == pascal_case(resource):
            input_type = f"{pascal_case(verb)}{pascal_case(resource)}Input"
            output_type = f"{pascal_case(verb)}{pascal_case(resource)}Output"
        else:
            # Use operation name for uniqueness
            input_type = f"{operation_name_pascal}Input"
            output_type = f"{operation_name_pascal}Output"

        return input_type, output_type

    def _map_dto_to_core_types(
        self,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext
    ) -> tuple[str, str]:
        """Map DTO types to their core type equivalents

        DTOs are aliases of core types:
        - EventsInput -> ListEventsParams (from core)
        - EventsOutput -> ListEventsResponse (from core)
        - GetEventInput -> { eventId: string } (inline type for path params)
        - GetEventOutput -> GetEventResponse (from core)

        Core types follow patterns:
        - Input: {Verb}{Resource}Params or {Operation}Params for query params
        - Input: {SchemaName} for request body schemas
        - Input: inline type for path-only params
        - Output: {Verb}{Resource}Response or {Operation}Response
        """
        verb = extract_verb_from_operation_id(operation_id)
        resource = NamingConvention.resource_for_grouping(operation_id)

        from ...utils.openapi import get_input_schema_or_type_name, get_response_schema_name

        # Unified input type (request body schema or Params)
        input_core_type = get_input_schema_or_type_name(
            operation, context.spec, operation_id, getattr(context, "unbundled_spec", None)
        )
        if input_core_type:
            pass  # use input_core_type
        else:
            # No request body and no parameters - fallback to inline from path params
            parameters = operation.get("parameters", [])
            has_path_params = any(
                p.get("in") == "path" for p in parameters
                if isinstance(p, dict)
            )
            if has_path_params:
                # Path-only params - generate inline type from path parameters
                # Core doesn't export Params types for path-only operations
                # So we generate inline type: { eventId: string }
                # But for adapters, we'll use operations type reference
                # Actually, let's extract path params and create inline type
                # Identify common org-scoped parameters to exclude (derived from OpenAPI, not hardcoded!)
                common_org_params = set()
                for param in parameters:
                    if isinstance(param, dict):
                        param_ref = param.get("$ref", "")
                        param_name = param.get("name", "")
                        # Check if it references OrgId parameter component
                        if "#/components/parameters/OrgId" in param_ref or param_name == "orgId":
                            common_org_params.add("orgId")
                    elif isinstance(param, str) and "#/components/parameters/OrgId" in param:
                        common_org_params.add("orgId")

                path_params = []
                for param in parameters:
                    if isinstance(param, dict) and param.get("in") == "path":
                        param_name = param.get("name", "")
                        param_ref = param.get("$ref", "")
                        # Exclude common org-scoped parameters (derived from OpenAPI, not hardcoded!)
                        is_org_param = (
                            param_name in common_org_params or
                            "#/components/parameters/OrgId" in param_ref
                        )
                        if not is_org_param:
                            param_schema = param.get("schema", {})
                            param_type = "string"  # Default to string
                            if "$ref" in param_schema:
                                # Resolve ref if needed
                                from ...utils.openapi import resolve_ref
                                resolved = resolve_ref(context.spec, param_schema["$ref"])
                                if resolved and "type" in resolved:
                                    param_type = resolved["type"]
                            elif "type" in param_schema:
                                param_type = param_schema["type"]
                            path_params.append(f"{param_name}: {param_type}")

                if path_params:
                    # Generate inline type
                    props_str = ", ".join(path_params)
                    input_core_type = f"{{ {props_str} }}"
                else:
                    # No path params (only common org-scoped params) - use empty object
                    input_core_type = "Record<string, never>"
            else:
                # No params - use empty object type
                input_core_type = "Record<string, never>"

        # For output: validate against OpenAPI spec and use the same pattern as core types generator
        # Core types use: ListEventsResponse = operations["listEvents"]["responses"]["200"]["content"]["application/json"]
        # Pattern: {PascalCase(operation_id)}Response (e.g., listEvents -> ListEventsResponse, listEventsInStream -> ListEventsInStreamResponse)
        # This matches what's actually exported from core/types/index.ts

        responses = operation.get("responses", {})
        if "204" in responses:
            # 204 No Content - use void (no response body)
            output_core_type = "void"
        else:
            # Check if response exists (200 or 201) - if it does, use the operation_id-based pattern
            # This matches the core types generator pattern exactly
            if "200" in responses or "201" in responses:
                output_core_type = f"{pascal_case(operation_id)}Response"
            else:
                # Fallback if no success response found
                output_core_type = f"{pascal_case(operation_id)}Response"

        return input_core_type, output_core_type

    def _generate_dto_imports(
        self,
        context: GenerationContext,
        operations: List[Dict[str, Any]],
        dto_imports: List[str]
    ) -> str:
        """Generate DTO import statements grouped by resource"""
        if not dto_imports:
            return ""

        # Group operations by resource to find the DTO file
        resource_to_types: Dict[str, List[str]] = {}
        for op_data in operations:
            operation_id = op_data["operation_id"]
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )
            resource_pascal = pascal_case(resource)

            # Find DTO types that belong to this resource
            for dto_type in dto_imports:
                if resource_pascal in dto_type:
                    if resource not in resource_to_types:
                        resource_to_types[resource] = []
                    resource_to_types[resource].append(dto_type)

        # Generate import statements for each resource
        import_lines = []
        for resource in sorted(resource_to_types.keys()):
            types_str = ", ".join(sorted(set(resource_to_types[resource])))
            import_lines.append(f"import type {{ {types_str} }} from \"@ddd/services/{context.domain_name}/dto/{kebab_case(resource)}-dto\";")

        return "\n".join(import_lines) + "\n" if import_lines else ""

    def _generate_method_body(
        self,
        port_name: str,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        input_type: str,
        dependency_ports: List[Dict[str, Any]] = None,
        verb: str = None,
        resource: str = None,
        ddb_repo_var: str = None
    ) -> str:
        """Generate method implementation body"""
        if dependency_ports is None:
            dependency_ports = []

        # Derive dependency variable names from dependency_ports (read from OpenAPI, not hardcoded!)
        # Store as list of port info, not hardcoded type keys!
        dependency_var_info = []
        for dep_port in dependency_ports:
            dep_port_name = dep_port["port_name"]
            dep_var = PortDetermination.derive_variable_name(dep_port_name)
            # Handle reserved words (e.g., "eval" -> "evalRepository")
            if dep_var == "eval":
                dep_var = "evalRepository"
            dependency_var_info.append({
                "port_name": dep_port_name,
                "var_name": dep_var,
                "port_suffix": dep_port_name.split("Repository")[0].split("Client")[0].split("Refresher")[0].split("Publisher")[0]
            })

        # Generate generic method body that uses params directly
        # Field names should be extracted from OpenAPI schemas, not hardcoded
        if port_name.endswith("Publisher"):
            return f"""    // TODO: Extract field names from OpenAPI request schema instead of hardcoding
    // TODO: Implement publishing logic using this.http or external API client
    // Field names like providerType, providerAccount, content should come from schema analysis

    // Example generic implementation:
    // const response = await this.http.post(url, params);
    // return response.data;

    throw new Error("Method not yet implemented - extract field names from OpenAPI schema");"""

        elif port_name.endswith("Client"):
            # Client port methods - generate delegation comments from actual dependencies
            dep_delegates = []
            for dep_info in dependency_var_info:
                dep_var = dep_info["var_name"]
                dep_delegates.append(f"    // if (this.{dep_var}) {{\n    //   return await this.{dep_var}.{camel_case(operation_id)}(input);\n    // }}")
            dep_delegate_str = "\n".join(dep_delegates) if dep_delegates else ""
            return f"""    // TODO: Extract field names from OpenAPI request schema instead of hardcoding
    // TODO: Implement client connection logic
    // Field names should come from schema analysis, not hardcoded
{dep_delegate_str}
    void (input); // Suppress unused parameter warning

    throw new Error("Method not yet implemented - extract field names from OpenAPI schema");"""

        elif port_name.endswith("Refresher"):
            # Refresher port methods - generate delegation comments from actual dependencies
            dep_delegates = []
            for dep_info in dependency_var_info:
                dep_var = dep_info["var_name"]
                dep_delegates.append(f"    // if (this.{dep_var}) {{\n    //   return await this.{dep_var}.{camel_case(operation_id)}(input);\n    // }}")
            dep_delegate_str = "\n".join(dep_delegates) if dep_delegates else ""
            return f"""    // TODO: Extract field names from OpenAPI request schema instead of hardcoding
    // TODO: Implement refresh logic
    // Field names should come from schema analysis, not hardcoded
{dep_delegate_str}
    void (input); // Suppress unused parameter warning

    throw new Error("Method not yet implemented - extract field names from OpenAPI schema");"""

        else:
            # Generic repository or other port types
            # Generate basic implementation skeleton from OpenAPI operation
            if verb is None:
                from ...utils.string import extract_verb_from_operation_id
                verb = extract_verb_from_operation_id(operation_id)
            if resource is None:
                from ...utils.naming import NamingConvention
                resource = NamingConvention.resource_for_grouping(operation_id)
            return self._generate_repository_adapter_body(
                port_name, operation_id, operation, context, input_type, verb, resource, dependency_var_info, ddb_repo_var
            )

    def _generate_repository_adapter_body(
        self,
        port_name: str,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        input_type: str,
        verb: str,
        resource: str,
        dependency_var_info: List[Dict[str, Any]],
        ddb_repo_var_from_content: str = None
    ) -> str:
        """Generate basic implementation skeleton for repository adapters from OpenAPI operation.
        ddb_repo_var_from_content: when set, use this (from _generate_adapter_content, spec-based lookup).
        """
        from ...utils.string import camel_case, pascal_case

        # Use precomputed DDB repo var from _generate_adapter_content (spec-based, no file reading)
        ddb_repo_var = ddb_repo_var_from_content

        # Extract path parameters from operation
        path_params = []
        parameters = operation.get("parameters", [])
        for param in parameters:
            if isinstance(param, dict) and param.get("in") == "path":
                param_name = param.get("name", "")
                if param_name != "orgId":  # orgId is typically handled separately
                    path_params.append(param_name)

        # Delegate to DynamoDB repository when available (CRUD and operation-scoped verbs like export, enable, disable)
        if ddb_repo_var:
            return f"""    // Delegate to DynamoDB repository
    return await this.{ddb_repo_var}.{camel_case(operation_id)}(input);"""

        # No DDB repo - stub
        if verb in ["list", "create", "get", "update", "delete"]:
            return f"""    // TODO: Implement {verb} operation (DynamoDB repository not available)
    throw new Error("Operation {verb} not yet implemented - DynamoDB repository not available");"""

        dep_comments = []
        for dep_info in dependency_var_info:
            dep_var = dep_info["var_name"]
            dep_port_name = dep_info["port_name"]
            dep_comments.append(f"    // Use this.{dep_var} ({dep_port_name}) for related operations")
        dep_comment_str = "\n".join(dep_comments) if dep_comments else "    // Use available dependencies (this.http, etc.) for implementation"

        return f"""    // TODO: Implement {verb} operation
    // TODO: Extract field names from OpenAPI request/response schemas
{dep_comment_str}
    // Input type: {input_type}
    void (input); // Suppress unused parameter warning

    throw new Error("Method not yet implemented");"""

    def _determine_port_suffix(self, port_name: str) -> str:
        """
        Determine port file suffix from port name (derived from OpenAPI, not hardcoded!)

        Examples:
            ProviderAccountRepository -> "repository"
            ProviderAccountClient -> "client"
            ContentPublisher -> "publisher"
            ProviderAccountTokenRefresher -> "refresher"
        """
        # Check for common port type suffixes (in order of specificity)
        if port_name.endswith("Repository"):
            return "repository"
        elif port_name.endswith("Client"):
            return "client"
        elif port_name.endswith("Publisher"):
            return "publisher"
        elif port_name.endswith("Refresher"):
            return "refresher"
        else:
            # Default to repository for unknown types
            return "repository"
