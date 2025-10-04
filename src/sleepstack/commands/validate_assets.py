"""
Validate assets command module.

This module provides the CLI command for validating ambient sound assets.
"""

import argparse
import logging
import sys

from ..asset_manager import get_asset_manager, AssetValidationError


def validate_assets_command(args: argparse.Namespace) -> int:
    """
    Handle the validate-assets subcommand.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        manager = get_asset_manager()

        if args.sound_name:
            # Validate specific sound
            is_valid, issues = manager.validate_asset_integrity(args.sound_name)

            if is_valid:
                print(f"✓ Asset '{args.sound_name}' is valid")
                return 0
            else:
                print(f"✗ Asset '{args.sound_name}' has issues:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
        else:
            # Validate all assets
            assets = manager.list_all_assets_with_status()

            if not assets:
                print("No assets found.")
                return 0

            valid_count = 0
            total_count = len(assets)

            for asset in assets:
                if asset["is_valid"]:
                    valid_count += 1
                    if args.verbose:
                        print(f"✓ {asset['name']}")
                else:
                    print(f"✗ {asset['name']}")
                    for issue in asset["issues"]:
                        print(f"  - {issue}")
                    if args.verbose:
                        print()

            print(f"\nValidation complete: {valid_count}/{total_count} assets are valid")

            if valid_count == total_count:
                return 0
            else:
                return 1

    except AssetValidationError as e:
        logging.error(f"Validation error: {e}")
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1


def add_validate_assets_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """
    Add the validate-assets subcommand parser.

    Args:
        subparsers: Subparsers action from main parser
    """
    parser = subparsers.add_parser(
        "validate-assets",
        help="Validate ambient sound assets",
        description="Validate the integrity of ambient sound assets and their metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack validate-assets
  sleepstack validate-assets --verbose
  sleepstack validate-assets campfire
  sleepstack validate-assets rain --verbose

This command checks:
  - WAV file format and properties (16-bit, 48kHz, stereo, ~60s duration)
  - Metadata file integrity and consistency
  - File size and hash validation
  - Directory structure compliance
        """.strip(),
    )

    parser.add_argument(
        "sound_name",
        nargs="?",
        help="Name of specific ambient sound to validate (validates all if not specified)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed output including valid assets"
    )

    parser.set_defaults(func=validate_assets_command)
