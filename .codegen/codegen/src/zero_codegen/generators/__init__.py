"""
Generators for unified codegen - DDD aligned

Per FINAL_ARCHITECTURE.md:
- Handlers should NOT be in services layer
- Handlers belong in api-server as thin adapters (or routes call use cases directly)
"""

# Core generators (domain layer)
from .core.entity import EntityGenerator
from .core.types import TypesGenerator
from .core.repository import RepositoryGenerator

# Services generators (application layer)
from .services.usecase import UseCaseGenerator
from .services.port import PortGenerator
from .services.dto import DTOGenerator
from .services.policy import PolicyGenerator
from .services.error import ErrorGenerator
from .services.services_domain_index import ServicesDomainIndexGenerator
from .services.services_main_index import ServicesMainIndexGenerator
    # Note: HandlerGenerator moved from services to api-server per FINAL_ARCHITECTURE.md
    # Handlers belong in api-server as thin adapters

# API Server generators (inbound layer)
from .api_server.routes import RoutesGenerator
from .api_server.handler import HandlerGenerator
from .api_server.openapi_types import OpenAPITypesGenerator
from .api_server.dependencies import DependenciesGenerator

# Adapter generators (infrastructure layer)
from .adapters.dynamodb_repository import DynamoDBRepositoryGenerator
from .adapters.port_adapter import PortAdapterGenerator

__all__ = [
    # Core
    "EntityGenerator",
    "TypesGenerator",
    "RepositoryGenerator",
    # Services
    "UseCaseGenerator",
    "PortGenerator",
    "DTOGenerator",
    "PolicyGenerator",
    "ErrorGenerator",
    "ServicesDomainIndexGenerator",
    "ServicesMainIndexGenerator",
    # API Server
    "RoutesGenerator",
    "HandlerGenerator",
    "OpenAPITypesGenerator",
    "DependenciesGenerator",
    # Adapters
    "DynamoDBRepositoryGenerator",
    "PortAdapterGenerator",
]
