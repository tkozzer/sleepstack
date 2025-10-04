"""
State management CLI command.

This module provides CLI commands for managing application state,
asset dependencies, and maintenance operations.
"""

import json
from pathlib import Path
from typing import Optional

import click

from ..state_manager import get_state_manager
from ..asset_manager import get_asset_manager


@click.group()
def state() -> None:
    """State management commands."""
    pass


@state.command()
@click.option("--key", "-k", help="Specific state key to show")
def show(key: Optional[str]) -> None:
    """Show application state."""
    state_manager = get_state_manager()

    if key:
        value = state_manager.get_state(key)
        click.echo(f"{key}: {value}")
    else:
        state = state_manager.get_state()
        if not state:
            click.echo("No application state found")
            return

        click.echo("Application State:")
        for k, v in state.items():
            if isinstance(v, (dict, list)):
                click.echo(f"  {k}: {json.dumps(v, indent=4)}")
            else:
                click.echo(f"  {k}: {v}")


@state.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a state value."""
    state_manager = get_state_manager()

    # Try to parse as JSON first, fall back to string
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    state_manager.set_state(key, parsed_value)
    click.echo(f"Set {key} = {parsed_value}")


@state.command()
@click.argument("asset_name")
def dependencies(asset_name: str) -> None:
    """Show dependencies for an asset."""
    state_manager = get_state_manager()
    deps = state_manager.get_dependencies(asset_name)
    dependents = state_manager.get_dependents(asset_name)

    if not deps and not dependents:
        click.echo(f"No dependencies found for '{asset_name}'")
        return

    if deps:
        click.echo(f"Dependencies for '{asset_name}':")
        for dep in deps:
            click.echo(f"  - {dep.dependency_type}: {dep.source_asset}")
            if dep.metadata:
                click.echo(f"    Metadata: {json.dumps(dep.metadata, indent=4)}")

    if dependents:
        click.echo(f"Assets depending on '{asset_name}':")
        for dep in dependents:
            click.echo(f"  - {dep.dependency_type}: {dep.dependent_asset}")
            if dep.metadata:
                click.echo(f"    Metadata: {json.dumps(dep.metadata, indent=4)}")


@state.command()
@click.argument("asset_name")
def references(asset_name: str) -> None:
    """Show references for an asset."""
    state_manager = get_state_manager()
    refs = state_manager.get_asset_references(asset_name)

    if not refs:
        click.echo(f"No references found for '{asset_name}'")
        return

    click.echo(f"References for '{asset_name}':")
    for ref in refs:
        click.echo(f"  - {ref.reference_type}: {ref.reference_id}")
        click.echo(f"    Created: {ref.created_at}")
        if ref.metadata:
            click.echo(f"    Metadata: {json.dumps(ref.metadata, indent=4)}")


@state.command()
@click.option("--limit", "-l", type=int, default=20, help="Number of records to show")
def maintenance(limit: int) -> None:
    """Show maintenance records."""
    state_manager = get_state_manager()
    records = state_manager.get_maintenance_records(limit)

    if not records:
        click.echo("No maintenance records found")
        return

    click.echo(f"Maintenance Records (last {len(records)}):")
    click.echo()

    for record in reversed(records):
        status = "✓" if record.success else "✗"
        timestamp = record.timestamp[:19]  # Remove microseconds
        asset_info = f" ({record.asset_name})" if record.asset_name else ""
        click.echo(f"{status} {record.operation_type}{asset_info} ({timestamp})")

        if not record.success and record.error_message:
            click.echo(f"    Error: {record.error_message}")

        if record.details:
            click.echo(f"    Details: {json.dumps(record.details, indent=4)}")


@state.command()
def stats() -> None:
    """Show maintenance statistics."""
    state_manager = get_state_manager()
    stats = state_manager.get_maintenance_stats()

    click.echo("Maintenance Statistics:")
    click.echo(f"  Total Operations: {stats['total_operations']}")
    click.echo(f"  Successful: {stats['successful_operations']}")
    click.echo(f"  Failed: {stats['failed_operations']}")
    click.echo(f"  Success Rate: {stats['success_rate']:.1%}")

    if stats["operation_types"]:
        click.echo("  Operation Types:")
        for op_type, count in stats["operation_types"].items():
            click.echo(f"    {op_type}: {count}")


@state.command()
def health() -> None:
    """Show asset health summary."""
    state_manager = get_state_manager()
    health = state_manager.get_asset_health_summary()

    click.echo("Asset Health Summary:")
    click.echo(f"  Total Assets: {health['total_assets']}")
    click.echo(f"  Valid Assets: {health['valid_assets']}")
    click.echo(f"  Invalid Assets: {health['invalid_assets']}")
    click.echo(f"  Health: {health['health_percentage']:.1f}%")

    if health["issue_types"]:
        click.echo("  Issue Types:")
        for issue_type, count in health["issue_types"].items():
            click.echo(f"    {issue_type}: {count}")

    if health["invalid_assets"] > 0:
        click.echo()
        click.echo("Invalid Assets:")
        for asset in health["assets"]:
            if not asset["is_valid"]:
                click.echo(f"  ✗ {asset['name']}")
                for issue in asset["issues"]:
                    click.echo(f"    - {issue}")


@state.command()
@click.argument("asset_name")
def validate(asset_name: str) -> None:
    """Validate asset integrity."""
    state_manager = get_state_manager()
    is_valid, issues = state_manager.validate_asset_integrity(asset_name)

    if is_valid:
        click.echo(f"✓ Asset '{asset_name}' is valid")
    else:
        click.echo(f"✗ Asset '{asset_name}' has issues:")
        for issue in issues:
            click.echo(f"  - {issue}")


@state.command()
@click.option("--days", "-d", type=int, default=30, help="Number of days to keep records")
def cleanup(days: int) -> None:
    """Clean up old maintenance records."""
    state_manager = get_state_manager()
    removed = state_manager.cleanup_old_records(days)
    click.echo(f"Removed {removed} old maintenance records")


@state.command()
@click.argument("output_file", type=click.Path())
def export(output_file: str) -> None:
    """Export all state data to file."""
    state_manager = get_state_manager()
    output_path = Path(output_file)

    state_manager.export_state(output_path)
    click.echo(f"State exported to {output_path}")


@state.command()
@click.argument("input_file", type=click.Path(exists=True))
def import_state(input_file: str) -> None:
    """Import state data from file."""
    if click.confirm(f"Are you sure you want to import state from {input_file}?"):
        state_manager = get_state_manager()
        input_path = Path(input_file)

        state_manager.import_state(input_path)
        click.echo(f"State imported from {input_path}")
    else:
        click.echo("State import cancelled")


@state.command()
def clear() -> None:
    """Clear all application state."""
    if click.confirm("Are you sure you want to clear all application state?"):
        state_manager = get_state_manager()
        state_manager.clear_state()
        click.echo("Application state cleared")
    else:
        click.echo("State clear cancelled")


if __name__ == "__main__":
    state()
