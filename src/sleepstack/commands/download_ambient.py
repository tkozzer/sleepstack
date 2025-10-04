"""
Download ambient sound command module.

This module provides the CLI command for downloading ambient sounds from YouTube.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..download_ambient import (
    download_and_process_ambient_sound,
    AmbientDownloadError,
    PrerequisiteError,
)
from ..ambient_manager import get_ambient_manager, AmbientSoundError
from ..asset_manager import get_asset_manager


def download_ambient_command(args: argparse.Namespace) -> int:
    """
    Handle the download-ambient subcommand.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """

    def progress_callback(downloaded_bytes: int, total_bytes: int) -> None:
        """Progress callback for download updates."""
        if total_bytes > 0:
            percent = (downloaded_bytes / total_bytes) * 100
            downloaded_mb = downloaded_bytes / (1024 * 1024)
            total_mb = total_bytes / (1024 * 1024)
            print(
                f"\rDownloading: {percent:.1f}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)",
                end="",
                flush=True,
            )
        else:
            downloaded_mb = downloaded_bytes / (1024 * 1024)
            print(f"\rDownloading: {downloaded_mb:.1f}MB", end="", flush=True)

    try:
        print(f"Downloading ambient sound '{args.name}' from {args.url}")
        print("Validating URL and checking prerequisites...")

        # Download and process the ambient sound
        output_path = download_and_process_ambient_sound(
            url=args.url,
            sound_name=args.name,
        )

        print(f"\n✓ Successfully downloaded and processed: {output_path}")

        # Add metadata to the ambient manager and create individual metadata file
        manager = get_ambient_manager()
        asset_manager = get_asset_manager()

        metadata = manager.get_sound_metadata(args.name)
        if metadata:
            # Update metadata with source URL if provided
            if args.url:
                metadata.source_url = args.url
            if args.description:
                metadata.description = args.description
            manager.add_sound_metadata(metadata)

            # Create individual metadata file
            asset_manager.create_individual_metadata_file(args.name, metadata)
            logging.info(f"Created individual metadata file for '{args.name}'")

        logging.info(f"Successfully downloaded and processed: {output_path}")
        print(f"✓ Downloaded ambient sound '{args.name}' from {args.url}")
        print(f"  Saved to: {output_path}")

        return 0

    except PrerequisiteError as e:
        logging.error(f"Prerequisite error: {e}")
        print(f"Error: {e}")
        return 1
    except AmbientDownloadError as e:
        logging.error(f"Download error: {e}")
        print(f"Error: {e}")
        return 1
    except AmbientSoundError as e:
        logging.error(f"Ambient sound error: {e}")
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1


def add_download_ambient_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore
    """
    Add the download-ambient subcommand parser.

    Args:
        subparsers: Subparsers action from main parser
    """
    parser = subparsers.add_parser(
        "download-ambient",
        help="Download ambient sound from YouTube",
        description="Download and process an ambient sound from a YouTube URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sleepstack download-ambient "https://www.youtube.com/watch?v=example" rain
  sleepstack download-ambient "https://youtu.be/example" ocean --description "Ocean waves"
  sleepstack download-ambient "https://www.youtube.com/watch?v=example" thunder --description "Thunderstorm sounds"

Prerequisites:
  - ffmpeg must be installed on your system
  - yt-dlp will be used to download the audio

The downloaded audio will be:
  - Converted to 48kHz stereo WAV format
  - Trimmed to 1 minute starting at 60 seconds
  - Saved to assets/ambience/<name>/<name>_1m.wav
        """.strip(),
    )

    parser.add_argument("url", help="YouTube URL to download audio from")
    parser.add_argument(
        "name", help="Name for the ambient sound (will be sanitized for filesystem use)"
    )
    parser.add_argument("--description", help="Optional description for the ambient sound")

    parser.set_defaults(func=download_ambient_command)
