"""Tests for asset_manager.py"""

import pytest
import tempfile
import json
import os
import wave
import hashlib
import unittest.mock
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from sleepstack.asset_manager import (
    AssetManager,
    AssetValidationError,
    get_asset_manager,
)
from sleepstack.ambient_manager import AmbientSoundMetadata


class TestAssetManager:
    """Test AssetManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)
        self.manager = AssetManager(self.assets_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_init_default_assets_dir(self):
        """Test initialization with default assets directory."""
        # Test that default initialization works without errors
        manager = AssetManager()
        assert manager.assets_dir is not None
        assert isinstance(manager.assets_dir, Path)

    def test_init_custom_assets_dir(self):
        """Test initialization with custom assets directory."""
        custom_dir = Path("/custom/assets")
        manager = AssetManager(custom_dir)
        assert manager.assets_dir == custom_dir

    def test_create_individual_metadata_file(self):
        """Test creating individual metadata file."""
        sound_name = "test_sound"
        metadata = AmbientSoundMetadata(
            name=sound_name,
            path=Path("test_sound/test_sound_1m.wav"),
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound",
        )

        result_path = self.manager.create_individual_metadata_file(sound_name, metadata)

        assert result_path.exists()
        assert result_path.name == f"{sound_name}_metadata.json"

        # Verify content
        with open(result_path, "r") as f:
            data = json.load(f)

        assert data["name"] == sound_name
        assert data["duration_seconds"] == 60.0
        assert data["sample_rate"] == 48000

    def test_load_individual_metadata_existing(self):
        """Test loading existing individual metadata."""
        sound_name = "test_sound"
        metadata_path = self.assets_dir / sound_name / f"{sound_name}_metadata.json"
        metadata_path.parent.mkdir()

        test_data = {
            "name": sound_name,
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": 1000000,
            "created_date": "2024-01-01T00:00:00Z",
            "last_modified": "2024-01-01T00:00:00Z",
            "source_url": "https://example.com",
            "description": "Test sound",
        }

        with open(metadata_path, "w") as f:
            json.dump(test_data, f)

        result = self.manager.load_individual_metadata(sound_name)

        assert result is not None
        assert result["name"] == sound_name
        assert result["duration_seconds"] == 60.0

    def test_load_individual_metadata_nonexistent(self):
        """Test loading nonexistent individual metadata."""
        result = self.manager.load_individual_metadata("nonexistent")
        assert result is None

    def test_load_individual_metadata_corrupted(self):
        """Test loading corrupted individual metadata."""
        sound_name = "test_sound"
        metadata_path = self.assets_dir / sound_name / f"{sound_name}_metadata.json"
        metadata_path.parent.mkdir()

        # Write invalid JSON
        with open(metadata_path, "w") as f:
            f.write("invalid json content")

        result = self.manager.load_individual_metadata(sound_name)
        assert result is None

    def test_validate_asset_integrity_valid(self):
        """Test validating valid asset."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file (60 seconds)
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)  # 60 seconds of silence

        # Create valid metadata
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {
            "name": sound_name,
            "path": str(wav_path),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": wav_path.stat().st_size,
            "created_date": "2024-01-01T00:00:00Z",
            "last_modified": "2024-01-01T00:00:00Z",
            "source_url": "https://example.com",
            "description": "Test sound",
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_asset_integrity_missing_wav(self):
        """Test validating asset with missing WAV file."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create metadata but no WAV file
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {"name": sound_name}

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is False
        assert any("WAV file does not exist" in issue for issue in issues)

    def test_validate_asset_integrity_missing_metadata(self):
        """Test validating asset with missing metadata file."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create WAV file but no metadata
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)  # 60 seconds

        is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is False
        assert any("Metadata file does not exist" in issue for issue in issues)

    def test_validate_asset_integrity_invalid_wav(self):
        """Test validating asset with invalid WAV file."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create invalid WAV file (wrong bit depth)
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(1)  # 8-bit instead of 16-bit
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 1 * 60)  # 60 seconds

        # Create metadata
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {
            "name": sound_name,
            "path": str(wav_path),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": wav_path.stat().st_size,
            "created_date": "2024-01-01T00:00:00Z",
            "last_modified": "2024-01-01T00:00:00Z",
            "source_url": "https://example.com",
            "description": "Test sound",
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is False
        assert any("Invalid sample width" in issue for issue in issues)

    def test_validate_asset_integrity_metadata_mismatch(self):
        """Test validating asset with metadata mismatch."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)  # 60 seconds

        # Create metadata with wrong file size
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {
            "name": sound_name,
            "path": str(wav_path),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": 999999,  # Wrong file size
            "created_date": "2024-01-01T00:00:00Z",
            "last_modified": "2024-01-01T00:00:00Z",
            "source_url": "https://example.com",
            "description": "Test sound",
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is False
        assert any("File size mismatch" in issue for issue in issues)

    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        # Create a test file
        test_file = self.assets_dir / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Calculate hash
        result_hash = self.manager._calculate_file_hash(test_file)

        # Verify hash matches expected
        expected_hash = hashlib.md5(test_content.encode()).hexdigest()
        assert result_hash == expected_hash

    def test_cleanup_corrupted_assets(self):
        """Test cleaning up corrupted assets."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create corrupted WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        wav_path.write_text("corrupted content")

        # Create metadata
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {"name": sound_name}

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        result = self.manager.cleanup_corrupted_assets(sound_name)

        assert result is True
        assert not wav_path.exists()
        assert not metadata_path.exists()
        assert not sound_dir.exists()

    def test_cleanup_corrupted_assets_nonexistent(self):
        """Test cleaning up nonexistent assets."""
        result = self.manager.cleanup_corrupted_assets("nonexistent")
        assert result is False

    def test_repair_asset(self):
        """Test repairing an asset."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)  # 60 seconds

        # Don't create metadata file (missing metadata case)
        metadata_path = sound_dir / f"{sound_name}_metadata.json"

        result = self.manager.repair_asset(sound_name)

        assert result is True
        # Should have created new metadata file
        assert metadata_path.exists()

        # Verify new metadata is valid
        with open(metadata_path, "r") as f:
            new_metadata = json.load(f)

        assert new_metadata["name"] == sound_name
        assert new_metadata["sample_rate"] == 48000
        assert new_metadata["channels"] == 2

    def test_repair_asset_nonexistent(self):
        """Test repairing nonexistent asset."""
        result = self.manager.repair_asset("nonexistent")
        assert result is False

    def test_list_all_assets_with_status(self):
        """Test listing all assets with status."""
        # Create test assets
        for sound_name in ["sound1", "sound2"]:
            sound_dir = self.assets_dir / sound_name
            sound_dir.mkdir()

            # Create WAV file
            wav_path = sound_dir / f"{sound_name}_1m.wav"
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)  # 60 seconds

            # Create metadata
            metadata_path = sound_dir / f"{sound_name}_metadata.json"
            metadata = {
                "name": sound_name,
                "path": str(wav_path),
                "duration_seconds": 60.0,
                "sample_rate": 48000,
                "channels": 2,
                "file_size_bytes": wav_path.stat().st_size,
                "created_date": "2024-01-01T00:00:00Z",
                "last_modified": "2024-01-01T00:00:00Z",
                "source_url": "https://example.com",
                "description": f"Test sound {sound_name}",
            }

            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

        result = self.manager.list_all_assets_with_status()

        assert len(result) == 2
        assert all(asset["is_valid"] is True for asset in result)
        assert all(asset["name"] in ["sound1", "sound2"] for asset in result)


class TestAssetManagerFunctions:
    """Test module-level functions."""

    def test_get_asset_manager(self):
        """Test getting asset manager instance."""
        manager = get_asset_manager()
        assert isinstance(manager, AssetManager)
        assert manager.assets_dir is not None

    def test_get_asset_manager_custom_dir(self):
        """Test getting asset manager with custom directory."""
        # The get_asset_manager function doesn't take parameters
        # We need to test AssetManager directly with custom directory
        custom_dir = Path("/custom/assets")
        manager = AssetManager(custom_dir)
        assert isinstance(manager, AssetManager)
        assert manager.assets_dir == custom_dir


class TestAssetValidationError:
    """Test AssetValidationError exception."""

    def test_asset_validation_error(self):
        """Test AssetValidationError can be raised and caught."""
        with pytest.raises(AssetValidationError):
            raise AssetValidationError("Test error message")

        try:
            raise AssetValidationError("Test error")
        except AssetValidationError as e:
            assert str(e) == "Test error"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)
        self.manager = AssetManager(self.assets_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_validate_wav_file_corrupted(self):
        """Test validating corrupted WAV file."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create corrupted WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        wav_path.write_text("not a wav file")

        issues = self.manager._validate_wav_file(wav_path)

        assert len(issues) > 0
        assert any("Error reading WAV file" in issue for issue in issues)

    def test_validate_metadata_file_corrupted(self):
        """Test validating corrupted metadata file."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2)

        # Create corrupted metadata
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata_path.write_text("invalid json")

        issues = self.manager._validate_metadata_file(metadata_path, wav_path)

        assert len(issues) > 0
        assert any("Invalid JSON" in issue for issue in issues)

    def test_validate_metadata_file_missing_fields(self):
        """Test validating metadata file with missing required fields."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)  # 60 seconds

        # Create metadata with missing required fields
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {"name": sound_name}  # Missing required fields

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        issues = self.manager._validate_metadata_file(metadata_path, wav_path)

        assert len(issues) > 0
        assert any("Missing required metadata field" in issue for issue in issues)

    def test_validate_asset_integrity_wav_validation_exception(self):
        """Test validate_asset_integrity when WAV validation raises exception."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create a file that will cause WAV validation to fail
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        wav_path.write_text("not a wav file")

        # Mock _validate_wav_file to raise an exception
        with patch.object(
            self.manager, "_validate_wav_file", side_effect=Exception("Test exception")
        ):
            is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is False
        assert any("Error validating WAV file: Test exception" in issue for issue in issues)

    def test_validate_asset_integrity_metadata_validation_exception(self):
        """Test validate_asset_integrity when metadata validation raises exception."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)

        # Create metadata file
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata_path.write_text("{}")

        # Mock _validate_metadata_file to raise an exception
        with patch.object(
            self.manager, "_validate_metadata_file", side_effect=Exception("Test exception")
        ):
            is_valid, issues = self.manager.validate_asset_integrity(sound_name)

        assert is_valid is False
        assert any("Error validating metadata file: Test exception" in issue for issue in issues)

    def test_validate_wav_file_invalid_channels(self):
        """Test WAV validation with invalid channel count."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create WAV file with mono (1 channel) instead of stereo
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)  # Mono instead of stereo
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 1 * 2 * 60)  # 60 seconds

        issues = self.manager._validate_wav_file(wav_path)

        assert len(issues) > 0
        assert any("Invalid channel count: 1 (expected stereo)" in issue for issue in issues)

    def test_validate_wav_file_invalid_sample_rate(self):
        """Test WAV validation with invalid sample rate."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create WAV file with wrong sample rate
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(44100)  # 44.1kHz instead of 48kHz
            wf.writeframes(b"\x00" * 44100 * 2 * 2 * 60)  # 60 seconds

        issues = self.manager._validate_wav_file(wav_path)

        assert len(issues) > 0
        assert any("Invalid sample rate: 44100 Hz (expected 48kHz)" in issue for issue in issues)

    def test_validate_metadata_file_hash_mismatch(self):
        """Test metadata validation with file hash mismatch."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)

        # Create metadata with wrong file hash
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {
            "name": sound_name,
            "path": str(wav_path),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": wav_path.stat().st_size,
            "file_hash": "wrong_hash_value",
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        issues = self.manager._validate_metadata_file(metadata_path, wav_path)

        assert len(issues) > 0
        assert any("File hash mismatch - file may have been modified" in issue for issue in issues)

    def test_validate_metadata_file_general_exception(self):
        """Test metadata validation with general exception."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)

        # Create metadata file with file_hash to trigger hash calculation
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {
            "name": sound_name,
            "path": str(wav_path),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": wav_path.stat().st_size,
            "file_hash": "some_hash_value",  # This will trigger hash calculation
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Mock _calculate_file_hash to raise an exception
        with patch.object(
            self.manager, "_calculate_file_hash", side_effect=Exception("Hash calculation failed")
        ):
            issues = self.manager._validate_metadata_file(metadata_path, wav_path)

        assert len(issues) > 0
        # The exception should be caught by the general exception handler
        assert any(
            "Error validating metadata file: Hash calculation failed" in issue for issue in issues
        )

    def test_cleanup_corrupted_assets_wav_validation_exception(self):
        """Test cleanup when WAV validation raises exception."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create corrupted WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        wav_path.write_text("corrupted content")

        # Mock _validate_wav_file to raise an exception
        with patch.object(
            self.manager, "_validate_wav_file", side_effect=Exception("Validation failed")
        ):
            result = self.manager.cleanup_corrupted_assets(sound_name)

        assert result is True
        assert not wav_path.exists()

    def test_cleanup_corrupted_assets_metadata_validation_exception(self):
        """Test cleanup when metadata validation raises exception."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)

        # Create metadata file
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata_path.write_text("invalid json")

        # Mock _validate_metadata_file to raise an exception
        with patch.object(
            self.manager, "_validate_metadata_file", side_effect=Exception("Validation failed")
        ):
            result = self.manager.cleanup_corrupted_assets(sound_name)

        assert result is True
        assert not metadata_path.exists()

    def test_repair_asset_already_valid(self):
        """Test repair_asset when asset is already valid."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)

        # Create valid metadata
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {
            "name": sound_name,
            "path": str(wav_path),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": wav_path.stat().st_size,
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        result = self.manager.repair_asset(sound_name)

        assert result is True

    def test_repair_asset_metadata_creation_exception(self):
        """Test repair_asset when metadata creation raises exception."""
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b"\x00" * 48000 * 2 * 2 * 60)

        # Mock create_individual_metadata_file to raise an exception
        with patch.object(
            self.manager,
            "create_individual_metadata_file",
            side_effect=Exception("Creation failed"),
        ):
            result = self.manager.repair_asset(sound_name)

        assert result is False

    def test_list_all_assets_with_status_no_assets_dir(self):
        """Test list_all_assets_with_status when assets directory doesn't exist."""
        # Create manager with non-existent directory
        non_existent_dir = Path("/non/existent/dir")
        manager = AssetManager(non_existent_dir)

        result = manager.list_all_assets_with_status()

        assert result == []

    def test_list_all_assets_with_status_non_directory_files(self):
        """Test list_all_assets_with_status with non-directory files in assets dir."""
        # Create a file (not directory) in assets dir
        file_path = self.assets_dir / "not_a_directory.txt"
        file_path.write_text("test")

        result = self.manager.list_all_assets_with_status()

        # Should skip the file and return empty list
        assert result == []


class TestMainFunction:
    """Test the main CLI function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)
        self.manager = AssetManager(self.assets_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "validate", "test_sound"])
    def test_main_validate_command_success(self, mock_get_manager):
        """Test main function with validate command - success case."""
        mock_manager = Mock()
        mock_manager.validate_asset_integrity.return_value = (True, [])
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Asset 'test_sound' is valid")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "validate", "test_sound"])
    def test_main_validate_command_with_issues(self, mock_get_manager):
        """Test main function with validate command - issues case."""
        mock_manager = Mock()
        mock_manager.validate_asset_integrity.return_value = (False, ["Issue 1", "Issue 2"])
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        expected_calls = [
            unittest.mock.call("Asset 'test_sound' has issues:"),
            unittest.mock.call("  - Issue 1"),
            unittest.mock.call("  - Issue 2"),
        ]
        mock_print.assert_has_calls(expected_calls)

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "validate"])
    def test_main_validate_command_no_args(self, mock_get_manager):
        """Test main function with validate command - no sound name."""
        mock_get_manager.return_value = Mock()

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Usage: python asset_manager.py validate <sound_name>")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "list"])
    def test_main_list_command_with_assets(self, mock_get_manager):
        """Test main function with list command - with assets."""
        mock_manager = Mock()
        mock_assets = [
            {"name": "sound1", "is_valid": True, "issues": []},
            {"name": "sound2", "is_valid": False, "issues": ["Issue 1"]},
        ]
        mock_manager.list_all_assets_with_status.return_value = mock_assets
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        expected_calls = [
            unittest.mock.call("Assets:"),
            unittest.mock.call("  ✓ sound1"),
            unittest.mock.call("  ✗ sound2"),
            unittest.mock.call("    - Issue 1"),
        ]
        mock_print.assert_has_calls(expected_calls)

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "list"])
    def test_main_list_command_no_assets(self, mock_get_manager):
        """Test main function with list command - no assets."""
        mock_manager = Mock()
        mock_manager.list_all_assets_with_status.return_value = []
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("No assets found.")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "cleanup", "test_sound"])
    def test_main_cleanup_command_success(self, mock_get_manager):
        """Test main function with cleanup command - success."""
        mock_manager = Mock()
        mock_manager.cleanup_corrupted_assets.return_value = True
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Cleaned up corrupted assets for 'test_sound'")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "cleanup", "test_sound"])
    def test_main_cleanup_command_no_cleanup(self, mock_get_manager):
        """Test main function with cleanup command - no cleanup needed."""
        mock_manager = Mock()
        mock_manager.cleanup_corrupted_assets.return_value = False
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("No cleanup needed for 'test_sound'")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "cleanup"])
    def test_main_cleanup_command_no_args(self, mock_get_manager):
        """Test main function with cleanup command - no sound name."""
        mock_get_manager.return_value = Mock()

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Usage: python asset_manager.py cleanup <sound_name>")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "repair", "test_sound"])
    def test_main_repair_command_success(self, mock_get_manager):
        """Test main function with repair command - success."""
        mock_manager = Mock()
        mock_manager.repair_asset.return_value = True
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Repaired asset 'test_sound'")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "repair", "test_sound"])
    def test_main_repair_command_failure(self, mock_get_manager):
        """Test main function with repair command - failure."""
        mock_manager = Mock()
        mock_manager.repair_asset.return_value = False
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Could not repair asset 'test_sound'")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "repair"])
    def test_main_repair_command_no_args(self, mock_get_manager):
        """Test main function with repair command - no sound name."""
        mock_get_manager.return_value = Mock()

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Usage: python asset_manager.py repair <sound_name>")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py", "unknown_command"])
    def test_main_unknown_command(self, mock_get_manager):
        """Test main function with unknown command."""
        mock_get_manager.return_value = Mock()

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        mock_print.assert_called_with("Unknown command. Available: validate, list, cleanup, repair")

    @patch("sleepstack.asset_manager.get_asset_manager")
    @patch("sys.argv", ["asset_manager.py"])
    def test_main_no_args(self, mock_get_manager):
        """Test main function with no arguments."""
        mock_get_manager.return_value = Mock()

        with patch("builtins.print") as mock_print:
            from sleepstack.asset_manager import main

            main()

        expected_calls = [
            unittest.mock.call("Usage: python asset_manager.py <command> [args]"),
            unittest.mock.call("Commands: validate, list, cleanup, repair"),
        ]
        mock_print.assert_has_calls(expected_calls)
