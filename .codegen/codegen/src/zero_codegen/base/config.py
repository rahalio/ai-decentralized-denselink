"""
Unified Configuration for DDD-Aligned Code Generation

Supports generating all layers: core, services, api_server, adapters
Following true DDD principles as established in channel domain refactoring.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class PathConfig(BaseModel):
    """Path configuration - INPUT paths only"""
    project_root: Path = Field(..., description="Project root directory (absolute path)")
    openapi_dir: Path = Field(..., description="OpenAPI specifications directory")
    bundled_dir: Path = Field(..., description="Bundled OpenAPI JSON directory")

    @field_validator("*", mode="before")
    @classmethod
    def convert_paths(cls, v: Any) -> Path:
        if isinstance(v, str):
            return Path(v)
        return v

    @field_validator("*", mode="after")
    @classmethod
    def resolve_paths(cls, v: Path) -> Path:
        if isinstance(v, Path):
            return v.resolve()
        return v


class GeneratorOptions(BaseModel):
    """Options for individual generators"""
    enabled: bool = Field(True, description="Whether this generator is enabled")
    include_js_docs: bool = Field(True, description="Include JSDoc comments")


# ============================================================================
# Core Layer Configuration (Domain Layer)
# ============================================================================

class CoreLayerConfig(BaseModel):
    """
    Core layer configuration - Pure domain only

    Per DDD: Core should only contain entities, types, repositories (temporary),
    and domain utilities. NO handlers, NO DTOs, NO OpenAPI types, NO converters.
    """
    entities: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate entities")
    types: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate domain types")
    repositories: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate repository interfaces (temporary)")

    # ❌ Handlers removed - handlers don't belong in core per DDD
    # ❌ DTOs removed - DTOs belong in services layer
    # ❌ OpenAPI types removed - belong in api-server layer
    # ❌ Converters removed - converters don't belong in core per DDD


# ============================================================================
# Services Layer Configuration (Application Layer)
# ============================================================================

class ServicesLayerConfig(BaseModel):
    """
    Services layer configuration - Application layer

    Per DDD: Services contains use cases, ports, DTOs, policies, errors, handlers.
    """
    usecases: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate use cases")
    ports: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate ports (method-based interfaces)")
    dtos: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate DTOs")
    policies: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate policies")
    errors: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate application errors")
    handlers: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate handlers (wrap repository calls)")

    # Port generation options
    port_style: str = Field("method_based", description="Port style: 'method_based' (preferred) or 'function_typed' (deprecated)")


# ============================================================================
# API Server Layer Configuration (Inbound Layer)
# ============================================================================

class ApiServerLayerConfig(BaseModel):
    """
    API Server layer configuration - Inbound layer

    Per DDD: API Server contains routes, OpenAPI types, composition root.
    """
    routes: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate routes")
    openapi_types: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate OpenAPI types")
    zod_schemas: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate Zod schemas")
    dependencies: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate composition root")


# ============================================================================
# Adapters Layer Configuration (Infrastructure Layer)
# ============================================================================

class AdaptersLayerConfig(BaseModel):
    """
    Adapters layer configuration - Infrastructure layer

    Per DDD: Adapters implement ports and handle infrastructure concerns.
    """
    dynamodb_repositories: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate DynamoDB repositories")
    port_adapters: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate port adapters")


# ============================================================================
# Postman Layer Configuration (Postman/Newman Test Suite)
# ============================================================================

class PostmanLayerConfig(BaseModel):
    """
    Postman layer configuration - Postman collections and env from OpenAPI

    Generates Postman collection + environment JSON per domain for Newman runs.
    """
    collection: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate Postman collection and env JSON per domain")


# ============================================================================
# Tests Layer Configuration (Test Utilities Layer)
# ============================================================================

class TestsLayerConfig(BaseModel):
    """
    Tests layer configuration - Test utilities layer

    Generates test factories, mocks, and setup files for domain testing.
    """
    tests: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate test utilities")


# ============================================================================
# Webapp Layer Configuration (Frontend Layer)
# ============================================================================

class WebappLayerConfig(BaseModel):
    """
    Webapp layer configuration - Frontend layer

    Generates webapp service layer and feature layer scaffolding.
    """
    services: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate webapp services (contracts, api-types, service, facade, hooks)")
    features: GeneratorOptions = Field(default_factory=lambda: GeneratorOptions(), description="Generate webapp features (components, views structure)")


# ============================================================================
# Unified Layers Configuration
# ============================================================================

class LayersConfig(BaseModel):
    """Unified layer configurations following DDD pattern"""
    core: CoreLayerConfig = Field(default_factory=lambda: CoreLayerConfig())
    services: ServicesLayerConfig = Field(default_factory=lambda: ServicesLayerConfig())
    api_server: ApiServerLayerConfig = Field(default_factory=lambda: ApiServerLayerConfig())
    adapters: AdaptersLayerConfig = Field(default_factory=lambda: AdaptersLayerConfig())
    tests: TestsLayerConfig = Field(default_factory=lambda: TestsLayerConfig())
    postman: PostmanLayerConfig = Field(default_factory=lambda: PostmanLayerConfig())
    webapp: WebappLayerConfig = Field(default_factory=lambda: WebappLayerConfig())


# ============================================================================
# Domain Configuration
# ============================================================================

class OperationAliasConfig(BaseModel):
    """Configuration for an operation that delegates to another use case"""
    model_config = {"populate_by_name": True}
    delegate_to: str = Field(..., alias="delegateTo", description="Operation ID of the target use case (e.g. GetEventAggregates)")
    input_merge: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="inputMerge",
        description="Additional input fields to merge when calling the delegated use case (e.g. { metric: 'summary' })"
    )


class DomainConfig(BaseModel):
    """Configuration for a single domain"""
    name: str = Field(..., description="Domain name")
    enabled: bool = Field(True, description="Whether this domain is enabled")
    spec_path: str = Field("", description="Path to OpenAPI spec file (optional; use empty when only bundled JSON exists)")
    bundled_path: str = Field(..., description="Path to bundled OpenAPI JSON")
    # Optional: map resource name (from operation grouping) to schema name for entity generation.
    # Use when codegen picks the wrong schema and you want to preserve a manual choice after regen.
    # Example: { "CancelBatch": "Batch", "StartApproval": "StartApprovalPayload" }
    entity_schema_overrides: Optional[Dict[str, str]] = Field(
        default=None,
        description="Resource -> schema name overrides for core entity generator"
    )
    # Optional: operations that delegate to another use case (e.g. GetEventSummary -> GetEventAggregates with metric=summary)
    operation_aliases: Optional[Dict[str, OperationAliasConfig]] = Field(
        default=None,
        description="Operation ID -> { delegate_to, input_merge } for handler delegation"
    )


# ============================================================================
# Pipeline Options
# ============================================================================

class PipelineOptions(BaseModel):
    """Pipeline execution options"""
    clean: bool = Field(True, description="Clean output directories before generation (ensures no stale code)")
    validate: bool = Field(True, description="Validate generated code")
    skip_build: bool = Field(False, description="Skip build validation")
    parallel: bool = Field(False, description="Process domains in parallel")
    fail_fast: bool = Field(True, description="Stop on first error")
    layers: Optional[List[str]] = Field(None, description="Specific layers to generate (None = all)")


# ============================================================================
# Main Configuration
# ============================================================================

class Config(BaseModel):
    """Main configuration for unified codegen"""
    domains: List[DomainConfig] = Field(..., description="Domain configurations")
    paths: PathConfig = Field(..., description="Path configuration")
    layers: LayersConfig = Field(default_factory=lambda: LayersConfig(), description="Layer configurations")
    pipeline: PipelineOptions = Field(default_factory=lambda: PipelineOptions(), description="Pipeline options")
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    verbose: bool = Field(False, description="Verbose output")
    version: str = Field("2.0.0", description="Configuration version")
    # npm scope for generated imports, e.g. "@ddd" → "@ddd/core", "@ddd/services"
    package_scope: str = Field("@ddd", description="npm package scope used in generated TypeScript imports")
