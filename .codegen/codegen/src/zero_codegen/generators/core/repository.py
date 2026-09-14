"""
Repository Generator - Generates repository interfaces

Per DDD: Repositories belong in core layer (domain layer).
"""

from pathlib import Path
from typing import List

from ...base.generator_bases import FileGenerator
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations
from ...utils.naming import NamingConvention
from ...utils.file import write_file, ensure_directory
from .repositories.entity_extractor import EntityExtractor
from .repositories.repository_builder import RepositoryBuilder


class RepositoryGenerator(FileGenerator):
    """Generates repository interfaces from OpenAPI schemas"""
    
    @property
    def name(self) -> str:
        return "Repository Generator"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def type(self) -> str:
        return "repository"
    
    def generate_files(self, context: GenerationContext, output_dir: Path) -> List[Path]:
        """Generate repository files for each resource"""
        files: List[Path] = []
        
        # Extract resources from operations and normalize using resource_for_grouping
        operations = extract_operations(context.spec)
        resources = set()
        
        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data["operation"]

            from ...utils.x_codegen_extensions import should_skip_persistence
            if should_skip_persistence(operation):
                continue

            # Skip OAuth operations - they don't return entities
            if any(pattern in operation_id.lower() for pattern in ["oauth", "connect", "callback", "start"]):
                from ...utils.openapi import get_response_schema_name
                response_schema_name = get_response_schema_name(operation, context.spec, "200")
                if not response_schema_name:
                    response_schema_name = get_response_schema_name(operation, context.spec, "201")
                if response_schema_name and "oauth" in response_schema_name.lower():
                    continue
            
            # Skip operations that return Response DTOs instead of entities
            from ...utils.openapi import get_response_schema_name, get_response_schema
            from ...utils.openapi import extract_schemas
            response_schema_name = get_response_schema_name(operation, context.spec, "200")
            if not response_schema_name:
                response_schema_name = get_response_schema_name(operation, context.spec, "201")
            
            # Skip operations with no response schema
            if not response_schema_name:
                responses = operation.get("responses", {})
                has_json_content = False
                for status_code in ["200", "201", "202"]:
                    if status_code in responses:
                        response = responses[status_code]
                        if isinstance(response, dict):
                            content = response.get("content", {})
                            if "application/json" in content:
                                has_json_content = True
                                break
                if not has_json_content:
                    continue
            
            if response_schema_name:
                # Get the actual response schema to check inner data schema
                response_schema = get_response_schema(operation, context.spec, "200")
                if not response_schema:
                    response_schema = get_response_schema(operation, context.spec, "201")
                
                schemas_dict = extract_schemas(context.spec)
                if not response_schema:
                    response_schema = schemas_dict.get(response_schema_name)
                
                # Check inner schema if wrapped in data
                if response_schema and isinstance(response_schema, dict):
                    if "properties" in response_schema:
                        data_prop = response_schema["properties"].get("data")
                        if data_prop and isinstance(data_prop, dict) and "properties" in data_prop:
                            data_props = data_prop["properties"]
                            if "isValid" in data_props or ("status" in data_props and "canRefresh" in data_props):
                                continue  # Skip Response DTO
                
                # Use semantic analysis to determine if we should skip repository generation
                from ...utils.string import extract_verb_from_operation_id
                verb = extract_verb_from_operation_id(operation_id)
                if verb != "list":
                    from ...utils.schema_analyzer import SchemaAnalyzer
                    if SchemaAnalyzer.should_skip_repository_generation(operation, context.spec, operation_id):
                        continue
            
            # Use resource_for_grouping to normalize (path-based when available)
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )
            resources.add(resource)
        
        if not resources:
            ensure_directory(output_dir)
            index_file = output_dir / "index.ts"
            write_file(
                index_file,
                f"""{self.generate_header(context, "Repositories barrel export")}
export {{}};
""",
            )
            files.append(index_file)
            return files
        
        # Generate repository interface for each resource
        # Skip value objects - they don't need repositories (not persisted)
        repo_filenames = []
        schemas_dict = extract_schemas(context.spec)
        
        for resource in resources:
            # Check if this resource is a value object (no repository needed)
            entity_name = EntityExtractor.extract_entity_name_from_operations(context, resource)
            # Core repos are driven by operations (entity file exists). x-dynamodb drives only DynamoDB adapters.
            if entity_name:
                entity_schema_def = schemas_dict.get(entity_name)
                is_value_object = False
                if entity_schema_def and isinstance(entity_schema_def, dict):
                    if entity_schema_def.get("x-value-object") is True:
                        is_value_object = True
                    elif entity_name.endswith("Response"):
                        data_prop = entity_schema_def.get("properties", {}).get("data")
                        if data_prop and isinstance(data_prop, dict) and "$ref" not in data_prop:
                            is_value_object = True
                if is_value_object:
                    context.logger.info(f"Skipping repository generation for '{resource}': value object (no repository)")
                    continue
            
            # Check if entity file exists - skip repository if entity wasn't generated
            # (e.g., computed data, transport DTOs that were skipped)
            from ...utils.string import kebab_case
            project_root = context.config.paths.project_root
            domain_dir = project_root / "packages" / "core" / "src" / context.domain_name
            models_dir = domain_dir / "models"
            resource_kebab = kebab_case(resource)
            entity_file = models_dir / f"{resource_kebab}.entity.ts"
            
            if not entity_file.exists():
                context.logger.info(f"Skipping repository generation for '{resource}': entity file does not exist (likely computed data or transport DTO)")
                continue
            
            repo_filename = NamingConvention.repository_filename(resource)
            repo_file = output_dir / repo_filename
            header = self.generate_header(context, f"Repository interface for {resource}")
            if not entity_name:
                from ...utils.string import pascal_case
                entity_name = pascal_case(resource)
            content = RepositoryBuilder.build_repository_content(context, resource, entity_name, header)
            write_file(repo_file, content)
            files.append(repo_file)
            repo_filenames.append((resource, repo_filename))
        
        # Generate index.ts for repositories directory (empty module when no repos)
        index_file = output_dir / "index.ts"
        if repo_filenames:
            index_content = self._generate_repositories_index(context, repo_filenames)
        else:
            ensure_directory(output_dir)
            index_content = f"""{self.generate_header(context, "Repositories barrel export")}
export {{}};
"""
        write_file(index_file, index_content)
        files.append(index_file)
        
        return files
    
    def _generate_repositories_index(
        self,
        context: GenerationContext,
        repo_filenames: List[tuple]
    ) -> str:
        """Generate index.ts for repositories directory"""
        header = self.generate_header(context, "Repositories barrel export")
        exports = []
        for resource, filename in sorted(repo_filenames):
            # Remove .ts extension
            import_name = filename.replace(".ts", "")
            exports.append(f'export * from "./{import_name}.js";')
        
        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""
