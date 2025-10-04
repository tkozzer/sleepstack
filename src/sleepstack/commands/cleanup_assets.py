"""
Cleanup assets command module.

This module provides the CLI command for cleaning up corrupted ambient sound assets.
"""

import argparse
import logging
import sys

from ..asset_manager import get_asset_manager, AssetValidationError


def cleanup_assets_command(args: argparse.Namespace) -> int:
    """
    Handle the cleanup-assets subcommand.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        manager = get_asset_manager()
        
        if args.sound_name:
            # Cleanup specific sound
            if manager.cleanup_corrupted_assets(args.sound_name):
                print(f"✓ Cleaned up corrupted assets for '{args.sound_name}'")
                return 0
            else:
                print(f"No cleanup needed for '{args.sound_name}'")
                return 0
        else:
            # Cleanup all assets
            assets = manager.list_all_assets_with_status()
            
            if not assets:
                print("No assets found.")
                return 0
            
            cleaned_count = 0
            total_invalid = 0
            
            for asset in assets:
                if not asset['is_valid']:
                    total_invalid += 1
                    if manager.cleanup_corrupted_assets(asset['name']):
                        cleaned_count += 1
                        print(f"✓ Cleaned up {asset['name']}")
            
            if total_invalid == 0:
                print("All assets are valid - no cleanup needed")
                return 0
            
            print(f"\nCleanup complete: {cleaned_count}/{total_invalid} assets cleaned up")
            return 0
        
    except AssetValidationError as e:
        logging.error(f"Cleanup error: {e}")
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1


def add_cleanup_assets_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """
    Add the cleanup-assets subcommand parser.
    
    Args:
        subparsers: Subparsers action from main parser
    """
    parser = subparsers.add_parser(
        "cleanup-assets",
        help="Clean up corrupted ambient sound assets",
        description="Remove corrupted ambient sound assets and their associated files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack cleanup-assets
  sleepstack cleanup-assets campfire
  sleepstack cleanup-assets rain

This command will:
  - Remove corrupted WAV files
  - Remove invalid metadata files
  - Remove empty directories
  - Clean up orphaned files

WARNING: This command permanently deletes corrupted files. Use with caution.
        """.strip(),
    )
    
    parser.add_argument(
        "sound_name",
        nargs="?",
        help="Name of specific ambient sound to cleanup (cleans up all if not specified)"
    )
    
    parser.set_defaults(func=cleanup_assets_command)
