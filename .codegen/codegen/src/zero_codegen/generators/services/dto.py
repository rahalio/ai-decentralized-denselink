"""
DTO Generator - Generates application DTOs

Per DDD: DTOs belong in services layer (application layer).
DTOs are input/output types for use cases.
"""

from pathlib import Path
from typing import Dict, Any, List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import (
    extract_operations,
    get_request_body_schema_name,
    get_response_schema_name,
)
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory
from ...utils.string import kebab_case, pascal_case, dto_input_type_name, dto_output_type_name, extract_verb_from_operation_id


class DTOGenerator(BaseGenerator):
    """
    Generates DTO files
    
    Pattern: export type PublishContentInput = { ... };
    export type PublishContentOutput = { ... };
    """
    
    @property
    def name(self) -> str:
        return "DTO Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "dto"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate DTO files"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "services" / "src" / context.domain_name / "dto"
        if context.config.pipeline.clean and output_dir.exists():
            clean_directory(output_dir)
        ensure_directory(output_dir)

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
        
        # Generate DTO file for each resource
        for resource, ops in resource_operations.items():
            # Use kebab-case for filename ending with .dto.ts (e.g., NotificationAuditLog -> notification-audit-log.dto.ts)
            dto_file_name = kebab_case(resource)
            dto_file = output_dir / f"{dto_file_name}.dto.ts"
            
            header = self.generate_header(
                context,
                f"{pascal_case(resource)} DTOs - Application DTOs"
            )
            
            dto_content = self._generate_dto_content(
                context,
                resource,
                ops,
                header
            )
            
            write_file(dto_file, dto_content)
            files.append(dto_file)
        
        # Generate DTOs index
        index_file = output_dir / "index.ts"
        index_content = self._generate_index(context, list(resource_operations.keys()))
        write_file(index_file, index_content)
        files.append(index_file)
        
        context.logger.info(f"Generated {len(files)} DTO files for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
    
    def _generate_dto_content(
        self,
        context: GenerationContext,
        resource: str,
        operations: List[Dict[str, Any]],
        header: str
    ) -> str:
        """Generate DTO file content"""
        seen_types = set()
        input_types = []
        output_types = []
        imported_types = set()  # Track types that need to be imported
        
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            
            # Generate input type
            input_type, input_imports = self._generate_input_type(context, verb, resource, operation_id, operation)
            if input_type:
                # Extract type name to check for duplicates
                type_name = input_type.split("=")[0].replace("export type", "").strip()
                if type_name not in seen_types:
                    seen_types.add(type_name)
                    input_types.append(input_type)
                    imported_types.update(input_imports)
            
            # Generate output type
            output_type, output_imports = self._generate_output_type(context, verb, resource, operation_id, operation)
            if output_type:
                # Extract type name to check for duplicates
                type_name = output_type.split("=")[0].replace("export type", "").strip()
                if type_name not in seen_types:
                    seen_types.add(type_name)
                    output_types.append(output_type)
                    imported_types.update(output_imports)
        
        types_str = "\n\n".join(input_types + output_types)
        
        # Generate import statement for referenced types
        import_stmt = ""
        if imported_types:
            types_list = ", ".join(sorted(imported_types))
            import_stmt = f"import type {{ {types_list} }} from \"@ddd/core/{context.domain_name}/types\";\n\n"
        
        return f"""{header}/**
 * {pascal_case(resource)} DTOs
 *
 * DDD: Application DTOs for {pascal_case(resource)} use cases.
 */

{import_stmt}{types_str}
"""
    
    def _generate_input_type(
        self,
        context: GenerationContext,
        verb: str,
        resource: str,
        operation_id: str,
        operation: Dict[str, Any]
    ) -> tuple[str, set[str]]:
        """Generate input type
        
        Returns:
            Tuple of (type_definition, imported_types_set)
        """
        input_type_name = dto_input_type_name(operation_id)

        from zero_codegen.utils.string import pascal_case
        from zero_codegen.utils.openapi import _operation_has_parameters

        has_params = _operation_has_parameters(operation, context.spec)
        params_name = f"{pascal_case(operation_id)}Params" if has_params else None

        body_schema = get_request_body_schema_name(
            operation, context.spec, getattr(context, "unbundled_spec", None)
        )
        request_body = operation.get("requestBody")
        content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
        has_json_body = bool(content.get("application/json"))
        body_name = body_schema
        if not body_name and has_json_body:
            body_name = f"{pascal_case(operation_id)}RequestInput"

        # Path/query Params intersected with body when both exist
        if params_name and body_name:
            return (
                f"export type {input_type_name} = {params_name} & {body_name};",
                {params_name, body_name},
            )
        if body_name:
            return f"export type {input_type_name} = {body_name};", {body_name}
        if params_name:
            return f"export type {input_type_name} = {params_name};", {params_name}

        # Fallback: inline path params if somehow not classified as Params
        parameters = operation.get("parameters", [])
        has_path_params = any(
            (p.get("in") == "path") if isinstance(p, dict) and "$ref" not in p
            else False
            for p in parameters
        )
        if has_path_params:
            props = []
            for param in parameters:
                if isinstance(param, dict) and param.get("in") == "path":
                    param_name = param.get("name", "")
                    param_schema = param.get("schema", {})
                    param_type = self._get_type_from_schema(param_schema)
                    props.append(f"  {param_name}: {param_type};")
            if props:
                props_str = "\n".join(props)
                return f"export type {input_type_name} = {{\n{props_str}\n}};", set()

        return f"export type {input_type_name} = {{}};", set()
    
    def _generate_output_type(
        self,
        context: GenerationContext,
        verb: str,
        resource: str,
        operation_id: str,
        operation: Dict[str, Any]
    ) -> tuple[str, set[str]]:
        """Generate output type
        
        Returns:
            Tuple of (type_definition, imported_types_set)
        """
        # Use canonical operation-based naming for consistency with port and use case generators
        output_type_name = dto_output_type_name(operation_id)
        
        # Check if there's a response schema
        response_schema_name = get_response_schema_name(operation, context.spec, "200")
        status_code = "200"
        if not response_schema_name:
            response_schema_name = get_response_schema_name(operation, context.spec, "201")
            status_code = "201"
        
        if response_schema_name:
            # Generate operation-based response type name (e.g., ListProvidersResponse)
            # This matches the naming convention used in the types index
            operation_response_type = f"{pascal_case(operation_id)}Response"
            # Use the operation-based response type (needs to be imported)
            return f"export type {output_type_name} = {operation_response_type};", {operation_response_type}
        
        # Default empty type
        return f"export type {output_type_name} = {{}};", set()
    
    def _get_type_from_schema(self, schema: Dict[str, Any]) -> str:
        """Get TypeScript type from OpenAPI schema"""
        schema_type = schema.get("type", "any")
        type_map = {
            "string": "string",
            "number": "number",
            "integer": "number",
            "boolean": "boolean",
            "array": "any[]",
            "object": "Record<string, any>",
        }
        return type_map.get(schema_type, "any")
    
    def _generate_index(self, context: GenerationContext, resources: List[str]) -> str:
        """Generate DTOs index file"""
        # Use kebab-case for export paths
        exports = "\n".join([f"export * from \"./{kebab_case(resource)}.dto.js\";" for resource in resources])
        
        return f"""/**
 * {pascal_case(context.domain_name)} DTOs
 *
 * DDD: Application DTOs for {context.domain_name} domain.
 */

{exports}
"""
