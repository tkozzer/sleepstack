"""
Remove ambient sound command module.

This module provides the CLI command for removing ambient sounds.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

from ..ambient_manager import get_ambient_manager, AmbientSoundError


def remove_ambient_command(args: argparse.Namespace) -> int:
    """
    Handle the remove-ambient subcommand.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        manager = get_ambient_manager()

        # Check if the ambient sound exists
        metadata = manager.get_sound_metadata(args.name)
        if not metadata:
            print(f"Error: Ambient sound '{args.name}' not found.")
            available = manager.get_available_sounds()
            if available:
                print(f"Available sounds: {', '.join(available)}")
            else:
                print("No ambient sounds available.")
            return 1

        # Confirm removal unless --force is used
        if not args.force:
            print(f"Are you sure you want to remove ambient sound '{args.name}'?")
            print(f"  Path: {metadata.path}")
            print(f"  Duration: {metadata.duration_seconds:.1f}s")
            if metadata.source_url:
                print(f"  Source: {metadata.source_url}")
            if metadata.description:
                print(f"  Description: {metadata.description}")
            print()

            response = input("Type 'yes' to confirm removal: ").strip().lower()
            if response != "yes":
                print("Removal cancelled.")
                return 0

        # Remove the directory and all files
        sound_dir = metadata.path.parent
        if sound_dir.exists():
            shutil.rmtree(sound_dir)
            print(f"✓ Removed directory: {sound_dir}")

        # Remove metadata
        removed = manager.remove_sound_metadata(args.name)
        if removed:
            print(f"✓ Removed metadata for '{args.name}'")

        print(f"✓ Successfully removed ambient sound '{args.name}'")
        return 0

    except AmbientSoundError as e:
        logging.error(f"Ambient sound error: {e}")
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Error removing ambient sound: {e}")
        print(f"Error: {e}")
        return 1


def add_remove_ambient_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """
    Add the remove-ambient subcommand parser.

    Args:
        subparsers: Subparsers action from main parser
    """
    parser = subparsers.add_parser(
        "remove-ambient",
        help="Remove an ambient sound",
        description="Remove an ambient sound and its associated files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack remove-ambient rain
  sleepstack remove-ambient thunder --force

This command will:
  - Remove the ambient sound directory and all files
  - Remove the sound from the metadata registry
  - Ask for confirmation unless --force is used

Use --force to skip the confirmation prompt.
        """.strip(),
    )

    parser.add_argument("name", help="Name of the ambient sound to remove")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    parser.set_defaults(func=remove_ambient_command)
