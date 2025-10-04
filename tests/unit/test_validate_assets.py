"""Tests for validate_assets.py"""

import pytest
import tempfile
import json
import wave
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from sleepstack.commands.validate_assets import (
    validate_assets_command,
    add_validate_assets_parser,
)
from sleepstack.asset_manager import AssetValidationError


class TestValidateAssetsCommand:
    """Test validate_assets_command function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_specific_sound_valid(self, mock_get_manager):
        """Test validating a specific valid sound."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.validate_asset_integrity.return_value = (True, [])

        # Create args
        args = Mock()
        args.sound_name = "campfire"
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 0
        mock_manager.validate_asset_integrity.assert_called_once_with("campfire")

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_specific_sound_invalid(self, mock_get_manager):
        """Test validating a specific invalid sound."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.validate_asset_integrity.return_value = (
            False,
            ["Missing WAV file", "Invalid metadata"],
        )

        # Create args
        args = Mock()
        args.sound_name = "broken_sound"
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 1
        mock_manager.validate_asset_integrity.assert_called_once_with("broken_sound")

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_all_assets_empty(self, mock_get_manager):
        """Test validating all assets when none exist."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = []

        # Create args
        args = Mock()
        args.sound_name = None
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_all_assets_mixed(self, mock_get_manager):
        """Test validating all assets with mixed validity."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {"name": "valid_sound", "is_valid": True, "issues": []},
            {"name": "invalid_sound", "is_valid": False, "issues": ["Missing WAV file"]},
        ]

        # Create args
        args = Mock()
        args.sound_name = None
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 1  # Some assets invalid
        mock_manager.list_all_assets_with_status.assert_called_once()

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_all_assets_verbose(self, mock_get_manager):
        """Test validating all assets with verbose output."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {"name": "valid_sound", "is_valid": True, "issues": []}
        ]

        # Create args
        args = Mock()
        args.sound_name = None
        args.verbose = True

        # Test command
        result = validate_assets_command(args)

        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_assets_validation_error(self, mock_get_manager):
        """Test handling AssetValidationError."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = AssetValidationError("Test validation error")

        # Create args
        args = Mock()
        args.sound_name = "test_sound"
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 1

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_assets_unexpected_error(self, mock_get_manager):
        """Test handling unexpected errors."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = Exception("Unexpected error")

        # Create args
        args = Mock()
        args.sound_name = "test_sound"
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 1

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_all_assets_all_valid(self, mock_get_manager):
        """Test validating all assets when all are valid."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {"name": "sound1", "is_valid": True, "issues": []},
            {"name": "sound2", "is_valid": True, "issues": []},
        ]

        # Create args
        args = Mock()
        args.sound_name = None
        args.verbose = False

        # Test command
        result = validate_assets_command(args)

        assert result == 0  # All assets valid
        mock_manager.list_all_assets_with_status.assert_called_once()

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_validate_all_assets_with_issues(self, mock_get_manager):
        """Test validating all assets with detailed issues."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {
                "name": "broken_sound",
                "is_valid": False,
                "issues": ["Missing WAV file", "Invalid metadata format"],
            }
        ]

        # Create args
        args = Mock()
        args.sound_name = None
        args.verbose = True

        # Test command
        result = validate_assets_command(args)

        assert result == 1  # Asset invalid
        mock_manager.list_all_assets_with_status.assert_called_once()


class TestAddValidateAssetsParser:
    """Test add_validate_assets_parser function."""

    def test_add_validate_assets_parser(self):
        """Test adding the validate-assets parser."""
        # Create mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser

        # Test function
        add_validate_assets_parser(mock_subparsers)

        # Verify parser was added with correct name
        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "validate-assets"

        # Verify arguments were added
        assert mock_parser.add_argument.call_count == 2  # sound_name and --verbose
        assert mock_parser.set_defaults.call_count == 1

    def test_parser_arguments(self):
        """Test that parser has correct arguments."""
        import argparse

        # Create real parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Add validate-assets parser
        add_validate_assets_parser(subparsers)

        # Test parsing valid arguments
        args = parser.parse_args(["validate-assets", "campfire", "--verbose"])
        assert args.sound_name == "campfire"
        assert args.verbose is True

        # Test parsing without sound name
        args = parser.parse_args(["validate-assets"])
        assert args.sound_name is None
        assert args.verbose is False

        # Test parsing with verbose only
        args = parser.parse_args(["validate-assets", "--verbose"])
        assert args.sound_name is None
        assert args.verbose is True


class TestIntegration:
    """Integration tests for validate_assets command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_real_asset_validation(self, mock_get_manager):
        """Test with real asset manager and files."""
        from sleepstack.asset_manager import AssetManager

        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager

        # Create a valid asset
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

        # Test validating specific sound
        args = Mock()
        args.sound_name = sound_name
        args.verbose = False

        result = validate_assets_command(args)
        assert result == 0

        # Test validating all assets
        args.sound_name = None
        result = validate_assets_command(args)
        assert result == 0

    @patch("sleepstack.commands.validate_assets.get_asset_manager")
    def test_invalid_asset_validation(self, mock_get_manager):
        """Test with invalid asset."""
        from sleepstack.asset_manager import AssetManager

        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager

        # Create an invalid asset (missing WAV file)
        sound_name = "broken_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()

        # Create metadata but no WAV file
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {"name": sound_name}

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Test validating specific sound
        args = Mock()
        args.sound_name = sound_name
        args.verbose = False

        result = validate_assets_command(args)
        assert result == 1

        # Test validating all assets
        args.sound_name = None
        result = validate_assets_command(args)
        assert result == 1
