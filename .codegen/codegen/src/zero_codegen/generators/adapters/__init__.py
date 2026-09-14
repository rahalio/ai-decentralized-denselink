"""
Adapter generators - Infrastructure layer

Per DDD: Adapters implement ports and handle infrastructure concerns.
"""

from .dynamodb_repository import DynamoDBRepositoryGenerator
from .port_adapter import PortAdapterGenerator

__all__ = [
    "DynamoDBRepositoryGenerator",
    "PortAdapterGenerator",
]
