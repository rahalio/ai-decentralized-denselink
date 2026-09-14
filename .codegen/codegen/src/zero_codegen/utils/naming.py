"""
Naming utilities for consistent file and directory naming across all generators.

Grouping is derived from path resource when available (see OPERATION_ID_NAMING_SCHEMA.md).
No domain-specific or qualifier-based hardcoding.
"""

import re
from typing import Tuple, Optional, List
from zero_codegen.utils.string import (
    kebab_case,
    camel_case,
    pascal_case,
    pluralize_resource_name,
    singularize,
    extract_resource_from_operation_id,
    extract_verb_from_operation_id,
)

# Scope prefixes stripped for grouping (longest match first). Configurable later.
DEFAULT_SCOPE_PREFIXES: List[str] = [
    "OrgActivity",
    "OrgAi",
    "PlatformAi",
    "OrgConnectivity",
    "OrgCompliance",
    "OrgContent",
    "OrgConversation",
    "OrgEngagement",
    "OrgEntitlement",
    "OrgIdentity",
    "OrgKnowledge",
    "OrgMarketing",
    "OrgMetrics",
    "OrgNotification",
    "OrgObservability",
    "OrgOperation",
    "OrgPlanning",
    "OrgProduct",
    "OrgPulse",
    "OrgSales",
    "PlatformSocial",
    "OrgSocial",
    "Org",
    "Platform",
]

# Generic path segments that indicate a sub-resource: use parent + segment for path resource
# e.g. /gateways/{id}/models -> GatewayModels not just Models
GENERIC_COLLECTION_SEGMENTS = frozenset({"models", "items", "list", "entries", "results"})


class NamingConvention:
    """
    Centralized naming convention utilities for consistent file naming
    across all generators (handlers, repositories, etc.)
    """

    @staticmethod
    def handler_directory(resource: str) -> str:
        """
        Get handler directory name for a resource (pluralized, kebab-cased)

        Examples:
            Chain -> chains
            ChainAdapter -> chain-adapters
            WalletBalance -> wallet-balances
        """
        plural = pluralize_resource_name(resource)
        return kebab_case(plural)

    @staticmethod
    def handler_filename(operation_id: str) -> Tuple[str, str]:
        """
        Get handler filename for an operation

        Returns:
            Tuple of (filename_without_ext, resource_name)

        Examples:
            listChains -> (list-chains, chains)
            createChain -> (create-chain, chain)
            getChainAdapter -> (get-chain-adapter, chain-adapter)
        """
        verb = extract_verb_from_operation_id(operation_id)
        resource = extract_resource_from_operation_id(operation_id)

        # For list operations, keep plural form in filename
        # For other operations, use singular form
        if verb == "list":
            filename_resource = resource  # Keep plural (e.g., "Chains")
        else:
            # Use singular for non-list operations
            filename_resource = resource.rstrip("s") if resource.endswith("s") and len(resource) > 1 else resource

        filename = f"{kebab_case(verb)}-{kebab_case(filename_resource)}"
        return filename, kebab_case(filename_resource)

    @staticmethod
    def repository_filename(resource: str) -> str:
        """
        Get repository filename for a resource (kebab-case, singular)

        Examples:
            Chain -> chain.repository.ts
            ChainAdapter -> chain-adapter.repository.ts
            WalletBalance -> wallet-balance.repository.ts
            SettlementStatus -> settlement-status.repository.ts
        """
        # Use proper singularization for repository files
        # Don't use rstrip("s") as it removes ALL trailing 's' characters
        # (e.g., "SettlementStatus" -> "SettlementStatu" which is wrong)
        if resource.lower().endswith('s') and len(resource) > 1:
            # Use inflection library for proper singularization
            singular = singularize(resource)
            # Preserve PascalCase if resource was PascalCase
            if resource[0].isupper():
                singular = singular[0].upper() + singular[1:] if len(singular) > 1 else singular.upper()
        else:
            singular = resource

        return f"{kebab_case(singular)}.repository.ts"

    @staticmethod
    def handler_function_name(operation_id: str) -> str:
        """
        Get handler function name (camelCase)

        Examples:
            listChains -> listChains
            createChain -> createChain
            getChainAdapter -> getChainAdapter
        """
        return camel_case(operation_id)

    @staticmethod
    def repository_type_name(resource: str) -> str:
        """
        Get repository type name (PascalCase)

        Examples:
            Chain -> ChainRepository
            ChainAdapter -> ChainAdapterRepository
        """
        return f"{pascal_case(resource)}Repository"

    @staticmethod
    def resource_from_path(path: str) -> str:
        """
        Derive grouping resource from path (source of truth per OPERATION_ID_NAMING_SCHEMA.md).

        - Strip path parameters {param}.
        - Last non-param segment = path resource; if it's a generic collection (models, items, ...),
          use previous segment + segment (e.g. gateways/models -> GatewayModel).
        - Convert to PascalCase and singularize for grouping key.
        """
        if not path or not path.strip():
            return ""
        segments = [s for s in path.strip().split("/") if s and not re.match(r"^\{.+\}$", s)]
        if not segments:
            return ""
        last_seg = segments[-1]
        last_seg_lower = last_seg.lower()
        # Only use parent+segment when last segment is exactly a generic collection word (e.g. "models"), not "gateway-models"
        if last_seg_lower in GENERIC_COLLECTION_SEGMENTS and len(segments) >= 2:
            prev_seg = segments[-2]
            prev_pascal = pascal_case(prev_seg.replace("-", " "))
            last_pascal = pascal_case(last_seg.replace("-", " "))
            # e.g. gateways + models -> GatewayModels -> GatewayModel
            combined = singularize(prev_pascal) + last_pascal
            combined = combined[0].upper() + combined[1:] if combined else ""
            s = singularize(combined)
            return s[0].upper() + s[1:] if len(s) > 1 else (s.upper() if s else combined)
        raw = pascal_case(last_seg.replace("-", " "))
        # Always singularize so irregular plurals work (People→Person).
        # Previously only words ending in "s" were singularized, which left
        # "People" as the grouping key and broke Person x-dynamodb lookup.
        s = singularize(raw)
        if not s:
            return raw
        return s[0].upper() + s[1:] if len(s) > 1 else s.upper()

    @staticmethod
    def resource_for_grouping(operation_id: str, path: Optional[str] = None) -> str:
        """
        Get resource name for grouping operations (singular).

        When path is provided, uses path as source of truth (resource_from_path).
        Otherwise derives from operation_id only: strip verb, strip scope prefix, singularize.
        No qualifier suffix/prefix or domain-specific hardcoding.
        """
        if path:
            return NamingConvention.resource_from_path(path)
        verb = extract_verb_from_operation_id(operation_id)
        resource = extract_resource_from_operation_id(operation_id)
        if not resource:
            return ""
        for prefix in DEFAULT_SCOPE_PREFIXES:
            if resource.startswith(prefix) and len(resource) > len(prefix):
                rest = resource[len(prefix):]
                if rest:
                    resource = rest
                    break
        if resource.lower().endswith("s") and len(resource) > 1:
            singular = singularize(resource)
            if resource[0].isupper():
                return singular[0].upper() + singular[1:] if len(singular) > 1 else singular.upper()
            return singular
        return resource
