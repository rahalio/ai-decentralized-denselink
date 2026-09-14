"""
Routes Generator - Generates API server routes

Per FINAL_ARCHITECTURE.md: Routes belong in api-server layer (inbound layer).
Routes register handlers with Fastify. Handlers (separate files) call use cases.
Routes are thin - they just register HTTP paths with handler functions.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id


class RoutesGenerator(BaseGenerator):
    """
    Generates route files

    Pattern: Routes call use cases from services layer
    const result = await deps.executePublishContent.execute({ ... });
    """

    @property
    def name(self) -> str:
        return "Routes Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "routes"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate route files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory (clean when pipeline.clean to remove stale routes)
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "api-server" / "src" / "domains" / context.domain_name / "routes"
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

        # Generate route file for each resource (static paths before parametric — P5)
        for resource, ops in sorted(
            resource_operations.items(),
            key=lambda item: self._resource_route_priority(item[0], item[1]),
        ):
            resource_kebab = kebab_case(resource)
            route_file = output_dir / f"{resource_kebab}.routes.ts"

            header = self.generate_header(
                context,
                f"Routes for {resource}"
            )

            route_content = self._generate_route_content(
                context,
                resource,
                ops,
                header
            )

            write_file(route_file, route_content)
            files.append(route_file)

        # Optional: auth aggregate from x-codegen.api-server.auth.routes_aggregate (e.g. identity.yaml)
        # Prefer spec (bundled); bundled JSON may omit x-codegen, so fall back to unbundled_spec
        auth_config = self._get_auth_config(context.spec) or self._get_auth_config(
            getattr(context, "unbundled_spec", None) or {}
        )
        extra_exports: Optional[List[tuple]] = None
        if auth_config:
            routes_aggregate = auth_config.get("routes_aggregate") or []
            resource_kebabs = {kebab_case(r) for r in resource_operations}
            if routes_aggregate and all(name in resource_kebabs for name in routes_aggregate):
                auth_routes_file = output_dir / "auth.routes.ts"
                auth_routes_content = self._generate_auth_routes_content(context, routes_aggregate)
                write_file(auth_routes_file, auth_routes_content)
                files.append(auth_routes_file)
                extra_exports = [("authRoutes", "auth.routes")]

        # Generate routes index (export order = registration order: static before param)
        index_file = output_dir / "index.ts"
        ordered_resources = [
            r
            for r, _ in sorted(
                resource_operations.items(),
                key=lambda item: self._resource_route_priority(item[0], item[1]),
            )
        ]
        index_content = self._generate_index(
            context, ordered_resources, extra_exports=extra_exports
        )
        write_file(index_file, index_content)
        files.append(index_file)

        context.logger.info(f"Generated {len(files)} route files for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _generate_route_content(
        self,
        context: GenerationContext,
        resource: str,
        operations: List[Dict[str, Any]],
        header: str
    ) -> str:
        """Generate route file content"""
        import re

        route_function_name = f"{camel_case(resource)}Routes"
        route_registrations = []
        handler_names = []
        body_type_names = set()
        from ...utils.openapi import get_request_body_schema_name

        def _normalized(route_path: str) -> str:
            return re.sub(r":[A-Za-z_][A-Za-z0-9_]*", ":param", route_path)

        def _last_param(p: str) -> Optional[str]:
            params = self._extract_path_params(p)
            return params[-1] if params else None

        # Fastify rejects /foo/:a and /foo/:b even across methods — canonicalize.
        canonical_last_param: Dict[str, str] = {}
        by_normalized: Dict[str, List[Dict[str, Any]]] = {}
        for op_data in operations:
            route_path = self._generate_route_path(op_data["path"])
            norm = _normalized(route_path)
            by_normalized.setdefault(norm, []).append(op_data)
        for norm, ops in by_normalized.items():
            last_params = {p for p in (_last_param(o["path"]) for o in ops) if p}
            if len(last_params) <= 1:
                if last_params:
                    canonical_last_param[norm] = next(iter(last_params))
                continue
            preferred = None
            for o in ops:
                oid = o["operation_id"]
                lp = _last_param(o["path"])
                if lp and ("ById" in oid or lp.lower().endswith("id")):
                    preferred = lp
                    break
            canonical_last_param[norm] = preferred or sorted(last_params)[0]

        skipped_operation_ids: set = set()
        path_method_groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for op_data in operations:
            method = op_data["method"].lower()
            route_path = self._generate_route_path(op_data["path"])
            key = (method, _normalized(route_path))
            path_method_groups.setdefault(key, []).append(op_data)

        # Within a resource file: fewer path params first (static before :id)
        operations = sorted(
            operations,
            key=lambda o: (
                (o.get("path") or "").count("{"),
                o.get("path") or "",
                o.get("operation_id") or "",
            ),
        )

        for op_data in operations:
            operation_id = op_data["operation_id"]
            if operation_id in skipped_operation_ids:
                continue
            verb = extract_verb_from_operation_id(operation_id)
            handler_name = camel_case(operation_id)
            handler_names.append(handler_name)
            op = op_data.get("operation", {})
            req_body_type = get_request_body_schema_name(
                op, context.spec, getattr(context, "unbundled_spec", None)
            )
            if req_body_type:
                body_type_names.add(req_body_type)

            method = op_data["method"].lower()
            route_path = self._generate_route_path(op_data["path"])
            norm = _normalized(route_path)
            group = path_method_groups.get((method, norm), [op_data])
            canon = canonical_last_param.get(norm)
            original_last = _last_param(op_data["path"])

            if method == "get" and len(group) == 2:
                other = next(o for o in group if o["operation_id"] != operation_id)
                other_handler = camel_case(other["operation_id"])
                handler_names.append(other_handler)
                skipped_operation_ids.add(other["operation_id"])
                primary, secondary = op_data, other
                primary_handler, secondary_handler = handler_name, other_handler
                if "ById" in other["operation_id"] or other["operation_id"].endswith("ById"):
                    primary, secondary = other, op_data
                    primary_handler, secondary_handler = other_handler, handler_name
                route_registration = self._generate_merged_get_route_registration(
                    context, primary, secondary, primary_handler, secondary_handler
                )
            else:
                alias_param = None
                override = None
                if canon and original_last and canon != original_last:
                    override = re.sub(
                        rf":{re.escape(original_last)}(/|$)",
                        rf":{canon}\1",
                        route_path,
                    )
                    alias_param = (canon, original_last)
                route_registration = self._generate_route_registration(
                    context, op_data, resource, verb, handler_name,
                    route_path_override=override, param_alias=alias_param,
                )
            route_registrations.append(route_registration)

        resource_kebab = kebab_case(resource)
        handler_imports = ", ".join(sorted(set(handler_names)))
        route_registrations_str = "\n".join(route_registrations)
        body_import_stmt = ""
        if body_type_names:
            body_imports_str = ", ".join(sorted(body_type_names))
            body_import_stmt = f'import type {{ {body_imports_str} }} from "@ddd/core/{context.domain_name}/types";\n'

        return f"""{header}import type {{ FastifyInstance, FastifyRequest, FastifyReply }} from "fastify";
import {{ getDependencyContainer }} from "../../../infrastructure/dependency-container.js";
import {{ {handler_imports} }} from "../handlers/{resource_kebab}.handlers.js";
import {{ wrapHandlerInExecutionContext }} from "../../../lib/execution-context-wrapper.js";
{body_import_stmt}
// Fastify types are available globally
export async function {route_function_name}(fastify: FastifyInstance) {{
{route_registrations_str}
}}
"""

    def _generate_merged_get_route_registration(
        self,
        context: GenerationContext,
        primary: Dict[str, Any],
        secondary: Dict[str, Any],
        primary_handler: str,
        secondary_handler: str,
    ) -> str:
        """Merge two GET ops that collide on the same Fastify path pattern.

        When the primary op is *ById, always dispatch by id (slug is informational only).
        """
        path = primary["path"]
        route_path = self._generate_route_path(path)
        is_org_scoped = "/orgs/:orgId" in route_path
        scope = "org" if is_org_scoped else "public"
        domain_name_pascal = pascal_case(context.domain_name)
        deps_line = f"const deps = getDependencyContainer().get{domain_name_pascal}DependenciesForRequest();"
        primary_params = self._extract_path_params(path)
        secondary_params = self._extract_path_params(secondary["path"])
        primary_param = primary_params[-1] if primary_params else "id"
        secondary_param = secondary_params[-1] if secondary_params else "id"
        params_type_str = self._build_params_type(primary_params)
        scope_label = "org-scoped" if is_org_scoped else "unscoped"
        primary_is_by_id = "ById" in (primary.get("operation_id") or "")
        if primary_is_by_id:
            # companyId (etc.) is canonical; do not fork to slug/getCompany.
            return f"""  // GET {path} (id-only; legacy {secondary['path']} unwired; {scope_label})
  fastify.get(
    "{route_path}",
    {{ config: {{ scope: '{scope}' }} }},
    async (request: FastifyRequest<{{ Params: {params_type_str}; Querystring: Record<string, string | string[] | undefined>; Body: unknown }}>, reply: FastifyReply) => {{
      await wrapHandlerInExecutionContext(request, async () => {{
        {deps_line}
        await {primary_handler}(request, reply, deps);
      }});
    }}
  );

"""
        return f"""  // GET {path} | {secondary['path']} (merged; Fastify path-param collision; {scope_label})
  fastify.get(
    "{route_path}",
    {{ config: {{ scope: '{scope}' }} }},
    async (request: FastifyRequest<{{ Params: {params_type_str}; Querystring: Record<string, string | string[] | undefined>; Body: unknown }}>, reply: FastifyReply) => {{
      await wrapHandlerInExecutionContext(request, async () => {{
        {deps_line}
        const seg = (request.params as {{ {primary_param}?: string }}).{primary_param} ?? "";
        if (seg.includes("_") || /^[0-9a-f-]{{8,}}$/i.test(seg)) {{
          await {primary_handler}(request, reply, deps);
        }} else {{
          (request.params as any).{secondary_param} = seg;
          await {secondary_handler}(request as any, reply, deps);
        }}
      }});
    }}
  );

"""

    def _generate_route_registration(
        self,
        context: GenerationContext,
        op_data: Dict[str, Any],
        resource: str,
        verb: str,
        handler_name: str,
        route_path_override: Optional[str] = None,
        param_alias: Optional[tuple] = None,
    ) -> str:
        """Generate route registration that calls handler."""
        path = op_data["path"]
        method = op_data["method"].lower()
        http_method_map = {
            "get": "get", "post": "post", "put": "put", "patch": "patch", "delete": "delete",
        }
        http_method = http_method_map.get(method, "get")
        route_path = route_path_override or self._generate_route_path(path)
        is_org_scoped = "/orgs/:orgId" in route_path
        domain_name_pascal = pascal_case(context.domain_name)
        path_params = self._extract_path_params(path)
        if param_alias:
            canon, original = param_alias
            path_params_for_route = [canon if p == original else p for p in path_params]
            if canon not in path_params_for_route:
                path_params_for_route = path_params_for_route + [canon]
            params_type_str = self._build_params_type(path_params_for_route)
            alias_line = f"(request.params as any).{original} = (request.params as any).{canon};"
        else:
            params_type_str = self._build_params_type(path_params)
            alias_line = ""
        from ...utils.openapi import get_request_body_schema_name
        operation = op_data.get("operation", {})
        request_body_type = get_request_body_schema_name(
            operation, context.spec, getattr(context, "unbundled_spec", None)
        )
        body_type = request_body_type if request_body_type else "unknown"
        request_type = f"FastifyRequest<{{ Params: {params_type_str}; Querystring: Record<string, string | string[] | undefined>; Body: {body_type} }}>"
        deps_line = f"const deps = getDependencyContainer().get{domain_name_pascal}DependenciesForRequest();"
        handler_call = (
            f"{alias_line}\n        await {handler_name}(request, reply, deps);"
            if alias_line else f"await {handler_name}(request, reply, deps);"
        )
        scope = "org" if is_org_scoped else "public"
        scope_label = "org-scoped" if is_org_scoped else "unscoped"
        return f"""  // {method.upper()} {path} ({scope_label}; scope set for security middleware)
  fastify.{http_method}(
    "{route_path}",
    {{ config: {{ scope: '{scope}' }} }},
    async (request: {request_type}, reply: FastifyReply) => {{
      await wrapHandlerInExecutionContext(request, async () => {{
        {deps_line}
        {handler_call}
      }});
    }}
  );

"""

    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameter names from path string (e.g. {orgId}, {notificationId})"""
        import re
        matches = re.findall(r'\{([^}]+)\}', path)
        return list(dict.fromkeys(matches))  # preserve order, dedupe

    def _build_params_type(self, path_params: List[str]) -> str:
        """Build Params type string for FastifyRequest"""
        if not path_params:
            return "Record<string, string>"
        params_dict = ", ".join([f"{p}: string" for p in path_params])
        return f"{{ {params_dict} }}"

    def _generate_route_path(self, path: str) -> str:
        """Convert OpenAPI path to Fastify route path.

        OpenAPI is the source of truth for org scoping:
        - Paths with ``{orgId}`` become ``/orgs/:orgId/...`` (already present).
        - Paths that omit ``{orgId}`` (``/api/health``, ``/api/public/...``,
          ``/api/auth/...``, webhooks, etc.) stay unscoped — do **not** invent
          an ``/orgs/:orgId`` prefix (that broke platform health/version).
        """
        import re
        route_path = re.sub(r'\{([^}]+)\}', r':\1', path)

        if "/orgs/:orgId" in route_path:
            return route_path

        # Legacy specs that used /v1/orgs/... without an explicit {orgId} segment
        if route_path.startswith("/v1/orgs/") and "/v1/orgs/:orgId" not in route_path:
            return route_path.replace("/v1/orgs/", "/v1/orgs/:orgId/", 1)

        return route_path

    @staticmethod
    def _get_auth_config(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Read x-codegen.api-server.auth from spec (no hardcoded domain)."""
        x = spec.get("x-codegen") or {}
        api_server = x.get("api-server") or x.get("api_server") or {}
        return api_server.get("auth")

    def _generate_auth_routes_content(
        self,
        context: GenerationContext,
        routes_aggregate: List[str],
    ) -> str:
        """Generate auth.routes.ts: single plugin that registers the listed route modules (kebab names)."""
        header = self.generate_header(
            context,
            "Auth routes (aggregate for auth-routes-setup; from x-codegen.api-server.auth.routes_aggregate)"
        )
        # routes_aggregate is already kebab (e.g. session, refresh); route function is camelCase e.g. sessionRoutes
        route_names = [f"{camel_case(r)}Routes" for r in routes_aggregate]
        imports = "\n".join(f'import {{ {name} }} from "./{mod}.routes.js";' for name, mod in zip(route_names, routes_aggregate))
        registrations = "\n".join(f"  await fastify.register({name});" for name in route_names)
        return f"""{header}import type {{ FastifyInstance }} from "fastify";
{imports}

export async function authRoutes(fastify: FastifyInstance): Promise<void> {{
{registrations}
}}
"""

    @staticmethod
    def _resource_route_priority(
        resource: str, ops: List[Dict[str, Any]]
    ) -> tuple:
        """Lower tuple → register earlier. Static collection actions before :id routes (P5)."""
        paths = [o.get("path") or "" for o in ops]
        max_params = max((p.count("{") for p in paths), default=0)
        # Prefer pure collection actions (…/export) over entity CRUD (…/{id})
        has_entity_id = any(
            "/{" in p.split("/orgs/{orgId}/", 1)[-1] if "/orgs/{orgId}/" in p else "/{" in p
            for p in paths
        )
        return (max_params, 1 if has_entity_id else 0, resource)

    def _generate_index(
        self,
        context: GenerationContext,
        resources: List[str],
        extra_exports: Optional[List[tuple]] = None,
    ) -> str:
        """Generate routes index file. extra_exports: list of (export_name, module_path_without_ext).

        ``resources`` must already be ordered for registration (static before param).
        """
        header = self.generate_header(
            context,
            "Routes index"
        )

        exports = []
        for resource in resources:
            resource_kebab = kebab_case(resource)
            route_function_name = f"{camel_case(resource)}Routes"
            exports.append(f'export {{ {route_function_name} }} from "./{resource_kebab}.routes.js";')
        if extra_exports:
            for name, mod in extra_exports:
                exports.append(f'export {{ {name} }} from "./{mod}.js";')

        exports_str = "\n".join(exports)

        return f"""{header}{exports_str}
"""
