#!/usr/bin/env python3
"""
List operationIds whose resource has no repository in core.

Usage (from repo root):
  PYTHONPATH=.codegen-zatca/codegen-merged/src python3 .codegen-zatca/codegen-merged/scripts/list_operations_without_repos.py
"""

import json
import sys
from pathlib import Path

# Add codegen src to path when run directly
SCRIPT_DIR = Path(__file__).resolve().parent
CODECEN_SRC = SCRIPT_DIR.parent / "src"
if str(CODECEN_SRC) not in sys.path:
    sys.path.insert(0, str(CODECEN_SRC))

from zero_codegen.base.config import Config
from zero_codegen.base.context import GenerationContext
from zero_codegen.base.logger import create_logger
from zero_codegen.utils.openapi import extract_operations, extract_schemas, load_openapi_spec
from zero_codegen.utils.naming import NamingConvention
from zero_codegen.utils.string import kebab_case
from zero_codegen.generators.core.repositories.entity_extractor import EntityExtractor


def main():
    config_path = SCRIPT_DIR.parent.parent / ".zero-codegen-merged.json"
    config = Config(**json.loads(config_path.read_text()))
    logger = create_logger(level="WARN", verbose=False)

    project_root = config.paths.project_root
    no_repo_ops = []  # (domain, operation_id)

    for domain_config in config.domains:
        if not getattr(domain_config, "enabled", True):
            continue
        domain_name = domain_config.name
        bundled_path = config.paths.bundled_dir / domain_config.bundled_path
        if not bundled_path.exists():
            print(f"Skip {domain_name}: bundled spec not found at {bundled_path}", file=sys.stderr)
            continue

        spec = load_openapi_spec(bundled_path)
        operations = extract_operations(spec)
        schemas_dict = extract_schemas(spec)
        context = GenerationContext(config=config, domain=domain_config, logger=logger, spec=spec)

        # Build set of resources that HAVE a repo (entity file exists, not value object)
        resources_with_repo = set()
        resource_to_ops = {}  # resource -> [operation_id, ...]

        for op_data in operations:
            operation_id = op_data["operation_id"]
            resource = NamingConvention.resource_for_grouping(
                operation_id, op_data.get("path")
            )
            resource_to_ops.setdefault(resource, []).append(operation_id)

        for resource in resource_to_ops:
            entity_name = EntityExtractor.extract_entity_name_from_operations(context, resource)
            if entity_name:
                entity_schema_def = schemas_dict.get(entity_name) or {}
                if isinstance(entity_schema_def, dict) and entity_schema_def.get("x-value-object") is True:
                    continue  # value object, no repo
                if isinstance(entity_schema_def, dict) and entity_name.endswith("Response"):
                    data_prop = (entity_schema_def.get("properties") or {}).get("data")
                    if data_prop and isinstance(data_prop, dict) and "$ref" not in str(data_prop):
                        continue  # response DTO, no repo
            domain_dir = project_root / "packages" / "core" / "src" / domain_name
            entity_file = domain_dir / "models" / f"{kebab_case(resource)}.entity.ts"
            if entity_file.exists():
                resources_with_repo.add(resource)

        for resource, op_ids in resource_to_ops.items():
            if resource not in resources_with_repo:
                for op_id in op_ids:
                    no_repo_ops.append((domain_name, op_id))

    no_repo_ops.sort(key=lambda x: (x[0], x[1]))
    for domain, op_id in no_repo_ops:
        print(f"{domain}\t{op_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
