"""Resolve npm package scope from codegen Config (default @ddd)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zero_codegen.base.config import Config


DEFAULT_SCOPE = "@ddd"


def get_package_scope(config: "Config | None" = None) -> str:
    if config is None:
        return DEFAULT_SCOPE
    scope = getattr(config, "package_scope", None) or DEFAULT_SCOPE
    return scope.rstrip("/")


def pkg(name: str, config: "Config | None" = None) -> str:
    """Return scoped package name, e.g. pkg('core') -> '@ddd/core'."""
    return f"{get_package_scope(config)}/{name.lstrip('/')}"
