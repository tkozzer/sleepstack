#!/usr/bin/env python3
"""
CLI entry point for sleepstack package.
"""

import argparse
import logging
import sys
from importlib.metadata import version

from .main import PRESETS, ALIASES, run


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
    """CLI entry point with enhanced argument parsing."""
    parser = argparse.ArgumentParser(
        prog="sleepstack",
        description="Generate binaural beats with ambient sounds for sleep and focus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack --vibe calm -a campfire -m 5
  sleepstack --vibe deep --ambience-file my_ambience.wav -s 300
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

    # Parse known args to handle standard flags
    args, remaining_args = parser.parse_known_args()

    # Handle special commands that don't need the main functionality
    if args.list_vibes:
        list_vibes()
        sys.exit(0)

    # Set up logging
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Pass remaining args to the main functionality
    # The main.run() function will handle its own argument parsing
    try:
        exit_code = run(remaining_args)
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


if __name__ == "__main__":
    main()
