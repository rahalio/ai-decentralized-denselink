"""
DynamoDB Repository Generator - Generates DynamoDB repository implementations

Per DDD: Adapters implement repository interfaces from core (temporary) or ports from services.
These adapters wrap core repositories and add infrastructure concerns (caching, transformation).
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations, get_response_schema_name, get_domain_prefix
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, remove_stale_domain_dirs
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id
from ...utils.port_determination import PortDetermination


def _to_entity_type_pk(entity_type: str) -> str:
    """Convert entityType (e.g. AUDIT_LOG, CREATE_CAMPAIGN) to PK segment (e.g. AUDIT_LOGS, CAMPAIGNS) for Universal pattern.
    Strips operation verb prefixes so operation-named schemas (CreateCampaign, ListAuditLog) map to persisted entity type.
    Handles proper English pluralization: POLICY → POLICIES, BATCH → BATCHES, TAXONOMY → TAXONOMIES."""
    if not entity_type:
        return ""
    # Strip operation verb prefixes so operation-named schemas map to persisted entity type
    for prefix in ("CREATE_", "LIST_", "GET_", "UPDATE_", "DELETE_", "ACKNOWLEDGE_"):
        if entity_type.upper().startswith(prefix):
            entity_type = entity_type[len(prefix):].lstrip("_")
            break
    
    # Handle compound words (e.g., USAGE_SUMMARY) - pluralize the last part
    parts = entity_type.split("_")
    if len(parts) > 1:
        # Pluralize the last part
        last_part = parts[-1]
        pluralized_last = _pluralize_word(last_part)
        parts[-1] = pluralized_last
        result = "_".join(parts)
    else:
        # Single word, pluralize directly
        result = _pluralize_word(entity_type)
    
    return result.upper()


def _pluralize_word(word: str) -> str:
    """Pluralize a single word following English rules."""
    if not word:
        return word
    
    word_upper = word.upper()
    
    # Already plural (ends with S)
    if word_upper.endswith("S"):
        return word
    
    # Words ending in Y → IES (POLICY → POLICIES, TAXONOMY → TAXONOMIES)
    # But not if preceded by a vowel (DAY → DAYS, not DAIES)
    if word_upper.endswith("Y") and len(word) > 1:
        # Check if second-to-last char is a vowel
        second_last = word_upper[-2]
        if second_last not in "AEIOU":
            return word[:-1] + "IES"
    
    # Words ending in CH → CHES (BATCH → BATCHES)
    if word_upper.endswith("CH"):
        return word + "ES"
    
    # Words ending in SH → SHES
    if word_upper.endswith("SH"):
        return word + "ES"
    
    # Words ending in X → XES
    if word_upper.endswith("X"):
        return word + "ES"
    
    # Words ending in Z → ZES
    if word_upper.endswith("Z"):
        return word + "ES"
    
    # Default: add S
    return word + "S"


class DynamoDBRepositoryGenerator(BaseGenerator):
    """Generates DynamoDB repository implementations"""

    @property
    def name(self) -> str:
        return "DynamoDB Repository Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "dynamodb_repository"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate DynamoDB repository files"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory
        project_root = context.config.paths.project_root
        adapters_src = project_root / "platform" / "adapters" / "src"
        output_dir = adapters_src / context.domain_name

        # Remove generated dirs for domains no longer in config (e.g. publishing)
        if not context.get_state("adapters_stale_domains_cleaned"):
            enabled = {d.name for d in context.config.domains if d.enabled}
            for name in remove_stale_domain_dirs(adapters_src, enabled, preserve={"_shared"}):
                context.logger.info(f"Removed stale adapters domain: {name}")
            context.set_state("adapters_stale_domains_cleaned", True)

        # Clean entire directory when pipeline.clean (ensures no stale adapters),
        # but keep hand-maintained identity auth store / directory adapters.
        from ...utils.file import clean_directory
        if context.config.pipeline.clean and output_dir.exists():
            preserve_names = set()
            if context.domain_name == "identity":
                preserve_names.add("user-repository.ddb.ts")
            if context.domain_name == "opportunity":
                preserve_names.add("intel-repository.ddb.ts")
            if context.domain_name == "company":
                preserve_names.add("company-repository.ddb.ts")
            if context.domain_name == "person":
                preserve_names.add("person-repository.ddb.ts")
                preserve_names.add("person-repository.adapter.ts")
            if context.domain_name == "meeting":
                preserve_names.add("preference-repository.ddb.ts")
                preserve_names.add("scheduling-page-repository.ddb.ts")
            if preserve_names:
                for child in list(output_dir.iterdir()):
                    if child.name in preserve_names:
                        continue
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        import shutil
                        shutil.rmtree(child)
                context.logger.info(
                    f"Cleaned output directory (preserved {sorted(preserve_names)}): {output_dir}"
                )
            else:
                clean_directory(output_dir)
                context.logger.info(f"Cleaned output directory: {output_dir}")

        ensure_directory(output_dir)

        # Extract operations to identify repositories
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)

        # Identify repositories that need DynamoDB adapters
        repositories = self._identify_repositories(operations, context)

        # Generate adapter for each repository
        adapter_filenames = []
        for repo_name, repo_info in repositories.items():
            adapter_filename = f"{kebab_case(repo_name.replace('Repository', ''))}-repository.ddb.ts"
            adapter_file = output_dir / adapter_filename

            # Never overwrite hand-written identity UserRepositoryDdb
            if (
                context.domain_name == "identity"
                and adapter_filename == "user-repository.ddb.ts"
            ):
                context.logger.info(
                    "Skipping generated user-repository.ddb.ts (hand-maintained identity auth store)"
                )
                adapter_filenames.append((repo_name, adapter_filename))
                continue

            # Never overwrite opportunity intel stub until x-dynamodb + computation exist
            if (
                context.domain_name == "opportunity"
                and adapter_filename == "intel-repository.ddb.ts"
            ):
                context.logger.info(
                    "Skipping generated intel-repository.ddb.ts (hand-maintained deal-intel stub)"
                )
                adapter_filenames.append((repo_name, adapter_filename))
                continue

            # Never overwrite hand-maintained directory (pkPattern: global) adapters
            if (
                context.domain_name == "company"
                and adapter_filename == "company-repository.ddb.ts"
            ):
                context.logger.info(
                    "Skipping generated company-repository.ddb.ts (hand-maintained directory adapter)"
                )
                adapter_filenames.append((repo_name, adapter_filename))
                continue
            if context.domain_name == "person" and adapter_filename in (
                "person-repository.ddb.ts",
                "person-repository.adapter.ts",
            ):
                context.logger.info(
                    f"Skipping generated {adapter_filename} (hand-maintained directory adapter)"
                )
                adapter_filenames.append((repo_name, adapter_filename))
                continue
            if context.domain_name == "meeting" and adapter_filename in (
                "preference-repository.ddb.ts",
                "scheduling-page-repository.ddb.ts",
            ):
                context.logger.info(
                    f"Skipping generated {adapter_filename} (hand-maintained meeting adapter)"
                )
                adapter_filenames.append((repo_name, adapter_filename))
                continue

            header = self.generate_header(
                context,
                f"{repo_name} - DynamoDB Implementation"
            )

            adapter_content = self._generate_adapter_content(
                context,
                repo_name,
                repo_info,
                header
            )

            # Skip if no content generated (all operations filtered out)
            if adapter_content is None:
                continue

            write_file(adapter_file, adapter_content)
            files.append(adapter_file)
            adapter_filenames.append((repo_name, adapter_filename))

        # Generate index.ts for adapters directory
        if adapter_filenames:
            index_file = output_dir / "index.ts"
            index_content = self._generate_adapters_index(context, adapter_filenames)
            write_file(index_file, index_content)
            files.append(index_file)

        context.logger.info(f"Generated {len(files)} DynamoDB repository adapters for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _generate_adapters_index(
        self,
        context: GenerationContext,
        adapter_filenames: List[tuple]
    ) -> str:
        """Generate index.ts for adapters directory"""
        header = self.generate_header(context, "DynamoDB repository adapters barrel export")
        exports = []
        for repo_name, filename in sorted(adapter_filenames):
            # Remove .ts extension
            import_name = filename.replace(".ts", "")
            exports.append(f'export * from "./{import_name}.js";')

        exports_str = "\n".join(exports)
        return f"""{header}{exports_str}
"""

    def _identify_repositories(
        self,
        operations: List[Dict[str, Any]],
        context: GenerationContext
    ) -> Dict[str, Dict[str, Any]]:
        """Identify ALL repository ports that need DynamoDB adapters.

        Emits a .ddb.ts file for every repository port (EventRepository, NotificationRepository, etc.).
        Repos with x-dynamodb metadata get full implementation; others get stub with TODO.
        Uses same port discovery as port adapter generator for consistency.
        """
        repositories: Dict[str, Dict[str, Any]] = {}

        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data.get("operation", {})

            # Use same port determination as port adapter - ensures 1:1 with adapter files
            raw_port_name = PortDetermination.determine_port_name(
                operation_id, operation, context, path=op_data.get("path")
            )
            # Normalize to resource-scoped (e.g. CreateEventRepository -> EventRepository)
            port_name = PortDetermination.normalize_port_name_to_resource_scoped(raw_port_name)

            # Only emit for Repository ports (skip Publisher, Client, Refresher)
            if not port_name.endswith("Repository"):
                continue

            resource = port_name.replace("Repository", "")

            if port_name not in repositories:
                repositories[port_name] = {
                    "resource": resource,
                    "needs_caching": True,
                    "wraps_core_repo": True,
                    "operations": [],
                }
            repositories[port_name]["operations"].append(op_data)

        return repositories

    def _generate_adapter_content(
        self,
        context: GenerationContext,
        repo_name: str,
        repo_info: Dict[str, Any],
        header: str
    ) -> Optional[str]:
        """Generate DynamoDB adapter content using x-dynamodb metadata"""
        resource = repo_info["resource"]
        resource_kebab = kebab_case(resource)
        adapter_class_name = f"{repo_name.replace('Repository', '')}RepositoryDdb"

        # Determine port name
        port_name = repo_name

        # Extract entity schema and x-dynamodb metadata
        from ...utils.openapi import extract_schemas
        from ...generators.core.repositories.entity_extractor import EntityExtractor

        schemas_dict = extract_schemas(context.spec)
        resource_pascal = pascal_case(resource)
        from ...utils.string import singularize
        # Prefer schema that exactly matches resource name (e.g. Org for Org) when it has x-dynamodb;
        # otherwise fuzzy match can pick wrong schema (e.g. Org -> OrgSettings instead of Org -> ORGANIZATIONS).
        # Also try singular form (People→Person) when path irregular plurals slip through.
        entity_schema_name = None
        for candidate_name in (resource_pascal, singularize(resource_pascal)):
            if not candidate_name or candidate_name not in schemas_dict:
                continue
            candidate = schemas_dict.get(candidate_name)
            if isinstance(candidate, dict) and candidate.get("x-dynamodb") and isinstance(candidate.get("x-dynamodb"), dict):
                entity_schema_name = candidate_name
                break
        if not entity_schema_name:
            entity_schema_name = EntityExtractor._find_entity_by_metadata(
                context, resource, resource_pascal, schemas_dict, require_exact_match=False
            )

        if not entity_schema_name:
            # Fallback to old behavior if entity not found
            return self._generate_adapter_content_fallback(context, repo_name, repo_info, header)

        entity_schema = schemas_dict.get(entity_schema_name, {})
        x_dynamodb = entity_schema.get("x-dynamodb", {}) if isinstance(entity_schema, dict) else {}

        if not x_dynamodb or not isinstance(x_dynamodb, dict):
            # Fallback if no x-dynamodb metadata
            return self._generate_adapter_content_fallback(context, repo_name, repo_info, header)

        # Extract x-dynamodb metadata - all values must be dynamic
        # Per .docs/database/DYNAMO_DESIGN.md: SK = <ENTITY>#<entityId>#TIMESTAMP#<ts>; ENTITY is singular (e.g. CAMPAIGN, AUDIT_LOG).
        # Derive entityToken and skPrefix from entityType when omitted, so YAML can stay minimal.
        entity_type = x_dynamodb.get("entityType") or ""
        entity_token = x_dynamodb.get("entityToken") or entity_type
        sk_prefix = x_dynamodb.get("skPrefix") or entity_token
        is_child_entity = x_dynamodb.get("isChildEntity", False)
        parent_entity_type = x_dynamodb.get("parentEntityType") or ""
        parent_entity_token = x_dynamodb.get("parentEntityToken") or ""
        parent_id_field = x_dynamodb.get("parentIdField") or ""
        # Validate that parent_id_field is set if is_child_entity is True
        if is_child_entity and not parent_id_field:
            # Fallback: if child entity but no parent_id_field, treat as regular entity
            # This prevents generating invalid code like `${input.}`
            is_child_entity = False
            context.logger.warn(f"Entity {entity_type} has isChildEntity=True but parentIdField is empty. Treating as regular entity.")
        table_type = x_dynamodb.get("tableType") or "core"
        gsi1_enabled = x_dynamodb.get("gsi1Enabled", False)
        gsi2_enabled = x_dynamodb.get("gsi2Enabled", False)
        gsi3_enabled = x_dynamodb.get("gsi3Enabled", False)
        createdAt_field = x_dynamodb.get("createdAtField") or "createdAt"
        updatedAt_field = x_dynamodb.get("updatedAtField") or "updatedAt"
        soft_delete_enabled = x_dynamodb.get("softDeleteEnabled", False)

        # NEW: Extract new pattern fields from manual adapter analysis
        pk_pattern = x_dynamodb.get("pkPattern") or "entity"  # "org" | "entity" | "global"
        status_prefix = x_dynamodb.get("statusPrefix", False)  # Deprecated: prefer deletedAt soft-delete
        # Virial-aligned default: never emit ACTIVE# unless explicitly statusPrefix: true
        if status_prefix:
            print(
                f"  ⚠️  statusPrefix=true for {entity_type} — prefer softDeleteEnabled + deletedAt"
            )
        filter_fields = x_dynamodb.get("filterFields") or []  # Fields to support in filter expressions
        use_pk_query = x_dynamodb.get("usePkQuery", False)  # Use PK query instead of GSI for org-scoped queries

        # Universal Entity+Domain pattern (.docs/DYNAMODB_DESIGN.md): pk = ORG#orgId#DOMAIN#ENTITY_TYPE_PK, sk = entityId#timestamp
        # Directory pattern (pkPattern: global): PK=DIRECTORY#COLLECTION#id, SK=ENTITY#METADATA on base table
        use_universal_pattern = pk_pattern == "org"
        use_global_directory_pattern = pk_pattern == "global"
        # Always set domain and entity_type_pk when we have entity_type so Universal branches run for create/list/get
        # even when the matched schema is operation-named (e.g. CreateCampaign) with pkPattern "entity"
        domain = x_dynamodb.get("domain") or context.domain_name.upper().replace("-", "_")
        entity_type_pk = x_dynamodb.get("entityTypePk") or _to_entity_type_pk(entity_type)

        # Extract ID field name from entity schema properties
        from ...utils.schema_field_extractor import SchemaFieldExtractor
        id_field_name = SchemaFieldExtractor.find_id_field(entity_schema, context.spec) or "id"

        # Get table name using TableNameExtractor (property + optional constructor body)
        from ...utils.table_name_extractor import TableNameExtractor
        table_name_property, table_name_constructor_body = TableNameExtractor.generate_table_name_code(
            table_type, x_dynamodb.get("tableName"), context.domain_name, entity_type
        )

        # Extract all operations to generate all methods
        operations = repo_info.get("operations", [])

        # Collect DTO types needed for imports
        dto_input_types = set()
        dto_output_types = set()
        methods = []

        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data.get("operation", {})
            
            # Skip publisher operations - they belong to Publisher ports, not Repository ports
            # Check if this operation belongs to a Publisher port
            operation_port_name = PortDetermination.determine_port_name(
                operation_id, operation, context, path=op_data.get("path")
            )
            if operation_port_name.endswith("Publisher"):
                continue
            
            # Skip Client operations - they belong to Client ports, not Repository ports
            if operation_port_name.endswith("Client"):
                continue
            
            verb = extract_verb_from_operation_id(operation_id)

            # Generate DTO type names matching the pattern used in DTO generator
            operation_name = operation_id.replace(verb, "", 1) if operation_id.lower().startswith(verb.lower()) else operation_id
            operation_name_pascal = pascal_case(operation_name)

            if operation_name_pascal == pascal_case(resource):
                input_type_name = f"{pascal_case(verb)}{pascal_case(resource)}Input"
                output_type_name = f"{pascal_case(verb)}{pascal_case(resource)}Output"
            else:
                input_type_name = f"{operation_name_pascal}Input"
                output_type_name = f"{operation_name_pascal}Output"

            dto_input_types.add(input_type_name)
            dto_output_types.add(output_type_name)

            # Generate method signature matching port interface
            method_name = camel_case(operation_id)

            # Get path from operation data for path parameter extraction
            path = op_data.get("path", "")

            # Generate DynamoDB implementation based on verb and metadata
            method_body = self._generate_dynamodb_method_body(
                verb, operation_id, operation, context, input_type_name, output_type_name,
                entity_type, entity_token, sk_prefix, is_child_entity, parent_entity_type,
                parent_entity_token, parent_id_field, table_type, gsi1_enabled, gsi2_enabled,
                gsi3_enabled, createdAt_field, updatedAt_field, soft_delete_enabled, x_dynamodb,
                id_field_name, path, pk_pattern, status_prefix, filter_fields, use_pk_query,
                domain, entity_type_pk
            )

            # Ensure method_body is never None - provide fallback if generation fails
            if method_body is None:
                method_body = f"""    // TODO: Implement {verb} operation
    throw new Error("Operation {verb} not yet implemented");"""

            method_body = self._apply_adapter_input_ext_fix(method_body)

            # Use TypeScript utility types to extract types from port interface
            # This avoids needing to import DTOs separately since they're already in the port interface
            # Use Awaited<> to unwrap Promise since port methods return Promise<T> and async functions also return Promise<T>
            input_type = f"Parameters<{port_name}['{method_name}']>[0]"
            output_type = f"Awaited<ReturnType<{port_name}['{method_name}']>>"

            method_code = f"""  async {method_name}(input: {input_type}): Promise<{output_type}> {{
{method_body}
  }}"""
            methods.append(method_code)

        # Skip generating repository if no methods were generated (all operations filtered out)
        if not methods:
            return None

        methods_str = "\n\n".join(methods)

        # Generate imports
        port_base_name = port_name.replace("Repository", "")
        port_import_path = kebab_case(port_base_name)
        dto_import_path = kebab_case(resource)

        # Import only the port interface from services barrel export - DTOs are not needed since we use utility types
        # This maintains proper dependency direction: adapters depend only on ports
        port_import = f"import type {{ {port_name} }} from \"@ddd/services/{context.domain_name}\";"

        # Import DynamoDB client type using relative import (within same package)
        # Using _shared folder to indicate internal utilities
        dynamo_import = "import type { AdapterDynamoDBClient } from \"../_shared/dynamodb-client-types.js\";"

        # Import table name resolvers using relative import (separate file for utilities)
        table_resolver_import = "import { getCoreTableName, getBaseTableName, getAnalyticsTableName } from \"../_shared/dynamodb-utils.js\";"

        # PK/SK/GSI are built in this adapter (per route/YAML x-dynamodb); only sanitizeItem is shared
        key_helpers_import = "import { sanitizeItem } from \"../_shared/dynamodb-key-helpers.js\";"

        # Import ULID for ID generation in CREATE operations and correlation IDs (fallback)
        has_create_ops = any(
            extract_verb_from_operation_id(op_data.get("operation_id", "")) == "create"
            for op_data in operations
        )
        # Always import ulid for correlation ID generation (even if no create ops)
        ulid_import = "import { ulid } from \"ulid\";"

        # Universal pattern constants (when domain + entity_type_pk are set)
        universal_constants = ""
        if domain and entity_type_pk:
            universal_constants = f"""
  private readonly DOMAIN = "{domain}";
  private readonly ENTITY_TYPE_PK = "{entity_type_pk}";"""

        # Define metadata constants at class level - all values from x-dynamodb metadata
        metadata_constants = f"""  // Metadata from x-dynamodb annotation - all values are dynamic
  private readonly ENTITY_TYPE = "{entity_type}";
  private readonly ENTITY_TOKEN = "{entity_token}";
  private readonly SK_PREFIX = "{sk_prefix}";
  private readonly IS_CHILD_ENTITY = {str(is_child_entity).lower()};
  private readonly CREATED_AT_FIELD = "{createdAt_field}";
  private readonly UPDATED_AT_FIELD = "{updatedAt_field}";
  private readonly SOFT_DELETE_ENABLED = {str(soft_delete_enabled).lower()};{universal_constants}"""

        if is_child_entity:
            metadata_constants += f"""
  private readonly PARENT_ENTITY_TYPE = "{parent_entity_type}";
  private readonly PARENT_ENTITY_TOKEN = "{parent_entity_token}";
  private readonly PARENT_ID_FIELD = "{parent_id_field}";"""

        # Add helper method for correlation ID generation (from spec info.x-domain)
        domain_prefix = get_domain_prefix(context.spec, context.domain_name)
        correlation_id_helper = f"""
  private generateCorrelationId(): string {{
    const domainPrefix = "{domain_prefix}";
    return `${{domainPrefix}}_${{ulid().toLowerCase()}}`;
  }}"""

        # Per-adapter key builders from x-dynamodb (domain, entityType, entityToken).
        # PK ends with entityId (ORG#orgId#DOMAIN#COLLECTION#entityId). Use getCollectionPK(orgId) for list.
        # Directory (pkPattern: global): DIRECTORY#COLLECTION#entityId / ENTITY#METADATA
        key_builder_methods = ""
        if domain and entity_type_pk:
            sk_active = ""
            if status_prefix:
                sk_active = "ACTIVE#"
            if use_global_directory_pattern:
                key_builder_methods = f"""
  /** Directory PK from x-dynamodb pkPattern=global: DIRECTORY#COLLECTION#entityId */
  private buildPK(entityId: string): string {{
    return `DIRECTORY#${{this.ENTITY_TYPE_PK}}#${{entityId}}`;
  }}
  /** Directory SK: ENTITY#METADATA */
  private buildSK(): string {{
    return `${{this.ENTITY_TOKEN}}#METADATA`;
  }}
  /** GSI1 catalog list: DIRECTORY#COLLECTION */
  private buildGSI1PK(): string {{
    return `DIRECTORY#${{this.ENTITY_TYPE_PK}}`;
  }}
"""
            else:
                key_builder_methods = f"""
  /** Partition key from x-dynamodb: ORG#orgId#DOMAIN#COLLECTION#entityId (id in PK). */
  private buildPK(orgId: string, entityId: string): string {{
    return `ORG#${{orgId}}#${{this.DOMAIN}}#${{this.ENTITY_TYPE_PK}}#${{entityId}}`;
  }}
  /** Collection prefix for list/query: ORG#orgId#DOMAIN#COLLECTION (no entityId). */
  private getCollectionPK(orgId: string): string {{
    return `ORG#${{orgId}}#${{this.DOMAIN}}#${{this.ENTITY_TYPE_PK}}`;
  }}
  /** Deterministic SK: ENTITY#entityId (legacy …#TIMESTAMP#ts dual-read via begins_with). */
  private buildSK(entityId: string, _identifier?: string): string {{
    return `{sk_active}${{this.ENTITY_TOKEN}}#${{entityId}}`;
  }}
  /** GSI time SK: updatedAt#entityId (uniqueness under bulk writes). */
  private buildGsiSK(updatedAt: string, entityId: string): string {{
    return `${{updatedAt}}#${{entityId}}`;
  }}
  /** GSI2 list-by-org: ORG#orgId#COLLECTION */
  private buildGSI2PK(orgId: string): string {{
    return `ORG#${{orgId}}#${{this.ENTITY_TYPE_PK}}`;
  }}
"""

        class_content = f"""export class {adapter_class_name} implements {port_name} {{
  {table_name_property}
{metadata_constants}{correlation_id_helper}{key_builder_methods}

  constructor(private readonly dynamoClient: AdapterDynamoDBClient) {{
{table_name_constructor_body}
  }}

{methods_str}
}}"""

        return f"""{header}/**
 * {adapter_class_name}
 *
 * DDD: Infrastructure adapter implementing {resource} repository using DynamoDB.
 * Generated from x-dynamodb metadata in OpenAPI schema.
 */

{port_import}
{dynamo_import}
{table_resolver_import}
{key_helpers_import}
{ulid_import if ulid_import else ""}

/**
 * {adapter_class_name} using DynamoDB table (type: {table_type})
 *
 * Entity Type: {entity_type}
 * Entity Token: {entity_token}
 * SK Prefix: {sk_prefix}
 */
{class_content}
"""

    def _generate_adapter_content_fallback(
        self,
        context: GenerationContext,
        repo_name: str,
        repo_info: Dict[str, Any],
        header: str
    ) -> str:
        """Fallback adapter generation when x-dynamodb metadata is not available"""
        resource = repo_info["resource"]
        resource_kebab = kebab_case(resource)
        adapter_class_name = f"{repo_name.replace('Repository', '')}RepositoryDdb"
        port_name = repo_name

        operations = repo_info.get("operations", [])
        dto_input_types = set()
        dto_output_types = set()
        methods = []

        for op_data in operations:
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            operation_name = operation_id.replace(verb, "", 1) if operation_id.lower().startswith(verb.lower()) else operation_id
            operation_name_pascal = pascal_case(operation_name)

            if operation_name_pascal == pascal_case(resource):
                input_type_name = f"{pascal_case(verb)}{pascal_case(resource)}Input"
                output_type_name = f"{pascal_case(verb)}{pascal_case(resource)}Output"
            else:
                input_type_name = f"{operation_name_pascal}Input"
                output_type_name = f"{operation_name_pascal}Output"

            dto_input_types.add(input_type_name)
            dto_output_types.add(output_type_name)
            method_name = camel_case(operation_id)
            # Use TypeScript utility types to extract types from port interface
            # Use Awaited<> to unwrap Promise since port methods return Promise<T> and async functions also return Promise<T>
            input_type = f"Parameters<{port_name}['{method_name}']>[0]"
            output_type = f"Awaited<ReturnType<{port_name}['{method_name}']>>"
            methods.append(f"""  async {method_name}(input: {input_type}): Promise<{output_type}> {{
    // TODO: Implement using x-dynamodb metadata
    throw new Error("Not implemented - missing x-dynamodb metadata");
  }}""")

        methods_str = "\n\n".join(methods)
        port_base_name = port_name.replace("Repository", "")
        port_import_path = kebab_case(port_base_name)
        dto_import_path = kebab_case(resource)

        # Import only the port interface from services barrel export - DTOs are not needed since we use utility types
        port_import = f"import type {{ {port_name} }} from \"@ddd/services/{context.domain_name}\";"

        return f"""{header}/**
 * {adapter_class_name}
 *
 * DDD: Infrastructure adapter for {resource} repository.
 * ⚠️  Missing x-dynamodb metadata - implementation not generated.
 */

{port_import}

export class {adapter_class_name} implements {port_name} {{
  constructor(private readonly dynamoClient: any) {{}}

{methods_str}
}}
"""

    def _extract_path_parameter(self, operation: Dict[str, Any], context: GenerationContext, field_name: str, path: str = "") -> str:
        """Extract path parameter name that matches the field name"""
        import re

        # orgId must be exact-only. Fuzzy matching would bind entity `{id}` because
        # `"id" in "orgid"` is true after the real orgId param is skipped.
        if field_name.lower() == "orgid":
            if path:
                for param_name in re.findall(r"\{([^}]+)\}", path):
                    if param_name.lower() == "orgid":
                        return param_name
            for param in operation.get("parameters", []):
                if isinstance(param, dict) and param.get("in") == "path":
                    param_name = param.get("name", "")
                    if param_name.lower() == "orgid":
                        return param_name
                elif isinstance(param, str) and "$ref" in param:
                    from ...utils.openapi import resolve_ref
                    resolved = resolve_ref(context.spec, param)
                    if resolved and resolved.get("in") == "path":
                        param_name = resolved.get("name", "")
                        if param_name.lower() == "orgid":
                            return param_name
            return None

        # First, try to extract from path string (most reliable)
        if path:
            # Find all {paramName} patterns in path
            matches = re.findall(r'\{([^}]+)\}', path)
            # Exclude orgId
            for param_name in matches:
                if param_name.lower() == "orgid":
                    continue
                # Direct match
                if param_name.lower() == field_name.lower():
                    return param_name
                # Check if parameter name matches or contains the field name
                if field_name.lower() in param_name.lower() or param_name.lower() in field_name.lower():
                    return param_name
                # Try common patterns: fieldNameId, fieldName_id, field_name_id
                field_lower = field_name.lower()
                if param_name.lower() == f"{field_lower}id" or param_name.lower() == f"{field_lower}_id":
                    return param_name
                # Try reverse: if field is "id" and param is "policyId", extract the resource part
                if field_lower == "id":
                    # If param ends with "Id" or "_id", it's likely the ID parameter
                    if param_name.lower().endswith("id") or param_name.lower().endswith("_id"):
                        return param_name

        # Also check operation parameters
        parameters = operation.get("parameters", [])
        for param in parameters:
            if isinstance(param, dict) and param.get("in") == "path":
                param_name = param.get("name", "")
                # Skip orgId
                if param_name.lower() == "orgid":
                    continue
                # Check if parameter name matches or contains the field name
                if field_name.lower() in param_name.lower() or param_name.lower() in field_name.lower():
                    return param_name
            elif isinstance(param, str) and "$ref" in param:
                # Resolve reference
                from ...utils.openapi import resolve_ref
                resolved = resolve_ref(context.spec, param)
                if resolved and resolved.get("in") == "path":
                    param_name = resolved.get("name", "")
                    if param_name.lower() == "orgid":
                        continue
                    if field_name.lower() in param_name.lower() or param_name.lower() in field_name.lower():
                        return param_name

        # Fallback: try common patterns
        common_patterns = [f"{field_name}Id", f"{field_name}_id", field_name]
        for pattern in common_patterns:
            for param in parameters:
                if isinstance(param, dict) and param.get("in") == "path":
                    param_name = param.get("name", "")
                    if param_name.lower() == "orgid":
                        continue
                    if param_name.lower() == pattern.lower():
                        return param_name

        return None

    def _get_id_accessor(self, operation: Dict[str, Any], context: GenerationContext, id_field_name: str, path: str = "", fallback_to_input: bool = True) -> str:
        """Get the correct way to access ID field - from path param or input"""
        path_param = self._extract_path_parameter(operation, context, id_field_name, path)
        if path_param:
            return f"(input as any).{path_param}"
        elif fallback_to_input:
            # Try to find any path param that might be the ID (e.g., contentId, policyId, etc.)
            # Check if there's a path param that ends with "Id" or matches common ID patterns
            import re
            if path:
                matches = re.findall(r'\{([^}]+)\}', path)
                for param_name in matches:
                    if param_name.lower() == "orgid":
                        continue
                    # If path param looks like an ID (ends with "Id" or "id"), use it
                    if param_name.lower().endswith("id") or param_name.lower() == "id":
                        return f"(input as any).{param_name}"
            return f"(input as any).{id_field_name}"
        else:
            return None

    def _apply_adapter_input_ext_fix(self, method_body: str) -> str:
        """
        Prepend inputExt and replace input property accesses to fix port/input type mismatches.
        Runtime adds correlationId, orgId, path params - port types may not include them.
        Also casts inputExt-derived values to string for buildPK/buildSK/buildGSI* helpers.
        """
        import re
        prefix = "    const inputExt = input as Record<string, unknown>;\n\n"
        body = prefix + method_body
        body = body.replace("(input as any)", "inputExt")
        body = body.replace("input?.", "inputExt?.").replace("input.", "inputExt.")
        # Cast first arg to string for key helpers (inputExt props are unknown); avoid double " as string"
        def _cast_first_arg(m: re.Match, fn_name: str) -> str:
            first = m.group(1).strip()
            if first.endswith(" as string"):
                return m.group(0)
            return f"{fn_name}({first} as string,"
        body = re.sub(r"buildPK\(([^,]+),", lambda m: _cast_first_arg(m, "buildPK"), body)
        body = re.sub(r"buildSK\(([^,]+),", lambda m: _cast_first_arg(m, "buildSK"), body)
        body = re.sub(r"buildGSI1Keys\(([^,]+),", r"buildGSI1Keys(\1 as string,", body)
        body = re.sub(r"buildGSI2Keys\(([^,]+),", r"buildGSI2Keys(\1 as string,", body)
        body = re.sub(r"buildGSI3Keys\(([^,]+),", r"buildGSI3Keys(\1 as string,", body)
        return body

    def _generate_dynamodb_method_body(
        self,
        verb: str,
        operation_id: str,
        operation: Dict[str, Any],
        context: GenerationContext,
        input_type: str,
        output_type: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_entity_type: str,
        parent_entity_token: str,
        parent_id_field: str,
        table_type: str,
        gsi1_enabled: bool,
        gsi2_enabled: bool,
        gsi3_enabled: bool,
        createdAt_field: str,
        updatedAt_field: str,
        soft_delete_enabled: bool,
        x_dynamodb: Dict[str, Any],
        id_field_name: str,
        path: str = "",
        pk_pattern: str = "entity",
        status_prefix: bool = False,
        filter_fields: List[str] = None,
        use_pk_query: bool = False,
        domain: str = "",
        entity_type_pk: str = ""
    ) -> str:
        """Generate DynamoDB implementation body using x-dynamodb metadata"""
        if filter_fields is None:
            filter_fields = []
        op_id_lower = (operation_id or "").lower()

        # Operation-scoped update: single-field updates (cancel, enable, disable)
        if verb == "update" and operation_id:
            if op_id_lower.startswith("cancel"):
                return self._generate_update_single_field_body(
                    operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                    id_field_name, updatedAt_field, pk_pattern, status_prefix, domain, entity_type_pk,
                    update_field="status", value_ts='"cancelled"'
                )
            if op_id_lower.startswith("enable"):
                return self._generate_update_single_field_body(
                    operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                    id_field_name, updatedAt_field, pk_pattern, status_prefix, domain, entity_type_pk,
                    update_field="enabled", value_ts="true"
                )
            if op_id_lower.startswith("disable"):
                return self._generate_update_single_field_body(
                    operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                    id_field_name, updatedAt_field, pk_pattern, status_prefix, domain, entity_type_pk,
                    update_field="enabled", value_ts="false"
                )
        # Test: get then return success
        if verb == "get" and operation_id and "test" in op_id_lower:
            return self._generate_test_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                id_field_name, pk_pattern, status_prefix, domain, entity_type_pk
            )
        # Export: query/list then wrap in export envelope
        if verb == "list" and operation_id and "export" in op_id_lower:
            return self._generate_export_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                gsi1_enabled, gsi2_enabled, gsi3_enabled, id_field_name,
                pk_pattern, status_prefix, domain, entity_type_pk
            )

        if verb == "get":
            return self._generate_get_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field, id_field_name,
                pk_pattern, status_prefix, domain, entity_type_pk
            )
        elif verb == "list":
            return self._generate_list_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                gsi1_enabled, gsi2_enabled, gsi3_enabled, x_dynamodb, id_field_name,
                pk_pattern, status_prefix, filter_fields, use_pk_query, domain, entity_type_pk
            )
        elif verb == "create":
            return self._generate_create_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_entity_type,
                parent_entity_token, parent_id_field, createdAt_field, updatedAt_field,
                soft_delete_enabled, id_field_name, pk_pattern, status_prefix, domain, entity_type_pk,
                gsi1_enabled, gsi2_enabled, gsi3_enabled, x_dynamodb,
            )
        elif verb == "update":
            return self._generate_update_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                updatedAt_field, soft_delete_enabled, id_field_name, pk_pattern, status_prefix, domain, entity_type_pk
            )
        elif verb == "delete":
            return self._generate_delete_method_body(
                operation, context, path, entity_type, entity_token, sk_prefix, is_child_entity, parent_id_field,
                soft_delete_enabled, id_field_name, pk_pattern, status_prefix, domain, entity_type_pk
            )
        else:
            return f"""    // TODO: Implement {verb} operation
    throw new Error("Operation {verb} not yet implemented");"""

    def _generate_update_single_field_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        id_field_name: str,
        updatedAt_field: str,
        pk_pattern: str,
        status_prefix: bool,
        domain: str,
        entity_type_pk: str,
        update_field: str,
        value_ts: str
    ) -> str:
        """Generate UPDATE body for single-field updates (cancel, enable, disable)."""
        if not (domain and entity_type_pk and not is_child_entity):
            return f"""    // TODO: Implement single-field update for this entity pattern
    throw new Error("Operation not yet implemented");"""
        id_accessor = self._get_id_accessor(operation, context, id_field_name, path) or f"(input as any).{id_field_name}"
        org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
        org_id_accessor = f"(input as any).{org_path_param}" if org_path_param else "(input as any).orgId"
        return f"""    const idVal = {id_accessor};
    if (!idVal || !(input as any).orgId) throw new Error("Missing required parameter: {id_field_name}/id or orgId");
    const pk = this.buildPK({org_id_accessor} as string, idVal as string);
    const getResult = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{ ":pk": pk, ":skPrefix": `${{this.ENTITY_TOKEN}}#${{idVal}}#` }},
      Limit: 1,
    }});
    const existing = getResult.Items?.[0] as Record<string, unknown> | undefined;
    if (!existing?.PK || !existing?.SK) throw new Error(`${{this.ENTITY_TYPE}} with id ${{idVal}} not found`);
    const now = new Date().toISOString();
    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: existing.PK, SK: existing.SK }},
      UpdateExpression: "SET #field = :value, #updatedAt = :updatedAt",
      ExpressionAttributeNames: {{ "#field": "{update_field}", "#updatedAt": this.UPDATED_AT_FIELD }},
      ExpressionAttributeValues: {{ ":value": {value_ts}, ":updatedAt": now }},
      ReturnValues: "ALL_NEW",
    }});
    return {{
      data: sanitizeItem((result.Attributes || {{}}) as Record<string, unknown>) as unknown as any,
      meta: {{ correlationId: (input?.correlationId as string) || this.generateCorrelationId(), timestamp: new Date().toISOString() }} as unknown as any,
    }};"""

    def _generate_test_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        id_field_name: str,
        pk_pattern: str,
        status_prefix: bool,
        domain: str,
        entity_type_pk: str
    ) -> str:
        """Generate TEST method body: get item then return success."""
        if not (domain and entity_type_pk):
            return """    return { data: { success: true } as unknown as any, meta: { correlationId: (input?.correlationId as string) ?? "", timestamp: new Date().toISOString() } as unknown as any };"""
        id_accessor = self._get_id_accessor(operation, context, id_field_name, path) or f"(input as any).{id_field_name}"
        org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
        org_id_accessor = f"(input as any).{org_path_param}" if org_path_param else "(input as any).orgId"
        return f"""    const idVal = {id_accessor};
    if (!idVal || !(input as any).orgId) throw new Error("Missing required parameter: ruleId/id or orgId");
    const pk = this.buildPK({org_id_accessor} as string, idVal as string);
    const getResult = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{ ":pk": pk, ":skPrefix": `${{this.ENTITY_TOKEN}}#${{idVal}}#` }},
      Limit: 1,
    }});
    const item = getResult.Items?.[0];
    if (!item) throw new Error(`${{this.ENTITY_TYPE}} with id ${{idVal}} not found`);
    return {{
      data: {{ success: true }} as unknown as any,
      meta: {{ correlationId: (input?.correlationId as string) || this.generateCorrelationId(), timestamp: new Date().toISOString() }} as unknown as any,
    }};"""

    def _generate_export_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        gsi1_enabled: bool,
        gsi2_enabled: bool,
        gsi3_enabled: bool,
        id_field_name: str,
        pk_pattern: str,
        status_prefix: bool,
        domain: str,
        entity_type_pk: str
    ) -> str:
        """Generate EXPORT method body: query by pk with limit, return export envelope."""
        if not (domain and entity_type_pk):
            return """    return { data: { exportId: ulid().toLowerCase(), status: 'completed', downloadUrl: null, items: [] } as unknown as any, meta: {} as unknown as any };"""
        org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
        org_id_accessor = f"(input as any).{org_path_param}" if org_path_param else "(input as any).orgId"
        export_domain_prefix = get_domain_prefix(context.spec, context.domain_name)
        return f"""    if (!input || !(input as any).orgId) {{
      throw new Error("Missing required parameter: input or orgId");
    }}
    const prefix = this.getCollectionPK({org_id_accessor} as string);
    const limit = (input as any)?.limit
      ? (typeof (input as any).limit === "string" ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 1000;
    const result = await this.dynamoClient.scan({{
      TableName: this.TABLE_NAME,
      FilterExpression: "begins_with(PK, :prefix)",
      ExpressionAttributeValues: {{ ":prefix": prefix }},
      Limit: limit,
    }});
    const items = ((result.Items || []) as Record<string, unknown>[]).map((i) => sanitizeItem(i));
    const exportId = `{export_domain_prefix}_${{ulid().toLowerCase()}}`;
    return {{
      data: {{
        exportId,
        status: "completed" as const,
        downloadUrl: null,
        items,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""

    def _generate_get_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        id_field_name: str,
        pk_pattern: str = "entity",
        status_prefix: bool = False,
        domain: str = "",
        entity_type_pk: str = ""
    ) -> str:
        """Generate GET method body - uses class constants, no hardcoded values"""
        # Universal pattern: get by query pk + begins_with(sk, id#), return sanitizeItem(item)
        if domain and entity_type_pk:
            org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
            # Resolve entity id from schema field, plain `id`, or any *Id path param
            # (e.g. Lead schema uses `id` but path is `{leadId}`).
            base_accessor = self._get_id_accessor(operation, context, id_field_name, path) or f"(input as any).{id_field_name}"
            id_accessor = (
                f"((input as any).{id_field_name} ?? (input as any).id ?? {base_accessor})"
                if id_field_name != "id"
                else f"((input as any).id ?? {base_accessor})"
            )
            org_id_accessor = f"(input as any).{org_path_param}" if org_path_param else "(input as any).orgId"
            # buildSK prefixes ACTIVE# when statusPrefix is set; queries must match.
            sk_prefix_expr = (
                f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                if status_prefix
                else f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}#`"
            )
            return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}
    const pk = this.buildPK({org_id_accessor} as string, {id_accessor} as string);
    // Soft-delete layout prefixes SK with ACTIVE# when statusPrefix is enabled.
    const skPrefix = {sk_prefix_expr};
    const result = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{ ":pk": pk, ":skPrefix": skPrefix }},
      Limit: 1,
    }});
    const item = result.Items?.[0];
    if (!item) {{
      throw new Error(`${{this.ENTITY_TYPE}} with id ${{{id_accessor}}} not found`);
    }}
    return {{
      data: sanitizeItem(item as Record<string, unknown>) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""

        # Extract path parameters from operation (path params may not be in input type for query-only operations)
        path_param_name = self._extract_path_parameter(operation, context, id_field_name, path)
        org_path_param = self._extract_path_parameter(operation, context, "orgId", path)

        # Use type assertion for path parameters since they may not be in the input type (which only has query params)
        # Path parameters are always present in the actual input at runtime
        if path_param_name:
            id_accessor = f"(input as any).{path_param_name}"
        else:
            # Fallback: try common ID patterns
            import re
            if path:
                matches = re.findall(r'\{([^}]+)\}', path)
                for param_name in matches:
                    if param_name.lower() == "orgid":
                        continue
                    if param_name.lower().endswith("id") or param_name.lower() == "id":
                        id_accessor = f"(input as any).{param_name}"
                        break
                else:
                    id_accessor = f"(input as any).{id_field_name}"
            else:
                id_accessor = f"(input as any).{id_field_name}"

        # Build PK based on pattern
        if pk_pattern == "org":
            # Use ORG#${orgId} pattern (manual standard)
            # Always use type assertion since orgId may not be in the input type
            if org_path_param:
                org_id_accessor = f"(input as any).{org_path_param}"
            else:
                org_id_accessor = "(input as any).orgId"
            # Use single curly braces in template string to properly substitute the accessor
            pk_expr = f"`ORG#${{{org_id_accessor}}}`"
        else:
            # Use ${ENTITY_TOKEN}#${id} pattern (default)
            pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"

        # Build SK based on status prefix
        if status_prefix:
            # Use ACTIVE#${TOKEN}#${id} pattern (manual standard)
            sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
        else:
            # Use ${SK_PREFIX}#${id} pattern (default)
            sk_expr = f"`${{this.SK_PREFIX}}#${{{id_accessor}}}`"

        parent_accessor = None
        if is_child_entity and parent_id_field:
            parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
            if parent_path_param:
                parent_accessor = f"(input as any).{parent_path_param}"
            else:
                parent_accessor = f"(input as any).{parent_id_field}"

        if is_child_entity and parent_accessor:
            # Child entity: use parent ID as PK
            if pk_pattern == "org":
                pk_expr = f"`ORG#${{{org_id_accessor}}}`"
            else:
                pk_expr = f"`${{{parent_accessor}}}`"

            return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const pk = {pk_expr};
    const sk = {sk_expr};

    const result = await this.dynamoClient.get({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
    }});

    if (!result.Item) {{
      throw new Error(`${{this.ENTITY_TYPE}} with {id_field_name} ${{{id_accessor}}} not found`);
    }}

    return {{
      data: result.Item as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""
        else:
            return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const pk = {pk_expr};
    const sk = {sk_expr};

    const result = await this.dynamoClient.get({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
    }});

    if (!result.Item) {{
      throw new Error(`${{this.ENTITY_TYPE}} with {id_field_name} ${{{id_accessor}}} not found`);
    }}

    return {{
      data: result.Item as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""

    def _generate_list_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        gsi1_enabled: bool,
        gsi2_enabled: bool,
        gsi3_enabled: bool,
        x_dynamodb: Dict[str, Any],
        id_field_name: str,
        pk_pattern: str = "entity",
        status_prefix: bool = False,
        filter_fields: List[str] = None,
        use_pk_query: bool = False,
        domain: str = "",
        entity_type_pk: str = ""
    ) -> str:
        """Generate LIST method body"""
        if filter_fields is None:
            filter_fields = []
        
        # Extract data field name from response schema (defaults to "items")
        data_field_name = "items"
        from ...utils.openapi import get_response_schema, get_response_schema_name, get_schema, resolve_ref
        from ...utils.openapi import extract_schemas
        
        # Try to get response schema name first, then resolve the full schema
        response_schema_name = get_response_schema_name(operation, context.spec, "200")
        if response_schema_name:
            schemas_dict = extract_schemas(context.spec)
            response_schema = schemas_dict.get(response_schema_name)
        else:
            response_schema = get_response_schema(operation, context.spec, "200")
            # Resolve $ref if present
            if isinstance(response_schema, dict) and "$ref" in response_schema:
                response_schema = resolve_ref(context.spec, response_schema["$ref"])
        
        if response_schema and isinstance(response_schema, dict):
            # Check for data property
            data_prop = response_schema.get("properties", {}).get("data", {})
            # Resolve $ref in data property if present
            if isinstance(data_prop, dict) and "$ref" in data_prop:
                data_prop = resolve_ref(context.spec, data_prop["$ref"])
            
            if isinstance(data_prop, dict):
                # Check if data has properties (could be nested)
                data_props = data_prop.get("properties", {})
                if data_props:
                    # Look for array fields (items, tags, etc.)
                    for field_name, field_schema in data_props.items():
                        # Resolve $ref in field schema if present
                        if isinstance(field_schema, dict) and "$ref" in field_schema:
                            field_schema = resolve_ref(context.spec, field_schema["$ref"])
                        if isinstance(field_schema, dict) and field_schema.get("type") == "array":
                            data_field_name = field_name
                            break
                # Also check if data itself is an array (data.items pattern)
                if data_prop.get("type") == "array" and "items" in data_prop:
                    data_field_name = "items"
            # Check allOf pattern
            if "allOf" in response_schema:
                for item in response_schema["allOf"]:
                    if isinstance(item, dict):
                        data_prop = item.get("properties", {}).get("data", {})
                        # Resolve $ref in data property if present
                        if isinstance(data_prop, dict) and "$ref" in data_prop:
                            data_prop = resolve_ref(context.spec, data_prop["$ref"])
                        if isinstance(data_prop, dict):
                            data_props = data_prop.get("properties", {})
                            if data_props:
                                for field_name, field_schema in data_props.items():
                                    # Resolve $ref in field schema if present
                                    if isinstance(field_schema, dict) and "$ref" in field_schema:
                                        field_schema = resolve_ref(context.spec, field_schema["$ref"])
                                    if isinstance(field_schema, dict) and field_schema.get("type") == "array":
                                        data_field_name = field_name
                                        break

        # Extract orgId path parameter (may not be in input type for query-only operations)
        org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
        if org_path_param:
            org_id_accessor = f"(input as any).{org_path_param}"
        else:
            org_id_accessor = "(input as any).orgId"

        # Org-scoped entity partitions (PK ends with entityId): list via GSI2 when enabled
        # (zatca design: GSI2-PK = ORG#orgId#COLLECTION). Fall back to Scan on PK prefix.
        if domain and entity_type_pk and not is_child_entity:
            if gsi2_enabled:
                filter_sk = ""
                if status_prefix:
                    filter_sk = """
      FilterExpression: "begins_with(SK, :activePrefix)",
      ExpressionAttributeValues: {
        ":pk": gsi2PK,
        ":activePrefix": `ACTIVE#${this.ENTITY_TOKEN}#`,
      },"""
                else:
                    filter_sk = """
      ExpressionAttributeValues: {
        ":pk": gsi2PK,
      },"""
                return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}
    const gsi2PK = `ORG#${{{org_id_accessor}}}#${{this.ENTITY_TYPE_PK}}`;
    const rawLimit = (input as any)?.limit;
    const parsedLimit = rawLimit == null || rawLimit === ""
      ? 50
      : (typeof rawLimit === "string" ? parseInt(rawLimit as string, 10) : Number(rawLimit));
    const limit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : 50;
    const result = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      IndexName: "GSI2",
      KeyConditionExpression: "#gsi2pk = :pk",
      ExpressionAttributeNames: {{ "#gsi2pk": "GSI2-PK" }},
{filter_sk}
      Limit: limit,
      ScanIndexForward: false,
      ...((() => {{
        const c = (input as any)?.cursor;
        if (!c || (typeof c === "string" && !c.trim())) return {{}};
        try {{
          return {{
            ExclusiveStartKey: typeof c === "string"
              ? JSON.parse(Buffer.from(c, "base64").toString())
              : c,
          }};
        }} catch {{
          return {{}};
        }}
      }})()),
    }});
    const items = ((result.Items || []) as Record<string, unknown>[]).map((i) => sanitizeItem(i));
    return {{
      data: {{ {data_field_name}: items }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""

            return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}
    const prefix = this.getCollectionPK({org_id_accessor} as string);
    const rawLimit = (input as any)?.limit;
    const parsedLimit = rawLimit == null || rawLimit === ""
      ? 50
      : (typeof rawLimit === "string" ? parseInt(rawLimit as string, 10) : Number(rawLimit));
    const limit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : 50;
    const result = await this.dynamoClient.scan({{
      TableName: this.TABLE_NAME,
      FilterExpression: "begins_with(PK, :prefix)",
      ExpressionAttributeValues: {{ ":prefix": prefix }},
      Limit: limit,
      ...((() => {{
        const c = (input as any)?.cursor;
        if (!c || (typeof c === "string" && !c.trim())) return {{}};
        try {{
          return {{
            ExclusiveStartKey: typeof c === "string"
              ? JSON.parse(Buffer.from(c, "base64").toString())
              : c,
          }};
        }} catch {{
          return {{}};
        }}
      }})()),
    }});
    const items = ((result.Items || []) as Record<string, unknown>[]).map((i) => sanitizeItem(i));
    return {{
      data: {{ {data_field_name}: items }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""

        # Check if we should use GSI for listing (non-universal / child paths below)
        # Prefer GSI when enabled; usePkQuery forces base-table PK query instead.
        should_use_pk_query = use_pk_query
        use_gsi = (gsi1_enabled or gsi2_enabled or gsi3_enabled) and not should_use_pk_query

        if is_child_entity:
            # Child entities: query by parent ID - use class constants
            parent_accessor = None
            if parent_id_field:
                parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                if parent_path_param:
                    parent_accessor = f"(input as any).{parent_path_param}"
                else:
                    parent_accessor = f"(input as any).{parent_id_field}"

            if parent_accessor:
                # Build SK prefix based on status prefix
                if status_prefix:
                    sk_prefix_value = f"`ACTIVE#${{this.ENTITY_TOKEN}}#`"
                else:
                    sk_prefix_value = f"`${{this.SK_PREFIX}}#`"

                # Build PK - child entities use parent ID, but if pkPattern is org, use ORG#${orgId}
                if pk_pattern == "org":
                    pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                else:
                    pk_expr = f"`${{{parent_accessor}}}`"

                return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const pk = {pk_expr};
    const skPrefixValue = {sk_prefix_value};

    // ✅ DynamoDB-specific: Convert limit from string/number to number (DynamoDB requires number for Limit parameter)
    const limit = (input as any)?.limit 
      ? (typeof (input as any).limit === 'string' ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 50;

    const result = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{
        ":pk": pk,
        ":skPrefix": skPrefixValue,
      }},
      Limit: limit, // ✅ DynamoDB-specific: Use converted number
    }});

    return {{
      data: {{
        {data_field_name}: (result.Items || []) as unknown as any,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""
            else:
                # Fallback if no parent accessor
                return f"""    const skPrefixValue = `${{this.SK_PREFIX}}#`;

    // ✅ DynamoDB-specific: Convert limit from string/number to number (DynamoDB requires number for Limit parameter)
    const limit = (input as any)?.limit 
      ? (typeof (input as any).limit === 'string' ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 50;

    const result = await this.dynamoClient.scan({{
      TableName: this.TABLE_NAME,
      FilterExpression: "begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{
        ":skPrefix": skPrefixValue,
      }},
      Limit: limit, // ✅ DynamoDB-specific: Use converted number
    }});

    return {{
      data: {{
        {data_field_name}: (result.Items || []) as unknown as any,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""
        elif should_use_pk_query:
            # Use PK query for org-scoped entities (manual standard pattern)
            # Build PK based on pattern
            if pk_pattern == "org":
                org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
                if org_path_param:
                    org_id_accessor = f"(input as any).{org_path_param}"
                else:
                    org_id_accessor = "(input as any).orgId"
                pk_expr = f"`ORG#${{{org_id_accessor}}}`"
            else:
                pk_expr = "`${this.ENTITY_TOKEN}#${input.id}`"  # Fallback, should not happen

            # Build SK prefix based on status prefix
            if status_prefix:
                sk_prefix_value = f"`ACTIVE#${{this.ENTITY_TOKEN}}#`"
            else:
                sk_prefix_value = f"`${{this.SK_PREFIX}}#`"

            # Build filter expressions if filterFields are specified
            filter_expression_code = ""
            expression_attr_names_code = ""
            expression_attr_values_code = f"""      ExpressionAttributeValues: {{
        ":pk": pk,
        ":skPrefix": skPrefixValue,"""

            if filter_fields:
                filter_parts = []
                attr_names_lines = []

                for i, field in enumerate(filter_fields):
                    attr_name_key = f"#field{i}"
                    attr_value_key = f":field{i}"
                    attr_names_lines.append(f'        "{attr_name_key}": "{field}",')
                    filter_parts.append(f"{attr_name_key} = {attr_value_key}")
                    expression_attr_values_code += f"\n        \"{attr_value_key}\": (input as any)?.{field},"

                if filter_parts:
                    filter_expression_code = f"""
      FilterExpression: "{' AND '.join(filter_parts)}","""
                    expression_attr_names_code = f"""
      ExpressionAttributeNames: {{
{chr(10).join(attr_names_lines)}
      }},"""

            expression_attr_values_code += "\n      },"

            return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}

    const pk = {pk_expr};
    const skPrefixValue = {sk_prefix_value};

    // ✅ DynamoDB-specific: Convert limit from string/number to number (DynamoDB requires number for Limit parameter)
    const limit = (input as any)?.limit 
      ? (typeof (input as any).limit === 'string' ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 50;

    const result = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",{filter_expression_code}{expression_attr_names_code}
{expression_attr_values_code}
      Limit: limit, // ✅ DynamoDB-specific: Use converted number
      ScanIndexForward: false,  // Sort descending
      ...((() => {{
        const c = (input as any)?.cursor;
        if (!c || (typeof c === "string" && !c.trim())) return {{}};
        try {{
          return {{
            ExclusiveStartKey: typeof c === "string"
              ? JSON.parse(Buffer.from(c, "base64").toString())
              : c,
          }};
        }} catch {{
          return {{}};
        }}
      }})()),
    }});

    return {{
      data: {{
        {data_field_name}: (result.Items || []) as unknown as any,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""
        elif use_gsi:
            # Use GSI for listing (prefer GSI1 if enabled)
            gsi_num = 1 if gsi1_enabled else (2 if gsi2_enabled else 3)
            gsi_index = f"GSI{gsi_num}"
            gsi_pk_key = f"gsi{gsi_num}PKFields"
            gsi_sk_key = f"gsi{gsi_num}SKFields"
            gsi_pk_fields = x_dynamodb.get(gsi_pk_key, [])
            gsi_sk_fields = x_dynamodb.get(gsi_sk_key, [])

            if gsi_pk_fields and len(gsi_pk_fields) > 0:
                # Build GSI PK from fields dynamically - use type assertions
                gsi_pk_parts = [f"${{(input as any).{field}}}" for field in gsi_pk_fields]
                gsi_pk_build = " + '#' + ".join(gsi_pk_parts)
                gsi_pk_var = f"gsi{gsi_num}PK"

                # Build GSI SK if fields are specified - use type assertions
                if gsi_sk_fields and len(gsi_sk_fields) > 0:
                    gsi_sk_parts = [f"${{(input as any).{field}}}" for field in gsi_sk_fields]
                    gsi_sk_build = " + '#' + ".join(gsi_sk_parts)
                    gsi_sk_var = f"gsi{gsi_num}SK"
                    key_condition = f"{gsi_pk_var}PK = :{gsi_pk_var} AND begins_with({gsi_sk_var}SK, :skPrefix)"
                else:
                    key_condition = f"{gsi_pk_var}PK = :{gsi_pk_var} AND begins_with({gsi_pk_var}SK, :skPrefix)"

                # Build SK prefix based on status prefix
                if status_prefix:
                    sk_prefix_value = f"`ACTIVE#${{this.ENTITY_TOKEN}}#`"
                else:
                    sk_prefix_value = f"`${{this.SK_PREFIX}}#`"

                return f"""    const {gsi_pk_var} = `{gsi_pk_build}`;
    const skPrefixValue = {sk_prefix_value};

    // ✅ DynamoDB-specific: Convert limit from string/number to number (DynamoDB requires number for Limit parameter)
    const limit = (input as any)?.limit 
      ? (typeof (input as any).limit === 'string' ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 50;

    const result = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      IndexName: "{gsi_index}",
      KeyConditionExpression: "{key_condition}",
      ExpressionAttributeValues: {{
        ":{gsi_pk_var}": {gsi_pk_var},
        ":skPrefix": skPrefixValue,
      }},
      Limit: limit, // ✅ DynamoDB-specific: Use converted number
    }});

    return {{
      data: {{
        {data_field_name}: (result.Items || []) as unknown as any,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""
            else:
                # Fallback to scan if GSI PK fields not configured - use class constants
                return f"""    const skPrefixValue = `${{this.SK_PREFIX}}#`;

    // ✅ DynamoDB-specific: Convert limit from string/number to number (DynamoDB requires number for Limit parameter)
    const limit = (input as any)?.limit 
      ? (typeof (input as any).limit === 'string' ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 50;

    const result = await this.dynamoClient.scan({{
      TableName: this.TABLE_NAME,
      FilterExpression: "begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{
        ":skPrefix": skPrefixValue,
      }},
      Limit: limit, // ✅ DynamoDB-specific: Use converted number
    }});

    return {{
      data: {{
        {data_field_name}: (result.Items || []) as unknown as any,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""
        else:
            # No GSI: use scan with filter - use class constants
            return f"""    const skPrefixValue = `${{this.SK_PREFIX}}#`;

    // ✅ DynamoDB-specific: Convert limit from string/number to number (DynamoDB requires number for Limit parameter)
    const limit = (input as any)?.limit 
      ? (typeof (input as any).limit === 'string' ? parseInt((input as any).limit, 10) : Number((input as any).limit))
      : 50;

    const result = await this.dynamoClient.scan({{
      TableName: this.TABLE_NAME,
      FilterExpression: "begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{
        ":skPrefix": skPrefixValue,
      }},
      Limit: limit, // ✅ DynamoDB-specific: Use converted number
    }});

    return {{
      data: {{
        {data_field_name}: (result.Items || []) as unknown as any,
      }} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
        pagination: {{
          nextCursor: result.LastEvaluatedKey ? Buffer.from(JSON.stringify(result.LastEvaluatedKey)).toString("base64") : null,
          prevCursor: null,
          limit: (input as any)?.limit || 50,
        }},
      }} as unknown as any,
    }};"""

    def _generate_create_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_entity_type: str,
        parent_entity_token: str,
        parent_id_field: str,
        createdAt_field: str,
        updatedAt_field: str,
        soft_delete_enabled: bool,
        id_field_name: str,
        pk_pattern: str = "entity",
        status_prefix: bool = False,
        domain: str = "",
        entity_type_pk: str = "",
        gsi1_enabled: bool = False,
        gsi2_enabled: bool = False,
        gsi3_enabled: bool = False,
        x_dynamodb: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate CREATE method body"""
        if x_dynamodb is None:
            x_dynamodb = {}
        now = "new Date().toISOString()"
        # Build timestamp fields - avoid duplicate if CREATED_AT_FIELD and UPDATED_AT_FIELD are the same
        if createdAt_field == updatedAt_field:
            timestamp_fields = f"      [this.CREATED_AT_FIELD]: now,"
        else:
            timestamp_fields = f"""      [this.CREATED_AT_FIELD]: now,
      [this.UPDATED_AT_FIELD]: now,"""
        # For create, ID might be from path param, or need to be generated
        # CREATE operations typically don't have ID in input body (it's generated)
        # Only use path params if they exist, otherwise always generate
        path_param = self._extract_path_parameter(operation, context, id_field_name, path)
        if path_param:
            # ID comes from path parameter
            id_accessor = f"(input as any).{path_param}"
        else:
            # No path param - always generate ID for CREATE operations
            id_accessor = "ulid()"

        # Universal pattern: buildPK, buildSK, PutItem, return sanitizeItem(item). ID is injected by use case (API/services layer).
        if domain and entity_type_pk and not is_child_entity:
            org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
            org_id_accessor = f"(input as any).{org_id_accessor}" if org_id_accessor else "(input as any).orgId"
            id_var = camel_case(id_field_name)
            gsi_fields = ""
            if gsi2_enabled:
                gsi_fields += f"""
      "GSI2-PK": this.buildGSI2PK(orgId as string),
      "GSI2-SK": this.buildGsiSK(now, {id_var} as string),"""
            if gsi1_enabled:
                # ORG#orgId#COLLECTION#STATUS#value when status present
                # Brace-escape TS template literals; only {id_var} is a Python f-string slot.
                gsi_fields += (
                    """
      "GSI1-PK": (input as any)?.status != null
        ? `ORG#${orgId}#${this.ENTITY_TYPE_PK}#STATUS#${(input as any).status}`
        : undefined,
      "GSI1-SK": this.buildGsiSK(now, """
                    + id_var
                    + """ as string),"""
                )
            return f"""    const now = {now};
    const orgId = {org_id_accessor};
    const {id_var} = (input as any)?.{id_field_name} ?? (input as any)?.id;
    if (!{id_var}) throw new Error("Missing required parameter: {id_field_name} (inject from use case)");
    const pk = this.buildPK(orgId, {id_var} as string);
    const sk = this.buildSK({id_var} as string);
    const excludedFields = ["{id_field_name}", "id"];
    const inputWithoutId = Object.fromEntries(
      Object.entries(input || {{}}).filter(([key]) => !excludedFields.includes(key))
    );
    const item = {{
      ...inputWithoutId,
      {id_field_name}: {id_var},
      PK: pk,
      SK: sk,
      entityType: this.ENTITY_TYPE,
{timestamp_fields}{gsi_fields}
    }};
    await this.dynamoClient.put({{
      TableName: this.TABLE_NAME,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK) AND attribute_not_exists(SK)",
    }});
    return {{
      data: sanitizeItem(item as Record<string, unknown>) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""

        if is_child_entity:
            parent_accessor = None
            if parent_id_field:
                parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                if parent_path_param:
                    parent_accessor = f"(input as any).{parent_path_param}"
                else:
                    parent_accessor = f"(input as any).{parent_id_field}"

            if parent_accessor:
                id_var = f"{camel_case(id_field_name)}"
                # Determine which fields to exclude - include path params if they exist
                excluded_fields_list = [f'"{id_field_name}"', f'"{parent_id_field}"']
                path_param = self._extract_path_parameter(operation, context, id_field_name, path)
                if path_param and path_param != id_field_name:
                    excluded_fields_list.append(f'"{path_param}"')
                parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                if parent_path_param and parent_path_param != parent_id_field:
                    excluded_fields_list.append(f'"{parent_path_param}"')
                excluded_fields_str = ", ".join(excluded_fields_list)

                # Build PK - child entities use parent ID, but if pkPattern is org, use ORG#${orgId}
                if pk_pattern == "org":
                    org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                    if not org_id_accessor:
                        org_id_accessor = "(input as any).orgId"
                    else:
                        org_id_accessor = f"(input as any).{org_id_accessor}"
                    pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                else:
                    pk_expr = f"`${{{parent_accessor}}}`"

                # Build SK based on status prefix
                if status_prefix:
                    sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_var}}}`"
                else:
                    sk_expr = f"`${{this.SK_PREFIX}}#${{{id_var}}}`"

                # Build PK - child entities use parent ID, but if pkPattern is org, use ORG#${orgId}
                if pk_pattern == "org":
                    org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                    if not org_id_accessor:
                        org_id_accessor = "(input as any).orgId"
                    else:
                        org_id_accessor = f"(input as any).{org_id_accessor}"
                    pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                else:
                    pk_expr = f"`${{{parent_accessor}}}`"

                # Build SK based on status prefix
                if status_prefix:
                    sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_var}}}`"
                else:
                    sk_expr = f"`${{this.SK_PREFIX}}#${{{id_var}}}`"

                return f"""    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const now = {now};
    const {id_var} = {id_accessor};
    const pk = {pk_expr};
    const sk = {sk_expr};

    // Exclude id fields to avoid duplicates
    const excludedFields = [{excluded_fields_str}];
    const inputWithoutIds = Object.fromEntries(
      Object.entries(input || {{}}).filter(([key]) => !excludedFields.includes(key))
    );
    const item = {{
      ...inputWithoutIds,
      {id_field_name}: {id_var},
      PK: pk,
      SK: sk,
      entityType: this.ENTITY_TYPE,
{timestamp_fields}
    }};

    await this.dynamoClient.put({{
      TableName: this.TABLE_NAME,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    }});

    return {{
      data: item as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
            else:
                id_var = f"{camel_case(id_field_name)}"
                # Determine which fields to exclude - if ID comes from path param, exclude that param name too
                excluded_fields_list = [f'"{id_field_name}"']
                path_param = self._extract_path_parameter(operation, context, id_field_name, path)
                if path_param and path_param != id_field_name:
                    excluded_fields_list.append(f'"{path_param}"')
                excluded_fields_str = ", ".join(excluded_fields_list)

                # If id_accessor is just "ulid()", we need to call it once and store the result
                if id_accessor == "ulid()":
                    # Build PK based on pattern
                    if pk_pattern == "org":
                        org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                        if not org_id_accessor:
                            org_id_accessor = "(input as any).orgId"
                        else:
                            org_id_accessor = f"(input as any).{org_id_accessor}"
                        pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                    else:
                        pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_var}}}`"

                    # Build SK based on status prefix
                    if status_prefix:
                        sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_var}}}`"
                    else:
                        sk_expr = f"`${{this.SK_PREFIX}}#${{{id_var}}}`"

                    # ID is injected by use case (API/services layer). Accept plain `id`
                    # when the schema primary key is resource-shaped (teamId, jobId, …).
                    return f"""    const now = {now};
    const {id_var} = (input as any)?.{id_field_name} ?? (input as any)?.id;
    if (!{id_var}) throw new Error("Missing required parameter: {id_field_name} (inject from use case)");
    const pk = {pk_expr};
    const sk = {sk_expr};

    // Exclude id fields to avoid duplicates
    const excludedFields = [{excluded_fields_str}];
    const inputWithoutId = Object.fromEntries(
      Object.entries(input || {{}}).filter(([key]) => !excludedFields.includes(key))
    );
    const item = {{
      ...inputWithoutId,
      {id_field_name}: {id_var},
      PK: pk,
      SK: sk,
      entityType: this.ENTITY_TYPE,
{timestamp_fields}
    }};

    await this.dynamoClient.put({{
      TableName: this.TABLE_NAME,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    }});

    return {{
      data: item as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
                else:
                    id_var = f"{camel_case(id_field_name)}"
                    # Determine which fields to exclude - if ID comes from path param, exclude that param name too
                    excluded_fields_list = [f'"{id_field_name}"']
                    path_param = self._extract_path_parameter(operation, context, id_field_name, path)
                    if path_param and path_param != id_field_name:
                        excluded_fields_list.append(f'"{path_param}"')
                    excluded_fields_str = ", ".join(excluded_fields_list)

                    # Build PK based on pattern
                    if pk_pattern == "org":
                        org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                        if not org_id_accessor:
                            org_id_accessor = "(input as any).orgId"
                        else:
                            org_id_accessor = f"(input as any).{org_id_accessor}"
                        pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                    else:
                        pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_var}}}`"

                    # Build SK based on status prefix
                    if status_prefix:
                        sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_var}}}`"
                    else:
                        sk_expr = f"`${{this.SK_PREFIX}}#${{{id_var}}}`"

                    return f"""    const now = {now};
    const {id_var} = {id_accessor};
    const pk = {pk_expr};
    const sk = {sk_expr};

    // Exclude id fields to avoid duplicates
    const excludedFields = [{excluded_fields_str}];
    const inputWithoutId = Object.fromEntries(
      Object.entries(input || {{}}).filter(([key]) => !excludedFields.includes(key))
    );
    const item = {{
      ...inputWithoutId,
      {id_field_name}: {id_var},
      PK: pk,
      SK: sk,
      entityType: this.ENTITY_TYPE,
{timestamp_fields}
    }};

    await this.dynamoClient.put({{
      TableName: this.TABLE_NAME,
      Item: item,
      ConditionExpression: "attribute_not_exists(PK)",
    }});

    return {{
      data: item as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""

    def _generate_update_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        updatedAt_field: str,
        soft_delete_enabled: bool,
        id_field_name: str,
        pk_pattern: str = "entity",
        status_prefix: bool = False,
        domain: str = "",
        entity_type_pk: str = ""
    ) -> str:
        """Generate UPDATE method body"""
        now = "new Date().toISOString()"
        id_accessor = self._get_id_accessor(operation, context, id_field_name, path)
        if not id_accessor:
            id_accessor = f"(input as any).{id_field_name}"

        # Universal pattern: query to get item pk/sk, then update by key, return sanitizeItem(attrs)
        if domain and entity_type_pk and not is_child_entity:
            org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
            org_id_accessor = f"(input as any).{org_path_param}" if org_path_param else "(input as any).orgId"
            sk_prefix_expr = (
                f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                if status_prefix
                else f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}#`"
            )
            return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}
    const pk = this.buildPK({org_id_accessor} as string, {id_accessor} as string);
    const getResult = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{ ":pk": pk, ":skPrefix": {sk_prefix_expr} }},
      ScanIndexForward: false,
      Limit: 1,
    }});
    const existing = getResult.Items?.[0] as Record<string, unknown> | undefined;
    const now = {now};
    if (!existing?.PK || !existing?.SK) {{
      // Upsert: create when missing (PUT semantics)
      const pkNew = this.buildPK({org_id_accessor} as string, {id_accessor} as string);
      const skNew = this.buildSK({id_accessor} as string);
      const item = {{
        ...(input as Record<string, unknown>),
        {id_field_name}: {id_accessor},
        PK: pkNew,
        SK: skNew,
        entityType: this.ENTITY_TYPE,
        [this.CREATED_AT_FIELD]: now,
        [this.UPDATED_AT_FIELD]: now,
        "GSI2-PK": this.buildGSI2PK({org_id_accessor} as string),
        "GSI2-SK": this.buildGsiSK(now, {id_accessor} as string),
      }};
      await this.dynamoClient.put({{
        TableName: this.TABLE_NAME,
        Item: item,
      }});
      return {{
        data: sanitizeItem(item as Record<string, unknown>) as unknown as any,
        meta: {{
          correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
          timestamp: new Date().toISOString(),
        }} as unknown as any,
      }};
    }}
    const updateExpressions: string[] = [`#${{this.UPDATED_AT_FIELD}} = :updatedAt`];
    const expressionAttributeNames: Record<string, string> = {{ [`#${{this.UPDATED_AT_FIELD}}`]: this.UPDATED_AT_FIELD }};
    const expressionAttributeValues: Record<string, unknown> = {{ ":updatedAt": now }};
    Object.keys(input || {{}}).forEach((key, index) => {{
      if (key !== "{id_field_name}" && key !== "orgId" && key !== "correlationId") {{
        const nameKey = `#field${{index}}`;
        const valueKey = `:value${{index}}`;
        updateExpressions.push(`${{nameKey}} = ${{valueKey}}`);
        expressionAttributeNames[nameKey] = key;
        expressionAttributeValues[valueKey] = (input as any)[key];
      }}
    }});
    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: existing.PK, SK: existing.SK }},
      UpdateExpression: `SET ${{updateExpressions.join(", ")}}`,
      ExpressionAttributeNames: expressionAttributeNames,
      ExpressionAttributeValues: expressionAttributeValues,
      ReturnValues: "ALL_NEW",
    }});
    return {{
      data: sanitizeItem((result.Attributes || {{}}) as Record<string, unknown>) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""

        if is_child_entity:
            parent_accessor = None
            if parent_id_field:
                parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                if parent_path_param:
                    parent_accessor = f"(input as any).{parent_path_param}"
                else:
                    parent_accessor = f"(input as any).{parent_id_field}"

            if parent_accessor:
                # Build PK - child entities use parent ID, but if pkPattern is org, use ORG#${orgId}
                if pk_pattern == "org":
                    org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                    if not org_id_accessor:
                        org_id_accessor = "(input as any).orgId"
                    else:
                        org_id_accessor = f"(input as any).{org_id_accessor}"
                    pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                else:
                    pk_expr = f"`${{{parent_accessor}}}`"

                # Build SK based on status prefix
                if status_prefix:
                    sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                else:
                    sk_expr = f"`${{this.SK_PREFIX}}#${{{id_accessor}}}`"

                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const now = {now};
    const pk = {pk_expr};
    const sk = {sk_expr};

    // Build update expression
    const updateExpressions: string[] = [];
    const expressionAttributeNames: Record<string, string> = {{}};
    const expressionAttributeValues: Record<string, any> = {{}};

    // Add updatedAt field dynamically using class constant
    updateExpressions.push(`#${{this.UPDATED_AT_FIELD}} = :updatedAt`);
    expressionAttributeNames[`#${{this.UPDATED_AT_FIELD}}`] = this.UPDATED_AT_FIELD;
    expressionAttributeValues[":updatedAt"] = now;

    // Add other fields from input (exclude id and parent_id fields)
    const excludedFields = ["{id_field_name}", "{parent_id_field}"]
    Object.keys(input || {{}}).forEach((key, index) => {{
      if (!excludedFields.includes(key)) {{
        const nameKey = `#field${{index}}`;
        const valueKey = `:value${{index}}`;
        updateExpressions.push(`${{nameKey}} = ${{valueKey}}`);
        expressionAttributeNames[nameKey] = key;
        expressionAttributeValues[valueKey] = (input as any)[key];
      }}
    }});

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
      UpdateExpression: `SET ${{updateExpressions.join(", ")}}`,
      ExpressionAttributeNames: expressionAttributeNames,
      ExpressionAttributeValues: expressionAttributeValues,
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
            else:
                # Fallback if no parent accessor
                # Build PK based on pattern
                if pk_pattern == "org":
                    org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                    if not org_id_accessor:
                        org_id_accessor = "(input as any).orgId"
                    else:
                        org_id_accessor = f"(input as any).{org_id_accessor}"
                    pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                else:
                    pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"

                # Build SK based on status prefix
                if status_prefix:
                    sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                else:
                    sk_expr = f"`${{this.SK_PREFIX}}#${{{id_accessor}}}`"

                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const now = {now};
    const pk = {pk_expr};
    const sk = {sk_expr};

    // Build update expression
    const updateExpressions: string[] = [];
    const expressionAttributeNames: Record<string, string> = {{}};
    const expressionAttributeValues: Record<string, any> = {{}};

    // Add updatedAt field dynamically using class constant
    updateExpressions.push(`#${{this.UPDATED_AT_FIELD}} = :updatedAt`);
    expressionAttributeNames[`#${{this.UPDATED_AT_FIELD}}`] = this.UPDATED_AT_FIELD;
    expressionAttributeValues[":updatedAt"] = now;

    // Add other fields from input (exclude id field)
    Object.keys(input || {{}}).forEach((key, index) => {{
      if (key !== "{id_field_name}") {{
        const nameKey = `#field${{index}}`;
        const valueKey = `:value${{index}}`;
        updateExpressions.push(`${{nameKey}} = ${{valueKey}}`);
        expressionAttributeNames[nameKey] = key;
        expressionAttributeValues[valueKey] = (input as any)[key];
      }}
    }});

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
      UpdateExpression: `SET ${{updateExpressions.join(", ")}}`,
      ExpressionAttributeNames: expressionAttributeNames,
      ExpressionAttributeValues: expressionAttributeValues,
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
        else:
            # Regular entity (not child)
            # Build PK based on pattern
            if pk_pattern == "org":
                org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                if not org_id_accessor:
                    org_id_accessor = "(input as any).orgId"
                else:
                    org_id_accessor = f"(input as any).{org_id_accessor}"
                pk_expr = f"`ORG#${{{org_id_accessor}}}`"
            else:
                pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"

            # Build SK based on status prefix
            if status_prefix:
                sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
            else:
                sk_expr = f"`${{this.SK_PREFIX}}#${{{id_accessor}}}`"

            return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const now = {now};
    const pk = {pk_expr};
    const sk = {sk_expr};

    // Build update expression
    const updateExpressions: string[] = [];
    const expressionAttributeNames: Record<string, string> = {{}};
    const expressionAttributeValues: Record<string, any> = {{}};

    // Add updatedAt field dynamically using class constant
    updateExpressions.push(`#${{this.UPDATED_AT_FIELD}} = :updatedAt`);
    expressionAttributeNames[`#${{this.UPDATED_AT_FIELD}}`] = this.UPDATED_AT_FIELD;
    expressionAttributeValues[":updatedAt"] = now;

    // Add other fields from input (exclude id field)
    Object.keys(input || {{}}).forEach((key, index) => {{
      if (key !== "{id_field_name}") {{
        const nameKey = `#field${{index}}`;
        const valueKey = `:value${{index}}`;
        updateExpressions.push(`${{nameKey}} = ${{valueKey}}`);
        expressionAttributeNames[nameKey] = key;
        expressionAttributeValues[valueKey] = (input as any)[key];
      }}
    }});

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
      UpdateExpression: `SET ${{updateExpressions.join(", ")}}`,
      ExpressionAttributeNames: expressionAttributeNames,
      ExpressionAttributeValues: expressionAttributeValues,
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""

    def _generate_delete_method_body(
        self,
        operation: Dict[str, Any],
        context: GenerationContext,
        path: str,
        entity_type: str,
        entity_token: str,
        sk_prefix: str,
        is_child_entity: bool,
        parent_id_field: str,
        soft_delete_enabled: bool,
        id_field_name: str,
        pk_pattern: str = "entity",
        status_prefix: bool = False,
        domain: str = "",
        entity_type_pk: str = ""
    ) -> str:
        """Generate DELETE method body"""
        id_accessor = self._get_id_accessor(operation, context, id_field_name, path)
        if not id_accessor:
            id_accessor = f"(input as any).{id_field_name}"

        # Universal pattern: query to get item pk/sk, then soft-delete (set deletedAt) or hard delete
        if domain and entity_type_pk and not is_child_entity:
            org_path_param = self._extract_path_parameter(operation, context, "orgId", path)
            org_id_accessor = f"(input as any).{org_path_param}" if org_path_param else "(input as any).orgId"
            sk_prefix_expr = (
                f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                if status_prefix
                else f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}#`"
            )
            if soft_delete_enabled:
                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}
    const pk = this.buildPK({org_id_accessor} as string, {id_accessor} as string);
    const getResult = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{ ":pk": pk, ":skPrefix": {sk_prefix_expr} }},
      Limit: 1,
    }});
    const existing = getResult.Items?.[0] as Record<string, unknown> | undefined;
    if (!existing?.PK || !existing?.SK) {{
      throw new Error(`${{this.ENTITY_TYPE}} with id ${{{id_accessor}}} not found`);
    }}
    const now = new Date().toISOString();
    await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: existing.PK, SK: existing.SK }},
      UpdateExpression: "SET #deletedAt = :deletedAt REMOVE #gsi1pk, #gsi1sk, #gsi2pk, #gsi2sk, #gsi3pk, #gsi3sk",
      ExpressionAttributeNames: {{
        "#deletedAt": "deletedAt",
        "#gsi1pk": "GSI1-PK",
        "#gsi1sk": "GSI1-SK",
        "#gsi2pk": "GSI2-PK",
        "#gsi2sk": "GSI2-SK",
        "#gsi3pk": "GSI3-PK",
        "#gsi3sk": "GSI3-SK",
      }},
      ExpressionAttributeValues: {{ ":deletedAt": now }},
      ReturnValues: "ALL_NEW",
    }});
    return {{
      data: {{}} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""
            else:
                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{org_id_accessor}) {{
      throw new Error("Missing required parameter: orgId");
    }}
    const pk = this.buildPK({org_id_accessor} as string, {id_accessor} as string);
    const getResult = await this.dynamoClient.query({{
      TableName: this.TABLE_NAME,
      KeyConditionExpression: "PK = :pk AND begins_with(SK, :skPrefix)",
      ExpressionAttributeValues: {{ ":pk": pk, ":skPrefix": {sk_prefix_expr} }},
      Limit: 1,
    }});
    const existing = getResult.Items?.[0] as Record<string, unknown> | undefined;
    if (!existing?.PK || !existing?.SK) {{
      throw new Error(`${{this.ENTITY_TYPE}} with id ${{{id_accessor}}} not found`);
    }}
    await this.dynamoClient.delete({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: existing.PK, SK: existing.SK }},
    }});
    return {{
      data: {{}} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }} as unknown as any,
    }};"""

        if soft_delete_enabled and status_prefix:
            # Soft delete with status prefix: update SK to DELETED# pattern
            if is_child_entity:
                parent_accessor = None
                if parent_id_field:
                    parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                    if parent_path_param:
                        parent_accessor = f"(input as any).{parent_path_param}"
                    else:
                        parent_accessor = f"(input as any).{parent_id_field}"

                if parent_accessor:
                    # Build PK - child entities use parent ID, but if pkPattern is org, use ORG#${orgId}
                    if pk_pattern == "org":
                        org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                        if not org_id_accessor:
                            org_id_accessor = "(input as any).orgId"
                        else:
                            org_id_accessor = f"(input as any).{org_id_accessor}"
                        pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                    else:
                        pk_expr = f"`${{{parent_accessor}}}`"

                    active_sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                    deleted_sk_expr = f"`DELETED#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}#${{now}}`"

                    return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const now = new Date().toISOString();
    const pk = {pk_expr};
    const activeSk = {active_sk_expr};
    const deletedSk = {deleted_sk_expr};

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: activeSk }},
      UpdateExpression: "SET #sk = :deletedSk, #deletedAt = :deletedAt",
      ExpressionAttributeNames: {{
        "#sk": "SK",
        "#deletedAt": "deletedAt",
      }},
      ExpressionAttributeValues: {{
        ":deletedSk": deletedSk,
        ":deletedAt": now,
      }},
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
                else:
                    # Fallback if no parent accessor
                    if pk_pattern == "org":
                        org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                        if not org_id_accessor:
                            org_id_accessor = "(input as any).orgId"
                        else:
                            org_id_accessor = f"(input as any).{org_id_accessor}"
                        pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                    else:
                        pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"

                    active_sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                    deleted_sk_expr = f"`DELETED#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}#${{now}}`"

                    return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const now = new Date().toISOString();
    const pk = {pk_expr};
    const activeSk = {active_sk_expr};
    const deletedSk = {deleted_sk_expr};

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: activeSk }},
      UpdateExpression: "SET #sk = :deletedSk, #deletedAt = :deletedAt",
      ExpressionAttributeNames: {{
        "#sk": "SK",
        "#deletedAt": "deletedAt",
      }},
      ExpressionAttributeValues: {{
        ":deletedSk": deletedSk,
        ":deletedAt": now,
      }},
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
            else:
                # Regular entity (not child)
                if pk_pattern == "org":
                    org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                    if not org_id_accessor:
                        org_id_accessor = "(input as any).orgId"
                    else:
                        org_id_accessor = f"(input as any).{org_id_accessor}"
                    pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                else:
                    pk_expr = f"`${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"

                active_sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                deleted_sk_expr = f"`DELETED#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}#${{now}}`"

                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const now = new Date().toISOString();
    const pk = {pk_expr};
    const activeSk = {active_sk_expr};
    const deletedSk = {deleted_sk_expr};

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: activeSk }},
      UpdateExpression: "SET #sk = :deletedSk, #deletedAt = :deletedAt",
      ExpressionAttributeNames: {{
        "#sk": "SK",
        "#deletedAt": "deletedAt",
      }},
      ExpressionAttributeValues: {{
        ":deletedSk": deletedSk,
        ":deletedAt": now,
      }},
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
        elif soft_delete_enabled:
            # Soft delete without status prefix: just update deletedAt field
            if is_child_entity:
                parent_accessor = None
                if parent_id_field:
                    parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                    if parent_path_param:
                        parent_accessor = f"(input as any).{parent_path_param}"
                    else:
                        parent_accessor = f"(input as any).{parent_id_field}"

                if parent_accessor:
                    if pk_pattern == "org":
                        org_id_accessor = self._extract_path_parameter(operation, context, "orgId", path)
                        if not org_id_accessor:
                            org_id_accessor = "(input as any).orgId"
                        else:
                            org_id_accessor = f"(input as any).{org_id_accessor}"
                        pk_expr = f"`ORG#${{{org_id_accessor}}}`"
                    else:
                        pk_expr = f"`${{{parent_accessor}}}`"

                    if status_prefix:
                        sk_expr = f"`ACTIVE#${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`"
                    else:
                        sk_expr = f"`${{this.SK_PREFIX}}#${{{id_accessor}}}`"

                    return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const pk = {pk_expr};
    const sk = {sk_expr};

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
      UpdateExpression: "SET deletedAt = :deletedAt",
      ExpressionAttributeValues: {{
        ":deletedAt": new Date().toISOString(),
      }},
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
                else:
                    return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const pk = `${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`;
    const sk = `${{this.SK_PREFIX}}#${{{id_accessor}}}`;

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
      UpdateExpression: "SET deletedAt = :deletedAt",
      ExpressionAttributeValues: {{
        ":deletedAt": new Date().toISOString(),
      }},
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
            else:
                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const pk = `${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`;
    const sk = `${{this.SK_PREFIX}}#${{{id_accessor}}}`;

    const result = await this.dynamoClient.update({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
      UpdateExpression: "SET deletedAt = :deletedAt",
      ExpressionAttributeValues: {{
        ":deletedAt": new Date().toISOString(),
      }},
      ReturnValues: "ALL_NEW",
    }});

    return {{
      data: (result.Attributes || {{}}) as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
        else:
            # Hard delete
            if is_child_entity:
                parent_accessor = None
                if parent_id_field:
                    parent_path_param = self._extract_path_parameter(operation, context, parent_id_field, path)
                    if parent_path_param:
                        parent_accessor = f"(input as any).{parent_path_param}"
                    else:
                        parent_accessor = f"(input as any).{parent_id_field}"

                if parent_accessor:
                    return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    if (!{parent_accessor}) {{
      throw new Error("Missing required parameter: {parent_id_field}");
    }}
    const pk = `${{{parent_accessor}}}`;
    const sk = `${{this.SK_PREFIX}}#${{{id_accessor}}}`;

    await this.dynamoClient.delete({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
    }});

    return {{
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
                else:
                    return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const pk = `${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`;
    const sk = `${{this.SK_PREFIX}}#${{{id_accessor}}}`;

    await this.dynamoClient.delete({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
    }});

    return {{
      data: {{}} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
            else:
                return f"""    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    const pk = `${{this.ENTITY_TOKEN}}#${{{id_accessor}}}`;
    const sk = `${{this.SK_PREFIX}}#${{{id_accessor}}}`;

    await this.dynamoClient.delete({{
      TableName: this.TABLE_NAME,
      Key: {{ PK: pk, SK: sk }},
    }});

    return {{
      data: {{}} as unknown as any,
      meta: {{
        correlationId: (input?.correlationId as string) || this.generateCorrelationId(),
        timestamp: new Date().toISOString(),
      }},
    }};"""
