"""Tests for repair_assets.py"""

import pytest
import tempfile
import json
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from sleepstack.commands.repair_assets import (
    repair_assets_command,
    add_repair_assets_parser,
)
from sleepstack.asset_manager import AssetValidationError


class TestRepairAssetsCommand:
    """Test repair_assets_command function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_specific_sound_success(self, mock_get_manager):
        """Test repairing a specific sound successfully."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.repair_asset.return_value = True
        
        # Create args
        args = Mock()
        args.sound_name = "campfire"
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 0
        mock_manager.repair_asset.assert_called_once_with("campfire")

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_specific_sound_failure(self, mock_get_manager):
        """Test repairing a specific sound that fails."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.repair_asset.return_value = False
        
        # Create args
        args = Mock()
        args.sound_name = "broken_sound"
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 1
        mock_manager.repair_asset.assert_called_once_with("broken_sound")

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_all_assets_empty(self, mock_get_manager):
        """Test repairing all assets when none exist."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = []
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_all_assets_all_valid(self, mock_get_manager):
        """Test repairing all assets when all are valid."""
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
        result = repair_assets_command(args)
        
        assert result == 0
        mock_manager.list_all_assets_with_status.assert_called_once()
        # Should not call repair_asset since all are valid
        mock_manager.repair_asset.assert_not_called()

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_all_assets_mixed(self, mock_get_manager):
        """Test repairing all assets with mixed validity."""
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
                'name': 'broken_sound1',
                'is_valid': False,
                'issues': ['Missing metadata']
            },
            {
                'name': 'broken_sound2',
                'is_valid': False,
                'issues': ['Corrupted WAV']
            }
        ]
        
        # Mock repair results
        def repair_side_effect(name):
            return name == 'broken_sound1'  # Only first broken sound can be repaired
        
        mock_manager.repair_asset.side_effect = repair_side_effect
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 1  # Some repairs failed
        mock_manager.list_all_assets_with_status.assert_called_once()
        # Should call repair_asset for invalid assets only
        assert mock_manager.repair_asset.call_count == 2
        mock_manager.repair_asset.assert_any_call('broken_sound1')
        mock_manager.repair_asset.assert_any_call('broken_sound2')

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_all_assets_all_repaired(self, mock_get_manager):
        """Test repairing all assets when all can be repaired."""
        # Mock asset manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_all_assets_with_status.return_value = [
            {
                'name': 'broken_sound1',
                'is_valid': False,
                'issues': ['Missing metadata']
            },
            {
                'name': 'broken_sound2',
                'is_valid': False,
                'issues': ['Corrupted metadata']
            }
        ]
        
        # Mock repair results - all can be repaired
        mock_manager.repair_asset.return_value = True
        
        # Create args
        args = Mock()
        args.sound_name = None
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 0  # All repairs successful
        mock_manager.list_all_assets_with_status.assert_called_once()
        assert mock_manager.repair_asset.call_count == 2

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_assets_validation_error(self, mock_get_manager):
        """Test handling AssetValidationError."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = AssetValidationError("Test validation error")
        
        # Create args
        args = Mock()
        args.sound_name = "test_sound"
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 1

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_assets_unexpected_error(self, mock_get_manager):
        """Test handling unexpected errors."""
        # Mock asset manager to raise exception
        mock_get_manager.side_effect = Exception("Unexpected error")
        
        # Create args
        args = Mock()
        args.sound_name = "test_sound"
        
        # Test command
        result = repair_assets_command(args)
        
        assert result == 1


class TestAddRepairAssetsParser:
    """Test add_repair_assets_parser function."""

    def test_add_repair_assets_parser(self):
        """Test adding the repair-assets parser."""
        # Create mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser
        
        # Test function
        add_repair_assets_parser(mock_subparsers)
        
        # Verify parser was added with correct name
        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "repair-assets"
        
        # Verify arguments were added
        assert mock_parser.add_argument.call_count == 1  # sound_name
        assert mock_parser.set_defaults.call_count == 1

    def test_parser_arguments(self):
        """Test that parser has correct arguments."""
        import argparse
        
        # Create real parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # Add repair-assets parser
        add_repair_assets_parser(subparsers)
        
        # Test parsing with sound name
        args = parser.parse_args(["repair-assets", "campfire"])
        assert args.sound_name == "campfire"
        
        # Test parsing without sound name
        args = parser.parse_args(["repair-assets"])
        assert args.sound_name is None


class TestIntegration:
    """Integration tests for repair_assets command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_real_asset_repair(self, mock_get_manager):
        """Test with real asset manager and files."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Create a repairable asset (missing metadata)
        sound_name = "test_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()
        
        # Create valid WAV file but no metadata
        wav_path = sound_dir / f"{sound_name}_1m.wav"
        with wave.open(str(wav_path), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(b'\x00' * 48000 * 2 * 2 * 60)  # 60 seconds
        
        # Test repairing specific sound
        args = Mock()
        args.sound_name = sound_name
        
        result = repair_assets_command(args)
        assert result == 0
        
        # Verify metadata was created
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        assert metadata_path.exists()
        
        # Test repairing all assets
        args.sound_name = None
        result = repair_assets_command(args)
        assert result == 0

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_nonexistent_asset(self, mock_get_manager):
        """Test repairing nonexistent asset."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Test repairing nonexistent sound
        args = Mock()
        args.sound_name = "nonexistent_sound"
        
        result = repair_assets_command(args)
        assert result == 1

    @patch('sleepstack.commands.repair_assets.get_asset_manager')
    def test_repair_corrupted_asset(self, mock_get_manager):
        """Test repairing corrupted asset that cannot be fixed."""
        from sleepstack.asset_manager import AssetManager
        
        # Use real asset manager with temp directory
        real_manager = AssetManager(self.assets_dir)
        mock_get_manager.return_value = real_manager
        
        # Create a corrupted asset (no WAV file, corrupted metadata)
        sound_name = "corrupted_sound"
        sound_dir = self.assets_dir / sound_name
        sound_dir.mkdir()
        
        # Create corrupted metadata file
        metadata_path = sound_dir / f"{sound_name}_metadata.json"
        metadata_path.write_text("corrupted json")
        
        # Test repairing specific sound
        args = Mock()
        args.sound_name = sound_name
        
        result = repair_assets_command(args)
        assert result == 1  # Cannot repair without WAV file
        
        # Test repairing all assets
        args.sound_name = None
        result = repair_assets_command(args)
        assert result == 1
