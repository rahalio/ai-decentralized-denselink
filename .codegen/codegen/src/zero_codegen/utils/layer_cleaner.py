"""
Layer Cleaner - Removes previously generated code before regeneration

Ensures no stale/orphaned files persist when operations or domains are removed.
Removes all generated domain dirs (including those for removed/non-existing domains).
Preserves hand-maintained directories (e.g. _shared) per layer.
Supports per-layer, per-domain file overrides so selected manual files are kept.
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

# Directory names to never delete (hand-maintained per layer)
PRESERVE_DIRS: Set[str] = {"_shared"}

# Subdirectory names to preserve inside each domain directory on clean
PRESERVE_DOMAIN_SUBDIRS: Set[str] = {"extensions"}

# Top-level core src dirs to preserve on core clean (non-domain manual modules)
CORE_MANUAL_MODULES: Set[str] = {"integration-events"}

# Per-layer, per-domain filenames to never delete (hand-maintained overrides).
# Layer -> domain -> list of filenames (e.g. identity-member-repository.ddb.ts)
PRESERVE_FILES_BY_LAYER: Dict[str, Dict[str, List[str]]] = {
    "adapters": {
        # Hand-written auth store (legacy identity partition). Do not wipe on adapters clean.
        "identity": ["user-repository.ddb.ts"],
        # Deal-intel stub until x-dynamodb + computation are wired.
        "opportunity": ["intel-repository.ddb.ts"],
        # Singleton org: get/update normalize id === orgId before DDB.
        "organization": ["org-repository.adapter.ts"],
        # Directory catalog (pkPattern: global / base table) until generator emits DIRECTORY# keys.
        "company": ["company-repository.ddb.ts"],
        "person": ["person-repository.ddb.ts", "person-repository.adapter.ts"],
        "meeting": [
            "preference-repository.ddb.ts",
            "scheduling-page-repository.ddb.ts",
        ],
        "company-search": ["save-repository.ddb.ts"],
        "person-search": ["save-repository.ddb.ts"],
        "data-exchange": ["csv-import.service.ts", "index.ts"],
        "provider": ["discover-repository.ddb.ts"],
    },
}

def clean_layer_output(
    project_root: Path,
    layer: str,
    domain_names: List[str],
    preserve_dirs: Optional[List[str]] = None,
    domain_names_to_clean: Optional[List[str]] = None,
) -> int:
    """
    Remove previously generated output for a layer.

    When domain_names_to_clean is None (e.g. generating for all domains): deletes
    every domain subdirectory that is not in preserve_dirs (full clean).
    When domain_names_to_clean is provided (e.g. generating for one domain): deletes
    only those domain subdirectories, leaving other domains untouched.

    Args:
        project_root: Project root path
        layer: Layer name (core, services, api_server, adapters, tests, postman)
        domain_names: List of current domain names (used for logging)
        preserve_dirs: Directory names to never delete (e.g. _shared). Default: _shared
        domain_names_to_clean: If set, only remove these domain dirs. If None, remove all.

    Returns:
        Number of items (dirs/files) removed
    """
    preserved = set(preserve_dirs) if preserve_dirs is not None else PRESERVE_DIRS
    removed = 0
    only_these_domains = set(domain_names_to_clean) if domain_names_to_clean is not None else None

    def remove_domain_dirs(parent: Path) -> int:
        count = 0
        if not parent.exists():
            return 0
        for child in list(parent.iterdir()):
            if not child.is_dir():
                continue
            if child.name in preserved:
                continue
            if only_these_domains is not None and child.name not in only_these_domains:
                continue
            shutil.rmtree(child)
            count += 1
        return count

    def clean_domain_dir_preserving_subdirs(parent: Path, subdirs: Set[str]) -> int:
        count = 0
        if not parent.exists():
            return 0
        for child in list(parent.iterdir()):
            if not child.is_dir():
                continue
            if child.name in preserved:
                continue
            if only_these_domains is not None and child.name not in only_these_domains:
                continue
            extensions_path = child / "extensions"
            has_preserved_subdir = any(
                (child / name).exists() and (child / name).is_dir() for name in subdirs
            )
            if has_preserved_subdir:
                for item in list(child.iterdir()):
                    if item.name in subdirs:
                        continue
                    if item.is_file():
                        item.unlink()
                        count += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        count += 1
            else:
                shutil.rmtree(child)
                count += 1
        return count

    if layer == "core":
        core_src = project_root / "packages" / "core" / "src"
        # Preserve hand-maintained top-level modules (e.g. integration-events types)
        # in addition to PRESERVE_DIRS (_shared).
        preserved = preserved | CORE_MANUAL_MODULES
        removed = remove_domain_dirs(core_src)
        return removed

    elif layer == "services":
        services_src = project_root / "platform" / "services" / "src"
        removed = clean_domain_dir_preserving_subdirs(services_src, PRESERVE_DOMAIN_SUBDIRS)
        if only_these_domains is None:
            index_file = services_src / "index.ts"
            if index_file.exists():
                index_file.unlink()
                removed += 1
        return removed

    elif layer == "api_server" or layer == "api-server":
        api_domains = project_root / "platform" / "api-server" / "src" / "domains"
        removed = clean_domain_dir_preserving_subdirs(api_domains, PRESERVE_DOMAIN_SUBDIRS)
        return removed

    elif layer == "adapters":
        adapters_src = project_root / "platform" / "adapters" / "src"
        preserve_by_domain = PRESERVE_FILES_BY_LAYER.get("adapters", {})
        if not preserve_by_domain:
            removed = remove_domain_dirs(adapters_src)
            return removed
        if not adapters_src.exists():
            return 0
        for child in list(adapters_src.iterdir()):
            if not child.is_dir():
                continue
            if child.name in preserved:
                continue
            if only_these_domains is not None and child.name not in only_these_domains:
                continue
            preserved_files = set(preserve_by_domain.get(child.name, []))
            for item in list(child.iterdir()):
                if item.name in preserved_files:
                    continue
                if item.is_file():
                    item.unlink()
                    removed += 1
                else:
                    shutil.rmtree(item)
                    removed += 1
        return removed

    elif layer == "tests":
        tests_src = project_root / "platform" / "tests" / "src"
        removed = remove_domain_dirs(tests_src)
        return removed

    elif layer == "postman":
        generated_dir = project_root / "platform" / "tests" / "postman" / "generated"
        if generated_dir.exists():
            for f in list(generated_dir.iterdir()):
                if f.suffix in (".json",) and f.name != "._bundle_temp.json":
                    f.unlink()
                    removed += 1
        e2e_dir = project_root / "platform" / "tests" / "src" / "__e2e__"
        if e2e_dir.exists():
            for f in list(e2e_dir.iterdir()):
                if f.is_file() and f.name.startswith("postman-") and f.name.endswith(".e2e.test.ts"):
                    f.unlink()
                    removed += 1
        return removed

    elif layer == "webapp":
        # Generated domain clients under services/domains; preserve services/shared
        services_domains = project_root / "platform" / "webapp" / "src" / "services" / "domains"
        removed += remove_domain_dirs(services_domains)
        # Generated feature stubs; preserve hand-maintained feature dirs via preserve list if needed
        features_src = project_root / "platform" / "webapp" / "src" / "features"
        removed += remove_domain_dirs(features_src)
        return removed

    return 0


def clean_layers_before_generation(
    project_root: Path,
    layers: List[str],
    domain_names: List[str],
    domain_names_to_clean: Optional[List[str]] = None,
) -> dict:
    """
    Clean specified layers before generation.

    When domain_names_to_clean is None (generating for all domains), all domain
    output in each layer is removed. When provided (generating for one or a subset
    of domains), only those domains' output is removed.

    Args:
        project_root: Project root path
        layers: List of layer names to clean
        domain_names: List of all domain names (for logging)
        domain_names_to_clean: If set, only clean these domains; if None, clean all.

    Returns:
        Dict mapping layer -> number of items removed
    """
    results = {}
    for layer in layers:
        n = clean_layer_output(
            project_root,
            layer,
            domain_names,
            domain_names_to_clean=domain_names_to_clean,
        )
        if n > 0:
            results[layer] = n
    return results
