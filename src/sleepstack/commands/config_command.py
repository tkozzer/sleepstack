"""
Configuration management CLI command.

This module provides CLI commands for managing sleepstack configuration,
user preferences, and application state.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import click

from ..config import (
    get_config_manager,
    AppConfig,
    DownloadConfig,
    ProcessingConfig,
    UserPreferences,
)
from ..state_manager import get_state_manager


@click.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml", "table"]),
    default="table",
    help="Output format",
)
def show(output_format: str) -> None:
    """Show current configuration."""
    manager = get_config_manager()
    config = manager.get_config()

    if output_format == "json":
        import json
        from dataclasses import asdict

        click.echo(json.dumps(asdict(config), indent=2))
    elif output_format == "yaml":
        try:
            import yaml
            from dataclasses import asdict

            click.echo(yaml.dump(asdict(config), default_flow_style=False))
        except ImportError:
            click.echo(
                "YAML output requires PyYAML package. Install with: pip install PyYAML", err=True
            )
            raise click.Abort()
    else:
        # Table format
        click.echo("Current Configuration:")
        click.echo(f"  Config File: {manager.get_config_path()}")
        click.echo(f"  Last Updated: {config.last_updated}")
        click.echo()

        click.echo("Download Settings:")
        click.echo(f"  Sample Rate: {config.download.default_sample_rate} Hz")
        click.echo(f"  Duration: {config.download.default_duration} seconds")
        click.echo(f"  Start Time: {config.download.default_start_time} seconds")
        click.echo(f"  Max Download Duration: {config.download.max_download_duration} seconds")
        click.echo(f"  Download Quality: {config.download.download_quality}")
        click.echo(f"  Volume Adjustment: {config.download.volume_adjustment}")
        click.echo(f"  Auto Cleanup Temp Files: {config.download.auto_cleanup_temp_files}")
        click.echo()

        click.echo("Processing Settings:")
        click.echo(f"  Output Format: {config.processing.output_format}")
        click.echo(f"  Output Codec: {config.processing.output_codec}")
        click.echo(f"  Channels: {config.processing.channels}")
        click.echo(f"  Fade In Duration: {config.processing.fade_in_duration} seconds")
        click.echo(f"  Fade Out Duration: {config.processing.fade_out_duration} seconds")
        click.echo(f"  Normalize Audio: {config.processing.normalize_audio}")
        click.echo()

        click.echo("User Preferences:")
        click.echo(f"  Default Assets Dir: {config.preferences.default_assets_dir or 'Not set'}")
        click.echo(f"  Auto Validate Downloads: {config.preferences.auto_validate_downloads}")
        click.echo(f"  Show Download Progress: {config.preferences.show_download_progress}")
        click.echo(f"  Backup Original Files: {config.preferences.backup_original_files}")
        click.echo(f"  Preferred Audio Quality: {config.preferences.preferred_audio_quality}")
        click.echo(f"  Download Timeout: {config.preferences.download_timeout} seconds")


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a configuration value."""
    manager = get_config_manager()

    # Parse value based on key
    parsed_value = _parse_config_value(key, value)

    try:
        manager.update_config(**{key: parsed_value})
        click.echo(f"Set {key} = {parsed_value}")
    except Exception as e:
        click.echo(f"Error setting configuration: {e}", err=True)
        raise click.Abort()


@config.command()
@click.argument("key")
def get(key: str) -> None:
    """Get a configuration value."""
    manager = get_config_manager()
    config = manager.get_config()

    try:
        value = _get_nested_value(config, key)
        click.echo(f"{key} = {value}")
    except KeyError:
        click.echo(f"Configuration key '{key}' not found", err=True)
        raise click.Abort()


@config.command()
def validate() -> None:
    """Validate current configuration."""
    manager = get_config_manager()
    is_valid, issues = manager.validate_config()

    if is_valid:
        click.echo("✓ Configuration is valid")
    else:
        click.echo("✗ Configuration has issues:")
        for issue in issues:
            click.echo(f"  - {issue}")
        raise click.Abort()


@config.command()
def reset() -> None:
    """Reset configuration to defaults."""
    if click.confirm("Are you sure you want to reset configuration to defaults?"):
        manager = get_config_manager()
        manager.reset_config()
        click.echo("Configuration reset to defaults")
    else:
        click.echo("Configuration reset cancelled")


@config.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export(output: Optional[str]) -> None:
    """Export configuration to file."""
    manager = get_config_manager()
    config = manager.get_config()

    if output:
        output_path = Path(output)
    else:
        output_path = Path(f"sleepstack_config_{config.last_updated[:10]}.json")

    from dataclasses import asdict

    with open(output_path, "w") as f:
        json.dump(asdict(config), f, indent=2)

    click.echo(f"Configuration exported to {output_path}")


@config.command()
@click.argument("input_file", type=click.Path(exists=True))
def import_config(input_file: str) -> None:
    """Import configuration from file."""
    if click.confirm(f"Are you sure you want to import configuration from {input_file}?"):
        try:
            with open(input_file, "r") as f:
                data = json.load(f)

            # Create new config from imported data
            config = AppConfig(
                download=DownloadConfig(**data.get("download", {})),
                processing=ProcessingConfig(**data.get("processing", {})),
                preferences=UserPreferences(**data.get("preferences", {})),
            )

            manager = get_config_manager()
            manager.save_config(config)
            click.echo(f"Configuration imported from {input_file}")
        except Exception as e:
            click.echo(f"Error importing configuration: {e}", err=True)
            raise click.Abort()
    else:
        click.echo("Configuration import cancelled")


@config.command()
@click.option("--limit", "-l", type=int, default=10, help="Number of records to show")
def history(limit: int) -> None:
    """Show download history."""
    manager = get_config_manager()
    history = manager.get_download_history()

    if not history:
        click.echo("No download history found")
        return

    # Show most recent records
    recent_history = history[-limit:]

    click.echo(f"Download History (last {len(recent_history)} records):")
    click.echo()

    for record in reversed(recent_history):
        status = "✓" if record["success"] else "✗"
        timestamp = record["timestamp"][:19]  # Remove microseconds
        click.echo(f"{status} {record['sound_name']} ({timestamp})")

        if not record["success"] and record["error_message"]:
            click.echo(f"    Error: {record['error_message']}")

        if record["metadata"]:
            metadata = record["metadata"]
            if metadata.get("video_title"):
                click.echo(f"    Title: {metadata['video_title']}")
            if metadata.get("file_size"):
                size_mb = metadata["file_size"] / (1024 * 1024)
                click.echo(f"    Size: {size_mb:.1f} MB")


@config.command()
def state() -> None:
    """Show application state."""
    state_manager = get_state_manager()
    state = state_manager.get_state()

    if not state:
        click.echo("No application state found")
        return

    click.echo("Application State:")
    for key, value in state.items():
        if isinstance(value, (dict, list)):
            click.echo(f"  {key}: {json.dumps(value, indent=4)}")
        else:
            click.echo(f"  {key}: {value}")


@config.command()
@click.option("--days", "-d", type=int, default=30, help="Number of days to keep records")
def cleanup(days: int) -> None:
    """Clean up old maintenance records."""
    state_manager = get_state_manager()
    removed = state_manager.cleanup_old_records(days)
    click.echo(f"Removed {removed} old maintenance records")


def _parse_config_value(key: str, value: str) -> Any:
    """Parse configuration value based on key."""
    # Handle nested keys like 'download.default_sample_rate'
    if "." in key:
        parts = key.split(".")
        section = parts[0]
        field = parts[1]
    else:
        section = key
        field = None

    # Type conversion based on expected field types
    if section == "download":
        if field in [
            "default_sample_rate",
            "default_duration",
            "default_start_time",
            "max_download_duration",
        ]:
            return int(value)
        elif field == "volume_adjustment":
            return float(value)
        elif field == "auto_cleanup_temp_files":
            return value.lower() in ("true", "1", "yes", "on")
    elif section == "processing":
        if field in ["channels"]:
            return int(value)
        elif field in ["fade_in_duration", "fade_out_duration"]:
            return float(value)
        elif field == "normalize_audio":
            return value.lower() in ("true", "1", "yes", "on")
    elif section == "preferences":
        if field == "download_timeout":
            return int(value)
        elif field in [
            "auto_validate_downloads",
            "show_download_progress",
            "backup_original_files",
        ]:
            return value.lower() in ("true", "1", "yes", "on")

    # Default to string
    return value


def _get_nested_value(obj: Any, key: str) -> Any:
    """Get nested value from object using dot notation."""
    if "." in key:
        parts = key.split(".")
        current = obj
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise KeyError(f"Key '{key}' not found")
        return current
    else:
        if hasattr(obj, key):
            return getattr(obj, key)
        else:
            raise KeyError(f"Key '{key}' not found")


if __name__ == "__main__":
    config()
