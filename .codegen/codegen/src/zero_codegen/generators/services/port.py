"""
Port Generator - Generates application ports (method-based interfaces)

Per DDD: Ports belong in services layer (application layer).
Ports define application contracts that adapters implement.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations, get_request_body_schema_name, get_response_schema_name
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory
from ...utils.string import kebab_case, pascal_case, camel_case, dto_input_type_name, dto_output_type_name, extract_verb_from_operation_id
from ...utils.port_determination import PortDetermination
from ...utils.x_codegen_extensions import should_skip_port


class PortGenerator(BaseGenerator):
    """
    Generates port interfaces (method-based)
    
    Pattern: export interface ProviderPublisher {
      publishContent(params: PublishContentParams): Promise<PublishContentResult>;
    }
    """
    
    @property
    def name(self) -> str:
        return "Port Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "port"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate port files"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "services" / "src" / context.domain_name / "ports"
        if context.config.pipeline.clean and output_dir.exists():
            clean_directory(output_dir)
        ensure_directory(output_dir)

        # Extract operations and group by port type
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)
        
        # Group operations by port (based on operation patterns)
        ports = self._identify_ports(operations, context)
        
        # Also check for entities with x-dynamodb metadata that need Repository ports
        # This ensures Repository ports exist even if operations are tagged as Client/Publisher
        from ...utils.openapi import extract_schemas
        from ...generators.core.repositories.entity_extractor import EntityExtractor
        schemas_dict = extract_schemas(context.spec)
        
        # Find all persisted entities (have x-dynamodb.entityType)
        persisted_entities = {}
        for schema_name, schema_def in schemas_dict.items():
            if isinstance(schema_def, dict):
                x_dynamodb = schema_def.get("x-dynamodb")
                if isinstance(x_dynamodb, dict) and x_dynamodb.get("entityType"):
                    if schema_def.get("x-value-object") is not True:
                        # Extract resource name from schema name
                        resource = NamingConvention.resource_for_grouping(schema_name)
                        repo_name = f"{pascal_case(resource)}Repository"
                        # Find operations for this entity
                        entity_ops = [op for op in operations if NamingConvention.resource_for_grouping(op["operation_id"], op.get("path")) == resource]
                        if entity_ops and repo_name not in ports:
                            ports[repo_name] = entity_ops
        
        # Generate port file for each identified port
        for port_name, port_operations in ports.items():
            # Determine port type suffix from port name (not hardcoded!)
            # Ports can be: Repository, Client, Publisher, Refresher, etc.
            port_suffix = self._determine_port_suffix(port_name)
            # Remove suffix from port_name before converting to kebab_case to avoid duplication
            # e.g., "EventRepository" -> "Event" -> "event.repository.port.ts"
            port_base_name = self._remove_port_suffix(port_name, port_suffix)
            port_file_name = kebab_case(port_base_name)
            port_file = output_dir / f"{port_file_name}.{port_suffix}.port.ts"
            
            header = self.generate_header(
                context,
                f"{port_name} Port - Application port interface"
            )
            
            port_content = self._generate_port_content(
                context,
                port_name,
                port_operations,
                header
            )
            
            write_file(port_file, port_content)
            files.append(port_file)
        
        # Generate ports index
        index_file = output_dir / "index.ts"
        index_content = self._generate_index(context, list(ports.keys()))
        write_file(index_file, index_content)
        files.append(index_file)
        
        context.logger.info(f"Generated {len(files)} port files for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
    
    def _identify_ports(
        self,
        operations: List[Dict[str, Any]],
        context: GenerationContext
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Identify ports from operations"""
        ports: Dict[str, List[Dict[str, Any]]] = {}
        
        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data["operation"]

            if should_skip_port(operation):
                continue
            
            # Identify port based on operation patterns
            port_name = self._determine_port_name(
                operation_id, operation, context, path=op_data.get("path")
            )
            
            if port_name not in ports:
                ports[port_name] = []
            ports[port_name].append(op_data)
        
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
    
    def _remove_port_suffix(self, port_name: str, port_suffix: str) -> str:
        """
        Remove port suffix from port name to avoid duplication in filename.
        
        Examples:
            "EventRepository", "repository" -> "Event"
            "ProviderAccountClient", "client" -> "ProviderAccount"
            "ContentPublisher", "publisher" -> "Content"
        """
        # Map suffix back to PascalCase version
        suffix_map = {
            "repository": "Repository",
            "client": "Client",
            "publisher": "Publisher",
            "refresher": "Refresher"
        }
        
        pascal_suffix = suffix_map.get(port_suffix, "Repository")
        
        if port_name.endswith(pascal_suffix):
            return port_name[:-len(pascal_suffix)]
        return port_name
    
    def _generate_port_content(
        self,
        context: GenerationContext,
        port_name: str,
        operations: List[Dict[str, Any]],
        header: str
    ) -> str:
        """Generate port interface content"""
        methods = []
        dto_imports = set()
        
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            
            # Generate method signature
            method_name = self._generate_method_name(operation_id)
            input_type, output_type = self._generate_dto_types(operation_id, operation, context)
            dto_imports.add(input_type)
            dto_imports.add(output_type)
            
            methods.append(f"  {method_name}(input: {input_type}): Promise<{output_type}>;")
        
        methods_str = "\n".join(methods)
        
        # Determine which DTO file to import from
        # Group operations by resource to find the DTO file
        resources = set()
        for op_data in operations:
            operation_id = op_data["operation_id"]
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )
            resources.add(resource)
        
        # Generate imports for each resource's DTO file
        # Match DTO types to resources by finding which resource each DTO type belongs to
        # We need to map DTO types back to their source operations to determine the resource
        dto_to_resource = {}
        for op_data in operations:
            operation = op_data["operation"]
            operation_id = op_data["operation_id"]
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )
            input_type, output_type = self._generate_dto_types(operation_id, operation, context)
            dto_to_resource[input_type] = resource
            dto_to_resource[output_type] = resource
        
        # Group DTO types by resource
        resource_to_dtos = {}
        for dto_type in dto_imports:
            if dto_type in dto_to_resource:
                resource = dto_to_resource[dto_type]
                if resource not in resource_to_dtos:
                    resource_to_dtos[resource] = []
                resource_to_dtos[resource].append(dto_type)
        
        # Generate imports for each resource's DTO file
        import_lines = []
        for resource in sorted(resource_to_dtos.keys()):
            resource_dto_types = sorted(resource_to_dtos[resource])
            types_str = ", ".join(resource_dto_types)
            import_lines.append(f"import type {{ {types_str} }} from \"../dto/{kebab_case(resource)}.dto\";")
        
        imports_str = "\n".join(import_lines) if import_lines else ""
        
        # Re-export DTO types so adapters can import them from the port file
        # This allows adapters to only import from services/ports (not services/dto)
        dto_exports = []
        for resource in sorted(resource_to_dtos.keys()):
            resource_dto_types = sorted(resource_to_dtos[resource])
            types_str = ", ".join(resource_dto_types)
            dto_exports.append(f"export type {{ {types_str} }} from \"../dto/{kebab_case(resource)}.dto\";")
        
        dto_exports_str = "\n".join(dto_exports) if dto_exports else ""
        
        return f"""{header}/**
 * {port_name} Port
 *
 * DDD: Application port for {port_name.lower()} operations.
 * This is an application-level abstraction, not a domain concept.
 * Implementations live in adapters layer.
 */

{imports_str}
export interface {port_name} {{
{methods_str}
}}

{dto_exports_str}
"""
    
    def _generate_method_name(self, operation_id: str) -> str:
        """Generate method name from operation ID"""
        # Convert operation ID to camelCase method name
        # e.g., publishContent -> publishContent
        # e.g., startProviderConnection -> startProviderConnection
        return camel_case(operation_id)
    
    def _generate_dto_types(
        self,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext
    ) -> tuple[str, str]:
        """Generate DTO type names (Input and Output) - matches DTO generator naming"""
        return dto_input_type_name(operation_id), dto_output_type_name(operation_id)
    
    def _generate_index(
        self,
        context: GenerationContext,
        port_names: List[str],
    ) -> str:
        """Generate ports index file"""
        # Use appropriate port suffix for each port (derived from port name, not hardcoded!)
        exports = []
        for port_name in port_names:
            port_suffix = self._determine_port_suffix(port_name)
            # Remove suffix from port_name before converting to kebab_case to avoid duplication
            port_base_name = self._remove_port_suffix(port_name, port_suffix)
            port_file_name = kebab_case(port_base_name)
            exports.append(f"export * from \"./{port_file_name}.{port_suffix}.port.js\";")
        exports_str = "\n".join(exports)
        
        return f"""/**
 * {pascal_case(context.domain_name)} Ports
 *
 * DDD: Application ports for {context.domain_name} domain.
 */

{exports_str}
"""
