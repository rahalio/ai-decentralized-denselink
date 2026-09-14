"""
Services Domain Index Generator - Generates {domain}/index.ts barrel export

Per DDD: Services layer contains use cases, ports, DTOs, policies, errors.
This generator creates the main barrel export file for each domain in the services layer.
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file
from ...utils.string import pascal_case


class ServicesDomainIndexGenerator(BaseGenerator):
    """Generates domain root index.ts barrel export file for services layer"""
    
    @property
    def name(self) -> str:
        return "Services Domain Index Generator"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def type(self) -> str:
        return "services_domain_index"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate domain root index.ts file for services layer"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        domain_dir = project_root / "platform" / "services" / "src" / context.domain_name
        ensure_directory(domain_dir)
        
        # Generate domain root index.ts
        index_file = domain_dir / "index.ts"
        
        header = self.generate_header(
            context,
            f"{pascal_case(context.domain_name)} Services - Application Layer Export"
        )
        
        domain_pascal = pascal_case(context.domain_name)
        
        content = f"""{header}/**
 * {domain_pascal} Services - Application Layer
 *
 * DDD: Application use cases, ports, DTOs, policies, and errors for {context.domain_name} domain.
 */

// Use Cases (Application layer - orchestrate business flows)
export * from "./usecases/index.js";

// DTOs (Application layer - input/output data transfer objects)
export * from "./dto/index.js";

// Ports (Application layer - interfaces that adapters implement)
export * from "./ports/index.js";

// Policies (Application layer - business rule policies)
export * from "./policies/index.js";

// Errors (Application layer - application error classes)
export * from "./errors/index.js";
"""
        
        write_file(index_file, content)
        files.append(index_file)
        
        context.logger.info(f"Generated services domain root index for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
