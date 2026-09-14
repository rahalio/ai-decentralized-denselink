"""
Generator Setup Utilities - Common setup patterns for generators
"""

from pathlib import Path
from typing import Optional

from zero_codegen.base.context import GenerationContext
from zero_codegen.base.folder_structure import FolderStructureConfig
from zero_codegen.utils.file import ensure_directory, clean_directory


class GeneratorSetup:
    """Common setup utilities for generators"""

    @staticmethod
    def get_output_directory(
        context: GenerationContext,
        generator_type: str,
        layer: str = "core",
        clean: bool = True,
    ) -> Path:
        """
        Get and setup output directory for a generator.

        Args:
            context: Generation context
            generator_type: Type of generator (e.g., "handler", "repository", "types")
            layer: Layer name (default: "core")
            clean: Whether to clean the directory before use (default: True)

        Returns:
            Path to output directory
        """
        # Guard: webapp generators must never clean/write packages/core.
        # FileGenerator historically defaulted layer="core"; a missing override
        # would wipe domain dirs under packages/core/src on every webapp run.
        if generator_type.startswith("webapp") and layer == "core":
            raise ValueError(
                f"Generator type '{generator_type}' cannot use layer='core'. "
                f"Pass layer='webapp_services' or layer='webapp_features'."
            )

        folder_config = FolderStructureConfig()
        output_dir = folder_config.get_layer_output_path(
            project_root=context.config.paths.project_root,
            layer=layer,
            domain_name=context.domain_name,
            generator_type=generator_type,
        )
        ensure_directory(output_dir)
        if clean:
            clean_directory(output_dir)
        return output_dir

    @staticmethod
    def get_output_directory_no_clean(
        context: GenerationContext,
        generator_type: str,
        layer: str = "core",
    ) -> Path:
        """
        Get output directory without cleaning (for generators that manage cleanup themselves).

        Args:
            context: Generation context
            generator_type: Type of generator
            layer: Layer name (default: "core")

        Returns:
            Path to output directory
        """
        return GeneratorSetup.get_output_directory(
            context, generator_type, layer, clean=False
        )
