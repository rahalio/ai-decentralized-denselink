"""
Shared API Server domain discovery.

Rescan platform/api-server/src/domains for directories that have both
routes/index.ts and dependencies/{domain}-ddd.dependencies.ts.
"""

from pathlib import Path
from typing import List


def discover_api_server_domains(domains_dir: Path) -> List[str]:
    """
    Rescan api-server/src/domains for domain directories that were generated.
    A domain is included only if it has both routes/index.ts and
    dependencies/{domain}-ddd.dependencies.ts.
    """
    domains: List[str] = []
    if not domains_dir.is_dir():
        return domains
    for path in sorted(domains_dir.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        domain = path.name
        routes_index = path / "routes" / "index.ts"
        deps_file = path / "dependencies" / f"{domain}-ddd.dependencies.ts"
        if routes_index.is_file() and deps_file.is_file():
            domains.append(domain)
    return sorted(domains)
