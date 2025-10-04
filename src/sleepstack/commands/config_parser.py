"""
Configuration management argument parser.

This module provides argparse-based command parsers for configuration management.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import (
    get_config_manager,
    AppConfig,
    DownloadConfig,
    ProcessingConfig,
    UserPreferences,
)


def add_config_parser(subparsers: Any) -> Any:
    """Add configuration management subparser."""
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management commands",
        description="Manage sleepstack configuration and user preferences",
    )

    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Configuration commands", required=True
    )

    # config show
    show_parser = config_subparsers.add_parser("show", help="Show current configuration")
    show_parser.add_argument(
        "--format",
        choices=["json", "yaml", "table"],
        default="table",
        help="Output format (default: table)",
    )
    show_parser.set_defaults(func=config_show)

    # config set
    set_parser = config_subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Configuration key (e.g., download.default_sample_rate)")
    set_parser.add_argument("value", help="Configuration value")
    set_parser.set_defaults(func=config_set)

    # config get
    get_parser = config_subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("key", help="Configuration key")
    get_parser.set_defaults(func=config_get)

    # config validate
    validate_parser = config_subparsers.add_parser(
        "validate", help="Validate current configuration"
    )
    validate_parser.set_defaults(func=config_validate)

    # config reset
    reset_parser = config_subparsers.add_parser("reset", help="Reset configuration to defaults")
    reset_parser.set_defaults(func=config_reset)

    # config export
    export_parser = config_subparsers.add_parser("export", help="Export configuration to file")
    export_parser.add_argument("--output", "-o", help="Output file path")
    export_parser.set_defaults(func=config_export)

    # config import
    import_parser = config_subparsers.add_parser("import", help="Import configuration from file")
    import_parser.add_argument("input_file", help="Input configuration file")
    import_parser.set_defaults(func=config_import)

    # config history
    history_parser = config_subparsers.add_parser("history", help="Show download history")
    history_parser.add_argument(
        "--limit", "-l", type=int, default=10, help="Number of records to show"
    )
    history_parser.set_defaults(func=config_history)

    # config state
    state_parser = config_subparsers.add_parser("state", help="Show application state")
    state_parser.set_defaults(func=config_state)

    return config_parser


def config_show(args: Any) -> int:
    """Show current configuration."""
    manager = get_config_manager()
    config = manager.get_config()

    if args.format == "json":
        from dataclasses import asdict

        print(json.dumps(asdict(config), indent=2))
    elif args.format == "yaml":
        try:
            import yaml  # type: ignore[import-untyped]
            from dataclasses import asdict

            print(yaml.dump(asdict(config), default_flow_style=False))
        except ImportError:
            print(
                "YAML output requires PyYAML package. Install with: pip install PyYAML",
                file=sys.stderr,
            )
            return 1
    else:
        # Table format
        print("Current Configuration:")
        print(f"  Config File: {manager.get_config_path()}")
        print(f"  Last Updated: {config.last_updated}")
        print()

        print("Download Settings:")
        print(f"  Sample Rate: {config.download.default_sample_rate} Hz")
        print(f"  Duration: {config.download.default_duration} seconds")
        print(f"  Start Time: {config.download.default_start_time} seconds")
        print(f"  Max Download Duration: {config.download.max_download_duration} seconds")
        print(f"  Download Quality: {config.download.download_quality}")
        print(f"  Volume Adjustment: {config.download.volume_adjustment}")
        print(f"  Auto Cleanup Temp Files: {config.download.auto_cleanup_temp_files}")
        print()

        print("Processing Settings:")
        print(f"  Output Format: {config.processing.output_format}")
        print(f"  Output Codec: {config.processing.output_codec}")
        print(f"  Channels: {config.processing.channels}")
        print(f"  Fade In Duration: {config.processing.fade_in_duration} seconds")
        print(f"  Fade Out Duration: {config.processing.fade_out_duration} seconds")
        print(f"  Normalize Audio: {config.processing.normalize_audio}")
        print()

        print("User Preferences:")
        print(f"  Default Assets Dir: {config.preferences.default_assets_dir or 'Not set'}")
        print(f"  Auto Validate Downloads: {config.preferences.auto_validate_downloads}")
        print(f"  Show Download Progress: {config.preferences.show_download_progress}")
        print(f"  Backup Original Files: {config.preferences.backup_original_files}")
        print(f"  Preferred Audio Quality: {config.preferences.preferred_audio_quality}")
        print(f"  Download Timeout: {config.preferences.download_timeout} seconds")

    return 0


def config_set(args: Any) -> int:
    """Set a configuration value."""
    manager = get_config_manager()

    # Parse value based on key
    parsed_value = _parse_config_value(args.key, args.value)

    try:
        manager.update_config(**{args.key: parsed_value})
        print(f"Set {args.key} = {parsed_value}")
        return 0
    except Exception as e:
        print(f"Error setting configuration: {e}", file=sys.stderr)
        return 1


def config_get(args: Any) -> int:
    """Get a configuration value."""
    manager = get_config_manager()
    config = manager.get_config()

    try:
        value = _get_nested_value(config, args.key)
        print(f"{args.key} = {value}")
        return 0
    except KeyError:
        print(f"Configuration key '{args.key}' not found", file=sys.stderr)
        return 0


def config_validate(args: Any) -> int:
    """Validate current configuration."""
    manager = get_config_manager()
    is_valid, issues = manager.validate_config()

    if is_valid:
        print("✓ Configuration is valid")
        return 0
    else:
        print("✗ Configuration has issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1


def config_reset(args: Any) -> int:
    """Reset configuration to defaults."""
    response = input("Are you sure you want to reset configuration to defaults? (y/N): ")
    if response.lower() in ("y", "yes"):
        manager = get_config_manager()
        manager.reset_config()
        print("Configuration reset to defaults")
        return 0
    else:
        print("Configuration reset cancelled")
        return 0


def config_export(args: Any) -> int:
    """Export configuration to file."""
    manager = get_config_manager()
    config = manager.get_config()

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"sleepstack_config_{config.last_updated[:10]}.json")

    from dataclasses import asdict

    with open(output_path, "w") as f:
        json.dump(asdict(config), f, indent=2)

    print(f"Configuration exported to {output_path}")
    return 0


def config_import(args: Any) -> int:
    """Import configuration from file."""
    response = input(
        f"Are you sure you want to import configuration from {args.input_file}? (y/N): "
    )
    if response.lower() not in ("y", "yes"):
        print("Configuration import cancelled")
        return 0

    try:
        with open(args.input_file, "r") as f:
            data = json.load(f)

        # Create new config from imported data
        config = AppConfig(
            download=DownloadConfig(**data.get("download", {})),
            processing=ProcessingConfig(**data.get("processing", {})),
            preferences=UserPreferences(**data.get("preferences", {})),
        )

        manager = get_config_manager()
        manager.save_config(config)
        print(f"Configuration imported from {args.input_file}")
        return 0
    except Exception as e:
        print(f"Error importing configuration: {e}", file=sys.stderr)
        return 1


def config_history(args: Any) -> int:
    """Show download history."""
    manager = get_config_manager()
    history = manager.get_download_history()

    if not history:
        print("No download history found")
        return 0

    # Show most recent records
    recent_history = history[-args.limit :]

    print(f"Download History (last {len(recent_history)} records):")
    print()

    for record in reversed(recent_history):
        status = "✓" if record["success"] else "✗"
        timestamp = record["timestamp"][:19]  # Remove microseconds
        print(f"{status} {record['sound_name']} ({timestamp})")

        if not record["success"] and record["error_message"]:
            print(f"    Error: {record['error_message']}")

        if record["metadata"]:
            metadata = record["metadata"]
            if metadata.get("video_title"):
                print(f"    Title: {metadata['video_title']}")
            if metadata.get("file_size"):
                size_mb = metadata["file_size"] / (1024 * 1024)
                print(f"    Size: {size_mb:.1f} MB")

    return 0


def config_state(args: Any) -> int:
    """Show application state."""
    from ..state_manager import get_state_manager

    state_manager = get_state_manager()
    state = state_manager.get_state()

    if not state:
        print("No application state found")
        return 0

    print("Application State:")
    for key, value in state.items():
        if isinstance(value, (dict, list)):
            print(f"  {key}: {json.dumps(value, indent=4)}")
        else:
            print(f"  {key}: {value}")

    return 0


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
