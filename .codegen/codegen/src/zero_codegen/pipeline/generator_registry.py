"""
Generator registry for unified codegen
"""

from typing import Dict, Type, Optional
from ..base.generator import BaseGenerator
from ..base.logger import Logger


class GeneratorRegistry:
    """Registry for all generators"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self._generators: Dict[str, Type[BaseGenerator]] = {}
    
    def register(self, name: str, generator_class: Type[BaseGenerator]) -> None:
        """Register a generator"""
        self._generators[name] = generator_class
        self.logger.debug(f"Registered generator: {name}")
    
    def get(self, name: str) -> Optional[Type[BaseGenerator]]:
        """Get a generator by name"""
        return self._generators.get(name)
    
    def get_all(self) -> Dict[str, Type[BaseGenerator]]:
        """Get all registered generators"""
        return self._generators.copy()
