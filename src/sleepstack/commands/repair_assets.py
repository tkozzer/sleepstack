"""
Repair assets command module.

This module provides the CLI command for repairing damaged ambient sound assets.
"""

import argparse
import logging
import sys

from ..asset_manager import get_asset_manager, AssetValidationError


def repair_assets_command(args: argparse.Namespace) -> int:
    """
    Handle the repair-assets subcommand.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        manager = get_asset_manager()
        
        if args.sound_name:
            # Repair specific sound
            if manager.repair_asset(args.sound_name):
                print(f"✓ Successfully repaired asset '{args.sound_name}'")
                return 0
            else:
                print(f"✗ Could not repair asset '{args.sound_name}'")
                return 1
        else:
            # Repair all assets
            assets = manager.list_all_assets_with_status()
            
            if not assets:
                print("No assets found.")
                return 0
            
            repaired_count = 0
            total_invalid = 0
            
            for asset in assets:
                if not asset['is_valid']:
                    total_invalid += 1
                    if manager.repair_asset(asset['name']):
                        repaired_count += 1
                        print(f"✓ Repaired {asset['name']}")
                    else:
                        print(f"✗ Could not repair {asset['name']}")
            
            if total_invalid == 0:
                print("All assets are valid - no repair needed")
                return 0
            
            print(f"\nRepair complete: {repaired_count}/{total_invalid} assets repaired")
            
            if repaired_count == total_invalid:
                return 0
            else:
                return 1
        
    except AssetValidationError as e:
        logging.error(f"Repair error: {e}")
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1


def add_repair_assets_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """
    Add the repair-assets subcommand parser.
    
    Args:
        subparsers: Subparsers action from main parser
    """
    parser = subparsers.add_parser(
        "repair-assets",
        help="Repair damaged ambient sound assets",
        description="Attempt to repair damaged ambient sound assets and their metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack repair-assets
  sleepstack repair-assets campfire
  sleepstack repair-assets rain

This command attempts to:
  - Recreate missing metadata files from WAV files
  - Fix corrupted metadata files
  - Restore missing file information
  - Clean up invalid entries

Note: This command cannot repair corrupted WAV files - only metadata issues.
        """.strip(),
    )
    
    parser.add_argument(
        "sound_name",
        nargs="?",
        help="Name of specific ambient sound to repair (repairs all if not specified)"
    )
    
    parser.set_defaults(func=repair_assets_command)
