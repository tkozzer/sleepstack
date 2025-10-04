#!/usr/bin/env python3
"""
Tests for src/sleepstack/ambient_manager.py
"""

import json
import os
import tempfile
import wave
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from sleepstack.ambient_manager import (
    AmbientSoundMetadata,
    AmbientSoundError,
    AmbientSoundManager,
    get_ambient_manager,
    get_available_ambient_sounds,
    validate_ambient_sound,
    get_ambient_sound_path,
    main,
)


class TestAmbientSoundMetadata:
    """Test AmbientSoundMetadata dataclass."""

    def test_ambient_sound_metadata_creation(self):
        """Test creating AmbientSoundMetadata with required fields."""
        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=Path("/path/to/test.wav"),
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
        )

        assert metadata.name == "test_sound"
        assert metadata.path == Path("/path/to/test.wav")
        assert metadata.duration_seconds == 60.0
        assert metadata.sample_rate == 48000
        assert metadata.channels == 2
        assert metadata.file_size_bytes == 1000000
        assert metadata.created_date is None
        assert metadata.source_url is None
        assert metadata.description is None

    def test_ambient_sound_metadata_with_optional_fields(self):
        """Test creating AmbientSoundMetadata with optional fields."""
        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=Path("/path/to/test.wav"),
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01",
            source_url="https://example.com/sound.wav",
            description="Test ambient sound",
        )

        assert metadata.created_date == "2024-01-01"
        assert metadata.source_url == "https://example.com/sound.wav"
        assert metadata.description == "Test ambient sound"


class TestAmbientSoundError:
    """Test AmbientSoundError exception."""

    def test_ambient_sound_error_creation(self):
        """Test creating AmbientSoundError."""
        error = AmbientSoundError("Test error message")
        assert str(error) == "Test error message"

    def test_ambient_sound_error_inheritance(self):
        """Test that AmbientSoundError inherits from Exception."""
        error = AmbientSoundError("Test error")
        assert isinstance(error, Exception)


class TestAmbientSoundManager:
    """Test AmbientSoundManager class."""

    def test_init_default_assets_dir(self):
        """Test AmbientSoundManager initialization with default assets directory."""
        manager = AmbientSoundManager()

        # Just verify that the manager initializes correctly
        assert manager.assets_dir is not None
        assert isinstance(manager.assets_dir, Path)
        assert manager.metadata_file == manager.assets_dir / "ambient_metadata.json"
        assert isinstance(manager._metadata_cache, dict)

    def test_init_custom_assets_dir(self):
        """Test AmbientSoundManager initialization with custom assets directory."""
        custom_dir = Path("/custom/assets")
        manager = AmbientSoundManager(assets_dir=custom_dir)

        assert manager.assets_dir == custom_dir
        assert manager.metadata_file == custom_dir / "ambient_metadata.json"

    def test_load_metadata_file_exists(self):
        """Test loading metadata from existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            metadata_file = assets_dir / "ambient_metadata.json"

            # Create test metadata file
            test_data = {
                "test_sound": {
                    "name": "test_sound",
                    "path": "/path/to/test.wav",
                    "duration_seconds": 60.0,
                    "sample_rate": 48000,
                    "channels": 2,
                    "file_size_bytes": 1000000,
                    "created_date": "2024-01-01",
                    "source_url": "https://example.com/sound.wav",
                    "description": "Test sound",
                }
            }

            with open(metadata_file, "w") as f:
                json.dump(test_data, f)

            manager = AmbientSoundManager(assets_dir=assets_dir)

            assert "test_sound" in manager._metadata_cache
            metadata = manager._metadata_cache["test_sound"]
            assert metadata.name == "test_sound"
            assert metadata.path == Path("/path/to/test.wav")
            assert metadata.duration_seconds == 60.0
            assert metadata.created_date == "2024-01-01"

    def test_load_metadata_file_not_exists(self):
        """Test loading metadata when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            manager = AmbientSoundManager(assets_dir=assets_dir)

            assert manager._metadata_cache == {}

    def test_load_metadata_corrupted_file(self):
        """Test loading metadata from corrupted file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            metadata_file = assets_dir / "ambient_metadata.json"

            # Create corrupted JSON file
            with open(metadata_file, "w") as f:
                f.write("invalid json content")

            manager = AmbientSoundManager(assets_dir=assets_dir)

            # Should start with empty cache when file is corrupted
            assert manager._metadata_cache == {}

    def test_save_metadata(self):
        """Test saving metadata to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            manager = AmbientSoundManager(assets_dir=assets_dir)

            # Add test metadata
            metadata = AmbientSoundMetadata(
                name="test_sound",
                path=Path("/path/to/test.wav"),
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
                created_date="2024-01-01",
                source_url="https://example.com/sound.wav",
                description="Test sound",
            )

            manager._metadata_cache["test_sound"] = metadata
            manager._save_metadata()

            # Verify file was created
            assert manager.metadata_file.exists()

            # Verify content
            with open(manager.metadata_file, "r") as f:
                data = json.load(f)

            assert "test_sound" in data
            assert data["test_sound"]["name"] == "test_sound"
            assert data["test_sound"]["path"] == "/path/to/test.wav"
            assert data["test_sound"]["duration_seconds"] == 60.0
            assert data["test_sound"]["created_date"] == "2024-01-01"

    def test_discover_ambient_sounds_no_assets_dir(self):
        """Test discovering sounds when assets directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir) / "nonexistent"
            manager = AmbientSoundManager(assets_dir=assets_dir)

            discovered = manager.discover_ambient_sounds()
            assert discovered == {}

    def test_discover_ambient_sounds_empty_dir(self):
        """Test discovering sounds in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            manager = AmbientSoundManager(assets_dir=assets_dir)

            discovered = manager.discover_ambient_sounds()
            assert discovered == {}

    def test_discover_ambient_sounds_with_valid_sound(self):
        """Test discovering sounds with valid WAV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            sound_dir = assets_dir / "test_sound"
            sound_dir.mkdir(parents=True)

            # Create a valid WAV file
            wav_file = sound_dir / "test_sound_1m.wav"
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                # Write 1 second of silence
                silence = b"\x00\x00" * 2 * 48000
                wf.writeframes(silence)

            manager = AmbientSoundManager(assets_dir=assets_dir)
            discovered = manager.discover_ambient_sounds()

            assert "test_sound" in discovered
            metadata = discovered["test_sound"]
            assert metadata.name == "test_sound"
            assert metadata.path == wav_file
            assert metadata.sample_rate == 48000
            assert metadata.channels == 2

    def test_discover_ambient_sounds_with_invalid_sound(self):
        """Test discovering sounds with invalid WAV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            sound_dir = assets_dir / "test_sound"
            sound_dir.mkdir(parents=True)

            # Create an invalid WAV file (wrong sample rate)
            wav_file = sound_dir / "test_sound_1m.wav"
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(44100)  # Wrong sample rate
                silence = b"\x00\x00" * 2 * 44100
                wf.writeframes(silence)

            manager = AmbientSoundManager(assets_dir=assets_dir)
            discovered = manager.discover_ambient_sounds()

            # Invalid sound should be skipped
            assert discovered == {}

    def test_validate_and_get_metadata_valid_file(self):
        """Test validating and getting metadata from valid WAV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_file = Path(temp_dir) / "test.wav"

            # Create a valid WAV file
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                silence = b"\x00\x00" * 2 * 48000  # 1 second
                wf.writeframes(silence)

            manager = AmbientSoundManager()
            metadata = manager._validate_and_get_metadata(wav_file, "test_sound")

            assert metadata.name == "test_sound"
            assert metadata.path == wav_file
            assert metadata.sample_rate == 48000
            assert metadata.channels == 2
            assert metadata.duration_seconds == 1.0
            assert metadata.file_size_bytes > 0

    def test_validate_and_get_metadata_invalid_sample_width(self):
        """Test validating WAV file with invalid sample width."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_file = Path(temp_dir) / "test.wav"

            # Create WAV file with 8-bit samples (invalid)
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(48000)
                silence = b"\x00" * 2 * 48000
                wf.writeframes(silence)

            manager = AmbientSoundManager()

            with pytest.raises(AmbientSoundError) as exc_info:
                manager._validate_and_get_metadata(wav_file, "test_sound")
            assert "Invalid sample width" in str(exc_info.value)

    def test_validate_and_get_metadata_invalid_channels(self):
        """Test validating WAV file with invalid channel count."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_file = Path(temp_dir) / "test.wav"

            # Create mono WAV file (invalid)
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)
                wf.setframerate(48000)
                silence = b"\x00\x00" * 48000
                wf.writeframes(silence)

            manager = AmbientSoundManager()

            with pytest.raises(AmbientSoundError) as exc_info:
                manager._validate_and_get_metadata(wav_file, "test_sound")
            assert "Invalid channel count" in str(exc_info.value)

    def test_validate_and_get_metadata_invalid_sample_rate(self):
        """Test validating WAV file with invalid sample rate."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_file = Path(temp_dir) / "test.wav"

            # Create WAV file with wrong sample rate
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(44100)  # Wrong sample rate
                silence = b"\x00\x00" * 2 * 44100
                wf.writeframes(silence)

            manager = AmbientSoundManager()

            with pytest.raises(AmbientSoundError) as exc_info:
                manager._validate_and_get_metadata(wav_file, "test_sound")
            assert "Invalid sample rate" in str(exc_info.value)

    def test_validate_and_get_metadata_with_cached_metadata(self):
        """Test validating WAV file with cached metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_file = Path(temp_dir) / "test.wav"

            # Create a valid WAV file
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                silence = b"\x00\x00" * 2 * 48000
                wf.writeframes(silence)

            manager = AmbientSoundManager()

            # Add cached metadata
            cached_metadata = AmbientSoundMetadata(
                name="test_sound",
                path=wav_file,
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
                created_date="2024-01-01",
                source_url="https://example.com/sound.wav",
                description="Test sound",
            )
            manager._metadata_cache["test_sound"] = cached_metadata

            metadata = manager._validate_and_get_metadata(wav_file, "test_sound")

            # Should preserve cached metadata
            assert metadata.created_date == "2024-01-01"
            assert metadata.source_url == "https://example.com/sound.wav"
            assert metadata.description == "Test sound"
            # But update basic info
            assert metadata.duration_seconds == 1.0  # Actual duration

    def test_get_available_sounds(self):
        """Test getting available sound names."""
        with patch.object(AmbientSoundManager, "discover_ambient_sounds") as mock_discover:
            mock_discover.return_value = {"sound1": Mock(), "sound2": Mock(), "sound3": Mock()}

            manager = AmbientSoundManager()
            sounds = manager.get_available_sounds()

            assert sounds == ["sound1", "sound2", "sound3"]

    def test_get_sound_metadata(self):
        """Test getting metadata for specific sound."""
        with patch.object(AmbientSoundManager, "discover_ambient_sounds") as mock_discover:
            mock_metadata = Mock()
            mock_discover.return_value = {"test_sound": mock_metadata}

            manager = AmbientSoundManager()
            metadata = manager.get_sound_metadata("test_sound")

            assert metadata == mock_metadata

    def test_get_sound_metadata_not_found(self):
        """Test getting metadata for non-existent sound."""
        with patch.object(AmbientSoundManager, "discover_ambient_sounds") as mock_discover:
            mock_discover.return_value = {}

            manager = AmbientSoundManager()
            metadata = manager.get_sound_metadata("nonexistent")

            assert metadata is None

    def test_get_sound_path(self):
        """Test getting path for specific sound."""
        with patch.object(AmbientSoundManager, "get_sound_metadata") as mock_get_metadata:
            mock_metadata = Mock()
            mock_metadata.path = Path("/path/to/sound.wav")
            mock_get_metadata.return_value = mock_metadata

            manager = AmbientSoundManager()
            path = manager.get_sound_path("test_sound")

            assert path == Path("/path/to/sound.wav")

    def test_get_sound_path_not_found(self):
        """Test getting path for non-existent sound."""
        with patch.object(AmbientSoundManager, "get_sound_metadata") as mock_get_metadata:
            mock_get_metadata.return_value = None

            manager = AmbientSoundManager()
            path = manager.get_sound_path("nonexistent")

            assert path is None

    def test_validate_sound_name(self):
        """Test validating sound name."""
        with patch.object(AmbientSoundManager, "get_sound_metadata") as mock_get_metadata:
            mock_get_metadata.return_value = Mock()  # Valid sound

            manager = AmbientSoundManager()
            assert manager.validate_sound_name("test_sound") is True

            mock_get_metadata.return_value = None  # Invalid sound
            assert manager.validate_sound_name("nonexistent") is False

    def test_add_sound_metadata(self):
        """Test adding sound metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            manager = AmbientSoundManager(assets_dir=assets_dir)

            metadata = AmbientSoundMetadata(
                name="test_sound",
                path=Path("/path/to/test.wav"),
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
            )

            manager.add_sound_metadata(metadata)

            assert "test_sound" in manager._metadata_cache
            assert manager._metadata_cache["test_sound"] == metadata
            assert manager.metadata_file.exists()

    def test_remove_sound_metadata(self):
        """Test removing sound metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            manager = AmbientSoundManager(assets_dir=assets_dir)

            # Add metadata first
            metadata = AmbientSoundMetadata(
                name="test_sound",
                path=Path("/path/to/test.wav"),
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
            )
            manager._metadata_cache["test_sound"] = metadata

            # Remove it
            result = manager.remove_sound_metadata("test_sound")

            assert result is True
            assert "test_sound" not in manager._metadata_cache

    def test_remove_sound_metadata_not_found(self):
        """Test removing non-existent sound metadata."""
        manager = AmbientSoundManager()

        result = manager.remove_sound_metadata("nonexistent")

        assert result is False

    def test_list_sounds_with_details(self):
        """Test listing sounds with details."""
        with patch.object(AmbientSoundManager, "discover_ambient_sounds") as mock_discover:
            mock_metadata = AmbientSoundMetadata(
                name="test_sound",
                path=Path("/path/to/test.wav"),
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
                source_url="https://example.com/sound.wav",
                description="Test sound",
            )
            mock_discover.return_value = {"test_sound": mock_metadata}

            manager = AmbientSoundManager()
            details = manager.list_sounds_with_details()

            assert len(details) == 1
            detail = details[0]
            assert detail["name"] == "test_sound"
            assert detail["path"] == "/path/to/test.wav"
            assert detail["duration"] == "60.0s"
            assert detail["sample_rate"] == "48000 Hz"
            assert detail["channels"] == 2
            assert detail["file_size"] == "976.6 KB"
            assert detail["source_url"] == "https://example.com/sound.wav"
            assert detail["description"] == "Test sound"

    def test_refresh_metadata(self):
        """Test refreshing metadata."""
        with patch.object(AmbientSoundManager, "discover_ambient_sounds") as mock_discover:
            # Create a real AmbientSoundMetadata object instead of Mock
            mock_metadata = AmbientSoundMetadata(
                name="test_sound",
                path=Path("/path/to/test.wav"),
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
            )
            mock_discover.return_value = {"test_sound": mock_metadata}

            manager = AmbientSoundManager()
            manager._metadata_cache = {"old_sound": Mock()}

            manager.refresh_metadata()

            assert manager._metadata_cache == {"test_sound": mock_metadata}


class TestGlobalFunctions:
    """Test global functions."""

    @patch("sleepstack.ambient_manager.AmbientSoundManager")
    def test_get_ambient_manager(self, mock_manager_class):
        """Test get_ambient_manager function."""
        mock_instance = Mock()
        mock_manager_class.return_value = mock_instance

        result = get_ambient_manager()

        assert result == mock_instance
        mock_manager_class.assert_called_once_with()

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    def test_get_available_ambient_sounds(self, mock_get_manager):
        """Test get_available_ambient_sounds function."""
        mock_manager = Mock()
        mock_manager.get_available_sounds.return_value = ["sound1", "sound2"]
        mock_get_manager.return_value = mock_manager

        result = get_available_ambient_sounds()

        assert result == ["sound1", "sound2"]
        mock_manager.get_available_sounds.assert_called_once()

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    def test_validate_ambient_sound(self, mock_get_manager):
        """Test validate_ambient_sound function."""
        mock_manager = Mock()
        mock_manager.validate_sound_name.return_value = True
        mock_get_manager.return_value = mock_manager

        result = validate_ambient_sound("test_sound")

        assert result is True
        mock_manager.validate_sound_name.assert_called_once_with("test_sound")

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    def test_get_ambient_sound_path(self, mock_get_manager):
        """Test get_ambient_sound_path function."""
        mock_manager = Mock()
        mock_path = Path("/path/to/sound.wav")
        mock_manager.get_sound_path.return_value = mock_path
        mock_get_manager.return_value = mock_manager

        result = get_ambient_sound_path("test_sound")

        assert result == mock_path
        mock_manager.get_sound_path.assert_called_once_with("test_sound")


class TestMain:
    """Test main function."""

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    @patch("sys.argv")
    def test_main_list_command(self, mock_argv, mock_get_manager):
        """Test main function with list command."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: ["ambient_manager.py", "list"][x])
        mock_argv.__len__ = Mock(return_value=2)

        mock_manager = Mock()
        mock_manager.list_sounds_with_details.return_value = [
            {
                "name": "test_sound",
                "path": "/path/to/test.wav",
                "duration": "60.0s",
                "sample_rate": "48000 Hz",
                "file_size": "976.6 KB",
                "source_url": "https://example.com/sound.wav",
                "description": "Test sound",
            }
        ]
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            main()

        mock_manager.list_sounds_with_details.assert_called_once()
        assert mock_print.call_count > 0

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    @patch("sys.argv")
    def test_main_list_command_empty(self, mock_argv, mock_get_manager):
        """Test main function with list command when no sounds found."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: ["ambient_manager.py", "list"][x])
        mock_argv.__len__ = Mock(return_value=2)

        mock_manager = Mock()
        mock_manager.list_sounds_with_details.return_value = []
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("No ambient sounds found.")

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    @patch("sys.argv")
    def test_main_default_command(self, mock_argv, mock_get_manager):
        """Test main function with default command."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: ["ambient_manager.py"][x])
        mock_argv.__len__ = Mock(return_value=1)

        mock_manager = Mock()
        mock_manager.get_available_sounds.return_value = ["sound1", "sound2"]
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            main()

        mock_manager.get_available_sounds.assert_called_once()
        assert mock_print.call_count > 0

    @patch("sleepstack.ambient_manager.get_ambient_manager")
    @patch("sys.argv")
    def test_main_default_command_empty(self, mock_argv, mock_get_manager):
        """Test main function with default command when no sounds found."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: ["ambient_manager.py"][x])
        mock_argv.__len__ = Mock(return_value=1)

        mock_manager = Mock()
        mock_manager.get_available_sounds.return_value = []
        mock_get_manager.return_value = mock_manager

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("No ambient sounds found.")


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete workflow from discovery to metadata management."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            sound_dir = assets_dir / "test_sound"
            sound_dir.mkdir(parents=True)

            # Create a valid WAV file
            wav_file = sound_dir / "test_sound_1m.wav"
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                silence = b"\x00\x00" * 2 * 48000  # 1 second
                wf.writeframes(silence)

            # Test complete workflow
            manager = AmbientSoundManager(assets_dir=assets_dir)

            # Discover sounds
            discovered = manager.discover_ambient_sounds()
            assert "test_sound" in discovered

            # Get available sounds
            sounds = manager.get_available_sounds()
            assert "test_sound" in sounds

            # Get metadata
            metadata = manager.get_sound_metadata("test_sound")
            assert metadata is not None
            assert metadata.name == "test_sound"

            # Get path
            path = manager.get_sound_path("test_sound")
            assert path == wav_file

            # Validate sound
            assert manager.validate_sound_name("test_sound") is True
            assert manager.validate_sound_name("nonexistent") is False

            # List with details
            details = manager.list_sounds_with_details()
            assert len(details) == 1
            assert details[0]["name"] == "test_sound"

    def test_metadata_persistence(self):
        """Test that metadata persists across manager instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)

            # Create first manager and add metadata
            manager1 = AmbientSoundManager(assets_dir=assets_dir)
            metadata = AmbientSoundMetadata(
                name="test_sound",
                path=Path("/path/to/test.wav"),
                duration_seconds=60.0,
                sample_rate=48000,
                channels=2,
                file_size_bytes=1000000,
                created_date="2024-01-01",
                source_url="https://example.com/sound.wav",
                description="Test sound",
            )
            manager1.add_sound_metadata(metadata)

            # Create second manager and check if metadata persists
            manager2 = AmbientSoundManager(assets_dir=assets_dir)
            assert "test_sound" in manager2._metadata_cache

            cached_metadata = manager2._metadata_cache["test_sound"]
            assert cached_metadata.created_date == "2024-01-01"
            assert cached_metadata.source_url == "https://example.com/sound.wav"
            assert cached_metadata.description == "Test sound"
