"""
Verb Mapping - Centralized, configurable mapping of API patterns to operation verbs

This module provides a centralized way to map:
- HTTP methods → verbs
- Operation ID patterns → verbs
- Response structures → verbs

Usage:
    from zero_codegen.utils.verb_mapping import VerbMapper

    verb = VerbMapper.get_verb(operation_id="runCompletion", http_method="post")
    # Returns: "create"
"""

from typing import Dict, Optional, List, Tuple
import re


class VerbMapper:
    """
    Centralized verb mapping system for API operations.

    Maps HTTP methods, operation IDs, and response patterns to standard verbs:
    - create: POST operations that create resources
    - list: GET operations that return collections
    - get: GET operations that return single resources
    - update: PUT/PATCH operations
    - delete: DELETE operations
    - run/execute: POST operations that execute actions (not create resources)
    """

    # HTTP method → verb mapping (primary mapping)
    HTTP_METHOD_TO_VERB: Dict[str, str] = {
        "post": "create",
        "put": "update",
        "patch": "update",
        "delete": "delete",
        "get": "get",  # Will be refined based on response structure
    }

    # Operation ID patterns → verb mapping (overrides HTTP method)
    # Patterns are checked in order, first match wins
    OPERATION_ID_PATTERNS: List[Tuple[str, str]] = [
        # List operations (GET that return collections)
        (r"^list[A-Z]", "list"),
        (r"^get[A-Z].*List", "list"),
        (r"^query[A-Z]", "list"),
        (r"^search[A-Z]", "list"),
        (r"^find[A-Z].*List", "list"),

        # Create operations (POST that create resources)
        (r"^create[A-Z]", "create"),
        (r"^post[A-Z]", "create"),
        (r"^add[A-Z]", "create"),
        (r"^new[A-Z]", "create"),
        (r"^invite[A-Z]", "create"),
        (r"^register[A-Z]", "create"),
        (r"^enroll[A-Z]", "create"),

        # Update operations (including refresh which updates existing resources)
        (r"^update[A-Z]", "update"),
        (r"^put[A-Z]", "update"),
        (r"^patch[A-Z]", "update"),
        (r"^edit[A-Z]", "update"),
        (r"^modify[A-Z]", "update"),
        (r"^set[A-Z]", "update"),
        (r"^refresh[A-Z]", "update"),  # Refresh updates existing resources

        # Delete operations
        (r"^delete[A-Z]", "delete"),
        (r"^remove[A-Z]", "delete"),
        (r"^drop[A-Z]", "delete"),

        # Get-by-id must beat generic get* (avoids getCompanyById colliding with getCompany → "get")
        (r"^get[A-Z].*ById$", "getById"),
        (r"^fetch[A-Z].*ById$", "getById"),
        (r"^retrieve[A-Z].*ById$", "getById"),

        # Get operations (single resource)
        (r"^get[A-Z]", "get"),
        (r"^fetch[A-Z]", "get"),
        (r"^retrieve[A-Z]", "get"),
        (r"^find[A-Z]", "get"),
        (r"^validate[A-Z]", "get"),  # Validate operations are GET that return DTOs

        # Action/Execute operations (POST that don't create resources)
        (r"^run[A-Z]", "create"),  # Treat as create for now (returns result)
        (r"^execute[A-Z]", "create"),
        (r"^trigger[A-Z]", "create"),
        (r"^invoke[A-Z]", "create"),
        (r"^send[A-Z]", "create"),
        (r"^submit[A-Z]", "create"),
        (r"^process[A-Z]", "create"),
        (r"^evaluate[A-Z]", "create"),
        (r"^start[A-Z]", "create"),
        (r"^stop[A-Z]", "create"),
        (r"^complete[A-Z]", "create"),  # Complete operations create/finalize resources (e.g., completeProviderConnection)
        (r"^cancel[A-Z]", "update"),  # Cancel operations update existing resources (subscription, job)
        (r"^enable[A-Z]", "update"),
        (r"^disable[A-Z]", "update"),
        (r"^test[A-Z]", "get"),   # Test operations read then return success
        (r"^export[A-Z]", "list"),  # Export operations query/list then wrap
        (r"^approve[A-Z]", "create"),
        (r"^reject[A-Z]", "create"),
    ]

    @staticmethod
    def get_verb(
        operation_id: str,
        http_method: Optional[str] = None,
        response_has_items: bool = False
    ) -> str:
        """
        Get verb for an operation based on operation ID, HTTP method, and response structure.

        Priority:
        1. Operation ID pattern matching
        2. HTTP method mapping
        3. Response structure refinement (for GET operations)

        Args:
            operation_id: The operation ID from OpenAPI spec
            http_method: HTTP method (lowercase: "get", "post", etc.)
            response_has_items: Whether response has data.items structure (list-like)

        Returns:
            Verb string: "create", "list", "get", "update", "delete"
        """
        # 1. Check operation ID patterns first (highest priority)
        # Use IGNORECASE so "CreateAuditLogExport" matches ^create[A-Z]
        for pattern, verb in VerbMapper.OPERATION_ID_PATTERNS:
            if re.match(pattern, operation_id, re.IGNORECASE):
                # Refine list operations based on response structure
                if verb == "get" and response_has_items:
                    return "list"
                return verb

        # 2. Fall back to HTTP method mapping
        if http_method:
            verb = VerbMapper.HTTP_METHOD_TO_VERB.get(http_method.lower(), "get")

            # Refine GET operations based on response structure
            if verb == "get" and response_has_items:
                return "list"

            return verb

        # 3. Default fallback
        return "get"

    @staticmethod
    def add_operation_pattern(pattern: str, verb: str) -> None:
        """
        Add a custom operation ID pattern → verb mapping.

        Patterns are checked in order, so add more specific patterns first.

        Args:
            pattern: Regex pattern to match operation IDs
            verb: Verb to map to ("create", "list", "get", "update", "delete")

        Example:
            VerbMapper.add_operation_pattern(r"^customAction[A-Z]", "create")
        """
        VerbMapper.OPERATION_ID_PATTERNS.insert(0, (pattern, verb))

    @staticmethod
    def add_http_method_mapping(http_method: str, verb: str) -> None:
        """
        Add or override HTTP method → verb mapping.

        Args:
            http_method: HTTP method (lowercase: "get", "post", etc.)
            verb: Verb to map to ("create", "list", "get", "update", "delete")

        Example:
            VerbMapper.add_http_method_mapping("head", "get")
        """
        VerbMapper.HTTP_METHOD_TO_VERB[http_method.lower()] = verb
