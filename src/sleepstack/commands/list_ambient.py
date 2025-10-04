"""
List ambient sounds command module.

This module provides the CLI command for listing available ambient sounds.
"""

import argparse
import logging
import sys
from typing import List

from ..ambient_manager import get_ambient_manager


def list_ambient_command(args: argparse.Namespace) -> int:
    """
    Handle the list-ambient subcommand.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        manager = get_ambient_manager()

        if args.detailed:
            # Show detailed information
            sounds = manager.list_sounds_with_details()
            if not sounds:
                print("No ambient sounds found.")
                return 0

            print("Available ambient sounds:")
            print()
            for sound in sounds:
                print(f"  {sound['name']}")
                print(f"    Path: {sound['path']}")
                print(f"    Duration: {sound['duration']}")
                print(f"    Sample Rate: {sound['sample_rate']}")
                print(f"    File Size: {sound['file_size']}")
                if sound["source_url"]:
                    print(f"    Source: {sound['source_url']}")
                if sound["description"]:
                    print(f"    Description: {sound['description']}")
                print()
        else:
            # Show simple list
            sound_names = manager.get_available_sounds()
            if not sound_names:
                print("No ambient sounds found.")
                return 0

            print("Available ambient sounds:")
            for name in sound_names:
                print(f"  {name}")

        return 0

    except Exception as e:
        logging.error(f"Error listing ambient sounds: {e}")
        print(f"Error: {e}")
        return 1


def add_list_ambient_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """
    Add the list-ambient subcommand parser.

    Args:
        subparsers: Subparsers action from main parser
    """
    parser = subparsers.add_parser(
        "list-ambient",
        help="List available ambient sounds",
        description="List all available ambient sounds with optional detailed information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack list-ambient
  sleepstack list-ambient --detailed

The --detailed flag shows additional information including:
  - File path and size
  - Duration and sample rate
  - Source URL (if available)
  - Description (if available)
        """.strip(),
    )

    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed information about each ambient sound"
    )

    parser.set_defaults(func=list_ambient_command)
