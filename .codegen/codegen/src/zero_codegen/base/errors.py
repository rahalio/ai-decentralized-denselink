"""
Error classes for code generation
"""


class GenerationError(Exception):
    """Base error for code generation"""
    pass


class ConfigError(GenerationError):
    """Configuration error"""
    pass


class ValidationError(GenerationError):
    """Validation error"""
    pass


class OpenAPIError(GenerationError):
    """OpenAPI specification error"""
    pass
