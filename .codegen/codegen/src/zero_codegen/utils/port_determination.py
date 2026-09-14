"""
Port determination utilities - derive port names from OpenAPI spec

This module provides utilities to determine port names and dependencies
from OpenAPI operations without hardcoding project-specific names.
"""

from typing import Dict, Any, List, Optional
from .naming import NamingConvention
from .string import pascal_case, camel_case, extract_verb_from_operation_id


class PortDetermination:
    """
    Utilities for determining port names from OpenAPI operations.
    All logic derives from the OpenAPI spec, not hardcoded project names.
    """
    
    @staticmethod
    def determine_port_name(
        operation_id: str,
        operation: Dict[str, Any],
        context: Optional[Any] = None,
        path: Optional[str] = None,
    ) -> str:
        """
        Determine port name from operation based on OpenAPI spec.
        
        Priority:
        1. Use OpenAPI tags to determine port type (if tag suggests a port type)
        2. Derive from operation characteristics (operation_id patterns, request/response schemas)
        3. Fall back to resource-based repository naming (path-based when path provided)
        
        Args:
            operation_id: Operation ID from OpenAPI
            operation: Full operation object from OpenAPI
            context: Optional generation context
            path: Optional path template for path-based grouping (see OPERATION_ID_NAMING_SCHEMA.md)
        
        Returns:
            Port name (e.g., "ContentPublisher", "ProviderConnectionClient", "ProviderAccountRepository")
        """
        # Derive port name from operationId and path semantics (see OPERATION_ID_NAMING_SPEC.md).
        # Action ports (`x-repository: none`) keep path-based names (ExportRepository, etc.)
        # to match existing adapters. Aggregate attach-by-x-repository is a separate rename.
        operation_id_lower = operation_id.lower()
        resource = NamingConvention.resource_for_grouping(operation_id, path)
        resource_pascal = pascal_case(resource)
        
        # Check for OpenAPI tags first (if available)
        tags = operation.get("tags", [])
        port_type_suffix = None
        
        # Check tags for port type hints (e.g., "publisher", "client", "repository")
        if tags:
            for tag in tags:
                tag_lower = tag.lower()
                # Common port type suffixes in tags
                if tag_lower.endswith("publisher") or tag_lower == "publisher":
                    port_type_suffix = "Publisher"
                    break
                elif tag_lower.endswith("client") or tag_lower == "client" or "oauth" in tag_lower or "connect" in tag_lower:
                    port_type_suffix = "Client"
                    break
                elif tag_lower.endswith("refresher") or tag_lower == "refresher" or ("refresh" in tag_lower and "token" in tag_lower):
                    port_type_suffix = "Refresher"
                    break
                elif tag_lower.endswith("repository") or tag_lower == "repository" or tag_lower == "repo":
                    port_type_suffix = "Repository"
                    break
        
        # If no port type from tags, derive from operation characteristics
        if not port_type_suffix:
            # Publishing operations → {Resource}Publisher
            if "publish" in operation_id_lower:
                port_type_suffix = "Publisher"
            # OAuth/connection operations → {Resource}Client (derived from resource)
            elif any(pattern in operation_id_lower for pattern in ["oauth", "connect", "callback"]):
                port_type_suffix = "Client"
            # Token refresh operations → {Resource}Refresher (derived from resource)
            elif "refresh" in operation_id_lower and "token" in operation_id_lower:
                port_type_suffix = "Refresher"
            # Default: use resource-based repository naming
            else:
                port_type_suffix = "Repository"
        
        return f"{resource_pascal}{port_type_suffix}"
    
    @staticmethod
    def determine_adapter_name(port_name: str) -> str:
        """
        Determine adapter class name from port name.
        
        Pattern: {PortName}Adapter
        
        Args:
            port_name: Port interface name
        
        Returns:
            Adapter class name
        """
        # Simple pattern: add "Adapter" suffix
        # Special cases can be handled here if needed, but should be generic
        return f"{port_name}Adapter"
    
    @staticmethod
    def determine_use_case_dependencies(
        operation_id: str,
        operation: Dict[str, Any],
        resource: str,
        verb: str,
        identified_ports: Dict[str, str]
    ) -> List[str]:
        """
        Determine port dependencies needed for a use case based on operation characteristics.
        
        This derives dependencies from the operation itself and the identified ports,
        using OpenAPI tags and operation patterns, not hardcoded project-specific names.
        
        Args:
            operation_id: Operation ID from OpenAPI
            operation: Full operation object from OpenAPI
            resource: Resource name derived from operation
            verb: Verb extracted from operation
            identified_ports: Dict of port_name -> adapter_name for all identified ports
        
        Returns:
            List of port names that this use case depends on
        """
        dependencies = []
        operation_id_lower = operation_id.lower()
        
        # Get operation tags to understand relationships
        tags = operation.get("tags", [])
        
        # Most CRUD operations need a repository for the resource
        if any(v in operation_id_lower for v in ["get", "list", "create", "update", "patch", "delete", "validate"]):
            repo_port_name = f"{pascal_case(resource)}Repository"
            # Only add if this port was actually identified
            if repo_port_name in identified_ports and repo_port_name not in dependencies:
                dependencies.append(repo_port_name)

        # Operation-scoped repository operations (export, enable, disable, test, cancel, etc.)
        # also need their repository port when it exists in identified_ports
        repo_port_name = f"{pascal_case(resource)}Repository"
        if repo_port_name in identified_ports and repo_port_name not in dependencies:
            dependencies.append(repo_port_name)
        
        # Find ports by suffix pattern (generic, not hardcoded to specific names)
        # Publishing operations need a publisher port; prefer the one matching this operation's resource
        if "publish" in operation_id_lower:
            resource_pascal = pascal_case(resource)
            publisher_port = PortDetermination._find_port_by_resource_and_suffix(identified_ports, resource_pascal, "Publisher")
            if not publisher_port:
                publisher_port = PortDetermination._find_port_by_suffix(identified_ports, "Publisher")
            if publisher_port:
                dependencies.append(publisher_port)
            
            # Check if operation needs a related repository (e.g., for account lookups)
            # Use OpenAPI tags or operation patterns to find related resources
            related_repo = PortDetermination._find_related_repository(operation, identified_ports, resource)
            if related_repo and related_repo not in dependencies:
                dependencies.append(related_repo)
        
        # OAuth/connection operations need a client port
        if "oauth" in operation_id_lower or "connect" in operation_id_lower:
            # Find client port matching the resource (e.g., ProviderConnectionImprovedClient for ProviderConnectionImproved resource)
            resource_pascal = pascal_case(resource)
            client_port = PortDetermination._find_port_by_resource_and_suffix(identified_ports, resource_pascal, "Client")
            if not client_port:
                # Fallback: find any client port by suffix pattern
                client_port = PortDetermination._find_port_by_suffix(identified_ports, "Client")
            if client_port:
                dependencies.append(client_port)
            
            # Check if operation needs a related repository for account management
            if "complete" in operation_id_lower or "start" in operation_id_lower:
                related_repo = PortDetermination._find_related_repository(operation, identified_ports, resource)
                if related_repo and related_repo not in dependencies:
                    dependencies.append(related_repo)
        
        # Token refresh operations need a refresher port
        if "refresh" in operation_id_lower and "token" in operation_id_lower:
            # Find refresher port by suffix pattern
            refresher_port = PortDetermination._find_port_by_suffix(identified_ports, "Refresher")
            if refresher_port:
                dependencies.append(refresher_port)
            
            # Check if operation needs a related repository
            related_repo = PortDetermination._find_related_repository(operation, identified_ports, resource)
            if related_repo and related_repo not in dependencies:
                dependencies.append(related_repo)
        
        return dependencies
    
    @staticmethod
    def _find_port_by_suffix(identified_ports: Dict[str, str], suffix: str) -> Optional[str]:
        """Find a port by suffix pattern (generic helper)"""
        for port_name in identified_ports.keys():
            if port_name.endswith(suffix):
                return port_name
        return None
    
    @staticmethod
    def _find_port_by_resource_and_suffix(identified_ports: Dict[str, str], resource_pascal: str, suffix: str) -> Optional[str]:
        """Find a port matching a specific resource and suffix (e.g., ProviderConnectionImprovedClient)"""
        for port_name in identified_ports.keys():
            if port_name.startswith(resource_pascal) and port_name.endswith(suffix):
                return port_name
        return None
    
    @staticmethod
    def _find_related_repository(
        operation: Dict[str, Any],
        identified_ports: Dict[str, str],
        primary_resource: str
    ) -> Optional[str]:
        """
        Find a related repository port based on operation characteristics.
        
        Uses OpenAPI tags, request body schemas, or operation patterns to find
        related resources that might need repository access.
        """
        # Check tags for related resource hints
        tags = operation.get("tags", [])
        for tag in tags:
            tag_lower = tag.lower()
            # Look for tags that suggest a related resource (e.g., "account", "user")
            # Try to find a repository port for that resource
            for port_name in identified_ports.keys():
                if port_name.endswith("Repository"):
                    # Extract resource from port name
                    resource_from_port = port_name.replace("Repository", "")
                    # Check if tag matches resource (case-insensitive)
                    if tag_lower in resource_from_port.lower() or resource_from_port.lower() in tag_lower:
                        return port_name
        
        # Check request body for related resource references
        request_body = operation.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            schema_ref = json_content.get("schema", {}).get("$ref", "")
            if schema_ref:
                # Extract schema name from ref
                schema_name = schema_ref.split("/")[-1] if "/" in schema_ref else ""
                # Try to find repository for this schema's resource
                if schema_name:
                    # Extract resource from schema name (remove common suffixes)
                    resource_candidate = schema_name.replace("Request", "").replace("Input", "").replace("Params", "")
                    repo_candidate = f"{pascal_case(resource_candidate)}Repository"
                    if repo_candidate in identified_ports:
                        return repo_candidate
        
        # Fallback: return None if no related repository found
        return None
    
    # Verb prefixes that may appear in port names when one port per operation was generated.
    # Normalizing removes them so we get one port per resource (matches adapters package exports).
    _RESOURCE_SCOPED_STRIP_PREFIXES = (
        "Create", "List", "Get", "Update", "Delete", "Cancel", "Retry", "Run",
        "Start", "Complete", "Refresh", "Handle", "Check", "Test", "Reconnect",
        "Clone", "Publish", "Unpublish", "Enable", "Disable", "Rotate",
        "Validate", "Acknowledge", "Archive", "Unarchive", "Pause", "Resume",
        "Mark", "Dismiss", "Export",
    )

    # Port-type-only suffixes. If stripping a verb prefix leaves only one of these,
    # do not strip (otherwise we get port "Repository" and filename "-repository.ddb.ts").
    _PORT_TYPE_SUFFIXES = ("Repository", "Refresher", "Client", "Publisher")

    @staticmethod
    def normalize_port_name_to_resource_scoped(port_name: str) -> str:
        """
        Normalize port name to resource-scoped form (one port per resource, not per operation).

        The adapters package exports one Adapter per port (e.g. ChannelAccountRepositoryAdapter),
        not per operation (e.g. CreateChannelAccountRepositoryAdapter). This strips leading
        verb prefixes so "CreateChannelAccountRepository" -> "ChannelAccountRepository".
        Does not strip if the remainder would be only a port-type suffix (e.g. RefreshRepository
        stays RefreshRepository so we get refresh-repository.ddb.ts, not -repository.ddb.ts).

        Args:
            port_name: Port name that may be operation-scoped (e.g. CreateChannelAccountRepository)

        Returns:
            Resource-scoped port name (e.g. ChannelAccountRepository)
        """
        for prefix in PortDetermination._RESOURCE_SCOPED_STRIP_PREFIXES:
            if port_name.startswith(prefix) and len(port_name) > len(prefix):
                rest = port_name[len(prefix):]
                # Only strip if the rest looks like a resource name (e.g. "ChannelAccountRepository")
                if rest and rest[0].isupper():
                    # Do not strip if remainder is only a port-type suffix (e.g. "Repository")
                    if rest in PortDetermination._PORT_TYPE_SUFFIXES:
                        return port_name
                    return PortDetermination.normalize_port_name_to_resource_scoped(rest)
        return port_name

    # JavaScript/TypeScript reserved words that cannot be used as identifiers.
    # If derive_variable_name would return one of these, we append a safe suffix.
    _RESERVED_IDENTIFIERS = frozenset({
        "export", "default", "class", "function", "return", "import", "delete",
        "new", "void", "typeof", "in", "instanceof", "var", "let", "const",
        "if", "else", "switch", "case", "break", "continue", "for", "while",
        "do", "try", "catch", "finally", "throw", "yield", "await", "async",
        "true", "false", "null", "undefined", "this", "super", "extends",
        "implements", "interface", "type", "enum", "package", "protected",
        "private", "public", "static", "abstract", "constructor",
    })

    @staticmethod
    def derive_variable_name(port_name: str) -> str:
        """
        Derive a variable name from a port name generically.
        
        Removes common port type suffixes and converts to camelCase.
        If the result is a JS/TS reserved word (e.g. "export"), appends a safe
        suffix (e.g. "Repo") so the identifier is valid.
        
        Args:
            port_name: Port interface name (e.g., "ContentPublisher", "ExportRepository")
        
        Returns:
            Variable name in camelCase (e.g., "contentPublisher", "exportRepo")
        
        Examples:
            "ContentPublisher" -> "contentPublisher"
            "ProviderAccountRepository" -> "providerAccountRepository"
            "ExportRepository" -> "exportRepo" (export is reserved)
        """
        # Common port type suffixes to remove (in order of specificity)
        suffixes = ["Repository", "Publisher", "Client", "Refresher", "Adapter"]
        stripped_suffix = ""
        base_name = port_name
        for suffix in suffixes:
            if port_name.endswith(suffix):
                base_name = port_name[:-len(suffix)]
                stripped_suffix = suffix
                break

        name = camel_case(base_name)
        if name in PortDetermination._RESERVED_IDENTIFIERS:
            # Append a short safe suffix based on port type so identifier is valid
            if stripped_suffix == "Repository":
                return name + "Repo"
            if stripped_suffix == "Publisher":
                return name + "Publisher"
            if stripped_suffix == "Client":
                return name + "Client"
            if stripped_suffix == "Refresher":
                return name + "Refresher"
            return name + "Port"
        return name
