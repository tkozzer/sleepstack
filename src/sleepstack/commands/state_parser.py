"""
State management argument parser.

This module provides argparse-based command parsers for state management.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from ..state_manager import get_state_manager
from ..asset_manager import get_asset_manager


def add_state_parser(subparsers: Any) -> Any:
    """Add state management subparser."""
    state_parser = subparsers.add_parser(
        "state",
        help="State management commands",
        description="Manage application state, asset dependencies, and maintenance operations",
    )

    state_subparsers = state_parser.add_subparsers(
        dest="state_command", help="State commands", required=True
    )

    # state show
    show_parser = state_subparsers.add_parser("show", help="Show application state")
    show_parser.add_argument("--key", "-k", help="Specific state key to show")
    show_parser.set_defaults(func=state_show)

    # state set
    set_parser = state_subparsers.add_parser("set", help="Set a state value")
    set_parser.add_argument("key", help="State key")
    set_parser.add_argument("value", help="State value")
    set_parser.set_defaults(func=state_set)

    # state dependencies
    deps_parser = state_subparsers.add_parser("dependencies", help="Show dependencies for an asset")
    deps_parser.add_argument("asset_name", help="Asset name")
    deps_parser.set_defaults(func=state_dependencies)

    # state references
    refs_parser = state_subparsers.add_parser("references", help="Show references for an asset")
    refs_parser.add_argument("asset_name", help="Asset name")
    refs_parser.set_defaults(func=state_references)

    # state maintenance
    maint_parser = state_subparsers.add_parser("maintenance", help="Show maintenance records")
    maint_parser.add_argument(
        "--limit", "-l", type=int, default=20, help="Number of records to show"
    )
    maint_parser.set_defaults(func=state_maintenance)

    # state stats
    stats_parser = state_subparsers.add_parser("stats", help="Show maintenance statistics")
    stats_parser.set_defaults(func=state_stats)

    # state health
    health_parser = state_subparsers.add_parser("health", help="Show asset health summary")
    health_parser.set_defaults(func=state_health)

    # state validate
    validate_parser = state_subparsers.add_parser("validate", help="Validate asset integrity")
    validate_parser.add_argument("asset_name", help="Asset name")
    validate_parser.set_defaults(func=state_validate)

    # state cleanup
    cleanup_parser = state_subparsers.add_parser("cleanup", help="Clean up old maintenance records")
    cleanup_parser.add_argument(
        "--days", "-d", type=int, default=30, help="Number of days to keep records"
    )
    cleanup_parser.set_defaults(func=state_cleanup)

    # state export
    export_parser = state_subparsers.add_parser("export", help="Export all state data to file")
    export_parser.add_argument("output_file", help="Output file path")
    export_parser.set_defaults(func=state_export)

    # state import
    import_parser = state_subparsers.add_parser("import", help="Import state data from file")
    import_parser.add_argument("input_file", help="Input state file")
    import_parser.set_defaults(func=state_import)

    # state clear
    clear_parser = state_subparsers.add_parser("clear", help="Clear all application state")
    clear_parser.set_defaults(func=state_clear)

    return state_parser


def state_show(args: Any) -> int:
    """Show application state."""
    state_manager = get_state_manager()

    if args.key:
        value = state_manager.get_state(args.key)
        print(f"{args.key}: {value}")
    else:
        state = state_manager.get_state()
        if not state:
            print("No application state found")
            return 0

        print("Application State:")
        for k, v in state.items():
            if isinstance(v, (dict, list)):
                print(f"  {k}: {json.dumps(v, indent=4)}")
            else:
                print(f"  {k}: {v}")

    return 0


def state_set(args: Any) -> int:
    """Set a state value."""
    state_manager = get_state_manager()

    # Try to parse as JSON first, fall back to string
    try:
        parsed_value = json.loads(args.value)
    except json.JSONDecodeError:
        parsed_value = args.value

    state_manager.set_state(args.key, parsed_value)
    print(f"Set {args.key} = {parsed_value}")
    return 0


def state_dependencies(args: Any) -> int:
    """Show dependencies for an asset."""
    state_manager = get_state_manager()
    deps = state_manager.get_dependencies(args.asset_name)
    dependents = state_manager.get_dependents(args.asset_name)

    if not deps and not dependents:
        print(f"No dependencies found for '{args.asset_name}'")
        return 0

    if deps:
        print(f"Dependencies for '{args.asset_name}':")
        for dep in deps:
            print(f"  - {dep.dependency_type}: {dep.source_asset}")
            if dep.metadata:
                print(f"    Metadata: {json.dumps(dep.metadata, indent=4)}")

    if dependents:
        print(f"Assets depending on '{args.asset_name}':")
        for dep in dependents:
            print(f"  - {dep.dependency_type}: {dep.dependent_asset}")
            if dep.metadata:
                print(f"    Metadata: {json.dumps(dep.metadata, indent=4)}")

    return 0


def state_references(args: Any) -> int:
    """Show references for an asset."""
    state_manager = get_state_manager()
    refs = state_manager.get_asset_references(args.asset_name)

    if not refs:
        print(f"No references found for '{args.asset_name}'")
        return 0

    print(f"References for '{args.asset_name}':")
    for ref in refs:
        print(f"  - {ref.reference_type}: {ref.reference_id}")
        print(f"    Created: {ref.created_at}")
        if ref.metadata:
            print(f"    Metadata: {json.dumps(ref.metadata, indent=4)}")

    return 0


def state_maintenance(args: Any) -> int:
    """Show maintenance records."""
    state_manager = get_state_manager()
    records = state_manager.get_maintenance_records(args.limit)

    if not records:
        print("No maintenance records found")
        return 0

    print(f"Maintenance Records (last {len(records)}):")
    print()

    for record in reversed(records):
        status = "✓" if record.success else "✗"
        timestamp = record.timestamp[:19]  # Remove microseconds
        asset_info = f" ({record.asset_name})" if record.asset_name else ""
        print(f"{status} {record.operation_type}{asset_info} ({timestamp})")

        if not record.success and record.error_message:
            print(f"    Error: {record.error_message}")

        if record.details:
            print(f"    Details: {json.dumps(record.details, indent=4)}")

    return 0


def state_stats(args: Any) -> int:
    """Show maintenance statistics."""
    state_manager = get_state_manager()
    stats = state_manager.get_maintenance_stats()

    print("Maintenance Statistics:")
    print(f"  Total Operations: {stats['total_operations']}")
    print(f"  Successful: {stats['successful_operations']}")
    print(f"  Failed: {stats['failed_operations']}")
    if stats["total_operations"] > 0:
        print(f"  Success Rate: {stats['success_rate']:.1%}")
    else:
        print("  Success Rate: N/A (no operations)")

    if stats["operation_types"]:
        print("  Operation Types:")
        for op_type, count in stats["operation_types"].items():
            print(f"    {op_type}: {count}")

    return 0


def state_health(args: Any) -> int:
    """Show asset health summary."""
    state_manager = get_state_manager()
    health = state_manager.get_asset_health_summary()

    print("Asset Health Summary:")
    print(f"  Total Assets: {health['total_assets']}")
    print(f"  Valid Assets: {health['valid_assets']}")
    print(f"  Invalid Assets: {health['invalid_assets']}")
    print(f"  Health: {health['health_percentage']:.1f}%")

    if health["issue_types"]:
        print("  Issue Types:")
        for issue_type, count in health["issue_types"].items():
            print(f"    {issue_type}: {count}")

    if health["invalid_assets"] > 0:
        print()
        print("Invalid Assets:")
        for asset in health["assets"]:
            if not asset["is_valid"]:
                print(f"  ✗ {asset['name']}")
                for issue in asset["issues"]:
                    print(f"    - {issue}")

    return 0


def state_validate(args: Any) -> int:
    """Validate asset integrity."""
    state_manager = get_state_manager()
    is_valid, issues = state_manager.validate_asset_integrity(args.asset_name)

    if is_valid:
        print(f"✓ Asset '{args.asset_name}' is valid")
        return 0
    else:
        print(f"✗ Asset '{args.asset_name}' has issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1


def state_cleanup(args: Any) -> int:
    """Clean up old maintenance records."""
    state_manager = get_state_manager()
    removed = state_manager.cleanup_old_records(args.days)
    print(f"Removed {removed} old maintenance records")
    return 0


def state_export(args: Any) -> int:
    """Export all state data to file."""
    state_manager = get_state_manager()
    output_path = Path(args.output_file)

    state_manager.export_state(output_path)
    print(f"State exported to {output_path}")
    return 0


def state_import(args: Any) -> int:
    """Import state data from file."""
    response = input(f"Are you sure you want to import state from {args.input_file}? (y/N): ")
    if response.lower() not in ("y", "yes"):
        print("State import cancelled")
        return 0

    state_manager = get_state_manager()
    input_path = Path(args.input_file)

    state_manager.import_state(input_path)
    print(f"State imported from {input_path}")
    return 0


def state_clear(args: Any) -> int:
    """Clear all application state."""
    response = input("Are you sure you want to clear all application state? (y/N): ")
    if response.lower() not in ("y", "yes"):
        print("State clear cancelled")
        return 0

    state_manager = get_state_manager()
    state_manager.clear_state()
    print("Application state cleared")
    return 0
