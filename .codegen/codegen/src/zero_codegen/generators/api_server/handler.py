"""
Handler Generator - Generates API server handlers

Per FINAL_ARCHITECTURE.md: Handlers belong in api-server layer (inbound layer).
Handlers are thin adapters that:
- Parse HTTP requests
- Call use cases from services layer
- Format HTTP responses
- NO business logic (business logic is in use cases)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory, remove_stale_domain_dirs
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id, dto_input_type_name
from ...utils.x_codegen_extensions import (
    is_extension_handler_operation,
    get_extension_handler_name,
    is_action_only_operation,
)


class HandlerGenerator(BaseGenerator):
    """
    Generates handler files for API server

    Pattern: Handlers are thin adapters that call use cases
    export async function listContentItems(request, reply, deps) {
      const orgId = request.effectiveOrgId;
      const input = { ... };
      const result = await deps.executeListContentItems.execute(orgId, input);
      return reply.code(200).send(result);
    }
    """

    @property
    def name(self) -> str:
        return "Handler Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "handler"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate handler files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory (clean when pipeline.clean to remove stale handlers)
        project_root = context.config.paths.project_root
        api_domains = project_root / "platform" / "api-server" / "src" / "domains"
        output_dir = api_domains / context.domain_name / "handlers"

        # Remove generated dirs for domains no longer in config (e.g. publishing)
        if not context.get_state("api_server_stale_domains_cleaned"):
            enabled = {d.name for d in context.config.domains if d.enabled}
            for name in remove_stale_domain_dirs(api_domains, enabled, preserve={"_shared"}):
                context.logger.info(f"Removed stale api-server domain: {name}")
            context.set_state("api_server_stale_domains_cleaned", True)

        ensure_directory(output_dir)
        if context.config.pipeline.clean:
            clean_directory(output_dir)

        # Extract operations and group by resource
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)

        # Group operations by resource
        resource_operations: Dict[str, List[Dict[str, Any]]] = {}
        for op_data in operations:
            operation_id = op_data["operation_id"]
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            if resource not in resource_operations:
                resource_operations[resource] = []
            resource_operations[resource].append(op_data)

        # Generate handler file for each resource
        for resource, ops in resource_operations.items():
            resource_kebab = kebab_case(resource)
            handler_file = output_dir / f"{resource_kebab}.handlers.ts"

            header = self.generate_header(
                context,
                f"Handlers for {resource}"
            )

            handler_content = self._generate_handler_content(
                context,
                resource,
                ops,
                header
            )

            write_file(handler_file, handler_content)
            files.append(handler_file)

        # Optional: auth handler aliases from x-codegen.api-server.auth.handler_aliases (e.g. identity.yaml)
        # Prefer spec (bundled); fall back to unbundled_spec when bundle omits x-codegen
        auth_config = self._get_auth_config(context.spec) or self._get_auth_config(
            getattr(context, "unbundled_spec", None) or {}
        )
        resource_kebabs = {kebab_case(r) for r in resource_operations}
        if auth_config:
            handler_aliases = auth_config.get("handler_aliases") or {}
            valid = bool(handler_aliases)
            for _export_name, v in handler_aliases.items():
                if not isinstance(v, dict) or not v.get("resource") or not v.get("handler"):
                    valid = False
                    break
                if v["resource"] not in resource_kebabs:
                    valid = False
                    break
            if valid:
                auth_handlers_file = output_dir / "auth.handlers.ts"
                auth_handlers_content = self._generate_auth_handlers_content(context, handler_aliases)
                write_file(auth_handlers_file, auth_handlers_content)
                files.append(auth_handlers_file)

        # Generate handlers index
        index_file = output_dir / "index.ts"
        index_content = self._generate_index(context, list(resource_operations.keys()))
        write_file(index_file, index_content)
        files.append(index_file)

        context.logger.info(f"Generated {len(files)} handler files for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _generate_handler_content(
        self,
        context: GenerationContext,
        resource: str,
        operations: List[Dict[str, Any]],
        header: str
    ) -> str:
        """Generate handler file content"""
        handlers = []

        # Collect use case names, request body types, and DTO input types
        use_case_names = set()
        type_names = set()
        input_type_names = set()

        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)

            if is_extension_handler_operation(operation):
                handler_name = camel_case(operation_id)
                ext_name = get_extension_handler_name(operation, handler_name)
                resource_kebab = kebab_case(resource)
                handlers.append(
                    f'export {{ {ext_name} }} from "../extensions/{resource_kebab}.handlers.js";\n'
                )
                continue

            # Resolve operation alias: delegate to another use case with optional input merge
            alias = self._resolve_operation_alias(context, operation_id, operation)
            if alias:
                delegate_to = alias["delegate_to"]
                use_case_name = f"Execute{pascal_case(delegate_to)}"
                # For aliased ops, repo_key and verb come from the delegate
                delegate_resource = NamingConvention.resource_for_grouping(delegate_to)
                delegate_verb = extract_verb_from_operation_id(delegate_to)
                alias_repo_key = self._resource_to_repo_key(delegate_resource, context.domain_name)
            else:
                delegate_to = None
                use_case_name = f"Execute{pascal_case(operation_id)}"
                alias_repo_key = None
                delegate_verb = None
            use_case_var = camel_case(use_case_name)
            use_case_names.add(use_case_var)

            # Collect request body types (for Fastify Body generic)
            from ...utils.openapi import get_request_body_schema_name
            request_schema_name = get_request_body_schema_name(
                operation, context.spec, getattr(context, "unbundled_spec", None)
            )
            if request_schema_name:
                type_names.add(request_schema_name)

            # Collect DTO input types (for use case execute; aliased ops use inline input)
            # Skip for action-only ops that emit inline DataEnvelope (no use-case input)
            if not alias and not (
                is_action_only_operation(operation)
                and self._generate_action_only_handler_body(operation_id, op_data.get("path"))
                is not None
            ):
                input_type_names.add(dto_input_type_name(operation_id))

            # Generate handler function (repo_key from resource for non-aliased, from delegate for aliased)
            effective_repo_key = alias_repo_key if alias else self._resource_to_repo_key(resource, context.domain_name)
            effective_verb = delegate_verb if alias else verb
            handler_func = self._generate_handler_function(
                context,
                op_data,
                resource,
                verb,
                effective_repo_key,
                use_case_var,
                alias,
                effective_verb,
            )
            handlers.append(handler_func)

        # Build imports
        use_case_imports = ", ".join(sorted(use_case_names))
        type_imports = ", ".join(sorted(type_names)) if type_names else ""

        # Build type import statements
        type_import_stmt = ""
        if type_imports:
            type_import_stmt = f'import type {{ {type_imports} }} from "@ddd/core/{context.domain_name}/types";\n'

        input_type_imports = ", ".join(sorted(input_type_names))
        input_import_stmt = f'import type {{ {input_type_imports} }} from "@ddd/services/{context.domain_name}";\n' if input_type_names else ""

        handlers_str = "\n".join(handlers)

        return f"""{header}import type {{ FastifyRequest, FastifyReply }} from "fastify";
import type {{ {pascal_case(context.domain_name)}DomainModule }} from "../dependencies/{context.domain_name}-ddd.dependencies.js";
{type_import_stmt}{input_import_stmt}// Use cases are available via deps.useCases.<repoKey>.<verb>
// Execution context is automatically set up by route wrapper (wrapHandlerInExecutionContext)

{handlers_str}
"""

    @staticmethod
    def _resource_to_repo_key(resource: str, domain_name: str) -> str:
        """Derive repo key from resource (matches dependencies generator)."""
        from ...utils.string import pluralize

        domain_prefix = pascal_case(domain_name)
        base = resource
        if domain_prefix and base.startswith(domain_prefix) and len(base) > len(domain_prefix):
            base = base[len(domain_prefix):]
        return camel_case(pluralize(base))

    def _resolve_operation_alias(
        self,
        context: GenerationContext,
        operation_id: str,
        operation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Resolve operation alias from domain config or operation x-codegen."""
        # 1. Check domain config operation_aliases
        aliases = getattr(context.domain, "operation_aliases", None) or {}
        alias_cfg = aliases.get(operation_id)
        if alias_cfg:
            return {
                "delegate_to": alias_cfg.delegate_to,
                "input_merge": alias_cfg.input_merge or {},
            }
        # 2. Check operation x-codegen
        x_codegen = operation.get("x-codegen") or {}
        if isinstance(x_codegen, dict) and x_codegen.get("delegateTo"):
            return {
                "delegate_to": x_codegen["delegateTo"],
                "input_merge": x_codegen.get("inputMerge") or {},
            }
        return None

    def _generate_handler_function(
        self,
        context: GenerationContext,
        op_data: Dict[str, Any],
        resource: str,
        verb: str,
        repo_key: str,
        use_case_var: str,
        alias: Optional[Dict[str, Any]] = None,
        effective_verb: Optional[str] = None,
    ) -> str:
        """Generate individual handler function"""
        operation = op_data["operation"]
        operation_id = op_data["operation_id"]
        method = op_data["method"].upper()
        path = op_data["path"]

        # Generate handler function name (camelCase operation_id)
        handler_name = camel_case(operation_id)

        # Get request body type for typing
        from ...utils.openapi import get_request_body_schema_name
        request_body_type = get_request_body_schema_name(
            operation, context.spec, getattr(context, "unbundled_spec", None)
        )

        # Extract path and query parameters for typing
        # Also extract from path string to catch path params not in parameters array
        path_params = self._extract_path_params(operation.get("parameters", []), path)
        query_params = self._extract_query_params(operation.get("parameters", []))

        # Build FastifyRequest type with generics
        needs_org_id = path and "{orgId}" in path if path else False
        request_type_parts = []
        if path_params or query_params or request_body_type or needs_org_id:
            # Build Params type (include orgId when path has it for proper typing from route)
            params_type = "Record<string, string>"
            params_for_type = list(path_params)
            if needs_org_id and "orgId" not in params_for_type:
                params_for_type = ["orgId"] + params_for_type
            if params_for_type:
                params_dict = ", ".join([f"{p}: string" for p in params_for_type])
                params_type = f"{{ {params_dict} }}"

            # Build Query type
            query_type = "Record<string, string | string[] | undefined>"
            if query_params:
                query_dict = ", ".join([f"{q}?: string | string[]" for q in query_params])
                query_type = f"{{ {query_dict} }}"

            # Build Body type
            body_type = "unknown"
            if request_body_type:
                body_type = request_body_type

            request_type_parts.append(f"FastifyRequest<{{ Params: {params_type}; Querystring: {query_type}; Body: {body_type} }}>")
        else:
            request_type_parts.append("FastifyRequest")

        request_type = request_type_parts[0] if request_type_parts else "FastifyRequest"

        # DTO input type for use case execute
        input_type = dto_input_type_name(operation_id)

        verb_for_uc = effective_verb if effective_verb is not None else verb

        # Action-only ops (x-repository: none) skip use-case codegen — emit inline bodies
        # for known platform probes; other action-only ops still need extension handlers.
        if is_action_only_operation(operation):
            inline = self._generate_action_only_handler_body(operation_id, path)
            if inline is not None:
                return f"""/**
 * Handler for {method} {path}
 * Operation: {operation_id}
 * Action-only (x-repository: none) — no use case; inline response.
 */
export async function {handler_name}(
  _request: {request_type},
  reply: FastifyReply,
  _deps: {pascal_case(context.domain_name)}DomainModule
): Promise<void> {{
{inline}
}}

"""

        # Generate handler body
        handler_body = self._generate_handler_body(
            context,
            operation,
            operation_id,
            verb,
            resource,
            repo_key,
            verb_for_uc,
            use_case_var,
            path_params,
            query_params,
            input_type,
            path,
            alias
        )

        return f"""/**
 * Handler for {method} {path}
 * Operation: {operation_id}
 */
export async function {handler_name}(
  request: {request_type},
  reply: FastifyReply,
  deps: {pascal_case(context.domain_name)}DomainModule
): Promise<void> {{
  // Security: orgId validated by setOrgContext hook; use case gets it from execution context
{handler_body}
}}

"""

    def _generate_action_only_handler_body(
        self, operation_id: str, path: Optional[str]
    ) -> Optional[str]:
        """Inline DataEnvelope bodies for action-only ops that have no use cases.

        Returns None when the generator should fall through to the use-case call
        pattern (caller may still emit a broken call — prefer extension handlers
        for other action-only ops).
        """
        if operation_id == "getHealth" or (path or "") == "/api/health":
            return """  const timestamp = new Date().toISOString();
  return reply.code(200).send({
    data: {
      status: "ok",
      timestamp,
    },
    meta: {
      correlationId: crypto.randomUUID(),
      timestamp,
    },
  });"""
        if operation_id == "getVersion" or (path or "") == "/api/version":
            return """  let name = "@ddd/api-server";
  let version = "0.1.0";
  try {
    const { readFileSync } = await import("node:fs");
    const { dirname, join } = await import("node:path");
    const { fileURLToPath } = await import("node:url");
    const here = dirname(fileURLToPath(import.meta.url));
    const pkgPath = join(here, "../../../../../../package.json");
    const pkg = JSON.parse(readFileSync(pkgPath, "utf8")) as {
      name?: string;
      version?: string;
    };
    name = pkg.name ?? name;
    version = pkg.version ?? version;
  } catch {
    // keep defaults
  }
  const timestamp = new Date().toISOString();
  return reply.code(200).send({
    data: {
      version,
      name,
      nodeVersion: process.version,
      runtime: "express",
    },
    meta: {
      correlationId: crypto.randomUUID(),
      timestamp,
    },
  });"""
        return None

    def _generate_handler_body(
        self,
        context: GenerationContext,
        operation: Dict[str, Any],
        operation_id: str,
        verb: str,
        resource: str,
        repo_key: str,
        verb_for_uc: str,
        use_case_var: str,
        path_params: List[str],
        query_params: List[str],
        input_type: str,
        path: Optional[str],
        alias: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate handler body that calls use case with proper typing.
        Include orgId when path has {orgId} - DTOs require it for org-scoped operations."""
        # Build input object from path params, body, and query (typed)
        input_parts = []

        needs_org_id = path and "{orgId}" in path if path else False

        # Aliased operations: build input (orgId + path params + input_merge)
        if alias:
            if needs_org_id:
                input_parts.append("    orgId: request.effectiveOrgId!,")
            for param_name in path_params:
                input_parts.append(f"    {param_name}: request.params.{param_name},")
            for key, val in (alias.get("input_merge") or {}).items():
                if isinstance(val, str):
                    input_parts.append(f'    {key}: "{val}" as const,')
                elif isinstance(val, bool):
                    input_parts.append(f"    {key}: {str(val).lower()},")
                elif isinstance(val, (int, float)):
                    input_parts.append(f"    {key}: {val},")
                else:
                    input_parts.append(f'    {key}: "{val}",')
            input_str = "\n".join(input_parts)
            status_code = self._determine_status_code(verb, operation)
            target_input_type = dto_input_type_name(alias["delegate_to"])
            return f"""  const input = {{
{input_str}
  }};
  const result = await deps.useCases.{repo_key}.{verb_for_uc}.execute(input);
  return reply.code({status_code}).send(result);"""

        # Non-aliased: build full input from request
        for param_name in path_params:
            input_parts.append(f"    {param_name}: request.params.{param_name},")

        if "requestBody" in operation:
            input_parts.append("    ...(request.body ?? {}),")

        if query_params:
            input_parts.append("    ...(request.query ?? {}),")

        if needs_org_id:
            input_parts.append("    orgId: request.effectiveOrgId!,")

        input_str = "\n".join(input_parts) if input_parts else ""

        status_code = self._determine_status_code(verb, operation)

        # Use type assertion when adding orgId - DTOs from OpenAPI often omit orgId (from path)
        if input_str:
            decl = f"  const input = {{\n{input_str}\n  }} as {input_type};" if needs_org_id else f"  const input: {input_type} = {{\n{input_str}\n  }};"
            return f"""{decl}
  const result = await deps.useCases.{repo_key}.{verb_for_uc}.execute(input);
  return reply.code({status_code}).send(result);"""
        else:
            if needs_org_id:
                return f"""  const input = {{ orgId: request.effectiveOrgId! }} as {input_type};
  const result = await deps.useCases.{repo_key}.{verb_for_uc}.execute(input);
  return reply.code({status_code}).send(result);"""
            return f"""  const input: {input_type} = {{}};
  const result = await deps.useCases.{repo_key}.{verb_for_uc}.execute(input);
  return reply.code({status_code}).send(result);"""

    def _extract_path_params(self, parameters: List[Dict[str, Any]], path: Optional[str] = None) -> List[str]:
        """Extract path parameter names from parameters and path string"""
        path_params = []
        seen_params = set()

        # First, extract from parameters array
        for param in parameters:
            if param.get("in") == "path":
                param_name = param.get("name", "")
                if param_name and param_name != "orgId":  # orgId is handled separately
                    if param_name not in seen_params:
                        path_params.append(param_name)
                        seen_params.add(param_name)

        # Also extract from path string to catch any params not in parameters array
        if path:
            import re
            matches = re.findall(r'\{([^}]+)\}', path)
            for param_name in matches:
                if param_name != "orgId" and param_name not in seen_params:
                    path_params.append(param_name)
                    seen_params.add(param_name)

        return path_params

    def _extract_query_params(self, parameters: List[Dict[str, Any]]) -> List[str]:
        """Extract query parameter names"""
        query_params = []
        for param in parameters:
            if param.get("in") == "query":
                param_name = param.get("name", "")
                if param_name:
                    query_params.append(param_name)
        return query_params

    def _determine_status_code(self, verb: str, operation: Dict[str, Any]) -> int:
        """Determine HTTP status code based on verb and operation"""
        responses = operation.get("responses", {})

        # Check for explicit status codes in responses
        if "201" in responses:
            return 201
        if "204" in responses:
            return 204
        if "200" in responses:
            return 200

        # Default based on verb
        if verb == "create":
            return 201
        elif verb == "delete":
            return 204
        else:
            return 200

    @staticmethod
    def _get_auth_config(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Read x-codegen.api-server.auth from spec (no hardcoded domain)."""
        x = spec.get("x-codegen") or {}
        api_server = x.get("api-server") or x.get("api_server") or {}
        return api_server.get("auth")

    def _generate_auth_handlers_content(
        self,
        context: GenerationContext,
        handler_aliases: Dict[str, Any],
    ) -> str:
        """Generate auth.handlers.ts: re-export handlers under alias names (from x-codegen.api-server.auth.handler_aliases)."""
        header = self.generate_header(
            context,
            "Auth handler aliases (for auth-routes-setup; from x-codegen.api-server.auth.handler_aliases)"
        )
        lines = []
        for export_name, v in sorted(handler_aliases.items()):
            if isinstance(v, dict) and v.get("resource") and v.get("handler"):
                mod = v["resource"]
                handler = v["handler"]
                lines.append(f'export {{ {handler} as {export_name} }} from "./{mod}.handlers.js";')
        exports_str = "\n".join(lines)
        return f"""{header}{exports_str}
"""

    def _generate_index(
        self,
        context: GenerationContext,
        resources: List[str]
    ) -> str:
        """Generate handlers index file"""
        header = self.generate_header(
            context,
            "Handlers index"
        )

        exports = []
        for resource in sorted(resources):
            resource_kebab = kebab_case(resource)
            exports.append(f'export * from "./{resource_kebab}.handlers.js";')

        exports_str = "\n".join(exports)

        return f"""{header}{exports_str}
"""
