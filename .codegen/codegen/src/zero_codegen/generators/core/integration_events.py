"""
Integration Events Generator - aggregates x-integration-events from OpenAPI specs
into packages/core/src/integration-events/generated/registry.ts
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file
from ...utils.x_codegen_extensions import aggregate_integration_events, load_domain_specs


class IntegrationEventsGenerator(BaseGenerator):
    """Generates integration event type registry from domain OpenAPI x-integration-events."""

    @property
    def name(self) -> str:
        return "Integration Events Generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def type(self) -> str:
        return "integration_events"

    def generate(self, context: GenerationContext) -> GenerateResult:
        project_root = Path(context.config.paths.project_root)
        openapi_dir = Path(context.config.paths.openapi_dir)
        domain_specs = load_domain_specs(openapi_dir, context.config.domains)
        entries = aggregate_integration_events(domain_specs)

        output_dir = project_root / "packages" / "core" / "src" / "integration-events" / "generated"
        ensure_directory(output_dir)
        registry_file = output_dir / "registry.ts"

        registry_body = self._format_registry_entries(entries)
        content = f'''/**
 * Integration event type registry (AUTO-GENERATED).
 *
 * Source: x-integration-events in OpenAPI domain specs.
 * Do not edit by hand — update YAML and re-run codegen.
 */

import type {{ IntegrationEventTypeDefinition }} from "../integration-event.types.js";

export const INTEGRATION_EVENT_TYPE_REGISTRY: IntegrationEventTypeDefinition[] = [
{registry_body}
];
'''
        write_file(registry_file, content)
        context.logger.info(
            f"Generated integration event registry with {len(entries)} type(s)"
        )
        return GenerateResult(files=[registry_file])

    @staticmethod
    def _format_registry_entries(entries: List[dict]) -> str:
        if not entries:
            return ""
        lines: List[str] = []
        for item in entries:
            event_type = str(item.get("type", ""))
            domain = str(item.get("domain", "unknown"))
            aggregate = str(item.get("aggregateType", "Unknown"))
            description = str(item.get("description", "")).replace('"', '\\"')
            delivery = str(item.get("defaultDeliveryMode", "sync"))
            if delivery not in ("sync", "async"):
                delivery = "sync"
            lines.append(
                f'  {{\n'
                f'    type: "{event_type}",\n'
                f'    domain: "{domain}",\n'
                f'    aggregateType: "{aggregate}",\n'
                f'    description: "{description}",\n'
                f'    defaultDeliveryMode: "{delivery}",\n'
                f'  }},'
            )
        return "\n".join(lines)
