"""
Enhanced asset management system for ambient sounds.

This module provides comprehensive asset management including individual
metadata files, validation, cleanup, and error handling.
"""

import json
import os
import shutil
import wave
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from .ambient_manager import AmbientSoundMetadata, AmbientSoundError, AmbientSoundManager


class AssetValidationError(Exception):
    """Custom exception for asset validation errors."""

    pass


class AssetManager:
    """Enhanced asset manager with individual metadata files and validation."""

    def __init__(self, assets_dir: Optional[Path] = None):
        """
        Initialize the asset manager.

        Args:
            assets_dir: Path to assets directory (defaults to project assets)
        """
        if assets_dir is None:
            # Find the project root and assets directory
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            assets_dir = project_root / "assets" / "ambience"

        self.assets_dir = assets_dir
        self.ambient_manager = AmbientSoundManager(assets_dir)

    def create_individual_metadata_file(
        self, sound_name: str, metadata: AmbientSoundMetadata
    ) -> Path:
        """
        Create an individual metadata file for an ambient sound.

        Args:
            sound_name: Name of the ambient sound
            metadata: AmbientSoundMetadata object

        Returns:
            Path to the created metadata file
        """
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = sound_dir / f"{sound_name}_metadata.json"

        # Convert metadata to dict and handle Path objects
        metadata_dict = {
            "name": metadata.name,
            "path": str(metadata.path),
            "duration_seconds": metadata.duration_seconds,
            "sample_rate": metadata.sample_rate,
            "channels": metadata.channels,
            "file_size_bytes": metadata.file_size_bytes,
            "created_date": metadata.created_date or datetime.now().isoformat(),
            "source_url": metadata.source_url,
            "description": metadata.description,
            "last_modified": datetime.now().isoformat(),
            "file_hash": (
                self._calculate_file_hash(metadata.path) if metadata.path.exists() else None
            ),
        }

        with open(metadata_file, "w") as f:
            json.dump(metadata_dict, f, indent=2)

        return metadata_file

    def load_individual_metadata(self, sound_name: str) -> Optional[Dict[str, Any]]:
        """
        Load metadata from an individual metadata file.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            Dictionary with metadata or None if not found
        """
        metadata_file = self.assets_dir / sound_name / f"{sound_name}_metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, IOError):
            return None

    def validate_asset_integrity(self, sound_name: str) -> Tuple[bool, List[str]]:
        """
        Validate the integrity of an ambient sound asset.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check if sound directory exists
        sound_dir = self.assets_dir / sound_name
        if not sound_dir.exists():
            issues.append(f"Sound directory does not exist: {sound_dir}")
            return False, issues

        # Check if WAV file exists
        wav_file = sound_dir / f"{sound_name}_1m.wav"
        if not wav_file.exists():
            issues.append(f"WAV file does not exist: {wav_file}")
            return False, issues

        # Check if metadata file exists
        metadata_file = sound_dir / f"{sound_name}_metadata.json"
        if not metadata_file.exists():
            issues.append(f"Metadata file does not exist: {metadata_file}")

        # Validate WAV file format
        try:
            wav_issues = self._validate_wav_file(wav_file)
            issues.extend(wav_issues)
        except Exception as e:
            issues.append(f"Error validating WAV file: {str(e)}")

        # Validate metadata file
        if metadata_file.exists():
            try:
                metadata_issues = self._validate_metadata_file(metadata_file, wav_file)
                issues.extend(metadata_issues)
            except Exception as e:
                issues.append(f"Error validating metadata file: {str(e)}")

        return len(issues) == 0, issues

    def _validate_wav_file(self, wav_path: Path) -> List[str]:
        """
        Validate a WAV file format and properties.

        Args:
            wav_path: Path to the WAV file

        Returns:
            List of validation issues
        """
        issues = []

        try:
            with wave.open(str(wav_path), "rb") as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frames = wf.getnframes()

            # Check sample width (should be 16-bit)
            if sample_width != 2:
                issues.append(f"Invalid sample width: {sample_width * 8}-bit (expected 16-bit)")

            # Check channels (should be stereo)
            if channels != 2:
                issues.append(f"Invalid channel count: {channels} (expected stereo)")

            # Check sample rate (should be 48kHz)
            if sample_rate != 48000:
                issues.append(f"Invalid sample rate: {sample_rate} Hz (expected 48kHz)")

            # Check duration (should be approximately 60 seconds)
            duration = frames / sample_rate
            if abs(duration - 60.0) > 1.0:  # Allow 1 second tolerance
                issues.append(f"Invalid duration: {duration:.1f}s (expected ~60s)")

            # Check file size (should be reasonable)
            file_size = wav_path.stat().st_size
            expected_size = int(48000 * 2 * 2 * 60)  # 48kHz * 2 channels * 2 bytes * 60 seconds
            if file_size < expected_size * 0.8 or file_size > expected_size * 1.2:
                issues.append(
                    f"Unexpected file size: {file_size} bytes (expected ~{expected_size} bytes)"
                )

        except Exception as e:
            issues.append(f"Error reading WAV file: {str(e)}")

        return issues

    def _validate_metadata_file(self, metadata_path: Path, wav_path: Path) -> List[str]:
        """
        Validate a metadata file.

        Args:
            metadata_path: Path to the metadata file
            wav_path: Path to the corresponding WAV file

        Returns:
            List of validation issues
        """
        issues = []

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Check required fields
            required_fields = [
                "name",
                "path",
                "duration_seconds",
                "sample_rate",
                "channels",
                "file_size_bytes",
            ]
            for field in required_fields:
                if field not in metadata:
                    issues.append(f"Missing required metadata field: {field}")

            # Check if metadata matches actual file
            if metadata.get("path") != str(wav_path):
                issues.append(f"Metadata path mismatch: {metadata.get('path')} vs {wav_path}")

            # Check file size match
            if wav_path.exists():
                actual_size = wav_path.stat().st_size
                metadata_size = metadata.get("file_size_bytes")
                if metadata_size and actual_size != metadata_size:
                    issues.append(
                        f"File size mismatch: metadata={metadata_size}, actual={actual_size}"
                    )

            # Check file hash if available
            if "file_hash" in metadata and metadata["file_hash"]:
                actual_hash = self._calculate_file_hash(wav_path)
                if actual_hash != metadata["file_hash"]:
                    issues.append("File hash mismatch - file may have been modified")

        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in metadata file: {str(e)}")
        except Exception as e:
            issues.append(f"Error validating metadata file: {str(e)}")

        return issues

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash as hex string
        """
        import hashlib

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def cleanup_corrupted_assets(self, sound_name: str) -> bool:
        """
        Clean up corrupted assets for a specific sound.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            True if cleanup was performed, False if no cleanup needed
        """
        is_valid, issues = self.validate_asset_integrity(sound_name)

        if is_valid:
            return False

        sound_dir = self.assets_dir / sound_name

        # Remove corrupted files
        wav_file = sound_dir / f"{sound_name}_1m.wav"
        metadata_file = sound_dir / f"{sound_name}_metadata.json"

        removed_files = []

        if wav_file.exists():
            try:
                # Try to validate the WAV file
                wav_issues = self._validate_wav_file(wav_file)
                if wav_issues:
                    wav_file.unlink()
                    removed_files.append(str(wav_file))
            except Exception:
                wav_file.unlink()
                removed_files.append(str(wav_file))

        if metadata_file.exists():
            try:
                # Try to validate the metadata file
                metadata_issues = self._validate_metadata_file(metadata_file, wav_file)
                if metadata_issues:
                    metadata_file.unlink()
                    removed_files.append(str(metadata_file))
            except Exception:
                metadata_file.unlink()
                removed_files.append(str(metadata_file))

        # If all files were removed, remove the directory
        if removed_files and not any((sound_dir / f).exists() for f in sound_dir.iterdir()):
            sound_dir.rmdir()
            removed_files.append(str(sound_dir))

        if removed_files:
            print(f"Cleaned up corrupted files for '{sound_name}':")
            for file_path in removed_files:
                print(f"  Removed: {file_path}")
            return True

        return False

    def repair_asset(self, sound_name: str) -> bool:
        """
        Attempt to repair a damaged asset.

        Args:
            sound_name: Name of the ambient sound

        Returns:
            True if repair was successful, False otherwise
        """
        is_valid, issues = self.validate_asset_integrity(sound_name)

        if is_valid:
            return True

        sound_dir = self.assets_dir / sound_name
        wav_file = sound_dir / f"{sound_name}_1m.wav"
        metadata_file = sound_dir / f"{sound_name}_metadata.json"

        # Try to repair metadata file
        if not metadata_file.exists() and wav_file.exists():
            try:
                # Recreate metadata from WAV file
                metadata = self.ambient_manager._validate_and_get_metadata(wav_file, sound_name)
                self.create_individual_metadata_file(sound_name, metadata)
                print(f"Repaired metadata file for '{sound_name}'")
                return True
            except Exception as e:
                print(f"Failed to repair metadata for '{sound_name}': {e}")
                return False

        return False

    def list_all_assets_with_status(self) -> List[Dict[str, Any]]:
        """
        List all assets with their validation status.

        Returns:
            List of dictionaries with asset information and status
        """
        assets: List[Dict[str, Any]] = []

        if not self.assets_dir.exists():
            return assets

        for sound_dir in self.assets_dir.iterdir():
            if not sound_dir.is_dir():
                continue

            sound_name = sound_dir.name
            is_valid, issues = self.validate_asset_integrity(sound_name)

            asset_info = {
                "name": sound_name,
                "path": str(sound_dir),
                "is_valid": is_valid,
                "issues": issues,
                "has_wav": (sound_dir / f"{sound_name}_1m.wav").exists(),
                "has_metadata": (sound_dir / f"{sound_name}_metadata.json").exists(),
            }

            # Add metadata if available
            metadata = self.load_individual_metadata(sound_name)
            if metadata:
                asset_info.update(
                    {
                        "duration": metadata.get("duration_seconds", 0),
                        "sample_rate": metadata.get("sample_rate", 0),
                        "file_size": metadata.get("file_size_bytes", 0),
                        "source_url": metadata.get("source_url"),
                        "description": metadata.get("description"),
                        "created_date": metadata.get("created_date"),
                    }
                )

            assets.append(asset_info)

        return sorted(assets, key=lambda x: x["name"])


def get_asset_manager() -> AssetManager:
    """Get a global asset manager instance."""
    return AssetManager()


def main() -> None:
    """CLI entry point for testing the asset manager."""
    import sys

    manager = get_asset_manager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "validate":
            if len(sys.argv) > 2:
                sound_name = sys.argv[2]
                is_valid, issues = manager.validate_asset_integrity(sound_name)
                if is_valid:
                    print(f"Asset '{sound_name}' is valid")
                else:
                    print(f"Asset '{sound_name}' has issues:")
                    for issue in issues:
                        print(f"  - {issue}")
            else:
                print("Usage: python asset_manager.py validate <sound_name>")

        elif command == "list":
            assets = manager.list_all_assets_with_status()
            if not assets:
                print("No assets found.")
                return

            print("Assets:")
            for asset in assets:
                status = "✓" if asset["is_valid"] else "✗"
                print(f"  {status} {asset['name']}")
                if not asset["is_valid"]:
                    for issue in asset["issues"]:
                        print(f"    - {issue}")

        elif command == "cleanup":
            if len(sys.argv) > 2:
                sound_name = sys.argv[2]
                if manager.cleanup_corrupted_assets(sound_name):
                    print(f"Cleaned up corrupted assets for '{sound_name}'")
                else:
                    print(f"No cleanup needed for '{sound_name}'")
            else:
                print("Usage: python asset_manager.py cleanup <sound_name>")

        elif command == "repair":
            if len(sys.argv) > 2:
                sound_name = sys.argv[2]
                if manager.repair_asset(sound_name):
                    print(f"Repaired asset '{sound_name}'")
                else:
                    print(f"Could not repair asset '{sound_name}'")
            else:
                print("Usage: python asset_manager.py repair <sound_name>")

        else:
            print("Unknown command. Available: validate, list, cleanup, repair")
    else:
        print("Usage: python asset_manager.py <command> [args]")
        print("Commands: validate, list, cleanup, repair")


if __name__ == "__main__":
    main()
