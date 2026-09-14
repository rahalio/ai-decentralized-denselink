"""
Repository Generator Configuration - Configurable settings for repository generation
"""

from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, field

# Repositories with manual DynamoDB implementations (not generated).
# Add port names here when a domain has hand-written DDB impls.
REPOS_WITH_MANUAL_DDB: Set[str] = set()

# Composite use case dependencies: domain -> operation_id -> list of refs.
# Refs are "repo_key.verb" (e.g. "organizations.create") or "repo_key" (e.g. "members").
# Used for two-phase init when x-use-case-constructor: composite.
COMPOSITE_USE_CASE_DEPS: Dict[str, Dict[str, List[str]]] = {}


@dataclass
class RepositoryConfig:
    """Configuration for repository generation"""

    # Status codes to check for successful responses
    success_status_codes: List[str] = field(default_factory=lambda: ["200", "201", "202"])

    # Status codes for create operations
    create_status_codes: List[str] = field(default_factory=lambda: ["201", "202"])

    # Status codes for update operations
    update_status_codes: List[str] = field(default_factory=lambda: ["200", "201", "202"])

    # Verbs that indicate create operations
    create_verbs: Set[str] = field(default_factory=lambda: {"create"})

    # Verbs that indicate update operations
    update_verbs: Set[str] = field(default_factory=lambda: {"update", "patch"})

    # Verbs that indicate delete operations
    delete_verbs: Set[str] = field(default_factory=lambda: {"delete"})

    # Verbs that indicate list operations
    list_verbs: Set[str] = field(default_factory=lambda: {"list"})

    # Verbs that indicate get operations
    get_verbs: Set[str] = field(default_factory=lambda: {"get"})

    # Type patterns that don't need imports
    builtin_type_patterns: Set[str] = field(default_factory=lambda: {
        "Record<string, never>",
        "PaginationParams"
    })

    # Default list params type when no query params found
    default_list_params_type: str = "Record<string, never>"

    # Default update request type pattern
    default_update_request_pattern: str = "Update{entity_name}Request"

    # Repository type determination rules
    # Format: (has_create, has_update, has_delete) -> repository_type
    repository_type_rules: Dict[tuple, str] = field(default_factory=lambda: {
        (True, True, True): "CrudRepository",
        (True, True, False): "CreateUpdateReadRepository",
        (True, False, True): "CreateDeleteReadRepository",
        (False, True, True): "UpdateDeleteReadRepository",
        (True, False, False): "CreateReadRepository",
        (False, True, False): "UpdateReadRepository",
        (False, False, True): "DeleteReadRepository",
        (False, False, False): "ReadRepository",
    })

    # Response schema suffixes to filter out
    response_schema_suffixes_to_filter: Set[str] = field(default_factory=lambda: {
        "Request",
        "Response",
        "Envelope"
    })

    # Content types to check for request bodies
    request_body_content_types: List[str] = field(default_factory=lambda: ["application/json"])

    def get_repository_type(self, has_create: bool, has_update: bool, has_delete: bool) -> str:
        """Get repository type based on operation flags"""
        key = (has_create, has_update, has_delete)
        return self.repository_type_rules.get(key, "ReadRepository")

    def is_builtin_type(self, type_name: str) -> bool:
        """Check if a type is a builtin type that doesn't need import"""
        return any(pattern in type_name for pattern in self.builtin_type_patterns)

    def should_filter_schema_name(self, schema_name: str) -> bool:
        """Check if a schema name should be filtered out"""
        return any(suffix in schema_name for suffix in self.response_schema_suffixes_to_filter)


# Default configuration instance
DEFAULT_CONFIG = RepositoryConfig()


# Domain-specific configurations can be added here
DOMAIN_CONFIGS: Dict[str, RepositoryConfig] = {
    # Example: "channel": RepositoryConfig(
    #     create_status_codes=["201", "202", "204"],
    #     ...
    # )
}


def get_repository_names_with_dynamodb(context: Any) -> Set[str]:
    """
    Return set of repository port names that have DynamoDB implementations.
    Centralized so dependencies and port adapter generators stay in sync.
    """
    from ....utils.openapi import extract_operations
    from ....generators.adapters.dynamodb_repository import DynamoDBRepositoryGenerator

    operations = extract_operations(context.spec)
    ddb_generator = DynamoDBRepositoryGenerator()
    repositories = ddb_generator._identify_repositories(operations, context)
    names = set(repositories.keys())
    names.update(REPOS_WITH_MANUAL_DDB)
    return names


def get_canonical_resource_for_operation(
    operation: Dict[str, Any],
    operation_id: str,
    domain_name: str,
    convention: Callable[[str, Optional[str]], str],
    path: Optional[str] = None,
) -> str:
    """
    Get canonical resource for operation (used for port dependency lookup).
    Aligns with entity-centric ports. Delegates to convention(operation_id, path).
    """
    return convention(operation_id, path)
