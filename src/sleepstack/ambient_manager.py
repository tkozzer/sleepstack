"""
Ambient sound discovery and management system.

This module provides functionality to discover, validate, and manage
ambient sounds in the sleepstack ecosystem.
"""

import json
import wave
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import numpy as np


@dataclass
class AmbientSoundMetadata:
    """Metadata for an ambient sound."""

    name: str
    path: Path
    duration_seconds: float
    sample_rate: int
    channels: int
    file_size_bytes: int
    created_date: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None


class AmbientSoundError(Exception):
    """Custom exception for ambient sound related errors."""

    pass


class AmbientSoundManager:
    """Manages ambient sound discovery, validation, and metadata."""

    def __init__(self, assets_dir: Optional[Path] = None):
        """
        Initialize the ambient sound manager.

        Args:
            assets_dir: Path to assets directory (defaults to project assets)
        """
        if assets_dir is None:
            # Find the project root and assets directory
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            assets_dir = project_root / "assets" / "ambience"

        self.assets_dir = assets_dir
        self.metadata_file = assets_dir / "ambient_metadata.json"
        self._metadata_cache: Dict[str, AmbientSoundMetadata] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from the metadata file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    for name, meta_dict in data.items():
                        meta_dict["path"] = Path(meta_dict["path"])
                        self._metadata_cache[name] = AmbientSoundMetadata(**meta_dict)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # If metadata file is corrupted, start fresh
                self._metadata_cache = {}

    def _save_metadata(self) -> None:
        """Save metadata to the metadata file."""
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # Convert Path objects to strings for JSON serialization
        data = {}
        for name, metadata in self._metadata_cache.items():
            meta_dict = asdict(metadata)
            meta_dict["path"] = str(meta_dict["path"])
            data[name] = meta_dict

        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def discover_ambient_sounds(self) -> Dict[str, AmbientSoundMetadata]:
        """
        Discover all ambient sounds in the assets directory.

        Returns:
            Dictionary mapping sound names to their metadata
        """
        discovered: Dict[str, AmbientSoundMetadata] = {}

        if not self.assets_dir.exists():
            return discovered

        for sound_dir in self.assets_dir.iterdir():
            if not sound_dir.is_dir():
                continue

            sound_name = sound_dir.name

            # Look for the standard 1-minute WAV file
            wav_file = sound_dir / f"{sound_name}_1m.wav"
            if wav_file.exists():
                try:
                    metadata = self._validate_and_get_metadata(wav_file, sound_name)
                    discovered[sound_name] = metadata
                except AmbientSoundError:
                    # Skip invalid files
                    continue

        return discovered

    def _validate_and_get_metadata(self, wav_path: Path, sound_name: str) -> AmbientSoundMetadata:
        """
        Validate a WAV file and extract its metadata.

        Args:
            wav_path: Path to the WAV file
            sound_name: Name of the ambient sound

        Returns:
            AmbientSoundMetadata object

        Raises:
            AmbientSoundError: If the file is invalid
        """
        try:
            with wave.open(str(wav_path), "rb") as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frames = wf.getnframes()

            # Validate format
            if sample_width != 2:
                raise AmbientSoundError(
                    f"Invalid sample width: {sample_width * 8}-bit (expected 16-bit)"
                )

            if channels != 2:
                raise AmbientSoundError(f"Invalid channel count: {channels} (expected stereo)")

            if sample_rate != 48000:
                raise AmbientSoundError(f"Invalid sample rate: {sample_rate} Hz (expected 48kHz)")

            # Calculate duration
            duration_seconds = frames / sample_rate

            # Get file size
            file_size = wav_path.stat().st_size

            # Check if we have cached metadata
            if sound_name in self._metadata_cache:
                cached = self._metadata_cache[sound_name]
                # Update path and basic info, preserve other metadata
                return AmbientSoundMetadata(
                    name=sound_name,
                    path=wav_path,
                    duration_seconds=duration_seconds,
                    sample_rate=sample_rate,
                    channels=channels,
                    file_size_bytes=file_size,
                    created_date=cached.created_date,
                    source_url=cached.source_url,
                    description=cached.description,
                )
            else:
                return AmbientSoundMetadata(
                    name=sound_name,
                    path=wav_path,
                    duration_seconds=duration_seconds,
                    sample_rate=sample_rate,
                    channels=channels,
                    file_size_bytes=file_size,
                )

        except Exception as e:
            raise AmbientSoundError(f"Failed to validate {wav_path}: {str(e)}")

    def get_available_sounds(self) -> List[str]:
        """
        Get list of available ambient sound names.

        Returns:
            List of ambient sound names
        """
        discovered = self.discover_ambient_sounds()
        return sorted(discovered.keys())

    def get_sound_metadata(self, sound_name: str) -> Optional[AmbientSoundMetadata]:
        """
        Get metadata for a specific ambient sound.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            AmbientSoundMetadata if found, None otherwise
        """
        discovered = self.discover_ambient_sounds()
        return discovered.get(sound_name)

    def get_sound_path(self, sound_name: str) -> Optional[Path]:
        """
        Get the file path for a specific ambient sound.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            Path to the WAV file if found, None otherwise
        """
        metadata = self.get_sound_metadata(sound_name)
        return metadata.path if metadata else None

    def validate_sound_name(self, sound_name: str) -> bool:
        """
        Validate that a sound name exists and is valid.

        Args:
            sound_name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        return self.get_sound_metadata(sound_name) is not None

    def add_sound_metadata(self, metadata: AmbientSoundMetadata) -> None:
        """
        Add or update metadata for an ambient sound.

        Args:
            metadata: AmbientSoundMetadata object
        """
        self._metadata_cache[metadata.name] = metadata
        self._save_metadata()

    def remove_sound_metadata(self, sound_name: str) -> bool:
        """
        Remove metadata for an ambient sound.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            True if removed, False if not found
        """
        if sound_name in self._metadata_cache:
            del self._metadata_cache[sound_name]
            self._save_metadata()
            return True
        return False

    def list_sounds_with_details(self) -> List[Dict[str, Any]]:
        """
        Get detailed information about all available sounds.

        Returns:
            List of dictionaries with sound information
        """
        discovered = self.discover_ambient_sounds()
        details = []

        for name, metadata in discovered.items():
            details.append(
                {
                    "name": name,
                    "path": str(metadata.path),
                    "duration": f"{metadata.duration_seconds:.1f}s",
                    "sample_rate": f"{metadata.sample_rate} Hz",
                    "channels": metadata.channels,
                    "file_size": f"{metadata.file_size_bytes / 1024:.1f} KB",
                    "source_url": metadata.source_url,
                    "description": metadata.description,
                }
            )

        return sorted(details, key=lambda x: x["name"])

    def refresh_metadata(self) -> None:
        """Refresh metadata by re-discovering all sounds."""
        discovered = self.discover_ambient_sounds()
        self._metadata_cache = discovered
        self._save_metadata()


def get_ambient_manager() -> AmbientSoundManager:
    """Get a global ambient sound manager instance."""
    return AmbientSoundManager()


def get_available_ambient_sounds() -> List[str]:
    """
    Get list of available ambient sound names.

    Returns:
        List of ambient sound names
    """
    manager = get_ambient_manager()
    return manager.get_available_sounds()


def validate_ambient_sound(sound_name: str) -> bool:
    """
    Validate that an ambient sound exists and is properly formatted.

    Args:
        sound_name: Name of the ambient sound

    Returns:
        True if valid, False otherwise
    """
    manager = get_ambient_manager()
    return manager.validate_sound_name(sound_name)


def get_ambient_sound_path(sound_name: str) -> Optional[Path]:
    """
    Get the file path for an ambient sound.

    Args:
        sound_name: Name of the ambient sound

    Returns:
        Path to the WAV file if found, None otherwise
    """
    manager = get_ambient_manager()
    return manager.get_sound_path(sound_name)


def main() -> None:
    """CLI entry point for testing the ambient manager."""
    import sys

    manager = get_ambient_manager()

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        sounds = manager.list_sounds_with_details()
        if not sounds:
            print("No ambient sounds found.")
            return

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
        sound_names = manager.get_available_sounds()
        if sound_names:
            print("Available ambient sounds:")
            for sound_name in sound_names:
                print(f"  {sound_name}")
        else:
            print("No ambient sounds found.")


if __name__ == "__main__":
    main()
