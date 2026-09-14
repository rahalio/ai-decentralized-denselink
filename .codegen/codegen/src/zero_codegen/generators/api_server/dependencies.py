"""
Dependencies Generator - Generates composition root

Per DDD: Composition root belongs in api-server layer.
Wires use cases with adapters implementing ports.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file, clean_directory
from ...utils.string import kebab_case, pascal_case, camel_case, extract_verb_from_operation_id
from ...utils.port_determination import PortDetermination
from ...utils.x_codegen_extensions import should_skip_port, should_skip_usecase


class DependenciesGenerator(BaseGenerator):
    """
    Generates composition root

    Pattern: Wires use cases with adapters implementing ports
    const publisher = new GenericProviderPublisherAdapter(configRepo, http);
    const executePublishContent = new ExecutePublishContent(publisher, accountsRepo);
    """

    @property
    def name(self) -> str:
        return "Dependencies Generator"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def type(self) -> str:
        return "dependencies"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate dependencies file"""
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Get output directory (clean when pipeline.clean to remove stale dependencies)
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "api-server" / "src" / "domains" / context.domain_name / "dependencies"
        ensure_directory(output_dir)
        if context.config.pipeline.clean:
            clean_directory(output_dir)

        # Extract operations to identify use cases
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)

        # Filter x-repository:none so we don't create ports for action-only ops
        port_ops = [o for o in operations if self._should_generate_port(o["operation"])]
        ports = self._identify_ports(port_ops, context)
        use_cases = self._identify_use_cases(operations, context, ports)

        # Generate dependencies file
        deps_file = output_dir / f"{context.domain_name}-ddd.dependencies.ts"

        header = self.generate_header(
            context,
            f"{pascal_case(context.domain_name)} DDD Dependencies - Composition root"
        )

        deps_content = self._generate_dependencies_content(
            context,
            use_cases,
            ports,
            header
        )

        write_file(deps_file, deps_content)
        files.append(deps_file)

        context.logger.info(f"Generated dependencies file for domain: {context.domain_name}")

        return GenerateResult(files=files, warnings=warnings)

    def _should_generate_port(self, operation: Any) -> bool:
        """Skip extension-handler ops; action-only still gets application ports."""
        return not should_skip_port(operation if isinstance(operation, dict) else {})

    def _resolve_operation_alias(
        self,
        context: GenerationContext,
        operation_id: str,
        operation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Resolve operation alias - aliased ops delegate to another use case and need no own entry."""
        aliases = getattr(context.domain, "operation_aliases", None) or {}
        alias_cfg = aliases.get(operation_id)
        if alias_cfg:
            return {"delegate_to": alias_cfg.delegate_to, "input_merge": alias_cfg.input_merge or {}}
        x_codegen = operation.get("x-codegen") or {}
        if isinstance(x_codegen, dict) and x_codegen.get("delegateTo"):
            return {
                "delegate_to": x_codegen["delegateTo"],
                "input_merge": x_codegen.get("inputMerge") or {},
            }
        return None

    def _identify_use_cases(
        self,
        operations: List[Dict[str, Any]],
        context: GenerationContext,
        identified_ports: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Identify use cases from operations (skip aliased operations - they use target's use case)"""
        from ...generators.core.repositories.repository_config import get_canonical_resource_for_operation

        use_cases = []
        seen_use_cases = set()

        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data["operation"]

            # Skip aliased operations - they delegate to another use case, no own entry needed
            if self._resolve_operation_alias(context, operation_id, operation):
                continue

            if should_skip_usecase(operation):
                continue

            verb = extract_verb_from_operation_id(operation_id)
            resource = get_canonical_resource_for_operation(
                operation, operation_id, context.domain_name,
                NamingConvention.resource_for_grouping,
                path=op_data.get("path"),
            )

            # Use full operation_id for unique use case names (matches use case generator)
            use_case_name = f"Execute{pascal_case(operation_id)}"
            use_case_var = camel_case(use_case_name)

            # Deduplicate use cases
            if use_case_name in seen_use_cases:
                continue
            seen_use_cases.add(use_case_name)

            # Determine dependencies (ports) needed using shared utility
            dependencies = PortDetermination.determine_use_case_dependencies(
                operation_id, operation, resource, verb, identified_ports
            )

            use_cases.append({
                "name": use_case_name,
                "var": use_case_var,
                "verb": verb,
                "resource": resource,
                "operation_id": operation_id,
                "operation": operation,
                "dependencies": dependencies
            })

        return use_cases

    def _identify_ports(
        self,
        operations: List[Dict[str, Any]],
        context: GenerationContext
    ) -> Dict[str, str]:
        """Identify ports needed using shared utility"""
        ports = {}

        for op_data in operations:
            operation_id = op_data["operation_id"]
            operation = op_data["operation"]

            port_name = PortDetermination.determine_port_name(
                operation_id, operation, context, path=op_data.get("path")
            )

            if port_name not in ports:
                adapter_name = PortDetermination.determine_adapter_name(port_name)
                ports[port_name] = adapter_name

        return ports

    @staticmethod
    def _port_name_to_repo_key(port_name: str, domain_name: str) -> str:
        """
        Derive the repo key for domain module structure (e.g. orders, quotes).
        ExchangeOrderRepository + exchange -> orders.
        PersonRepository + person -> people (do not strip when base equals domain).
        """
        from ...utils.string import pluralize

        if not port_name.endswith("Repository"):
            base = port_name
        else:
            base = port_name[:-len("Repository")]
        domain_prefix = pascal_case(domain_name)
        # Only strip domain prefix when a remainder remains (PersonRepository in
        # person domain must stay "Person" → "people", not "" → "s").
        if domain_prefix and base.startswith(domain_prefix) and len(base) > len(domain_prefix):
            base = base[len(domain_prefix):]
        return camel_case(pluralize(base))

    @staticmethod
    def _resource_to_repo_key(resource: str, domain_name: str) -> str:
        """
        Derive the repo key from canonical resource for use case grouping.
        Order + exchange -> orders; Person + person -> people.
        """
        from ...utils.string import pluralize

        domain_prefix = pascal_case(domain_name)
        base = resource
        if domain_prefix and base.startswith(domain_prefix) and len(base) > len(domain_prefix):
            base = base[len(domain_prefix):]
        return camel_case(pluralize(base))

    def _generate_dependencies_content(
        self,
        context: GenerationContext,
        use_cases: List[Dict[str, Any]],
        ports: Dict[str, str],
        header: str
    ) -> str:
        """Generate dependencies file content"""
        domain_name = context.domain_name
        domain_pascal = pascal_case(domain_name)

        # Single source of truth: same as port_adapter — only repos with DDB get adapters.
        from ...generators.core.repositories.repository_config import (
            get_repository_names_with_dynamodb,
            COMPOSITE_USE_CASE_DEPS,
        )
        ddb_repo_names = get_repository_names_with_dynamodb(context)

        # Build adapter imports using barrel exports from domain index
        adapter_class_names = []
        repo_ports = {}  # port_name -> adapter_name for Repository ports only
        repo_key_to_port_name = {}  # repo_key -> port_name for domain module structure

        for port_name, adapter_name in ports.items():
            if port_name.endswith("Repository"):
                # Only include repository ports that have a DDB implementation (and thus an adapter).
                if port_name not in ddb_repo_names:
                    continue
                adapter_class_names.append(adapter_name)
                repo_ports[port_name] = adapter_name
                repo_key = self._port_name_to_repo_key(port_name, domain_name)
                repo_key_to_port_name[repo_key] = port_name

        # Group use cases by repo_key and verb for domain module structure
        use_cases_by_repo_key: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for use_case in use_cases:
            repo_key = self._resource_to_repo_key(use_case["resource"], domain_name)
            verb = use_case["verb"]
            if repo_key not in use_cases_by_repo_key:
                use_cases_by_repo_key[repo_key] = {}
            use_cases_by_repo_key[repo_key][verb] = use_case

        # Adapter imports only — adapters encapsulate Ddb internally; api-server passes dynamoClient
        adapter_imports = []
        if adapter_class_names:
            adapter_imports_str = ",\n  ".join(sorted(adapter_class_names))
            adapter_imports.append(
                f"import {{\n  {adapter_imports_str},\n}} from \"@ddd/adapters/{domain_name}\";"
            )

        # Use-case imports (concrete classes)
        use_case_names = sorted(set(uc["name"] for uc in use_cases))
        use_case_imports = []
        if use_case_names:
            use_case_imports_str = ",\n  ".join(use_case_names)
            use_case_imports.append(
                f"// Use-case constructors (concrete)\nimport {{\n  {use_case_imports_str},\n}} from \"@ddd/services/{domain_name}/usecases\";"
            )

        # Port type imports (interfaces from services layer)
        port_type_imports = []
        if repo_ports:
            port_type_names = sorted(repo_ports.keys())
            port_types_str = ",\n  ".join(port_type_names)
            port_type_imports.append(
                f"// Ports (interfaces)\nimport type {{\n  {port_types_str},\n}} from \"@ddd/services/{domain_name}/ports\";"
            )

        # Build DomainModule interface: repos and useCases grouped by repo_key
        repos_interface_lines = []
        for repo_key in sorted(repo_key_to_port_name.keys()):
            port_name = repo_key_to_port_name[repo_key]
            repos_interface_lines.append(f"    {repo_key}: {port_name};")

        # Only expose use case groups for repos we actually have (those with DDB adapters)
        use_cases_interface_lines = []
        for repo_key in sorted(use_cases_by_repo_key.keys()):
            if repo_key not in repo_key_to_port_name:
                continue
            verbs = use_cases_by_repo_key[repo_key]
            use_cases_interface_lines.append(f"    {repo_key}: {{")
            for verb in sorted(verbs.keys()):
                uc = verbs[verb]
                use_cases_interface_lines.append(f"      {verb}: {uc['name']};")
            use_cases_interface_lines.append("    };")

        # Factory: buildDomainModule(dynamoClient) — no orgId
        # Adapters encapsulate Ddb; api-server passes dynamoClient only
        factory_body = []
        factory_body.append("  // Adapters implementing ports (adapters encapsulate Ddb)")
        factory_body.append("  const repos = (() => {")
        factory_body.append("    const obj: {")
        for repo_key in sorted(repo_key_to_port_name.keys()):
            port_name = repo_key_to_port_name[repo_key]
            factory_body.append(f"      {repo_key}?: {port_name};")
        factory_body.append("    } = {};")
        factory_body.append("")
        for repo_key in sorted(repo_key_to_port_name.keys()):
            port_name = repo_key_to_port_name[repo_key]
            adapter_name = repo_ports[port_name]
            factory_body.append(f"    obj.{repo_key} = new {adapter_name}(dynamoClient);")
        factory_body.append("    return {")
        for repo_key in sorted(repo_key_to_port_name.keys()):
            factory_body.append(f"      {repo_key}: obj.{repo_key}!,")
        factory_body.append("    };")
        factory_body.append("  })();")
        factory_body.append("")
        factory_body.append("  const executionContext = executionContextService;")
        factory_body.append("  const idGenerator = getIdGeneratorService();")
        factory_body.append("")
        factory_body.append("  // Use cases depend only on ports (repos.*)")
        factory_body.append("  const useCases = {")

        # Build useCases object: repo_key -> { verb -> new Execute...(executionContext, idGenerator, repos.*) }
        # x-use-case-repository in OpenAPI overrides which repo is passed (e.g. IdentityMember -> repos.members)
        composite_cases = []  # (repo_key, verb, uc) for two-phase init
        for repo_key in sorted(use_cases_by_repo_key.keys()):
            if repo_key not in repo_key_to_port_name:
                continue
            verbs = use_cases_by_repo_key[repo_key]
            factory_body.append(f"    {repo_key}: {{")
            for verb in sorted(verbs.keys()):
                uc = verbs[verb]
                operation = uc.get("operation") if isinstance(uc.get("operation"), dict) else None
                repo_key_for_deps = repo_key
                if operation:
                    x_uc_repo = operation.get("x-use-case-repository")
                    if x_uc_repo and isinstance(x_uc_repo, str):
                        port_name = f"{x_uc_repo}Repository" if not x_uc_repo.endswith("Repository") else x_uc_repo
                        repo_key_for_deps = self._port_name_to_repo_key(port_name, domain_name)
                    if operation.get("x-use-case-constructor") == "composite":
                        composite_cases.append((repo_key, verb, uc))
                        factory_body.append(f"      {verb}: undefined as unknown as {uc['name']},")
                        continue
                deps_str = f"executionContext, idGenerator, repos.{repo_key_for_deps}"
                factory_body.append(
                    f"      {verb}: new {uc['name']}({deps_str}),"
                )
            factory_body.append("    },")
        factory_body.append("  };")
        # Two-phase init for composite use cases (e.g. register depends on other use cases + repo)
        if composite_cases:
            for repo_key, verb, uc in composite_cases:
                operation_id = uc.get("operation_id", "")
                deps_list = (COMPOSITE_USE_CASE_DEPS.get(domain_name) or {}).get(operation_id)
                if not deps_list:
                    factory_body.append(f"  // TODO: add COMPOSITE_USE_CASE_DEPS for {domain_name}/{operation_id}")
                    continue
                # deps_list e.g. ["organizations.create", "members.create", "members"] -> useCases.organizations.create, useCases.members.create, repos.members
                args = []
                for ref in deps_list:
                    if "." in ref:
                        uc_ref, v = ref.split(".", 1)
                        args.append(f"useCases.{uc_ref}.{v}")
                    else:
                        args.append(f"repos.{ref}")
                args_str = "executionContext, idGenerator, " + ", ".join(args)
                factory_body.append(
                    f"  (useCases.{repo_key} as {{ {verb}: {uc['name']} }}).{verb} = new {uc['name']}({args_str});"
                )
            factory_body.append("")
        factory_body.append("  return { repos, useCases: useCases as " + f"{domain_pascal}DomainModule[\"useCases\"]" + " };")

        return f"""{header}/**
 * {domain_pascal} Domain Module - Composition root
 *
 * DDD: Composition root for {domain_name} domain. Exposes repos (ports) and use cases
 * grouped by aggregate. No orgId at build time — use execution context at call time.
 */

{chr(10).join(adapter_imports)}
import {{ getIdGeneratorService }} from "@ddd/adapters";
import type {{ AdapterDynamoDBClient }} from "@ddd/adapters";
import {{ executionContextService }} from "../../../lib/execution-context.service.js";
{chr(10).join(use_case_imports)}
{chr(10).join(port_type_imports)}

export interface {domain_pascal}DomainModule {{
  repos: {{
{chr(10).join(repos_interface_lines)}
  }};
  useCases: {{
{chr(10).join(use_cases_interface_lines)}
  }};
}}

export function build{domain_pascal}DomainModule(
  dynamoClient: AdapterDynamoDBClient,
): {domain_pascal}DomainModule {{
{chr(10).join(factory_body)}
}}
"""
