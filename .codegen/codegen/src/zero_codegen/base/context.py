"""
Generation context - shared state across generators
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .config import Config, DomainConfig
from .logger import Logger


class GenerationContext:
    """Context shared across all generators"""

    def __init__(
        self,
        config: Config,
        domain: DomainConfig,
        logger: Logger,
        spec: Optional[Dict[str, Any]] = None,
        unbundled_spec: Optional[Dict[str, Any]] = None,
    ):
        self.config = config
        self.domain = domain
        self.logger = logger
        self.spec = spec
        self.unbundled_spec = unbundled_spec
        self.metadata: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set state value"""
        self.state[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.metadata[key] = value

    @property
    def domain_name(self) -> str:
        """Get domain name"""
        return self.domain.name

    @property
    def spec_path(self) -> Path:
        """Get OpenAPI spec path"""
        return self.config.paths.openapi_dir / self.domain.spec_path

    @property
    def bundled_path(self) -> Path:
        """Get bundled OpenAPI spec path"""
        return self.config.paths.bundled_dir / self.domain.bundled_path
