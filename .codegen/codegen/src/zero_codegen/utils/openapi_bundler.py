"""
OpenAPI Bundler - Handles OpenAPI spec bundling using redocly
"""

from pathlib import Path
from typing import Optional, List
import subprocess

from zero_codegen.base.config import DomainConfig
from zero_codegen.base.logger import Logger
from zero_codegen.base.errors import GenerationError
from zero_codegen.utils.file import file_exists
from zero_codegen.utils.openapi import dereference_common_query_params


class OpenApiBundler:
    """Handles OpenAPI spec bundling"""

    def __init__(self, logger: Logger):
        self.logger = logger

    def bundle_domain(
        self,
        domain: DomainConfig,
        source_path: Path,
        bundled_path: Path,
        openapi_dir: Path,
    ) -> bool:
        """
        Bundle a domain OpenAPI spec to JSON using redocly.

        Args:
            domain: Domain configuration
            source_path: Path to source YAML file
            bundled_path: Path where bundled JSON should be written
            openapi_dir: OpenAPI directory (for working directory)

        Returns:
            True if bundling succeeded, False otherwise

        Raises:
            GenerationError: If bundling fails
        """
        if not source_path.exists():
            # Check if openapi directory exists
            openapi_dir = source_path.parent.parent if source_path.parent.name == "src" else source_path.parent
            available_files = []

            if openapi_dir.exists():
                yaml_files = list(openapi_dir.glob("*.yaml"))
                if yaml_files:
                    available_files = [f.name for f in sorted(yaml_files)[:10]]

            error_msg = f"""
❌ Source OpenAPI spec not found: {source_path}

Domain: {domain.name}
Expected file: {source_path.name}
"""
            if available_files:
                error_msg += f"""
💡 Found these YAML files in {openapi_dir}:
   {', '.join(available_files)}

💡 Suggestions:
1. Check if the domain name matches the file name
2. Restore missing files from main branch:
   git checkout main -- openapi/
"""
            else:
                error_msg += f"""
💡 The OpenAPI directory ({openapi_dir}) exists but contains no YAML files.

💡 To restore OpenAPI files from main branch:
   git checkout main -- openapi/
"""

            raise GenerationError(error_msg.strip(), domain.name)

        # Ensure bundled directory exists
        bundled_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.debug(f"Bundling {source_path.name} -> {bundled_path.name}...")

        try:
            cmd = [
                "npx",
                "--yes",
                "@redocly/cli@latest",
                "bundle",
                str(source_path.resolve()),
                "--dereferenced",
                "-o",
                str(bundled_path.resolve()),
                "--force",
            ]

            result = subprocess.run(
                cmd,
                cwd=str(openapi_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise GenerationError(
                    f"Failed to bundle OpenAPI spec: {result.stderr}",
                    domain.name,
                    "redocly_bundle",
                )

            if not file_exists(bundled_path):
                raise GenerationError(
                    f"Bundled file not created: {bundled_path}",
                    domain.name,
                    "redocly_bundle",
                )

            # Inline common/query-params.yaml refs so downstream tools don't need external resolution
            if dereference_common_query_params(bundled_path, openapi_dir):
                self.logger.debug(f"Dereferenced common query params in {domain.name} bundle.")

            self.logger.debug(f"Bundled {domain.name} spec successfully.")
            return True

        except subprocess.TimeoutExpired:
            raise GenerationError("Bundling timed out", domain.name, "redocly_bundle")
        except Exception as e:
            raise GenerationError(
                f"Failed to bundle OpenAPI spec: {str(e)}", domain.name, "redocly_bundle"
            )

    def bundle_common_files(
        self,
        common_files: List[Path],
        output_path: Path,
        common_dir: Path,
    ) -> Optional[Path]:
        """
        Bundle all common files into a master spec.

        Args:
            common_files: List of common YAML file paths
            output_path: Path where bundled JSON should be written
            common_dir: Common directory (for working directory)

        Returns:
            Path to bundled file if successful, None otherwise
        """
        if not common_files:
            return None

        # Create a temporary master YAML that references all common files
        # For now, we'll bundle the first file and let redocly resolve $refs
        # In practice, SharedTypesGenerator handles this more carefully
        master_yaml = common_files[0]  # Start with first file

        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.debug(f"Bundling common files -> {output_path.name}...")

        try:
            cmd = [
                "npx",
                "--yes",
                "@redocly/cli@latest",
                "bundle",
                str(master_yaml.resolve()),
                "-o",
                str(output_path.resolve()),
                "--force",
            ]

            result = subprocess.run(
                cmd,
                cwd=str(common_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                self.logger.warn(f"Failed to bundle common files: {result.stderr}")
                return None

            if not file_exists(output_path):
                self.logger.warn(f"Bundled common file not created: {output_path}")
                return None

            self.logger.debug("Bundled common files successfully.")
            return output_path

        except subprocess.TimeoutExpired:
            self.logger.warn("Bundling common files timed out")
            return None
        except Exception as e:
            self.logger.warn(f"Failed to bundle common files: {str(e)}")
            return None

    def should_rebundle(self, source_path: Path, bundled_path: Path) -> bool:
        """
        Check if rebundling is needed based on file modification times.

        Args:
            source_path: Path to source YAML file
            bundled_path: Path to bundled JSON file

        Returns:
            True if rebundling is needed, False otherwise
        """
        if not bundled_path.exists():
            return True

        if not source_path.exists():
            return False

        source_mtime = source_path.stat().st_mtime
        bundled_mtime = bundled_path.stat().st_mtime
        return source_mtime > bundled_mtime
