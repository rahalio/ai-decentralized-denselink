"""
API Server generators - Inbound layer

Per DDD: API Server generates routes, handlers, OpenAPI types, Zod schemas, composition root.
Handlers are thin adapters that call use cases.
Routes register handlers with Fastify.
"""

from .routes import RoutesGenerator
from .handler import HandlerGenerator
from .openapi_types import OpenAPITypesGenerator
from .zod_schemas import ZodSchemasGenerator
from .dependencies import DependenciesGenerator
from .domain_routes import ApiServerDomainRoutesGenerator
from .domain_dependencies import ApiServerDomainDependenciesGenerator
from .system_routes import ApiServerSystemRoutesGenerator

__all__ = [
    "RoutesGenerator",
    "HandlerGenerator",
    "OpenAPITypesGenerator",
    "ZodSchemasGenerator",
    "DependenciesGenerator",
    "ApiServerDomainRoutesGenerator",
    "ApiServerDomainDependenciesGenerator",
    "ApiServerSystemRoutesGenerator",
]
