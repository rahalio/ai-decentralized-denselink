"""
Folder structure configuration for DDD-aligned code generation

Defines output paths for all layers following DDD principles.
"""

from pathlib import Path
from typing import Dict, Optional


class FolderStructureConfig:
    """
    Folder structure configuration for unified codegen

    Per DDD:
    - Core: packages/core/src/{domain}/
    - Services: platform/services/src/{domain}/
    - API Server: platform/api-server/src/domains/{domain}/
    - Adapters: platform/adapters/src/{domain}/
    """

    # Core layer paths
    CORE_BASE = "packages/core/src"
    CORE_ENTITIES = "models/{resource}/entity"
    CORE_TYPES = "types"
    CORE_REPOSITORIES = "repositories"
    CORE_UTILS = "utils"

    # Services layer paths
    SERVICES_BASE = "platform/services/src"
    SERVICES_USECASES = "usecases"
    SERVICES_PORTS = "ports"
    SERVICES_DTOS = "dto"
    SERVICES_POLICIES = "policies"
    SERVICES_ERRORS = "errors"

    # API Server layer paths
    API_SERVER_BASE = "platform/api-server/src/domains"
    API_SERVER_ROUTES = "routes"
    API_SERVER_CONTRACTS = "contracts"
    API_SERVER_DEPENDENCIES = "dependencies"

    # Adapters layer paths
    ADAPTERS_BASE = "platform/adapters/src"

    # Webapp layer paths
    WEBAPP_SERVICES_BASE = "platform/webapp/src/services/domains"
    WEBAPP_FEATURES_BASE = "platform/webapp/src/features"

    @staticmethod
    def get_core_output_path(project_root: Path, domain_name: str, generator_type: str) -> Path:
        """Get output path for core layer generators"""
        base = project_root / FolderStructureConfig.CORE_BASE / domain_name

        if generator_type == "entity":
            return base / FolderStructureConfig.CORE_ENTITIES.format(resource="{resource}")
        elif generator_type == "types":
            return base / FolderStructureConfig.CORE_TYPES
        elif generator_type == "repository":
            return base / FolderStructureConfig.CORE_REPOSITORIES

        return base

    @staticmethod
    def get_services_output_path(project_root: Path, domain_name: str, generator_type: str) -> Path:
        """Get output path for services layer generators"""
        base = project_root / FolderStructureConfig.SERVICES_BASE / domain_name

        if generator_type == "usecase":
            return base / FolderStructureConfig.SERVICES_USECASES
        elif generator_type == "port":
            return base / FolderStructureConfig.SERVICES_PORTS
        elif generator_type == "dto":
            return base / FolderStructureConfig.SERVICES_DTOS
        elif generator_type == "policy":
            return base / FolderStructureConfig.SERVICES_POLICIES
        elif generator_type == "error":
            return base / FolderStructureConfig.SERVICES_ERRORS

        return base

    @staticmethod
    def get_api_server_output_path(project_root: Path, domain_name: str, generator_type: str) -> Path:
        """Get output path for API server layer generators"""
        base = project_root / FolderStructureConfig.API_SERVER_BASE / domain_name

        if generator_type == "routes":
            return base / FolderStructureConfig.API_SERVER_ROUTES
        elif generator_type == "openapi_types":
            return base / FolderStructureConfig.API_SERVER_CONTRACTS
        elif generator_type == "zod_schemas":
            return base / FolderStructureConfig.API_SERVER_CONTRACTS
        elif generator_type == "dependencies":
            return base / FolderStructureConfig.API_SERVER_DEPENDENCIES

        return base

    @staticmethod
    def get_adapters_output_path(project_root: Path, domain_name: str) -> Path:
        """Get output path for adapters layer generators"""
        return project_root / FolderStructureConfig.ADAPTERS_BASE / domain_name

    @staticmethod
    def get_webapp_services_output_path(project_root: Path, domain_name: str, generator_type: str) -> Path:
        """Get output path for webapp services layer generators"""
        base = project_root / FolderStructureConfig.WEBAPP_SERVICES_BASE / domain_name

        if generator_type == "webapp_contracts":
            return base / "contracts"
        elif generator_type in ["webapp_api_types", "webapp_service", "webapp_facade", "webapp_services_index"]:
            return base
        elif generator_type == "webapp_hooks":
            return base / "hooks"

        return base

    @staticmethod
    def get_webapp_features_output_path(project_root: Path, domain_name: str) -> Path:
        """Get output path for webapp features layer generators"""
        return project_root / FolderStructureConfig.WEBAPP_FEATURES_BASE / domain_name

    @staticmethod
    def get_layer_output_path(project_root: Path, layer: str, domain_name: str, generator_type: str) -> Path:
        """Get output path for any layer"""
        if layer == "core":
            return FolderStructureConfig.get_core_output_path(project_root, domain_name, generator_type)
        elif layer == "services":
            return FolderStructureConfig.get_services_output_path(project_root, domain_name, generator_type)
        elif layer == "api_server":
            return FolderStructureConfig.get_api_server_output_path(project_root, domain_name, generator_type)
        elif layer == "adapters":
            return FolderStructureConfig.get_adapters_output_path(project_root, domain_name)
        elif layer == "webapp_services":
            return FolderStructureConfig.get_webapp_services_output_path(project_root, domain_name, generator_type)
        elif layer == "webapp_features":
            return FolderStructureConfig.get_webapp_features_output_path(project_root, domain_name)

        raise ValueError(f"Unknown layer: {layer}")

    @staticmethod
    def get_layer_import_path(project_root: Path, layer: str, from_generator: str, to_generator: str, domain_name: str) -> str:
        """Get import path from one generator to another within the same layer"""
        if layer == "core":
            if to_generator == "types":
                return "../types/index.js"
            elif to_generator == "repositories":
                return f"@ddd/core/{domain_name}/repositories/index.js"
        return ""

    @staticmethod
    def get_layer_shared_import_path(layer: str, generator_type: str, shared_type: str) -> str:
        """Get import path for shared types/repositories"""
        if shared_type == "repositories":
            return "../../_shared/repositories/_base-repository.js"
        elif shared_type == "types":
            return "@ddd/core/_shared/types"
        return ""
