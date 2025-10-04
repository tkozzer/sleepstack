"""Tests for remove_ambient.py"""

import pytest
import tempfile
import json
import wave
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from sleepstack.commands.remove_ambient import (
    remove_ambient_command,
    add_remove_ambient_parser,
)
from sleepstack.ambient_manager import AmbientSoundError, AmbientSoundMetadata


class TestRemoveAmbientCommand:
    """Test remove_ambient_command function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_not_found(self, mock_get_manager):
        """Test removing an ambient sound that doesn't exist."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_sound_metadata.return_value = None
        mock_manager.get_available_sounds.return_value = ["campfire", "rain"]

        # Create args
        args = Mock()
        args.name = "nonexistent_sound"
        args.force = False

        # Test command
        result = remove_ambient_command(args)

        assert result == 1
        mock_manager.get_sound_metadata.assert_called_once_with("nonexistent_sound")
        mock_manager.get_available_sounds.assert_called_once()

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_not_found_no_available(self, mock_get_manager):
        """Test removing an ambient sound when no sounds are available."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_sound_metadata.return_value = None
        mock_manager.get_available_sounds.return_value = []

        # Create args
        args = Mock()
        args.name = "nonexistent_sound"
        args.force = False

        # Test command
        result = remove_ambient_command(args)

        assert result == 1
        mock_manager.get_sound_metadata.assert_called_once_with("nonexistent_sound")
        mock_manager.get_available_sounds.assert_called_once()

    @patch("sleepstack.commands.remove_ambient.input")
    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_with_confirmation_yes(self, mock_get_manager, mock_input):
        """Test removing an ambient sound with user confirmation."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Create mock metadata
        sound_dir = self.assets_dir / "test_sound"
        sound_dir.mkdir()
        wav_path = sound_dir / "test_sound_1m.wav"
        wav_path.touch()

        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=wav_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound",
        )

        mock_manager.get_sound_metadata.return_value = metadata
        mock_manager.remove_sound_metadata.return_value = True
        mock_input.return_value = "yes"

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = False

        # Test command
        result = remove_ambient_command(args)

        assert result == 0
        mock_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_manager.remove_sound_metadata.assert_called_once_with("test_sound")
        mock_input.assert_called_once()
        assert not sound_dir.exists()

    @patch("sleepstack.commands.remove_ambient.input")
    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_with_confirmation_no(self, mock_get_manager, mock_input):
        """Test removing an ambient sound with user cancellation."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Create mock metadata
        sound_dir = self.assets_dir / "test_sound"
        sound_dir.mkdir()
        wav_path = sound_dir / "test_sound_1m.wav"
        wav_path.touch()

        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=wav_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound",
        )

        mock_manager.get_sound_metadata.return_value = metadata
        mock_input.return_value = "no"

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = False

        # Test command
        result = remove_ambient_command(args)

        assert result == 0  # Cancellation returns 0
        mock_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_manager.remove_sound_metadata.assert_not_called()
        mock_input.assert_called_once()
        assert sound_dir.exists()  # Directory should still exist

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_with_force(self, mock_get_manager):
        """Test removing an ambient sound with --force flag."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Create mock metadata
        sound_dir = self.assets_dir / "test_sound"
        sound_dir.mkdir()
        wav_path = sound_dir / "test_sound_1m.wav"
        wav_path.touch()

        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=wav_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound",
        )

        mock_manager.get_sound_metadata.return_value = metadata
        mock_manager.remove_sound_metadata.return_value = True

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = True

        # Test command
        result = remove_ambient_command(args)

        assert result == 0
        mock_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_manager.remove_sound_metadata.assert_called_once_with("test_sound")
        assert not sound_dir.exists()

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_minimal_metadata(self, mock_get_manager):
        """Test removing an ambient sound with minimal metadata."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Create mock metadata with minimal fields
        sound_dir = self.assets_dir / "test_sound"
        sound_dir.mkdir()
        wav_path = sound_dir / "test_sound_1m.wav"
        wav_path.touch()

        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=wav_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date=None,
            source_url=None,
            description=None,
        )

        mock_manager.get_sound_metadata.return_value = metadata
        mock_manager.remove_sound_metadata.return_value = True

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = True

        # Test command
        result = remove_ambient_command(args)

        assert result == 0
        mock_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_manager.remove_sound_metadata.assert_called_once_with("test_sound")
        assert not sound_dir.exists()

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_metadata_removal_fails(self, mock_get_manager):
        """Test removing an ambient sound when metadata removal fails."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Create mock metadata
        sound_dir = self.assets_dir / "test_sound"
        sound_dir.mkdir()
        wav_path = sound_dir / "test_sound_1m.wav"
        wav_path.touch()

        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=wav_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound",
        )

        mock_manager.get_sound_metadata.return_value = metadata
        mock_manager.remove_sound_metadata.return_value = False

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = True

        # Test command
        result = remove_ambient_command(args)

        assert result == 0  # Still returns 0 even if metadata removal fails
        mock_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_manager.remove_sound_metadata.assert_called_once_with("test_sound")
        assert not sound_dir.exists()  # Directory should still be removed

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_directory_not_exists(self, mock_get_manager):
        """Test removing an ambient sound when directory doesn't exist."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Create mock metadata pointing to non-existent directory
        wav_path = Path("/nonexistent/path/test_sound_1m.wav")

        metadata = AmbientSoundMetadata(
            name="test_sound",
            path=wav_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound",
        )

        mock_manager.get_sound_metadata.return_value = metadata
        mock_manager.remove_sound_metadata.return_value = True

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = True

        # Test command
        result = remove_ambient_command(args)

        assert result == 0
        mock_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_manager.remove_sound_metadata.assert_called_once_with("test_sound")

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_ambient_sound_error(self, mock_get_manager):
        """Test handling AmbientSoundError."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = AmbientSoundError("Test ambient sound error")

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = False

        # Test command
        result = remove_ambient_command(args)

        assert result == 1

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_remove_ambient_unexpected_error(self, mock_get_manager):
        """Test handling unexpected errors."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = Exception("Unexpected error")

        # Create args
        args = Mock()
        args.name = "test_sound"
        args.force = False

        # Test command
        result = remove_ambient_command(args)

        assert result == 1


class TestAddRemoveAmbientParser:
    """Test add_remove_ambient_parser function."""

    def test_add_remove_ambient_parser(self):
        """Test adding the remove-ambient parser."""
        # Create mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        # Test function
        add_remove_ambient_parser(mock_subparsers)

        # Verify parser was added with correct name
        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "remove-ambient"

        # Verify arguments were added
        assert mock_parser.add_argument.call_count == 2  # name and --force
        assert mock_parser.set_defaults.call_count == 1

    def test_parser_arguments(self):
        """Test that parser has correct arguments."""
        import argparse

        # Create real parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add remove-ambient parser
        add_remove_ambient_parser(subparsers)

        # Test parsing with name only
        args = parser.parse_args(["remove-ambient", "test_sound"])
        assert args.name == "test_sound"
        assert args.force is False

        # Test parsing with --force
        args = parser.parse_args(["remove-ambient", "test_sound", "--force"])
        assert args.name == "test_sound"
        assert args.force is True


class TestIntegration:
    """Integration tests for remove_ambient command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_real_ambient_removal(self, mock_get_manager):
        """Test with real ambient manager and files."""
        from sleepstack.ambient_manager import AmbientSoundManager

        # Use real ambient manager with temp directory
        real_manager = AmbientSoundManager(self.assets_dir)
        mock_get_manager.return_value = real_manager

        # Create a real ambient sound
        sound_name = "test_sound"
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
            "description": "Test sound",
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Test removing with force
        args = Mock()
        args.name = sound_name
        args.force = True

        result = remove_ambient_command(args)
        assert result == 0

        # Verify files were removed
        assert not wav_path.exists()
        assert not metadata_path.exists()
        assert not sound_dir.exists()

    @patch("sleepstack.commands.remove_ambient.input")
    @patch("sleepstack.commands.remove_ambient.get_ambient_manager")
    def test_real_ambient_removal_with_confirmation(self, mock_get_manager, mock_input):
        """Test with real ambient manager and user confirmation."""
        from sleepstack.ambient_manager import AmbientSoundManager

        # Use real ambient manager with temp directory
        real_manager = AmbientSoundManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        mock_input.return_value = "yes"

        # Create a real ambient sound
        sound_name = "test_sound"
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
            "description": "Test sound",
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Test removing with confirmation
        args = Mock()
        args.name = sound_name
        args.force = False

        result = remove_ambient_command(args)
        assert result == 0

        # Verify files were removed
        assert not wav_path.exists()
        assert not metadata_path.exists()
        assert not sound_dir.exists()
        mock_input.assert_called_once()
