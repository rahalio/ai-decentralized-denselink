"""
Read x-codegen and related OpenAPI extensions from domain specs.

Single source for handler extension routing, action-only ops, integration events,
api-server extension route config, and preserve-on-clean hints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _load_spec_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_x_codegen(spec: Dict[str, Any]) -> Dict[str, Any]:
    raw = spec.get("x-codegen") if isinstance(spec, dict) else None
    return raw if isinstance(raw, dict) else {}


def get_api_server_codegen(spec: Dict[str, Any]) -> Dict[str, Any]:
    api = get_x_codegen(spec).get("api-server") or get_x_codegen(spec).get("apiServer")
    return api if isinstance(api, dict) else {}


def get_operation_api_server_codegen(operation: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(operation, dict):
        return {}
    raw = operation.get("x-codegen") or {}
    if not isinstance(raw, dict):
        return {}
    api = raw.get("api-server") or raw.get("apiServer")
    return api if isinstance(api, dict) else {}


def is_action_only_operation(operation: Dict[str, Any]) -> bool:
    if not isinstance(operation, dict):
        return False
    x_repo = operation.get("x-repository")
    return isinstance(x_repo, str) and x_repo.lower() == "none"


def is_extension_handler_operation(operation: Dict[str, Any]) -> bool:
    api = get_operation_api_server_codegen(operation)
    handler = api.get("handler")
    return isinstance(handler, str) and handler.lower() == "extension"


def should_skip_persistence(operation: Dict[str, Any]) -> bool:
    """Skip core entity/repository binding for action-only ops (no persisted aggregate)."""
    return is_action_only_operation(operation)


def should_skip_usecase(operation: Dict[str, Any]) -> bool:
    """Skip generated usecases for action-only ops and extension handlers."""
    return is_action_only_operation(operation) or is_extension_handler_operation(operation)


def should_skip_port(operation: Dict[str, Any]) -> bool:
    """
    Application ports are always generated.

    Action-only and extension-handler ops still need ports — adapters implement them.
    Usecases/handlers are skipped separately via should_skip_usecase.
    """
    return False


def should_skip_codegen_operation(operation: Dict[str, Any]) -> bool:
    """
    Legacy combined skip (usecase + persistence style).

    Prefer should_skip_port / should_skip_usecase / should_skip_persistence.
    Kept for callers not yet migrated; equals should_skip_usecase.
    """
    return should_skip_usecase(operation)


def get_extension_handler_name(operation: Dict[str, Any], default_handler_name: str) -> str:
    api = get_operation_api_server_codegen(operation)
    name = api.get("extensionHandler")
    return name if isinstance(name, str) and name else default_handler_name


def get_response_merge(operation: Dict[str, Any]) -> Optional[str]:
    api = get_operation_api_server_codegen(operation)
    merge = api.get("responseMerge")
    return merge if isinstance(merge, str) else None


def get_integration_events(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = spec.get("x-integration-events") if isinstance(spec, dict) else None
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict) and item.get("type")]


def get_preserve_on_clean(spec: Dict[str, Any]) -> List[str]:
    raw = get_x_codegen(spec).get("preserveOnClean")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if item]


def get_api_server_extensions_config(spec: Dict[str, Any]) -> Dict[str, Any]:
    api = get_api_server_codegen(spec)
    ext = api.get("extensions")
    return ext if isinstance(ext, dict) else {}


def load_domain_specs(openapi_dir: Path, domain_configs: List[Any]) -> Dict[str, Dict[str, Any]]:
    """Load unbundled YAML specs keyed by domain name (falls back to bundled JSON)."""
    specs: Dict[str, Dict[str, Any]] = {}
    bundled_dir = openapi_dir / ".bundled"
    for domain in domain_configs:
        name = getattr(domain, "name", None) or (domain.get("name") if isinstance(domain, dict) else None)
        if not name:
            continue
        spec_path = getattr(domain, "spec_path", None) or (
            domain.get("spec_path") if isinstance(domain, dict) else None
        )
        bundled_path = getattr(domain, "bundled_path", None) or (
            domain.get("bundled_path") if isinstance(domain, dict) else None
        )
        yaml_path = openapi_dir / spec_path if spec_path else None
        json_path = bundled_dir / bundled_path if bundled_path else None
        if yaml_path and yaml_path.exists():
            specs[name] = _load_spec_file(yaml_path)
        elif json_path and json_path.exists():
            specs[name] = _load_spec_file(json_path)
    return specs


def collect_domain_route_excludes(domain_specs: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    excludes: Dict[str, List[str]] = {}
    for domain, spec in domain_specs.items():
        ext = get_api_server_extensions_config(spec)
        if not ext.get("enabled"):
            continue
        raw = ext.get("excludeGeneratedRoutes")
        if isinstance(raw, list) and raw:
            excludes[domain] = [str(r) for r in raw]
    return excludes


def collect_domains_with_extensions(domain_specs: Dict[str, Dict[str, Any]]) -> List[str]:
    enabled: List[str] = []
    for domain, spec in domain_specs.items():
        ext = get_api_server_extensions_config(spec)
        if ext.get("enabled"):
            enabled.append(domain)
    return sorted(enabled)


def aggregate_integration_events(domain_specs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for _domain, spec in domain_specs.items():
        for item in get_integration_events(spec):
            event_type = str(item.get("type", ""))
            if not event_type or event_type in seen:
                continue
            seen.add(event_type)
            entries.append(item)
    return entries


def collect_preserve_dirs(domain_specs: Dict[str, Dict[str, Any]]) -> List[str]:
    dirs: set[str] = set()
    for spec in domain_specs.values():
        for item in get_preserve_on_clean(spec):
            dirs.add(item)
    return sorted(dirs)
