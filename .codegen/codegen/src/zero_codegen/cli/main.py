"""
CLI entry point for unified codegen

Enterprise-ready CLI with proper error handling, config resolution, and DDD layer support.
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

from ..base.config import Config, LogLevel
from ..base.logger import create_logger
from ..pipeline.pipeline import Pipeline, PipelineOptions
from ..utils.file import find_project_root


def find_config_file(config_path: Path) -> Path:
    """
    Find config file in multiple locations
    
    Searches in order:
    1. Provided path (if absolute or relative to current dir)
    2. Project root / .zero-codegen-merged.json
    3. Project root / .codegen-zatca / codegen-merged / .zero-codegen-merged.json
    """
    # If absolute path provided and exists, use it
    if config_path.is_absolute() and config_path.exists():
        return config_path
    
    # Try relative to current directory
    if config_path.exists():
        return config_path.resolve()
    
    # Try to find project root
    try:
        project_root = find_project_root()
        
        # Try project root
        project_config = project_root / config_path.name
        if project_config.exists():
            return project_config
        
        # Try .codegen-zatca/codegen-merged
        codegen_config = project_root / ".codegen-zatca" / "codegen-merged" / config_path.name
        if codegen_config.exists():
            return codegen_config
        
    except FileNotFoundError:
        pass
    
    # Return original path (will fail later with better error message)
    return config_path


@click.group()
@click.version_option(version="2.0.0", prog_name="zero-codegen")
def cli():
    """
    Zero CodeGen - Unified DDD-aligned code generator
    
    Generates all layers: core, services, api_server, adapters
    Following true Domain-Driven Design principles.
    
    Examples:
    
      # Initialize config file
      zero-codegen init
      
      # Generate all domains
      zero-codegen generate --all
      
      # Generate specific domain
      zero-codegen generate --domain channel
      
      # Generate specific layers
      zero-codegen generate --domain channel --layers core services
      
      # Generate with bundling
      zero-codegen generate --all --bundle
    """
    pass


@cli.command()
@click.option("--domain", "-d", multiple=True, help="Domain(s) to generate (can be specified multiple times)")
@click.option("--all", "-a", is_flag=True, help="Generate all enabled domains")
@click.option("--layers", "-l", multiple=True, help="Layers to generate: core, services, api_server, adapters, tests, postman, webapp (default: all)")
@click.option("--config", "-c", type=Path, default=Path(".zero-codegen-merged.json"), help="Config file path")
@click.option("--clean/--no-clean", "clean", default=None, help="Clean output directories before generation (default: clean)")
@click.option("--skip-build", "--no-build", is_flag=True, help="Skip build validation")
@click.option("--fail-fast/--no-fail-fast", default=True, help="Stop on first error (default: True)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--bundle", is_flag=True, help="Bundle OpenAPI YAML files before generation")
@click.option("--log-level", type=click.Choice(["debug", "info", "warn", "error"], case_sensitive=False), default="info", help="Log level")
def generate(
    domain: Tuple[str, ...],
    all: bool,
    layers: Tuple[str, ...],
    config: Path,
    clean: bool,
    skip_build: bool,
    fail_fast: bool,
    verbose: bool,
    bundle: bool,
    log_level: str,
):
    """
    Generate code for specified domains and layers
    
    Examples:
    
      # Generate all domains
      zero-codegen generate --all
      
      # Generate specific domain
      zero-codegen generate --domain channel
      
      # Generate specific layers
      zero-codegen generate --domain channel --layers core services
      
      # Generate with bundling
      zero-codegen generate --all --bundle
      
      # Generate without build validation (faster)
      zero-codegen generate --all --skip-build
    """
    try:
        # Find config file
        config_path = find_config_file(config)
        
        if not config_path.exists():
            click.echo(f"❌ Config file not found: {config_path}", err=True)
            click.echo(f"💡 Run 'zero-codegen init' to create a config file", err=True)
            click.echo(f"💡 Or specify config file with --config option", err=True)
            sys.exit(1)
        
        # Load config
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            click.echo(f"❌ Invalid JSON in config file: {config_path}", err=True)
            click.echo(f"   Error: {str(e)}", err=True)
            sys.exit(1)
        
        try:
            codegen_config = Config(**config_data)
        except Exception as e:
            click.echo(f"❌ Invalid config file: {config_path}", err=True)
            click.echo(f"   Error: {str(e)}", err=True)
            sys.exit(1)
        
        # Override config with CLI options
        if verbose:
            codegen_config.verbose = True
            codegen_config.log_level = LogLevel.DEBUG
        else:
            codegen_config.log_level = LogLevel(log_level)
        
        if clean is not None:
            codegen_config.pipeline.clean = clean
        codegen_config.pipeline.skip_build = skip_build
        codegen_config.pipeline.fail_fast = fail_fast
        
        # Validate domain selection
        if not all and not domain:
            click.echo("❌ Error: Must specify --domain or --all", err=True)
            click.echo("💡 Use 'zero-codegen generate --all' to generate all domains", err=True)
            sys.exit(1)
        
        # Validate layers
        valid_layers = {"core", "services", "api_server", "adapters", "tests", "postman", "webapp"}
        if layers:
            invalid_layers = set(layers) - valid_layers
            if invalid_layers:
                click.echo(f"❌ Invalid layers: {', '.join(invalid_layers)}", err=True)
                click.echo(f"💡 Valid layers: {', '.join(sorted(valid_layers))}", err=True)
                sys.exit(1)
        
        # Create pipeline
        logger = create_logger(
            level=codegen_config.log_level,
            verbose=codegen_config.verbose
        )
        
        try:
            pipeline = Pipeline(config=codegen_config, logger=logger)
        except Exception as e:
            click.echo(f"❌ Failed to initialize pipeline: {str(e)}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        
        # Determine domains
        domains = list(domain) if domain else None
        
        # Determine layers
        layers_list = list(layers) if layers else None
        
        # Run pipeline
        click.echo("🚀 Starting unified DDD-aligned code generation...")
        if domains:
            click.echo(f"   Domains: {', '.join(domains)}")
        else:
            click.echo("   Domains: all enabled")
        
        if layers_list:
            click.echo(f"   Layers: {', '.join(layers_list)}")
        else:
            click.echo("   Layers: all enabled")
        
        if bundle:
            click.echo("   Bundling: enabled")
        
        try:
            result = pipeline.generate(domains=domains, layers=layers_list)
        except KeyboardInterrupt:
            click.echo("\n⚠️  Generation interrupted by user", err=True)
            sys.exit(130)
        except Exception as e:
            click.echo(f"❌ Generation failed: {str(e)}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        
        # Report results
        if result.success:
            click.echo(f"\n✅ Generation completed successfully!")
            click.echo(f"   Domains processed: {result.domains_processed}")
            click.echo(f"   Domains succeeded: {result.domains_succeeded}")
            click.echo(f"   Total duration: {result.total_duration:.2f}s")
            
            if result.steps:
                click.echo(f"\n   Steps executed: {len(result.steps)}")
                if verbose:
                    for step in result.steps:
                        status = "✅" if step.success else "❌"
                        click.echo(f"   {status} {step.layer}/{step.step} ({step.duration:.2f}s)")
        else:
            click.echo(f"\n❌ Generation completed with errors", err=True)
            click.echo(f"   Domains processed: {result.domains_processed}")
            click.echo(f"   Domains succeeded: {result.domains_succeeded}")
            click.echo(f"   Domains failed: {result.domains_failed}")
            
            if result.errors:
                click.echo(f"\n   Errors:", err=True)
                for error in result.errors:
                    click.echo(f"   • {error}", err=True)
            
            if result.steps:
                failed_steps = [s for s in result.steps if not s.success]
                if failed_steps:
                    click.echo(f"\n   Failed steps:", err=True)
                    for step in failed_steps:
                        click.echo(f"   • {step.layer}/{step.step}: {step.error}", err=True)
            
            sys.exit(1)
            
    except click.Abort:
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=Path, default=Path(".zero-codegen-merged.json"), help="Output config file path")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config file without prompting")
def init(output: Path):
    """
    Initialize configuration file
    
    Creates a new configuration file with default settings.
    If the file already exists, prompts for confirmation unless --force is used.
    
    Examples:
    
      # Create default config
      zero-codegen init
      
      # Create config at specific path
      zero-codegen init --output .codegen/config.json
      
      # Overwrite existing config
      zero-codegen init --force
    """
    if output.exists() and not force:
        if not click.confirm(f"Config file {output} already exists. Overwrite?"):
            click.echo("Cancelled.")
            return
    
    # Try to find example config
    example_paths = [
        Path(__file__).parent.parent.parent / ".zero-codegen-merged.json.example",
        Path(__file__).parent.parent.parent.parent / ".zero-codegen-merged.json.example",
    ]
    
    example_path = None
    for path in example_paths:
        if path.exists():
            example_path = path
            break
    
    if example_path and example_path.exists():
        import shutil
        shutil.copy(example_path, output)
        click.echo(f"✅ Created config file from example: {output}")
        click.echo(f"💡 Edit {output} to configure your domains and paths")
    else:
        # Create minimal config
        config = {
            "version": "2.0.0",
            "domains": [
                {
                    "name": "channel",
                    "enabled": True,
                    "spec_path": "channel.openapi.yaml",
                    "bundled_path": "channel.openapi.json"
                }
            ],
            "paths": {
                "project_root": ".",
                "openapi_dir": "openapi",
                "bundled_dir": ".bundled"
            },
            "layers": {
                "core": {
                    "entities": {"enabled": True},
                    "types": {"enabled": True},
                    "repositories": {"enabled": True}
                },
                "services": {
                    "usecases": {"enabled": True},
                    "ports": {"enabled": True},
                    "dtos": {"enabled": True},
                    "policies": {"enabled": True},
                    "errors": {"enabled": True}
                },
                "api_server": {
                    "routes": {"enabled": True},
                    "openapi_types": {"enabled": True},
                    "zod_schemas": {"enabled": True},
                    "dependencies": {"enabled": True}
                },
                "adapters": {
                    "dynamodb_repositories": {"enabled": True},
                    "port_adapters": {"enabled": True}
                },
                "tests": {
                    "tests": {"enabled": True}
                },
                "postman": {
                    "collection": {"enabled": True}
                }
            },
            "pipeline": {
                "clean": False,
                "validate": True,
                "skip_build": False,
                "parallel": False,
                "fail_fast": True
            },
            "log_level": "info",
            "verbose": False
        }
        
        with open(output, "w") as f:
            json.dump(config, f, indent=2)
        
        click.echo(f"✅ Created minimal config file: {output}")
        click.echo(f"💡 Edit {output} to configure your domains and paths")


@cli.command()
@click.option("--config", "-c", type=Path, default=Path(".zero-codegen-merged.json"), help="Config file path")
@click.option("--output", "-o", type=Path, default=None, help="Output config path (default: overwrite input)")
def sync(config: Path, output: Path):
    """
    Sync domain list from OpenAPI directory

    Discovers domain names from packages/openapi-core/src *.yaml files and
    updates config.domains. Existing domain entries are preserved for overrides.

    Examples:

      # Sync domains into config (overwrites domains in place)
      zero-codegen sync

      # Sync and write to different file
      zero-codegen sync --output .zero-codegen-synced.json
    """
    try:
        config_path = find_config_file(config)

        if not config_path.exists():
            click.echo(f"❌ Config file not found: {config_path}", err=True)
            sys.exit(1)

        with open(config_path, "r") as f:
            config_data = json.load(f)

        codegen_config = Config(**config_data)
        from ..utils.openapi_discovery import sync_config_domains_from_openapi

        synced = sync_config_domains_from_openapi(codegen_config)
        out_path = output or config_path

        def _to_json_serializable(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, dict):
                return {k: _to_json_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_to_json_serializable(v) for v in obj]
            return obj

        with open(out_path, "w") as f:
            json.dump(_to_json_serializable(synced.model_dump()), f, indent=2)

        click.echo(f"✅ Synced domains from OpenAPI: {out_path}")
        click.echo(f"   Domains: {len(synced.domains)}")
        click.echo(f"   Enabled: {sum(1 for d in synced.domains if d.enabled)}")

    except Exception as e:
        click.echo(f"❌ Sync failed: {str(e)}", err=True)
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", type=Path, default=Path(".zero-codegen-merged.json"), help="Config file path")
def validate(config: Path):
    """
    Validate configuration file
    
    Checks if the configuration file is valid and can be loaded.
    
    Examples:
    
      # Validate default config
      zero-codegen validate
      
      # Validate specific config
      zero-codegen validate --config .codegen/config.json
    """
    try:
        config_path = find_config_file(config)
        
        if not config_path.exists():
            click.echo(f"❌ Config file not found: {config_path}", err=True)
            sys.exit(1)
        
        with open(config_path, "r") as f:
            config_data = json.load(f)
        
        codegen_config = Config(**config_data)
        
        click.echo(f"✅ Configuration file is valid: {config_path}")
        click.echo(f"   Domains: {len(codegen_config.domains)}")
        click.echo(f"   Enabled domains: {sum(1 for d in codegen_config.domains if d.enabled)}")
        
    except json.JSONDecodeError as e:
        click.echo(f"❌ Invalid JSON: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Invalid configuration: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
