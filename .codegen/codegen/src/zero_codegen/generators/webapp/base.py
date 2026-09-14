"""
Webapp FileGenerator base — isolates frontend codegen from packages/core.
"""

from ...base.generator_bases import FileGenerator


class WebappServicesFileGenerator(FileGenerator):
    """Writes under platform/webapp/src/services/domains; never touches core."""

    @property
    def output_layer(self) -> str:
        return "webapp_services"

    def should_clean(self) -> bool:
        # Pipeline layer_cleaner handles webapp wipe; generators write subdirs themselves.
        return False

    def should_generate_index(self) -> bool:
        # Domain index is produced by WebappServicesIndexGenerator.
        return False


class WebappFeaturesFileGenerator(FileGenerator):
    """Writes under platform/webapp/src/features; never touches core."""

    @property
    def output_layer(self) -> str:
        return "webapp_features"

    def should_clean(self) -> bool:
        return False

    def should_generate_index(self) -> bool:
        # Features generator writes its own feature index.ts.
        return False
