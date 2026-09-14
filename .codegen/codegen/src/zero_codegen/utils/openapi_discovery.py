"""
Discover domain names from the OpenAPI directory (packages/openapi-core/src).

Domain list is derived from top-level main spec YAML files:
- Includes: {name}.yaml (e.g. activity.yaml, ai.yaml)
- Excludes: *.lean.yaml, *.schemas.yaml, and files in subdirs (e.g. common/)
"""

from pathlib import Path
from typing import List, Optional

from ..base.config import DomainConfig


def discover_domain_names_from_openapi(openapi_dir: Path) -> List[str]:
    """
    List domain names from main OpenAPI spec files in openapi_dir.

    A file is considered a main spec if it is a top-level *.yaml and
    does not end with .lean.yaml or .schemas.yaml.
    """
    if not openapi_dir.is_dir():
        return []
    names: List[str] = []
    for f in sorted(openapi_dir.iterdir()):
        if not f.is_file() or f.suffix != ".yaml":
            continue
        name = f.name
        if name.endswith(".lean.yaml") or name.endswith(".schemas.yaml"):
            continue
        names.append(f.stem)
    return names


def discover_domain_configs_from_openapi(
    openapi_dir: Path,
    existing_domains: Optional[List[DomainConfig]] = None,
) -> List[DomainConfig]:
    """
    Build domain configs from the YAML list in openapi_dir.

    For each discovered main spec {name}.yaml we create a DomainConfig with
    spec_path="{name}.yaml", bundled_path="{name}.json" (relative to bundled_dir).
    If existing_domains contains a domain with the same name, its enabled,
    spec_path, bundled_path, and other overrides are used.
    """
    names = discover_domain_names_from_openapi(openapi_dir)
    overrides = {d.name: d for d in (existing_domains or [])}
    result: List[DomainConfig] = []
    for name in names:
        if name in overrides:
            result.append(overrides[name])
        else:
            result.append(
                DomainConfig(
                    name=name,
                    enabled=True,
                    spec_path=f"{name}.yaml",
                    bundled_path=f"{name}.json",
                )
            )
    return result


def sync_config_domains_from_openapi(config: "Config") -> "Config":
    """
    Replace config.domains with the list derived from packages/openapi-core/src.

    Domain names and presence are driven by the YAML files on disk; existing
    config entries are used for overrides (enabled, spec_path, bundled_path, etc.).
    """
    from ..base.config import Config

    openapi_dir = config.paths.openapi_dir
    merged = discover_domain_configs_from_openapi(
        openapi_dir,
        existing_domains=config.domains,
    )
    return config.model_copy(update={"domains": merged})
