#!/usr/bin/env python3
"""
CLI entry point for sleepstack package.
"""

import argparse
import logging
import sys
from importlib.metadata import version

from .main import PRESETS, ALIASES, run
from .commands import (
    add_download_ambient_parser, 
    add_list_ambient_parser, 
    add_remove_ambient_parser,
    add_validate_assets_parser,
    add_repair_assets_parser,
    add_cleanup_assets_parser
)


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Set up logging based on verbosity flags."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", datefmt="%H:%M:%S")


def list_vibes() -> None:
    """Print available vibe presets and aliases."""
    print("Available vibe presets:")
    print()

    for name, preset in PRESETS.items():
        print(f"  {name:<12} - {preset.desc}")
        print(f"    Beat: {preset.beat} Hz, Carrier: {preset.carrier} Hz, Volume: {preset.volume}")
        print()

    if ALIASES:
        print("Aliases:")
        for alias, target in ALIASES.items():
            print(f"  {alias:<12} → {target}")
        print()


def main() -> None:
    """CLI entry point with enhanced argument parsing and subcommands."""
    parser = argparse.ArgumentParser(
        prog="sleepstack",
        description="Generate binaural beats with ambient sounds for sleep and focus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate binaural beats with ambient sounds
  sleepstack --vibe calm -a campfire -m 5
  sleepstack --vibe deep --ambience-file my_ambience.wav -s 300
  sleepstack --vibe calm -a campfire,rain,ocean -m 5

  # Manage ambient sounds
  sleepstack download-ambient "https://youtube.com/watch?v=example" rain
  sleepstack list-ambient --detailed
  sleepstack remove-ambient thunder
  
  # Asset management
  sleepstack validate-assets
  sleepstack repair-assets campfire
  sleepstack cleanup-assets

  # Other commands
  sleepstack --list-vibes
  sleepstack --version

For more information, see the user guide in _docs/user-guide.md
        """.strip(),
    )

    # Standard CLI flags
    parser.add_argument(
        "--version", action="version", version=f"sleepstack {version('sleepstack')}"
    )
    parser.add_argument(
        "--list-vibes", action="store_true", help="List all available vibe presets and aliases"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        metavar="COMMAND",
        required=False
    )

    # Add subcommand parsers
    add_download_ambient_parser(subparsers)
    add_list_ambient_parser(subparsers)
    add_remove_ambient_parser(subparsers)
    add_validate_assets_parser(subparsers)
    add_repair_assets_parser(subparsers)
    add_cleanup_assets_parser(subparsers)

    # Check if the first argument is a known subcommand
    known_commands = [
        'download-ambient', 'list-ambient', 'remove-ambient',
        'validate-assets', 'repair-assets', 'cleanup-assets'
    ]
    first_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    # If no arguments provided, show help with subcommands
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    if first_arg in known_commands:
        # Parse as subcommand
        args = parser.parse_args()
        
        # Handle special commands that don't need the main functionality
        if args.list_vibes:
            list_vibes()
            sys.exit(0)

        # Set up logging
        setup_logging(verbose=args.verbose, quiet=args.quiet)

        # Handle subcommands
        if hasattr(args, 'func'):
            try:
                exit_code = args.func(args)
                sys.exit(exit_code)
            except KeyboardInterrupt:
                logging.info("Interrupted by user")
                sys.exit(130)
            except Exception as e:
                if args.verbose:
                    logging.exception("Unexpected error occurred")
                else:
                    logging.error(f"Error: {e}")
                sys.exit(1)
    else:
        # Parse as main command (backward compatibility)
        # Only parse global flags, pass the rest to main.run()
        global_parser = argparse.ArgumentParser(add_help=False)
        global_parser.add_argument("--verbose", "-v", action="store_true")
        global_parser.add_argument("--quiet", "-q", action="store_true")
        global_parser.add_argument("--list-vibes", action="store_true")
        global_parser.add_argument("--version", action="version", version=f"sleepstack {version('sleepstack')}")
        
        try:
            global_args, remaining_args = global_parser.parse_known_args()
        except SystemExit:
            # If --version or --help was used, let it handle it
            return
        
        # Handle special commands that don't need the main functionality
        if global_args.list_vibes:
            list_vibes()
            sys.exit(0)

        # Set up logging
        setup_logging(verbose=global_args.verbose, quiet=global_args.quiet)

        # Pass remaining args to the main functionality
        try:
            exit_code = run(remaining_args)
            sys.exit(exit_code)
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            sys.exit(130)
        except Exception as e:
            if global_args.verbose:
                logging.exception("Unexpected error occurred")
            else:
                logging.error(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
