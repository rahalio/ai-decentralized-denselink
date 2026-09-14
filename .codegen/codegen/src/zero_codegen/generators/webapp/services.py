"""
Webapp Services Generators

Generates webapp service layer scaffolding:
- Contracts (Zod schemas re-exports)
- API Types (TypeScript types re-exports)
- Service (API client)
- Facade (High-level API)
- Hooks (React Query hooks)
- Index (Barrel exports)
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...base.generator_bases import FileGenerator
from ...utils.openapi import extract_operations, get_request_body_schema, get_response_schema_name
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id
from ...utils.generator_setup import GeneratorSetup
from .base import WebappServicesFileGenerator


class WebappContractsGenerator(WebappServicesFileGenerator):
    """
    Generates contracts file (Zod schemas re-exports from @ddd/core)

    Pattern: Re-exports Zod schemas from core package for runtime validation
    """

    @property
    def name(self) -> str:
        return "Webapp Contracts Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_contracts"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate contracts directory and file"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_services", clean=False
        )

        # output_dir is already .../domains/{domain}/contracts
        ensure_directory(output_dir)

        domain_name = context.domain_name
        contracts_file = output_dir / f"{domain_name}.zod.schema.ts"

        content = self._generate_contracts_content(context, domain_name)
        write_file(contracts_file, content)
        files.append(contracts_file)

        return files

    def _generate_contracts_content(self, context: GenerationContext, domain_name: str) -> str:
        """Generate contracts file content"""
        domain_pascal = pascal_case(domain_name)

        return f'''/**
 * {domain_pascal} Domain Contracts
 *
 * Re-exports Zod schemas from @ddd/core for runtime validation.
 * This avoids duplication and ensures alignment with the API contract.
 *
 * Architecture:
 * - Single source of truth: @ddd/core
 * - No code duplication or drift
 * - Runtime validation of API responses
 * - Used in services to validate responses
 *
 * @see @ddd/core/{domain_name} for the source schemas
 */

import {{ {domain_name}Schemas as core{domain_pascal}Schemas }} from "@ddd/core/{domain_name}";
import type {{ z }} from "zod";

/**
 * Re-export schemas from core
 * These are the same schemas used by the api-server, ensuring perfect alignment
 */
export const {{
  // TODO: Add specific schema exports based on OpenAPI spec
  // ResponseMeta,
  // PageInfo,
  // etc.
}} = core{domain_pascal}Schemas;

/**
 * Export all schemas as a namespace for convenience
 */
export const {domain_name}Schemas = core{domain_pascal}Schemas;
'''


class WebappApiTypesGenerator(WebappServicesFileGenerator):
    """
    Generates API types file (TypeScript types re-exports from @ddd/core)

    Pattern: Re-exports TypeScript types from core package
    """

    @property
    def name(self) -> str:
        return "Webapp API Types Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_api_types"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate API types file"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_services", clean=False
        )

        domain_name = context.domain_name
        api_types_file = output_dir / f"{domain_name}.api-types.ts"

        content = self._generate_api_types_content(context, domain_name)
        write_file(api_types_file, content)
        files.append(api_types_file)

        return files

    def _generate_api_types_content(self, context: GenerationContext, domain_name: str) -> str:
        """Generate API types file content"""
        domain_pascal = pascal_case(domain_name)

        return f'''/**
 * {domain_pascal} API Types
 *
 * API contract types come from @ddd/core.
 * This file contains ONLY re-exports - no local API contract definitions.
 */

// ============================================================================
// API Type Re-exports (from @ddd/core)
// ============================================================================
// All API contract types must come from core - no local definitions

// Re-export types from core
// TODO: Add specific type exports based on OpenAPI spec
export type {{
  // Add types from @ddd/core/{domain_name}
}} from "@ddd/core";

// Re-export with alias for backward compatibility if needed
// export type Core{domain_pascal}Item = {domain_pascal}Item;
'''


class WebappServiceGenerator(WebappServicesFileGenerator):
    """
    Generates service file (API client)

    Pattern: Service class that wraps apiClient calls
    """

    @property
    def name(self) -> str:
        return "Webapp Service Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_service"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate service file"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_services", clean=False
        )

        domain_name = context.domain_name
        service_file = output_dir / f"{domain_name}.service.ts"

        # Extract operations to generate service methods
        operations = extract_operations(context.spec)

        content = self._generate_service_content(context, domain_name, operations)
        write_file(service_file, content)
        files.append(service_file)

        return files

    def _generate_service_content(
        self, context: GenerationContext, domain_name: str, operations: List[Dict[str, Any]]
    ) -> str:
        """Generate service file content"""
        domain_pascal = pascal_case(domain_name)
        service_name = f"{domain_name}Service"

        # Generate service methods from operations
        methods = []
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            path = op_data["path"]
            method = op_data["method"].upper()

            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            method_name = self._generate_method_name(verb, resource, operation_id)
            method_code = self._generate_method_code(
                method_name, operation, operation_id, path, method, verb, resource, domain_name
            )
            methods.append(method_code)

        methods_str = "\n\n".join(methods)

        return f'''/**
 * {domain_pascal} Service
 *
 * API client for {domain_name} domain.
 * Uses ApiResponse<T> pattern - response.data is already T.
 *
 * TODO(client): Migrate all endpoints to typed client when generated.
 * Currently using apiClient.get/post() as temporary fallback.
 */

import {{ apiClient }} from "@/services/shared/infrastructure";
import {{ makeService }} from "@/services/shared/infrastructure/service-wrapper";
import {{ getEffectiveOrgId }} from "@/services/shared/infrastructure/tenant-state";
import {{ validateApiResponse, formatValidationError }} from "@/services/shared/contracts";
// TODO: Import schemas from contracts
// import {{ ... }} from "./contracts";
// TODO: Import types from api-types
// import type {{ ... }} from "./{domain_name}.api-types";

// ============================================================================
// Response Type Definitions (for API responses)
// ============================================================================

const raw{domain_pascal}Service = {{
{methods_str}
}};

// Wrap service with error handling and logging
export const {service_name} = makeService(raw{domain_pascal}Service, "{domain_name}");
'''

    def _generate_method_name(self, verb: str, resource: str, operation_id: str) -> str:
        """Generate method name from operation"""
        # Use operation_id to generate method name
        # e.g., "getContentItems" -> "getContent", "createContentItem" -> "createContent"
        resource_pascal = pascal_case(resource) if resource else ""
        if verb == "get" and resource:
            return f"get{resource_pascal}"
        elif verb == "list" and resource:
            return f"get{resource_pascal}"
        elif verb == "create" and resource:
            return f"create{resource_pascal}"
        elif verb == "update" and resource:
            return f"update{resource_pascal}"
        elif verb == "delete" and resource:
            return f"delete{resource_pascal}"
        else:
            # Fallback to camelCase operation_id
            return camel_case(operation_id)

    def _generate_method_code(
        self, method_name: str, operation: Dict[str, Any], operation_id: str,
        path: str, http_method: str, verb: str, resource: str, domain_name: str
    ) -> str:
        """Generate method code"""
        # Extract path parameters
        path_params = []
        if "{" in path:
            import re
            path_params = re.findall(r'\{(\w+)\}', path)

        # Build method signature
        params = []
        if path_params:
            params.extend([f"{p}: string" for p in path_params if p != "orgId"])

        # Add query/body params based on HTTP method
        if http_method in ["GET", "DELETE"]:
            params.append("params?: Record<string, any>")
        elif http_method in ["POST", "PUT", "PATCH"]:
            params.append("data?: any")

        params.append("signal?: AbortSignal")

        params_str = ", ".join(params)

        # Build URL
        clean_path = path.replace("/orgs/{orgId}/", "").replace("{orgId}/", "")
        url_template = f"/orgs/${{orgId}}/{clean_path}"
        for param in path_params:
            if param != "orgId":
                url_template = url_template.replace(f"{{{param}}}", f"${{{param}}}")

        url_builder = f"`{url_template}`"
        if http_method in ["GET", "DELETE"] and "params" in params_str:
            url_builder += " + (params ? `?${new URLSearchParams(params).toString()}` : '')"

        return_code = "response.data" if http_method in ["GET", "POST", "PUT", "PATCH"] else "undefined"

        # Build request body line
        body_line = ""
        if http_method in ["POST", "PUT", "PATCH"]:
            body_line = "      body: data,"

        return f'''  /**
   * {operation.get("summary", operation_id)}
   */
  async {method_name}({params_str}): Promise<any> {{
    const orgId = getEffectiveOrgId();
    if (!orgId) {{
      throw new Error("Organization ID is required");
    }}

    const url = {url_builder};

    // TODO(client): migrate when generated
    const response = await apiClient.{http_method.lower()}<any>(url, {{
{body_line}
      signal,
    }});

    // TODO: Validate response with Zod schema
    // const validation = validateApiResponse(
    //   ResponseSchema,
    //   response
    // );

    return {return_code};
  }}'''


class WebappFacadeGenerator(WebappServicesFileGenerator):
    """
    Generates facade file (High-level API for components)
    """

    @property
    def name(self) -> str:
        return "Webapp Facade Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_facade"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate facade file"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_services", clean=False
        )

        domain_name = context.domain_name
        facade_file = output_dir / "facade.ts"

        operations = extract_operations(context.spec)
        content = self._generate_facade_content(context, domain_name, operations)
        write_file(facade_file, content)
        files.append(facade_file)

        return files

    def _generate_method_name(self, verb: str, resource: str, operation_id: str) -> str:
        """Generate method name from operation (shared with service generator)."""
        resource_pascal = pascal_case(resource) if resource else ""
        if verb == "get" and resource:
            return f"get{resource_pascal}"
        elif verb == "list" and resource:
            return f"get{resource_pascal}"
        elif verb == "create" and resource:
            return f"create{resource_pascal}"
        elif verb == "update" and resource:
            return f"update{resource_pascal}"
        elif verb == "delete" and resource:
            return f"delete{resource_pascal}"
        else:
            return camel_case(operation_id)

    def _generate_facade_content(
        self, context: GenerationContext, domain_name: str, operations: List[Dict[str, Any]]
    ) -> str:
        """Generate facade file content"""
        domain_pascal = pascal_case(domain_name)
        service_name = f"{domain_name}Service"

        # Generate facade methods
        methods = []
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            method_name = self._generate_method_name(verb, resource, operation_id)
            facade_method = f'''  /**
   * {operation.get("summary", operation_id)}
   */
  async {method_name}(...args: Parameters<typeof {service_name}.{method_name}>): Promise<any> {{
    return {service_name}.{method_name}(...args);
  }}'''
            methods.append(facade_method)

        methods_str = "\n\n".join(methods)

        return f'''/**
 * {domain_pascal} Domain Facade
 *
 * High-level API for {domain_name} domain operations.
 * Provides simplified interface for components.
 *
 * Architecture:
 * - Facade pattern for domain operations
 * - Components should use facades, not services directly
 * - Hides complexity of domain orchestration
 */

import {{ {service_name} }} from "./{domain_name}.service";
// TODO: Import types
// import type {{ ... }} from "./{domain_name}.api-types";

/**
 * {domain_pascal} Facade
 *
 * High-level API for {domain_name} operations.
 * Components should use this facade instead of services directly.
 */
export const {domain_name}Facade = {{
{methods_str}
}};
'''


class WebappHooksGenerator(WebappServicesFileGenerator):
    """
    Generates React Query hooks (queries.ts, mutations.ts, index.ts)
    """

    @property
    def name(self) -> str:
        return "Webapp Hooks Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_hooks"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate hooks files"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_services", clean=False
        )

        # output_dir is already .../domains/{domain}/hooks
        hooks_dir = output_dir
        ensure_directory(hooks_dir)

        operations = extract_operations(context.spec)

        # Separate operations into queries and mutations
        queries = [op for op in operations if op["method"].upper() in ["GET", "HEAD", "OPTIONS"]]
        mutations = [op for op in operations if op["method"].upper() in ["POST", "PUT", "PATCH", "DELETE"]]

        # Generate queries.ts
        queries_file = hooks_dir / "queries.ts"
        queries_content = self._generate_queries_content(context, queries)
        write_file(queries_file, queries_content)
        files.append(queries_file)

        # Generate mutations.ts
        mutations_file = hooks_dir / "mutations.ts"
        mutations_content = self._generate_mutations_content(context, mutations)
        write_file(mutations_file, mutations_content)
        files.append(mutations_file)

        # Generate index.ts
        index_file = hooks_dir / "index.ts"
        index_content = self._generate_hooks_index_content(context)
        write_file(index_file, index_content)
        files.append(index_file)

        return files

    def _generate_queries_content(
        self, context: GenerationContext, queries: List[Dict[str, Any]]
    ) -> str:
        """Generate queries.ts content"""
        domain_name = context.domain_name
        domain_pascal = pascal_case(domain_name)
        service_name = f"{domain_name}Service"

        hooks = []
        for op_data in queries:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            hook_name = self._generate_hook_name(verb, resource, operation_id, "query")
            method_name = self._generate_hooks_method_name(verb, resource, operation_id)

            # Extract path params for query key
            path = op_data["path"]
            path_params = []
            if "{" in path:
                import re
                path_params = [p for p in re.findall(r'\{(\w+)\}', path) if p != "orgId"]

            query_key = f'["{domain_name}", "{resource}", {", ".join([f"{p}" for p in path_params]) if path_params else ""}]'

            hook_code = f'''/**
 * Hook to {operation.get("summary", operation_id).lower()}
 *
 * Query key: {query_key}
 */
export function {hook_name}({self._generate_hook_params(op_data)}) {{
  return useTenantQuery(
    {query_key},
    async (orgId: string, signal?: AbortSignal) => {{
      return {service_name}.{method_name}({self._generate_hook_call_args(op_data)});
    }}{self._generate_hook_options(op_data)}
  );
}}'''
            hooks.append(hook_code)

        hooks_str = "\n\n".join(hooks)

        return f'''/**
 * {domain_pascal} Query Hooks
 *
 * React Query hooks for fetching {domain_name} data
 */

import {{ useTenantQuery }} from "@/services/shared/infrastructure";
import {{ {service_name} }} from "../{domain_name}.service";

{hooks_str}
'''

    def _generate_mutations_content(
        self, context: GenerationContext, mutations: List[Dict[str, Any]]
    ) -> str:
        """Generate mutations.ts content"""
        domain_name = context.domain_name
        domain_pascal = pascal_case(domain_name)
        service_name = f"{domain_name}Service"

        hooks = []
        for op_data in mutations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )

            hook_name = self._generate_hook_name(verb, resource, operation_id, "mutation")
            method_name = self._generate_hooks_method_name(verb, resource, operation_id)

            # Determine invalidate queries
            invalidate_key = f'["{domain_name}", "{resource}"]'

            hook_code = f'''/**
 * Hook to {operation.get("summary", operation_id).lower()}
 *
 * Automatically invalidates {domain_name} queries on success.
 */
export function {hook_name}() {{
  return useTenantMutation(
    async (orgId: string, data: any) => {{
      return {service_name}.{method_name}(data);
    }},
    {{
      invalidateQueries: [{invalidate_key}],
    }}
  );
}}'''
            hooks.append(hook_code)

        hooks_str = "\n\n".join(hooks)

        return f'''/**
 * {domain_pascal} Mutation Hooks
 *
 * React Query hooks for mutating {domain_name} data
 */

import {{ useTenantMutation }} from "@/services/shared/infrastructure";
import {{ {service_name} }} from "../{domain_name}.service";
// TODO: Import types
// import type {{ ... }} from "../{domain_name}.api-types";

{hooks_str}
'''

    def _generate_hooks_index_content(self, context: GenerationContext) -> str:
        """Generate hooks index.ts content"""
        domain_name = context.domain_name

        return f'''/**
 * {pascal_case(domain_name)} Hooks
 *
 * Centralized exports for all {domain_name}-related hooks
 */

// React Query hooks
export * from "./queries";
export * from "./mutations";
'''

    def _generate_hook_name(self, verb: str, resource: str, operation_id: str, hook_type: str) -> str:
        """Generate hook name"""
        resource_pascal = pascal_case(resource) if resource else ""
        if hook_type == "query":
            if verb == "get" or verb == "list":
                return f"use{resource_pascal}"
            else:
                return f"use{verb.capitalize()}{resource_pascal}"
        else:  # mutation
            if verb == "create":
                return f"useCreate{resource_pascal}"
            elif verb == "update":
                return f"useUpdate{resource_pascal}"
            elif verb == "delete":
                return f"useDelete{resource_pascal}"
            else:
                return f"use{verb.capitalize()}{resource_pascal}"

    def _generate_hooks_method_name(self, verb: str, resource: str, operation_id: str) -> str:
        """Generate service method name for hooks"""
        resource_pascal = pascal_case(resource) if resource else ""
        if verb == "get" and resource:
            return f"get{resource_pascal}"
        elif verb == "list" and resource:
            return f"get{resource_pascal}"
        elif verb == "create" and resource:
            return f"create{resource_pascal}"
        elif verb == "update" and resource:
            return f"update{resource_pascal}"
        elif verb == "delete" and resource:
            return f"delete{resource_pascal}"
        else:
            return camel_case(operation_id)

    def _generate_hook_params(self, op_data: Dict[str, Any]) -> str:
        """Generate hook function parameters"""
        path = op_data["path"]
        path_params = []
        if "{" in path:
            import re
            path_params = [p for p in re.findall(r'\{(\w+)\}', path) if p != "orgId"]

        params = []
        for param in path_params:
            params.append(f"{param}: string")

        # Add query params for GET requests
        if op_data["method"].upper() == "GET":
            params.append("params?: Record<string, any>")

        return ", ".join(params) if params else ""

    def _generate_hook_call_args(self, op_data: Dict[str, Any]) -> str:
        """Generate service method call arguments"""
        path = op_data["path"]
        path_params = []
        if "{" in path:
            import re
            path_params = [p for p in re.findall(r'\{(\w+)\}', path) if p != "orgId"]

        args = []
        args.extend(path_params)

        if op_data["method"].upper() == "GET":
            args.append("params")
            args.append("signal")
        elif op_data["method"].upper() in ["POST", "PUT", "PATCH"]:
            args.append("data")
            args.append("signal")
        elif op_data["method"].upper() == "DELETE":
            if path_params:
                args.append("signal")

        return ", ".join(args)

    def _generate_hook_options(self, op_data: Dict[str, Any]) -> str:
        """Generate hook options"""
        path = op_data["path"]
        path_params = []
        if "{" in path:
            import re
            path_params = [p for p in re.findall(r'\{(\w+)\}', path) if p != "orgId"]

        options = []
        if path_params:
            # Enable hook only if required params are provided
            enabled_condition = " && ".join([f"!!{p}" for p in path_params])
            options.append(f"enabled: {enabled_condition}")

        if options:
            return ",\n    {\n      " + ",\n      ".join(options) + "\n    }"
        return ""


class WebappServicesIndexGenerator(WebappServicesFileGenerator):
    """
    Generates services domain index.ts (barrel export)
    """

    @property
    def name(self) -> str:
        return "Webapp Services Index Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_services_index"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate index file"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_services", clean=False
        )

        domain_name = context.domain_name
        index_file = output_dir / "index.ts"

        content = self._generate_index_content(context, domain_name)
        write_file(index_file, content)
        files.append(index_file)

        return files

    def _generate_index_content(self, context: GenerationContext, domain_name: str) -> str:
        """Generate index.ts content"""
        domain_pascal = pascal_case(domain_name)
        service_name = f"{domain_name}Service"

        return f'''/**
 * {domain_pascal} Domain
 *
 * Barrel export for {domain_name} service, types, hooks, and view models.
 *
 * Architecture Rules:
 * - API types: re-exports from @ddd/core only
 * - View models: UI-only extensions (VM suffix)
 * - Service: only place that touches network
 * - Hooks: call service only (never apiClient directly)
 * - Mappers: internal to service layer (not for components)
 * - Components: domain-specific UI (not exported from barrel)
 */

// ============================================================================
// Service (runtime boundary - only place that touches network)
// ============================================================================
export {{ {service_name} }} from './{domain_name}.service';

// ============================================================================
// Facade (high-level API for components)
// ============================================================================
export {{ {domain_name}Facade }} from './facade';

// ============================================================================
// Contracts (runtime validation)
// ============================================================================
export * from "./contracts";

// ============================================================================
// API Types (re-exports from @ddd/core only)
// ============================================================================
// These are immutable API contracts - never define locally
export type {{
  // TODO: Add type exports from api-types
}} from './{domain_name}.api-types';

// ============================================================================
// Hooks (consolidated in hooks/ directory)
// ============================================================================
export * from './hooks';

// ============================================================================
// Components (domain-specific UI - not exported from barrel)
// ============================================================================
// Components are now in features/ directory and should be imported from there.
// This prevents cross-domain component dependencies and keeps the barrel focused.
'''
