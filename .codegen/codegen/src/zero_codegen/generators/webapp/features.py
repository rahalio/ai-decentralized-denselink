"""
Webapp Features Generator

Generates webapp feature layer scaffolding:
- Components directory structure
- Views directory structure
- Index files
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...base.generator_bases import FileGenerator
from ...utils.file import ensure_directory, write_file
from ...utils.string import pascal_case
from ...utils.generator_setup import GeneratorSetup
from .base import WebappFeaturesFileGenerator


class WebappFeaturesGenerator(WebappFeaturesFileGenerator):
    """
    Generates feature layer scaffolding (components, views, index)
    """

    @property
    def name(self) -> str:
        return "Webapp Features Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "webapp_features"

    def generate_files(
        self, context: GenerationContext, output_dir: Path
    ) -> List[Path]:
        """Generate feature layer structure"""
        files: List[Path] = []

        # Use generator setup to get proper output directory
        output_dir = GeneratorSetup.get_output_directory(
            context, self.type, layer="webapp_features", clean=False
        )

        domain_name = context.domain_name
        domain_pascal = pascal_case(domain_name)

        # Create components directory
        components_dir = output_dir / "components"
        ensure_directory(components_dir)

        # Create components index.ts
        components_index = components_dir / "index.ts"
        components_index_content = f'''/**
 * {domain_pascal} Components
 *
 * Domain-specific UI components for {domain_name} domain.
 * Components should be imported from features, not from services.
 */

// TODO: Export components as they are created
// export {{ ComponentName }} from "./ComponentName";
'''
        write_file(components_index, components_index_content)
        files.append(components_index)

        # Create views directory
        views_dir = output_dir / "views"
        ensure_directory(views_dir)

        # Create a basic view file
        view_name = f"{domain_pascal}View"
        view_file = views_dir / f"{view_name}.tsx"
        view_content = f'''/**
 * {domain_pascal} View
 *
 * Main view component for {domain_name} domain.
 */

import {{ {domain_pascal}ViewProps }} from "./types";

export function {view_name}({{}}: {domain_pascal}ViewProps) {{
  return (
    <div>
      <h1>{domain_pascal} View</h1>
      <p>This is a generated view component for the {domain_name} domain.</p>
      {{/* TODO: Implement view */}}
    </div>
  );
}}
'''
        write_file(view_file, view_content)
        files.append(view_file)

        # Create views types file
        views_types = views_dir / "types.ts"
        views_types_content = f'''/**
 * {domain_pascal} View Types
 *
 * Type definitions for {domain_name} views.
 */

export interface {domain_pascal}ViewProps {{
  // TODO: Add view props
}}
'''
        write_file(views_types, views_types_content)
        files.append(views_types)

        # Create views index.ts
        views_index = views_dir / "index.ts"
        views_index_content = f'''/**
 * {domain_pascal} Views
 *
 * Barrel export for {domain_name} views.
 */

export {{ {view_name} }} from "./{view_name}";
export type {{ {domain_pascal}ViewProps }} from "./types";
'''
        write_file(views_index, views_index_content)
        files.append(views_index)

        # Create main feature index.ts
        feature_index = output_dir / "index.ts"
        feature_index_content = f'''/**
 * {domain_pascal} Feature
 *
 * Barrel export for {domain_name} feature layer.
 * Includes components and views.
 */

// Components
export * from "./components";

// Views
export * from "./views";
'''
        write_file(feature_index, feature_index_content)
        files.append(feature_index)

        return files
