"""Tests for commands/download_ambient.py"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from sleepstack.commands.download_ambient import (
    download_ambient_command,
    add_download_ambient_parser,
)
from sleepstack.download_ambient import AmbientDownloadError, PrerequisiteError
from sleepstack.ambient_manager import AmbientSoundError, AmbientSoundMetadata


class TestDownloadAmbientCommand:
    """Test download_ambient_command function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.download_ambient.get_asset_manager')
    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_success(self, mock_download, mock_get_ambient_manager, mock_get_asset_manager):
        """Test successful download of ambient sound."""
        # Mock download function
        mock_output_path = Path("/test/output/path.wav")
        mock_download.return_value = mock_output_path
        
        # Mock managers
        mock_ambient_manager = Mock()
        mock_asset_manager = Mock()
        mock_get_ambient_manager.return_value = mock_ambient_manager
        mock_get_asset_manager.return_value = mock_asset_manager
        
        # Mock metadata
        mock_metadata = AmbientSoundMetadata(
            name="test_sound",
            path=mock_output_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description="Test sound"
        )
        mock_ambient_manager.get_sound_metadata.return_value = mock_metadata
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = "Test description"
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 0
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )
        mock_ambient_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_ambient_manager.add_sound_metadata.assert_called_once()
        mock_asset_manager.create_individual_metadata_file.assert_called_once_with("test_sound", mock_metadata)

    @patch('sleepstack.commands.download_ambient.get_asset_manager')
    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_success_no_description(self, mock_download, mock_get_ambient_manager, mock_get_asset_manager):
        """Test successful download without description."""
        # Mock download function
        mock_output_path = Path("/test/output/path.wav")
        mock_download.return_value = mock_output_path
        
        # Mock managers
        mock_ambient_manager = Mock()
        mock_asset_manager = Mock()
        mock_get_ambient_manager.return_value = mock_ambient_manager
        mock_get_asset_manager.return_value = mock_asset_manager
        
        # Mock metadata
        mock_metadata = AmbientSoundMetadata(
            name="test_sound",
            path=mock_output_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://example.com",
            description=None
        )
        mock_ambient_manager.get_sound_metadata.return_value = mock_metadata
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 0
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )
        mock_ambient_manager.get_sound_metadata.assert_called_once_with("test_sound")
        mock_ambient_manager.add_sound_metadata.assert_called_once()
        mock_asset_manager.create_individual_metadata_file.assert_called_once_with("test_sound", mock_metadata)

    @patch('sleepstack.commands.download_ambient.get_asset_manager')
    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_success_no_metadata(self, mock_download, mock_get_ambient_manager, mock_get_asset_manager):
        """Test successful download when no metadata is found."""
        # Mock download function
        mock_output_path = Path("/test/output/path.wav")
        mock_download.return_value = mock_output_path
        
        # Mock managers
        mock_ambient_manager = Mock()
        mock_asset_manager = Mock()
        mock_get_ambient_manager.return_value = mock_ambient_manager
        mock_get_asset_manager.return_value = mock_asset_manager
        
        # Mock no metadata found
        mock_ambient_manager.get_sound_metadata.return_value = None
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = "Test description"
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 0
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )
        mock_ambient_manager.get_sound_metadata.assert_called_once_with("test_sound")
        # Should not call add_sound_metadata or create_individual_metadata_file when no metadata
        mock_ambient_manager.add_sound_metadata.assert_not_called()
        mock_asset_manager.create_individual_metadata_file.assert_not_called()

    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_prerequisite_error(self, mock_download):
        """Test handling PrerequisiteError."""
        # Mock download function to raise PrerequisiteError
        mock_download.side_effect = PrerequisiteError("ffmpeg not found")
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 1
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )

    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_download_error(self, mock_download):
        """Test handling AmbientDownloadError."""
        # Mock download function to raise AmbientDownloadError
        mock_download.side_effect = AmbientDownloadError("Download failed")
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 1
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )

    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_ambient_sound_error(self, mock_download, mock_get_ambient_manager):
        """Test handling AmbientSoundError."""
        # Mock download function
        mock_output_path = Path("/test/output/path.wav")
        mock_download.return_value = mock_output_path
        
        # Mock ambient manager to raise AmbientSoundError
        mock_ambient_manager = Mock()
        mock_get_ambient_manager.return_value = mock_ambient_manager
        mock_ambient_manager.get_sound_metadata.side_effect = AmbientSoundError("Sound error")
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 1
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )

    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_unexpected_error(self, mock_download):
        """Test handling unexpected errors."""
        # Mock download function to raise unexpected error
        mock_download.side_effect = Exception("Unexpected error")
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 1
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )

    @patch('sleepstack.commands.download_ambient.get_asset_manager')
    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_update_metadata_with_url(self, mock_download, mock_get_ambient_manager, mock_get_asset_manager):
        """Test updating metadata with URL when not provided."""
        # Mock download function
        mock_output_path = Path("/test/output/path.wav")
        mock_download.return_value = mock_output_path
        
        # Mock managers
        mock_ambient_manager = Mock()
        mock_asset_manager = Mock()
        mock_get_ambient_manager.return_value = mock_ambient_manager
        mock_get_asset_manager.return_value = mock_asset_manager
        
        # Mock metadata without source_url
        mock_metadata = AmbientSoundMetadata(
            name="test_sound",
            path=mock_output_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url=None,  # No source URL initially
            description="Original description"
        )
        mock_ambient_manager.get_sound_metadata.return_value = mock_metadata
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = "Updated description"
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 0
        
        # Verify that metadata was updated with URL and description
        updated_metadata = mock_ambient_manager.add_sound_metadata.call_args[0][0]
        assert updated_metadata.source_url == "https://example.com"
        assert updated_metadata.description == "Updated description"

    @patch('sleepstack.commands.download_ambient.get_asset_manager')
    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_ambient_no_url_provided(self, mock_download, mock_get_ambient_manager, mock_get_asset_manager):
        """Test download when no URL is provided."""
        # Mock download function
        mock_output_path = Path("/test/output/path.wav")
        mock_download.return_value = mock_output_path
        
        # Mock managers
        mock_ambient_manager = Mock()
        mock_asset_manager = Mock()
        mock_get_ambient_manager.return_value = mock_ambient_manager
        mock_get_asset_manager.return_value = mock_asset_manager
        
        # Mock metadata
        mock_metadata = AmbientSoundMetadata(
            name="test_sound",
            path=mock_output_path,
            duration_seconds=60.0,
            sample_rate=48000,
            channels=2,
            file_size_bytes=1000000,
            created_date="2024-01-01T00:00:00Z",
            source_url="https://original.com",
            description="Original description"
        )
        mock_ambient_manager.get_sound_metadata.return_value = mock_metadata
        
        # Create args with no URL
        args = Mock()
        args.url = None
        args.name = "test_sound"
        args.description = "Updated description"
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 0
        
        # Verify that metadata was updated with description but not URL
        updated_metadata = mock_ambient_manager.add_sound_metadata.call_args[0][0]
        assert updated_metadata.source_url == "https://original.com"  # Should remain unchanged
        assert updated_metadata.description == "Updated description"


class TestAddDownloadAmbientParser:
    """Test add_download_ambient_parser function."""

    def test_add_download_ambient_parser(self):
        """Test adding the download-ambient parser."""
        # Create mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser
        
        # Test function
        add_download_ambient_parser(mock_subparsers)
        
        # Verify parser was added with correct name
        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "download-ambient"
        
        # Verify arguments were added
        assert mock_parser.add_argument.call_count == 3  # url, name, --description
        assert mock_parser.set_defaults.call_count == 1

    def test_parser_arguments(self):
        """Test that parser has correct arguments."""
        import argparse
        
        # Create real parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # Add download-ambient parser
        add_download_ambient_parser(subparsers)
        
        # Test parsing with all arguments
        args = parser.parse_args([
            "download-ambient", 
            "https://example.com", 
            "test_sound", 
            "--description", 
            "Test description"
        ])
        assert args.url == "https://example.com"
        assert args.name == "test_sound"
        assert args.description == "Test description"
        
        # Test parsing without description
        args = parser.parse_args([
            "download-ambient", 
            "https://example.com", 
            "test_sound"
        ])
        assert args.url == "https://example.com"
        assert args.name == "test_sound"
        assert args.description is None


class TestIntegration:
    """Integration tests for download_ambient command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.download_ambient.get_asset_manager')
    @patch('sleepstack.commands.download_ambient.get_ambient_manager')
    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_real_download_workflow(self, mock_download, mock_get_ambient_manager, mock_get_asset_manager):
        """Test with real managers and realistic workflow."""
        from sleepstack.ambient_manager import AmbientSoundManager
        from sleepstack.asset_manager import AssetManager
        
        # Use real managers with temp directory
        real_ambient_manager = AmbientSoundManager(self.assets_dir)
        real_asset_manager = AssetManager(self.assets_dir)
        mock_get_ambient_manager.return_value = real_ambient_manager
        mock_get_asset_manager.return_value = real_asset_manager
        
        # Mock download function
        mock_output_path = self.assets_dir / "test_sound" / "test_sound_1m.wav"
        mock_output_path.parent.mkdir()
        mock_output_path.touch()
        mock_download.return_value = mock_output_path
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "test_sound"
        args.description = "Test description"
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 0
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="test_sound"
        )

    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_with_invalid_url(self, mock_download):
        """Test download with invalid URL."""
        # Mock download function to raise error
        mock_download.side_effect = AmbientDownloadError("Invalid URL")
        
        # Create args
        args = Mock()
        args.url = "invalid_url"
        args.name = "test_sound"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 1
        mock_download.assert_called_once_with(
            url="invalid_url",
            sound_name="test_sound"
        )

    @patch('sleepstack.commands.download_ambient.download_and_process_ambient_sound')
    def test_download_with_invalid_sound_name(self, mock_download):
        """Test download with invalid sound name."""
        # Mock download function to raise error
        mock_download.side_effect = AmbientDownloadError("Invalid sound name")
        
        # Create args
        args = Mock()
        args.url = "https://example.com"
        args.name = "invalid/name"
        args.description = None
        
        # Test command
        result = download_ambient_command(args)
        
        assert result == 1
        mock_download.assert_called_once_with(
            url="https://example.com",
            sound_name="invalid/name"
        )
