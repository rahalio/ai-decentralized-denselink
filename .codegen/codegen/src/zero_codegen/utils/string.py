"""
String manipulation utilities
"""

import re
from typing import Optional
import inflection


def camel_case(text: str) -> str:
    """Convert text to camelCase"""
    # Handle kebab-case, snake_case first (before checking if already camelCase)
    if "-" in text or "_" in text or " " in text:
        text = re.sub(r"[-_\s]+", " ", text)
        words = text.split()
        if not words:
            return ""
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])

    # If already camelCase (starts with lowercase, no separators), return as-is
    if text and text[0].islower() and not "_" in text and not "-" in text:
        return text

    # Handle PascalCase (e.g., "ChainAdapter" -> "chainAdapter")
    if text and text[0].isupper() and not "_" in text and not "-" in text:
        # Split on capital letters
        words = re.findall(r'[A-Z][a-z]*', text)
        if words:
            return words[0].lower() + "".join(words[1:])

    # Fallback: treat as single word
    return text.lower() if text else ""


def pascal_case(text: str) -> str:
    """Convert text to PascalCase"""
    # If already PascalCase (starts with uppercase, no separators), return as-is
    if text and text[0].isupper() and not "_" in text and not "-" in text and not " " in text:
        return text

    # Handle camelCase - split on capital letters
    if text and text[0].islower():
        # Split camelCase into words
        words = re.findall(r'[a-z]+|[A-Z][a-z]*', text)
        if words:
            return "".join(word.capitalize() for word in words)

    # Handle snake_case, kebab-case
    text = re.sub(r"[-_\s]+", " ", text)
    words = text.split()
    if not words:
        return ""
    return "".join(word.capitalize() for word in words)


def kebab_case(text: str) -> str:
    """Convert text to kebab-case"""
    # Handle camelCase, PascalCase, snake_case
    text = re.sub(r"([a-z])([A-Z])", r"\1-\2", text)
    text = re.sub(r"[-_\s]+", "-", text)
    return text.lower()


def snake_case(text: str) -> str:
    """Convert text to snake_case"""
    # Handle camelCase, PascalCase, kebab-case
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[-_\s]+", "_", text)
    return text.lower()


def pluralize(text: str) -> str:
    """Pluralize a word"""
    return inflection.pluralize(text)


def pluralize_resource_name(resource_name: str) -> str:
    """
    Pluralize resource name with edge case handling

    Edge cases that are already plural or shouldn't pluralize:
    - status, liveness, readiness, class, case
    """
    # Edge cases that are already plural or shouldn't pluralize
    plural_edge_cases = {
        "status", "liveness", "readiness", "class", "case"
    }

    # Check if entire resource matches edge case
    lower_resource = resource_name.lower()
    if lower_resource in plural_edge_cases:
        return resource_name

    # For compound words (e.g., "shareholder-registry"), check the last part
    parts = lower_resource.split("-")
    if len(parts) > 1:
        last_part = parts[-1]
        if last_part in plural_edge_cases:
            return resource_name  # Don't pluralize if last part is edge case

    # Use inflection for normal pluralization
    return inflection.pluralize(resource_name)


def singularize(text: str) -> str:
    """Singularize a word"""
    return inflection.singularize(text)


# Action prefixes that operate on an underlying resource (e.g. CancelSubscription -> Subscription)
# Used to normalize operation-scoped resources into the base entity for repository grouping.
_ACTION_PREFIXES_FOR_RESOURCE_EXTRACT = (
    "Cancel", "Post", "Create", "Update", "Delete", "Get", "List",
    "Enable", "Disable", "Pause", "Resume", "Archive", "Unarchive",
    "Approve", "Reject", "Complete", "Start", "Stop", "Rotate", "Refresh",
    "Provision", "Clone", "Publish", "Unpublish", "Test", "Validate", "Retry",
    "Execute", "Compose", "Detect", "Resolve",
    "Add", "Remove", "Replace", "Restore", "Assign", "Transition",
    "Launch", "Generate", "Optimize", "Reconnect", "Check", "Handle",
)


def extract_resource_from_operation_id(operation_id: str) -> str:
    """
    Extract resource name from operation ID

    Examples:
        createMarket -> Market
        updateOrder -> Order
        getWalletById -> Wallet
        listChains -> Chain
        CancelSubscription -> Subscription
        PostSubscription -> Subscription
    """
    # Use VerbMapper to get the verb, then extract resource by removing verb prefix
    from zero_codegen.utils.verb_mapping import VerbMapper
    
    # Get verb using VerbMapper (without HTTP method, so it uses pattern matching)
    verb = VerbMapper.get_verb(operation_id)
    
    # Remove verb prefix from operation_id (case-insensitive)
    operation_id_lower = operation_id.lower()
    verb_lower = verb.lower()
    
    if operation_id_lower.startswith(verb_lower):
        remaining = operation_id[len(verb):]
        if remaining:
            # Capitalize first letter
            return remaining[0].upper() + remaining[1:]
    
    # Strip known action prefixes (verb may differ from actual prefix, e.g. Cancel->update)
    for prefix in _ACTION_PREFIXES_FOR_RESOURCE_EXTRACT:
        if operation_id.startswith(prefix) and len(operation_id) > len(prefix):
            remaining = operation_id[len(prefix):]
            if remaining:
                return remaining[0].upper() + remaining[1:]
    
    # If verb extraction didn't work, try extracting from camelCase pattern
    # Try to extract resource (usually second word in camelCase)
    match = re.match(r"^[a-z]+([A-Z][a-zA-Z]+)", operation_id)
    if match:
        return match.group(1)

    # If no verb found, assume first word is verb
    # Try to extract resource (usually second word in camelCase)
    match = re.match(r"^[A-Z][a-z]+([A-Z][a-zA-Z]+)", operation_id)
    if match:
        return match.group(1)

    # Fallback: return as-is capitalized
    return pascal_case(operation_id)


def extract_verb_from_operation_id(operation_id: str, http_method: Optional[str] = None, response_has_items: bool = False) -> str:
    """
    Extract HTTP verb from operation ID using centralized VerbMapper.

    This function now delegates to VerbMapper for consistent verb extraction
    across all generators. The VerbMapper supports:
    - HTTP method → verb mapping
    - Operation ID pattern matching
    - Response structure refinement

    Args:
        operation_id: The operation ID from OpenAPI spec
        http_method: Optional HTTP method (lowercase: "get", "post", etc.)
        response_has_items: Whether response has data.items structure (list-like)

    Returns:
        Verb string: "create", "list", "get", "update", "delete"
    """
    from zero_codegen.utils.verb_mapping import VerbMapper
    return VerbMapper.get_verb(operation_id, http_method, response_has_items)


def build_type_name(resource: str, suffix: str = "") -> str:
    """Build a type name from resource and suffix"""
    resource_pascal = pascal_case(resource)
    if suffix:
        suffix_pascal = pascal_case(suffix)
        return f"{resource_pascal}{suffix_pascal}"
    return resource_pascal


def build_function_name(resource: str, verb: str) -> str:
    """Build a function name from resource and verb"""
    resource_camel = camel_case(resource)
    verb_lower = verb.lower()
    return f"{verb_lower}{resource_camel[0].upper()}{resource_camel[1:]}" if resource_camel else verb_lower


def dto_input_type_name(operation_id: str) -> str:
    """
    Canonical DTO input type name for an operation. Used by DTO, port, and use case generators.
    Examples: listProducts -> ListProductsInput, createProduct -> CreateProductInput
    """
    return f"{pascal_case(operation_id)}Input"


def dto_output_type_name(operation_id: str) -> str:
    """
    Canonical DTO output type name for an operation. Used by DTO, port, and use case generators.
    Examples: listProducts -> ListProductsOutput, createProduct -> CreateProductOutput
    """
    return f"{pascal_case(operation_id)}Output"
