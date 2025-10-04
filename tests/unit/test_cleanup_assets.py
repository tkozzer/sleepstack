"""Tests for cleanup_assets.py"""

import pytest
import tempfile
import json
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from sleepstack.commands.cleanup_assets import (
    cleanup_assets_command,
    add_cleanup_assets_parser,
)
from sleepstack.asset_manager import AssetValidationError


class TestCleanupAssetsCommand:
    """Test cleanup_assets_command function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_specific_sound_success(self, mock_get_manager):
        """Test cleaning up a specific sound successfully."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.cleanup_corrupted_assets.return_value = True
        
        # Create args
        args = Mock()
        args.sound_name = "corrupted_sound"
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 0
        mock_manager.cleanup_corrupted_assets.assert_called_once_with("corrupted_sound")

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_specific_sound_no_cleanup_needed(self, mock_get_manager):
        """Test cleaning up a specific sound that doesn't need cleanup."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.cleanup_corrupted_assets.return_value = False
        
        # Create args
        args = Mock()
        args.sound_name = "valid_sound"
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 0  # Still returns 0 even if no cleanup needed
        mock_manager.cleanup_corrupted_assets.assert_called_once_with("valid_sound")

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_all_assets_empty(self, mock_get_manager):
        """Test cleaning up all assets when none exist."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = []
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_all_assets_all_valid(self, mock_get_manager):
        """Test cleaning up all assets when all are valid."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {
                'name': 'valid_sound1',
                'is_valid': True,
                'issues': []
            },
            {
                'name': 'valid_sound2',
                'is_valid': True,
                'issues': []
            }
        ]
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()
        # Should not call cleanup_corrupted_assets since all are valid
        mock_manager.cleanup_corrupted_assets.assert_not_called()

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_all_assets_mixed(self, mock_get_manager):
        """Test cleaning up all assets with mixed validity."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {
                'name': 'valid_sound',
                'is_valid': True,
                'issues': []
            },
            {
                'name': 'corrupted_sound1',
                'is_valid': False,
                'issues': ['Corrupted WAV file']
            },
            {
                'name': 'corrupted_sound2',
                'is_valid': False,
                'issues': ['Invalid metadata']
            }
        ]
        
        # Mock cleanup results
        def cleanup_side_effect(name):
            return name == 'corrupted_sound1'  # Only first corrupted sound can be cleaned
        
        mock_manager.cleanup_corrupted_assets.side_effect = cleanup_side_effect
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 0  # Always returns 0 for cleanup command
        mock_manager.list_all_assets_with_status.assert_called_once()
        # Should call cleanup_corrupted_assets for invalid assets only
        assert mock_manager.cleanup_corrupted_assets.call_count == 2
        mock_manager.cleanup_corrupted_assets.assert_any_call('corrupted_sound1')
        mock_manager.cleanup_corrupted_assets.assert_any_call('corrupted_sound2')

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_all_assets_all_cleaned(self, mock_get_manager):
        """Test cleaning up all assets when all can be cleaned."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {
                'name': 'corrupted_sound1',
                'is_valid': False,
                'issues': ['Corrupted WAV file']
            },
            {
                'name': 'corrupted_sound2',
                'is_valid': False,
                'issues': ['Invalid metadata']
            }
        ]
        
        # Mock cleanup results - all can be cleaned
        mock_manager.cleanup_corrupted_assets.return_value = True
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()
        assert mock_manager.cleanup_corrupted_assets.call_count == 2

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_assets_validation_error(self, mock_get_manager):
        """Test handling AssetValidationError."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = AssetValidationError("Test validation error")
        
        # Create args
        args = Mock()
        args.sound_name = "test_sound"
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 1

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_assets_unexpected_error(self, mock_get_manager):
        """Test handling unexpected errors."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = Exception("Unexpected error")
        
        # Create args
        args = Mock()
        args.sound_name = "test_sound"
        
        # Test command
        result = cleanup_assets_command(args)
        
        assert result == 1


class TestAddCleanupAssetsParser:
    """Test add_cleanup_assets_parser function."""

    def test_add_cleanup_assets_parser(self):
        """Test adding the cleanup-assets parser."""
        # Create mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser
        
        # Test function
        add_cleanup_assets_parser(mock_subparsers)
        
        # Verify parser was added with correct name
        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "cleanup-assets"
        
        # Verify arguments were added
        assert mock_parser.add_argument.call_count == 1  # sound_name
        assert mock_parser.set_defaults.call_count == 1

    def test_parser_arguments(self):
        """Test that parser has correct arguments."""
        import argparse
        
        # Create real parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # Add cleanup-assets parser
        add_cleanup_assets_parser(subparsers)
        
        # Test parsing with sound name
        args = parser.parse_args(["cleanup-assets", "corrupted_sound"])
        assert args.sound_name == "corrupted_sound"
        
        # Test parsing without sound name
        args = parser.parse_args(["cleanup-assets"])
        assert args.sound_name is None


class TestIntegration:
    """Integration tests for cleanup_assets command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_real_asset_cleanup(self, mock_get_manager):
        """Test with real asset manager and files."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Create a corrupted asset (corrupted WAV file)
        sound_name = "corrupted_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()
        
        # Create corrupted WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        wav_path.write_text("corrupted wav content")
        
        # Create metadata
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata = {"name": sound_name}
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        # Test cleaning up specific sound
        args = Mock()
        args.sound_name = sound_name
        
        result = cleanup_assets_command(args)
        assert result == 0
        
        # Verify files were cleaned up
        assert not wav_path.exists()
        assert not metadata_path.exists()
        assert not sound_dir.exists()
        
        # Test cleaning up all assets
        args.sound_name = None
        result = cleanup_assets_command(args)
        assert result == 0

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_nonexistent_asset(self, mock_get_manager):
        """Test cleaning up nonexistent asset."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Test cleaning up nonexistent sound
        args = Mock()
        args.sound_name = "nonexistent_sound"
        
        result = cleanup_assets_command(args)
        assert result == 0  # Returns 0 even if no cleanup needed

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_valid_asset(self, mock_get_manager):
        """Test cleaning up valid asset (should not be cleaned)."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Create a valid asset
        sound_name = "valid_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()
        
        # Create valid WAV file
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b'\x00' * 48000 * 2 * 2 * 60)  # 60 seconds
        
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
            "description": "Test sound"
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        # Test cleaning up specific sound
        args = Mock()
        args.sound_name = sound_name
        
        result = cleanup_assets_command(args)
        assert result == 0
        
        # Verify files were NOT cleaned up (they're valid)
        assert wav_path.exists()
        assert metadata_path.exists()
        assert sound_dir.exists()
        
        # Test cleaning up all assets
        args.sound_name = None
        result = cleanup_assets_command(args)
        assert result == 0

    @patch('sleepstack.commands.cleanup_assets.get_asset_manager')
    def test_cleanup_mixed_assets(self, mock_get_manager):
        """Test cleaning up mixed valid and corrupted assets."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Create a valid asset
        valid_sound = "valid_sound"
        valid_dir = self.assets_dir / valid_sound
        valid_dir.mkdir()
        
        valid_wav = valid_dir / f"{valid_sound}_1m.wav"
        with wave.open(str(valid_wav), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b'\x00' * 48000 * 2 * 2 * 60)
        
        valid_metadata = valid_dir / f"{valid_sound}_metadata.json"
        metadata = {
            "name": valid_sound,
            "path": str(valid_wav),
            "duration_seconds": 60.0,
            "sample_rate": 48000,
            "channels": 2,
            "file_size_bytes": valid_wav.stat().st_size,
            "created_date": "2024-01-01T00:00:00Z",
            "last_modified": "2024-01-01T00:00:00Z",
            "source_url": "https://example.com",
            "description": "Test sound"
        }
        
        with open(valid_metadata, 'w') as f:
            json.dump(metadata, f)
        
        # Create a corrupted asset
        corrupted_sound = "corrupted_sound"
        corrupted_dir = self.assets_dir / corrupted_sound
        corrupted_dir.mkdir()
        
        corrupted_wav = corrupted_dir / f"{corrupted_sound}_1m.wav"
        corrupted_wav.write_text("corrupted content")
        
        corrupted_metadata = corrupted_dir / f"{corrupted_sound}_metadata.json"
        corrupted_metadata.write_text("corrupted json")
        
        # Test cleaning up all assets
        args = Mock()
        args.sound_name = None
        
        result = cleanup_assets_command(args)
        assert result == 0
        
        # Verify valid asset was NOT cleaned up
        assert valid_wav.exists()
        assert valid_metadata.exists()
        assert valid_dir.exists()
        
        # Verify corrupted asset WAS cleaned up
        assert not corrupted_wav.exists()
        assert not corrupted_metadata.exists()
        assert not corrupted_dir.exists()
