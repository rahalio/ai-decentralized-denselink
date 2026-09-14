"""
Base infrastructure for unified codegen
"""

from .config import Config, DomainConfig, LogLevel
from .context import GenerationContext
from .logger import Logger, create_logger
from .generator import BaseGenerator, GenerateResult
from .errors import GenerationError

__all__ = [
    "Config",
    "DomainConfig",
    "LogLevel",
    "GenerationContext",
    "Logger",
    "create_logger",
    "BaseGenerator",
    "GenerateResult",
    "GenerationError",
]
