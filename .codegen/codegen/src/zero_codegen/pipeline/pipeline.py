"""
Unified Pipeline - Orchestrates all generators following DDD pattern

Generates all layers: core, services, api_server, adapters

Per FINAL_ARCHITECTURE.md:
- Handlers should NOT be in services layer
- Routes in api-server call use cases directly (no handlers needed)
"""

import time
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

from ..base.config import Config, DomainConfig, PipelineOptions as ConfigPipelineOptions
from ..base.logger import Logger, create_logger
from ..base.context import GenerationContext
from ..base.errors import GenerationError
from ..utils.openapi import load_openapi_spec
from ..utils.openapi_bundler import OpenApiBundler
from ..utils.layer_cleaner import clean_layers_before_generation
from .generator_registry import GeneratorRegistry


@dataclass
class StepResult:
    """Result of a pipeline step"""
    step: str
    domain: str
    layer: str
    success: bool
    duration: float
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of pipeline execution"""
    success: bool
    total_duration: float
    steps: List[StepResult]
    domains_processed: int
    domains_succeeded: int
    domains_failed: int
    errors: List[str]


class Pipeline:
    """
    Unified pipeline for DDD-aligned code generation

    Generates all layers following the DDD pattern:
    - Core (domain): entities, types, repositories
    - Services (application): use cases, ports, DTOs, policies, errors
    - API Server (inbound): routes, OpenAPI types, dependencies
    - Adapters (infrastructure): DynamoDB repos, port adapters

    Per FINAL_ARCHITECTURE.md:
    - Handlers belong in api-server layer (not services layer)
    - Routes register handlers, handlers call use cases
    """

    # Generator execution order per layer
    # Core: entity before types so types can skip exporting XEntity when models/{x}.entity.ts exists
    CORE_GENERATORS = [
        "openapi_typescript_extractor",  # Extract OpenAPI types to openapi/{domain}.openapi.types.ts
        "openapi_zod_client_extractor",   # Extract Zod schemas to openapi/{domain}.zod.schema.ts
        "schemas",                        # Generate schemas/{domain}.schemas.ts barrel export
        "entity",                         # Generate entities (operations-driven; x-dynamodb is for adapters only)
        "types",                          # Generate types; skips aliases that clash with model entity types
        "repository",                     # Generate repository interfaces
        "domain_index",                   # Generate domain root index.ts
    ]
    # Note: handlers moved from services to api-server per FINAL_ARCHITECTURE.md
    # Handlers belong in api-server as thin adapters
    SERVICES_GENERATORS = ["error", "dto", "port", "policy", "usecase", "services_domain_index"]
    # Handlers must be generated before routes (routes import handlers)
    API_SERVER_GENERATORS = ["openapi_types", "zod_schemas", "handler", "routes", "dependencies"]
    ADAPTERS_GENERATORS = ["dynamodb_repository", "port_adapter"]
    WEBAPP_GENERATORS = [
        "webapp_contracts",
        "webapp_api_types",
        "webapp_service",
        "webapp_facade",
        "webapp_hooks",
        "webapp_services_index",
        "webapp_features",
    ]
    TEST_GENERATORS = ["test"]
    POSTMAN_GENERATORS = ["postman_collection"]

    def __init__(
        self,
        config: Optional[Config] = None,
        logger: Optional[Logger] = None,
        config_path: Optional[Path] = None
    ):
        """Initialize pipeline"""
        if config is None and config_path:
            config = self._load_config(config_path)

        if config is None:
            raise GenerationError("Config is required")

        self.config = config
        self.logger = logger or create_logger(
            level=config.log_level,
            verbose=config.verbose
        )
        self.registry = GeneratorRegistry(self.logger)

        # Register all generators
        self._register_generators()

    def _load_config(self, config_path: Path) -> Config:
        """Load configuration from file"""
        import json
        with open(config_path, "r") as f:
            data = json.load(f)
        return Config(**data)

    def _register_generators(self):
        """Register all generators"""
        from ..generators.core import (
            EntityGenerator,
            TypesGenerator,
            RepositoryGenerator,
            SchemasGenerator,
            DomainIndexGenerator,
            MainIndexGenerator,
        )
        from ..generators.services import (
            UseCaseGenerator,
            PortGenerator,
            DTOGenerator,
            PolicyGenerator,
            ErrorGenerator,
            ServicesDomainIndexGenerator,
            ServicesMainIndexGenerator,
        )
        # Note: HandlerGenerator removed - handlers should NOT be in services layer per FINAL_ARCHITECTURE.md
        # Routes in api-server call use cases directly (no handlers needed)
        from ..generators.api_server import (
            RoutesGenerator,
            HandlerGenerator,
            OpenAPITypesGenerator,
            ZodSchemasGenerator,
            DependenciesGenerator,
            ApiServerDomainRoutesGenerator,
            ApiServerDomainDependenciesGenerator,
            ApiServerSystemRoutesGenerator,
        )
        from ..generators.adapters import (
            DynamoDBRepositoryGenerator,
            PortAdapterGenerator,
        )
        from ..generators.tests import (
            TestGenerator,
        )
        from ..generators.postman import (
            PostmanCollectionGenerator,
        )
        from ..generators.webapp import (
            WebappContractsGenerator,
            WebappApiTypesGenerator,
            WebappServiceGenerator,
            WebappFacadeGenerator,
            WebappHooksGenerator,
            WebappServicesIndexGenerator,
            WebappFeaturesGenerator,
        )
        from ..extractors.openapi_typescript_extractor import OpenApiTypeScriptExtractor
        from ..extractors.openapi_zod_client_extractor import OpenApiZodClientExtractor

        # Core generators
        self.registry.register("openapi_typescript_extractor", OpenApiTypeScriptExtractor)
        self.registry.register("openapi_zod_client_extractor", OpenApiZodClientExtractor)
        self.registry.register("schemas", SchemasGenerator)
        self.registry.register("entity", EntityGenerator)
        self.registry.register("types", TypesGenerator)
        self.registry.register("repository", RepositoryGenerator)
        self.registry.register("domain_index", DomainIndexGenerator)
        self.registry.register("main_index", MainIndexGenerator)

        # Services generators
        self.registry.register("usecase", UseCaseGenerator)
        self.registry.register("port", PortGenerator)
        self.registry.register("dto", DTOGenerator)
        self.registry.register("policy", PolicyGenerator)
        self.registry.register("error", ErrorGenerator)
        self.registry.register("services_domain_index", ServicesDomainIndexGenerator)
        self.registry.register("services_main_index", ServicesMainIndexGenerator)
        # Note: HandlerGenerator moved from services to api-server per FINAL_ARCHITECTURE.md
        # Handlers belong in api-server as thin adapters

        # API Server generators
        self.registry.register("openapi_types", OpenAPITypesGenerator)
        self.registry.register("zod_schemas", ZodSchemasGenerator)
        self.registry.register("handler", HandlerGenerator)  # Handlers before routes (routes import handlers)
        self.registry.register("routes", RoutesGenerator)
        self.registry.register("dependencies", DependenciesGenerator)
        self.registry.register("api_server_domain_routes", ApiServerDomainRoutesGenerator)
        self.registry.register("api_server_domain_dependencies", ApiServerDomainDependenciesGenerator)
        self.registry.register("api_server_system_routes", ApiServerSystemRoutesGenerator)

        # Adapter generators
        self.registry.register("dynamodb_repository", DynamoDBRepositoryGenerator)
        self.registry.register("port_adapter", PortAdapterGenerator)

        # Test generators
        self.registry.register("test", TestGenerator)

        # Postman/Newman generators
        self.registry.register("postman_collection", PostmanCollectionGenerator)

        # Webapp generators
        self.registry.register("webapp_contracts", WebappContractsGenerator)
        self.registry.register("webapp_api_types", WebappApiTypesGenerator)
        self.registry.register("webapp_service", WebappServiceGenerator)
        self.registry.register("webapp_facade", WebappFacadeGenerator)
        self.registry.register("webapp_hooks", WebappHooksGenerator)
        self.registry.register("webapp_services_index", WebappServicesIndexGenerator)
        self.registry.register("webapp_features", WebappFeaturesGenerator)

    def generate(
        self,
        domains: Optional[List[str]] = None,
        layers: Optional[List[str]] = None,
        options: Optional[ConfigPipelineOptions] = None
    ) -> PipelineResult:
        """
        Generate code for specified domains and layers

        Args:
            domains: List of domain names (None = all enabled domains)
            layers: List of layers to generate (None = all enabled layers)
            options: Pipeline options
        """
        start_time = time.time()
        steps: List[StepResult] = []
        errors: List[str] = []

        options = options or self.config.pipeline

        # Determine domains to process
        domains_to_process = self._determine_domains(domains)
        if not domains_to_process:
            self.logger.warn("No domains to process")
            return PipelineResult(
                success=False,
                total_duration=time.time() - start_time,
                steps=steps,
                domains_processed=0,
                domains_succeeded=0,
                domains_failed=0,
                errors=["No domains to process"]
            )

        # Determine layers to generate
        layers_to_generate = self._determine_layers(layers)

        # Clean previously generated output for the layers we're about to generate.
        # When generating for all domains (domains is None): clean all domain output.
        # When generating for one or a subset (--domain X): clean only those domains' output.
        if options.clean:
            output_layers = self._get_output_layers_from_generators(layers_to_generate)
            if output_layers:
                domain_names = [d.name for d in self.config.domains]
                domain_names_to_clean = None if domains is None else [d.name for d in domains_to_process]
                cleaned = clean_layers_before_generation(
                    Path(self.config.paths.project_root),
                    output_layers,
                    domain_names,
                    domain_names_to_clean=domain_names_to_clean,
                )
                for layer_name, count in cleaned.items():
                    self.logger.info(f"Cleaned {layer_name} layer: removed {count} previously generated item(s)")

        self.logger.info(f"Starting unified DDD-aligned code generation")
        domain_names = [d.name for d in domains_to_process]
        self.logger.info(f"Domains: {', '.join(domain_names)}")
        self.logger.info(f"Layers: {', '.join(layers_to_generate)}")

        domains_succeeded = 0
        domains_failed = 0

        # Process each domain
        bundler = OpenApiBundler(self.logger)

        for domain_config in domains_to_process:
            domain_name = domain_config.name

            try:
                # Step 1: Bundle OpenAPI YAML to JSON (skip when spec_path empty; use bundled-only)
                spec_path = (self.config.paths.openapi_dir / domain_config.spec_path) if (domain_config.spec_path and domain_config.spec_path.strip()) else None
                bundled_path = self.config.paths.bundled_dir / domain_config.bundled_path

                if spec_path is not None and spec_path.exists() and spec_path.is_file():
                    # Bundle first for core generation (pure OpenAPI-based generation)
                    self.logger.info(f"Bundling OpenAPI spec for {domain_name}...")
                    bundler.bundle_domain(
                        domain_config,
                        spec_path,
                        bundled_path,
                        self.config.paths.openapi_dir
                    )
                elif not bundled_path.exists():
                    raise GenerationError(f"OpenAPI spec not found: {spec_path} and bundled path not found: {bundled_path}")
                else:
                    self.logger.info(f"Using existing bundled spec for {domain_name}...")

                # Load OpenAPI spec (from bundled JSON if available, otherwise from YAML)
                if bundled_path.exists():
                    spec = load_openapi_spec(bundled_path)
                elif spec_path and spec_path.exists():
                    spec = load_openapi_spec(spec_path)
                else:
                    raise GenerationError(f"No OpenAPI spec available for {domain_name}")

                # Load unbundled YAML for $ref resolution (bundler dereferences, losing schema names)
                unbundled_spec = None
                if spec_path and spec_path.exists() and spec_path.suffix in (".yaml", ".yml"):
                    unbundled_spec = load_openapi_spec(spec_path)

                # Create context
                context = GenerationContext(
                    config=self.config,
                    domain=domain_config,
                    logger=self.logger,
                    spec=spec,
                    unbundled_spec=unbundled_spec,
                )

                # Generate layers in order
                domain_success = True
                for layer in layers_to_generate:
                    layer_success = self._generate_layer(
                        context,
                        layer,
                        steps,
                        options
                    )
                    if not layer_success and options.fail_fast:
                        domain_success = False
                        break

                if domain_success:
                    domains_succeeded += 1
                else:
                    domains_failed += 1
                    errors.append(f"Domain {domain_name} failed")

            except Exception as e:
                domains_failed += 1
                error_msg = f"Domain {domain_name} failed: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                if options.fail_fast:
                    break

        # Generate main index.ts after all domains are processed (if core layer is enabled)
        if "core" in layers_to_generate or any(layer in self.CORE_GENERATORS for layer in layers_to_generate):
            try:
                self.logger.info("Generating main packages/core/src/index.ts...")
                # Create a dummy context for main index generation (it doesn't need domain-specific info)
                main_context = GenerationContext(
                    config=self.config,
                    domain=domains_to_process[0] if domains_to_process else None,  # Just for context, not used
                    logger=self.logger,
                    spec=None  # Not needed for main index
                )
                from ..generators.core.main_index import MainIndexGenerator
                generator = MainIndexGenerator()
                result = generator.generate(main_context)
                if result.files:
                    self.logger.info(f"✅ Generated main index.ts")
                else:
                    warnings = result.warnings or []
                    if warnings:
                        self.logger.warn(f"⚠️ Main index generation warnings: {', '.join(warnings)}")
            except Exception as e:
                error_msg = f"Main index generation failed: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

            try:
                self.logger.info("Generating integration event registry from x-integration-events...")
                integration_context = GenerationContext(
                    config=self.config,
                    domain=domains_to_process[0] if domains_to_process else None,
                    logger=self.logger,
                    spec=None,
                )
                from ..generators.core.integration_events import IntegrationEventsGenerator
                integration_generator = IntegrationEventsGenerator()
                integration_result = integration_generator.generate(integration_context)
                if integration_result.files:
                    self.logger.info("✅ Generated integration event registry")
            except Exception as e:
                error_msg = f"Integration events generation failed: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        # Generate services main index.ts after all domains are processed (if services layer is enabled)
        if "services" in layers_to_generate or any(layer in self.SERVICES_GENERATORS for layer in layers_to_generate):
            try:
                self.logger.info("Generating main platform/services/src/index.ts...")
                # Create a dummy context for services main index generation (it doesn't need domain-specific info)
                services_main_context = GenerationContext(
                    config=self.config,
                    domain=domains_to_process[0] if domains_to_process else None,  # Just for context, not used
                    logger=self.logger,
                    spec=None  # Not needed for main index
                )
                from ..generators.services.services_main_index import ServicesMainIndexGenerator
                generator = ServicesMainIndexGenerator()
                result = generator.generate(services_main_context)
                if result.files:
                    self.logger.info(f"✅ Generated services main index.ts")
                else:
                    warnings = result.warnings or []
                    if warnings:
                        self.logger.warn(f"⚠️ Services main index generation warnings: {', '.join(warnings)}")
            except Exception as e:
                error_msg = f"Services main index generation failed: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        # Generate api-server domain-routes.ts and domains/index.ts after all api_server domains (rescan)
        if "api_server" in layers_to_generate or any(layer in self.API_SERVER_GENERATORS for layer in layers_to_generate):
            try:
                self.logger.info("Generating api-server domain-routes and domains index...")
                api_main_context = GenerationContext(
                    config=self.config,
                    domain=domains_to_process[0] if domains_to_process else None,
                    logger=self.logger,
                    spec=None,
                )
                from ..generators.api_server.domain_routes import ApiServerDomainRoutesGenerator
                generator = ApiServerDomainRoutesGenerator()
                result = generator.generate(api_main_context)
                if result.files:
                    self.logger.info("✅ Generated api-server domain-routes and domains index")
                else:
                    warnings = result.warnings or []
                    if warnings:
                        self.logger.warn(f"⚠️ Api-server domain routes warnings: {', '.join(warnings)}")
                # Domain dependencies (domain-dependencies.ts, dependency-container.ts)
                from ..generators.api_server.domain_dependencies import ApiServerDomainDependenciesGenerator
                dep_generator = ApiServerDomainDependenciesGenerator()
                dep_result = dep_generator.generate(api_main_context)
                if dep_result.files:
                    self.logger.info("✅ Generated api-server domain-dependencies and dependency-container")
                else:
                    dep_warnings = dep_result.warnings or []
                    if dep_warnings:
                        self.logger.warn(f"⚠️ Api-server domain dependencies warnings: {', '.join(dep_warnings)}")
                # System routes (health, /routes, /routes/full) from specs
                from ..generators.api_server.system_routes import ApiServerSystemRoutesGenerator
                sys_routes_generator = ApiServerSystemRoutesGenerator()
                sys_result = sys_routes_generator.generate(api_main_context)
                if sys_result.files:
                    self.logger.info("✅ Generated api-server system-routes.ts")
                else:
                    sys_warnings = sys_result.warnings or []
                    if sys_warnings:
                        self.logger.warn(f"⚠️ Api-server system routes warnings: {', '.join(sys_warnings)}")
            except Exception as e:
                error_msg = f"Api-server domain routes/dependencies generation failed: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        total_duration = time.time() - start_time

        result = PipelineResult(
            success=domains_failed == 0,
            total_duration=total_duration,
            steps=steps,
            domains_processed=len(domains_to_process),
            domains_succeeded=domains_succeeded,
            domains_failed=domains_failed,
            errors=errors
        )

        self.logger.info(f"Pipeline completed: {domains_succeeded} succeeded, {domains_failed} failed")
        self.logger.info(f"Total duration: {total_duration:.2f}s")

        return result

    def _get_output_layers_from_generators(self, generator_names: List[str]) -> List[str]:
        """Map generator names (or layer names) to output layer names for cleaning"""
        output_layers = set()
        for name in generator_names:
            if name in ("core", "services", "api_server", "adapters", "tests", "postman", "webapp"):
                output_layers.add(name)
            elif name in ("api-server",):
                output_layers.add("api_server")
            elif name in self.CORE_GENERATORS:
                output_layers.add("core")
            elif name in self.SERVICES_GENERATORS:
                output_layers.add("services")
            elif name in self.API_SERVER_GENERATORS:
                output_layers.add("api_server")
            elif name in self.ADAPTERS_GENERATORS:
                output_layers.add("adapters")
            elif name in self.TEST_GENERATORS:
                output_layers.add("tests")
            elif name in self.POSTMAN_GENERATORS:
                output_layers.add("postman")
            elif name in self.WEBAPP_GENERATORS:
                output_layers.add("webapp")
        return list(output_layers)

    def _determine_domains(self, domains: Optional[List[str]]) -> List[DomainConfig]:
        """Determine which domains to process"""
        if domains:
            return [
                d for d in self.config.domains
                if d.name in domains and d.enabled
            ]
        return [d for d in self.config.domains if d.enabled]

    def _determine_layers(self, layers: Optional[List[str]]) -> List[str]:
        """Determine which layers to generate"""
        if layers:
            return layers

        # Return all enabled layers
        enabled = []
        if self.config.layers.core.entities.enabled:
            enabled.extend(self.CORE_GENERATORS)
        if self.config.layers.services.usecases.enabled:
            enabled.extend(self.SERVICES_GENERATORS)
        if self.config.layers.api_server.routes.enabled:
            enabled.extend(self.API_SERVER_GENERATORS)
        if self.config.layers.adapters.dynamodb_repositories.enabled:
            enabled.extend(self.ADAPTERS_GENERATORS)
        if self.config.layers.tests.tests.enabled:
            enabled.extend(self.TEST_GENERATORS)
        if getattr(self.config.layers, "postman", None) and getattr(self.config.layers.postman, "collection", None) and self.config.layers.postman.collection.enabled:
            enabled.extend(self.POSTMAN_GENERATORS)
        webapp_cfg = getattr(self.config.layers, "webapp", None)
        if webapp_cfg and (
            (getattr(webapp_cfg, "services", None) and webapp_cfg.services.enabled)
            or (getattr(webapp_cfg, "features", None) and webapp_cfg.features.enabled)
        ):
            enabled.extend(self.WEBAPP_GENERATORS)

        return enabled

    def _generate_layer(
        self,
        context: GenerationContext,
        layer: str,
        steps: List[StepResult],
        options: ConfigPipelineOptions
    ) -> bool:
        """Generate a specific layer"""
        # Map layer names to generator lists
        if layer == "core":
            generators = self.CORE_GENERATORS
        elif layer == "services":
            generators = self.SERVICES_GENERATORS
        elif layer == "api_server" or layer == "api-server":
            generators = self.API_SERVER_GENERATORS
        elif layer == "adapters":
            generators = self.ADAPTERS_GENERATORS
        elif layer == "tests":
            generators = self.TEST_GENERATORS
        elif layer == "postman":
            generators = self.POSTMAN_GENERATORS
        elif layer == "webapp":
            generators = self.WEBAPP_GENERATORS
        # Check if it's a specific generator type
        elif layer in self.CORE_GENERATORS:
            generators = [layer]
        elif layer in self.SERVICES_GENERATORS:
            generators = [layer]
        elif layer in self.API_SERVER_GENERATORS:
            generators = [layer]
        elif layer in self.ADAPTERS_GENERATORS:
            generators = [layer]
        elif layer in self.TEST_GENERATORS:
            generators = [layer]
        elif layer in self.POSTMAN_GENERATORS:
            generators = [layer]
        elif layer in self.WEBAPP_GENERATORS:
            generators = [layer]
        else:
            generators = [layer]

        # Execute generators
        for generator_type in generators:
            success = self._execute_generator(
                context,
                generator_type,
                steps,
                options
            )
            if not success and options.fail_fast:
                return False

        return True

    def _execute_generator(
        self,
        context: GenerationContext,
        generator_type: str,
        steps: List[StepResult],
        options: ConfigPipelineOptions
    ) -> bool:
        """Execute a single generator"""
        start_time = time.time()

        try:
            generator_class = self.registry.get(generator_type)
            if not generator_class:
                raise GenerationError(f"Generator not found: {generator_type}")

            generator = generator_class()
            result = generator.generate(context)

            duration = time.time() - start_time

            step_result = StepResult(
                step=generator_type,
                domain=context.domain_name,
                layer=self._get_layer_for_generator(generator_type),
                success=result.success,
                duration=duration
            )

            if not result.success:
                step_result.error = "; ".join(result.errors)
                self.logger.error(f"Generator {generator_type} failed: {step_result.error}")

            steps.append(step_result)

            return result.success

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            step_result = StepResult(
                step=generator_type,
                domain=context.domain_name,
                layer=self._get_layer_for_generator(generator_type),
                success=False,
                duration=duration,
                error=error_msg
            )
            steps.append(step_result)

            self.logger.error(f"Generator {generator_type} raised exception: {error_msg}")
            return False

    def _get_layer_for_generator(self, generator_type: str) -> str:
        """Get layer name for a generator type"""
        if generator_type in self.CORE_GENERATORS:
            return "core"
        elif generator_type in self.SERVICES_GENERATORS:
            return "services"
        elif generator_type in self.API_SERVER_GENERATORS:
            return "api_server"
        elif generator_type in self.ADAPTERS_GENERATORS:
            return "adapters"
        elif generator_type in self.TEST_GENERATORS:
            return "tests"
        elif generator_type in self.POSTMAN_GENERATORS:
            return "postman"
        elif generator_type in self.WEBAPP_GENERATORS:
            return "webapp"
        return "unknown"


# Alias for backward compatibility
PipelineOptions = ConfigPipelineOptions
