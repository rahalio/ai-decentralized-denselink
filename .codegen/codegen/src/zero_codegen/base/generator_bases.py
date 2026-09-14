"""
Generator Base Classes - Standardized generator patterns
"""

from pathlib import Path
from typing import List, Optional
from abc import abstractmethod

from zero_codegen.base.generator import BaseGenerator, GenerateResult
from zero_codegen.base.context import GenerationContext
from zero_codegen.utils.generator_setup import GeneratorSetup
from zero_codegen.utils.index_file_generator import IndexFileGenerator
from zero_codegen.utils.file import write_file


class FileGenerator(BaseGenerator):
    """
    Base class for generators that create multiple files + index file.

    This class handles the common pattern:
    1. Setup output directory
    2. Generate multiple files
    3. Generate index file
    4. Return results

    Subclasses targeting a non-core layer MUST override ``output_layer``
    (e.g. webapp_services / webapp_features). Defaulting to core + clean
    would wipe packages/core when a webapp generator runs.
    """

    @property
    def output_layer(self) -> str:
        """FolderStructure layer key for this generator (default: core)."""
        return "core"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """
        Standard generation flow for file generators.

        Subclasses should implement:
        - generate_files() - returns list of generated file paths
        """
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Setup output directory (clean when pipeline.clean or generator prefers it)
        should_clean = context.config.pipeline.clean or self.should_clean()
        output_dir = GeneratorSetup.get_output_directory(
            context,
            generator_type=self.type,
            layer=self.output_layer,
            clean=should_clean,
        )

        # Generate files (implemented by subclass)
        generated_files = self.generate_files(context, output_dir)
        files.extend(generated_files)

        # Generate index file if needed
        if self.should_generate_index():
            index_file = self.generate_index(context, output_dir, generated_files)
            if index_file:
                files.append(index_file)

        return GenerateResult(files=files, warnings=warnings)

    @abstractmethod
    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """
        Generate files - must be implemented by subclass.

        Args:
            context: Generation context
            output_dir: Output directory path

        Returns:
            List of generated file paths
        """
        pass

    def should_clean(self) -> bool:
        """
        Whether to clean output directory before generation.

        Override in subclass if different behavior needed.

        Returns:
            True to clean directory, False otherwise
        """
        return True

    def should_generate_index(self) -> bool:
        """
        Whether to generate index file.

        Override in subclass if different behavior needed.

        Returns:
            True to generate index, False otherwise
        """
        return True

    def generate_index(
        self,
        context: GenerationContext,
        output_dir: Path,
        files: List[Path],
    ) -> Optional[Path]:
        """
        Generate index file with exports.

        Override in subclass for custom index generation.

        Args:
            context: Generation context
            output_dir: Output directory
            files: List of generated files

        Returns:
            Path to index file or None if not generated
        """
        exports = []
        for file_path in files:
            # Skip index file itself
            if file_path.name == "index.ts":
                continue
            file_base = file_path.stem
            exports.append(f'export * from "./{file_base}.js";')

        if not exports:
            return None

        return IndexFileGenerator.generate_with_header(
            context,
            output_dir,
            exports,
            description=f"{self.name} exports",
            generator_name=self.name,
        )


class SingleFileGenerator(BaseGenerator):
    """
    Base class for generators that create a single file.

    This class handles the common pattern:
    1. Setup output directory
    2. Generate file content
    3. Write file
    4. Return results
    """

    @property
    def output_layer(self) -> str:
        """FolderStructure layer key for this generator (default: core)."""
        return "core"

    def generate(self, context: GenerationContext) -> GenerateResult:
        """
        Standard generation flow for single file generators.

        Subclasses should implement:
        - generate_content() - returns file content as string
        - get_filename() - returns filename
        """
        self.validate_context(context)

        files: List[Path] = []
        warnings: List[str] = []

        # Setup output directory (clean when pipeline.clean or generator prefers it)
        should_clean = context.config.pipeline.clean or self.should_clean()
        output_dir = GeneratorSetup.get_output_directory(
            context,
            generator_type=self.type,
            layer=self.output_layer,
            clean=should_clean,
        )

        # Generate content (implemented by subclass)
        content = self.generate_content(context)

        # Write file
        filename = self.get_filename(context)
        file_path = output_dir / filename
        write_file(file_path, content)
        files.append(file_path)

        return GenerateResult(files=files, warnings=warnings)

    @abstractmethod
    def generate_content(self, context: GenerationContext) -> str:
        """
        Generate file content - must be implemented by subclass.

        Args:
            context: Generation context

        Returns:
            File content as string
        """
        pass

    @abstractmethod
    def get_filename(self, context: GenerationContext) -> str:
        """
        Get filename for generated file - must be implemented by subclass.

        Args:
            context: Generation context

        Returns:
            Filename (e.g., "index.ts", "converters.ts")
        """
        pass

    def should_clean(self) -> bool:
        """
        Whether to clean output directory before generation.

        Override in subclass if different behavior needed.

        Returns:
            True to clean directory, False otherwise
        """
        return False  # Single file generators usually don't clean


class PostProcessingGenerator(BaseGenerator):
    """
    Base class for generators that run after all domains are processed.

    Examples: main_index_builder, shared_types

    These generators don't process individual domains but run once
    after all domain processing is complete.
    """

    def generate(self, context: GenerationContext) -> GenerateResult:
        """
        Generate method required by BaseGenerator.

        Post-processing generators should implement their own
        specialized methods (e.g., generate_main_index, generate_shared_types)
        rather than using this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is a post-processing generator. "
            "Use specialized methods instead of generate()."
        )

    def should_clean(self) -> bool:
        """
        Whether to clean output directory.

        Post-processing generators usually don't clean.

        Returns:
            False (override if needed)
        """
        return False
