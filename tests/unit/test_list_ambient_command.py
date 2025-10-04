"""Tests for commands/list_ambient.py"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from sleepstack.commands.list_ambient import (
    list_ambient_command,
    add_list_ambient_parser,
)


class TestListAmbientCommand:
    """Test list_ambient_command function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_simple_success(self, mock_get_ambient_manager):
        """Test successful simple listing of ambient sounds."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        mock_manager.get_available_sounds.return_value = ["campfire", "rain", "ocean"]
        
        # Create args
        args = Mock()
        args.detailed = False
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.get_available_sounds.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_detailed_success(self, mock_get_ambient_manager):
        """Test successful detailed listing of ambient sounds."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        
        # Mock detailed sounds data
        mock_sounds = [
            {
                'name': 'campfire',
                'path': '/path/to/campfire.wav',
                'duration': '60.0s',
                'sample_rate': '48000 Hz',
                'file_size': '1.2 MB',
                'source_url': 'https://example.com',
                'description': 'Crackling campfire sounds'
            },
            {
                'name': 'rain',
                'path': '/path/to/rain.wav',
                'duration': '60.0s',
                'sample_rate': '48000 Hz',
                'file_size': '1.1 MB',
                'source_url': None,
                'description': 'Gentle rain sounds'
            }
        ]
        mock_manager.list_sounds_with_details.return_value = mock_sounds
        
        # Create args
        args = Mock()
        args.detailed = True
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.list_sounds_with_details.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_simple_empty(self, mock_get_ambient_manager):
        """Test simple listing when no sounds are available."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        mock_manager.get_available_sounds.return_value = []
        
        # Create args
        args = Mock()
        args.detailed = False
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.get_available_sounds.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_detailed_empty(self, mock_get_ambient_manager):
        """Test detailed listing when no sounds are available."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        mock_manager.list_sounds_with_details.return_value = []
        
        # Create args
        args = Mock()
        args.detailed = True
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.list_sounds_with_details.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_detailed_with_optional_fields(self, mock_get_ambient_manager):
        """Test detailed listing with sounds that have optional fields."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        
        # Mock detailed sounds data with optional fields
        mock_sounds = [
            {
                'name': 'campfire',
                'path': '/path/to/campfire.wav',
                'duration': '60.0s',
                'sample_rate': '48000 Hz',
                'file_size': '1.2 MB',
                'source_url': 'https://example.com',
                'description': 'Crackling campfire sounds'
            },
            {
                'name': 'rain',
                'path': '/path/to/rain.wav',
                'duration': '60.0s',
                'sample_rate': '48000 Hz',
                'file_size': '1.1 MB',
                'source_url': None,  # No source URL
                'description': None  # No description
            },
            {
                'name': 'ocean',
                'path': '/path/to/ocean.wav',
                'duration': '60.0s',
                'sample_rate': '48000 Hz',
                'file_size': '1.0 MB',
                'source_url': 'https://ocean.com',
                'description': None  # No description
            }
        ]
        mock_manager.list_sounds_with_details.return_value = mock_sounds
        
        # Create args
        args = Mock()
        args.detailed = True
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.list_sounds_with_details.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_manager_error(self, mock_get_ambient_manager):
        """Test handling of ambient manager errors."""
        # Mock ambient manager to raise exception
        mock_get_ambient_manager.side_effect = Exception("Manager error")
        
        # Create args
        args = Mock()
        args.detailed = False
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 1
        mock_get_ambient_manager.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_get_available_sounds_error(self, mock_get_ambient_manager):
        """Test handling of get_available_sounds errors."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        mock_manager.get_available_sounds.side_effect = Exception("Get sounds error")
        
        # Create args
        args = Mock()
        args.detailed = False
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 1
        mock_get_ambient_manager.assert_called_once()
        mock_manager.get_available_sounds.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_list_sounds_with_details_error(self, mock_get_ambient_manager):
        """Test handling of list_sounds_with_details errors."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        mock_manager.list_sounds_with_details.side_effect = Exception("List details error")
        
        # Create args
        args = Mock()
        args.detailed = True
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 1
        mock_get_ambient_manager.assert_called_once()
        mock_manager.list_sounds_with_details.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_single_sound_simple(self, mock_get_ambient_manager):
        """Test listing a single sound in simple mode."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        mock_manager.get_available_sounds.return_value = ["campfire"]
        
        # Create args
        args = Mock()
        args.detailed = False
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.get_available_sounds.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_list_ambient_single_sound_detailed(self, mock_get_ambient_manager):
        """Test listing a single sound in detailed mode."""
        # Mock ambient manager
        mock_manager = Mock()
        mock_get_ambient_manager.return_value = mock_manager
        
        # Mock single detailed sound
        mock_sounds = [
            {
                'name': 'campfire',
                'path': '/path/to/campfire.wav',
                'duration': '60.0s',
                'sample_rate': '48000 Hz',
                'file_size': '1.2 MB',
                'source_url': 'https://example.com',
                'description': 'Crackling campfire sounds'
            }
        ]
        mock_manager.list_sounds_with_details.return_value = mock_sounds
        
        # Create args
        args = Mock()
        args.detailed = True
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()
        mock_manager.list_sounds_with_details.assert_called_once()


class TestAddListAmbientParser:
    """Test add_list_ambient_parser function."""

    def test_add_list_ambient_parser(self):
        """Test adding the list-ambient parser."""
        # Create mock subparsers
        mock_subparsers = Mock()
        mock_parser = Mock()
        mock_subparsers.add_parser.return_value = mock_parser
        
        # Test function
        add_list_ambient_parser(mock_subparsers)
        
        # Verify parser was added with correct name
        mock_subparsers.add_parser.assert_called_once()
        call_args = mock_subparsers.add_parser.call_args
        assert call_args[0][0] == "list-ambient"
        
        # Verify arguments were added
        assert mock_parser.add_argument.call_count == 1  # --detailed
        assert mock_parser.set_defaults.call_count == 1

    def test_parser_arguments(self):
        """Test that parser has correct arguments."""
        import argparse
        
        # Create real parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # Add list-ambient parser
        add_list_ambient_parser(subparsers)
        
        # Test parsing without --detailed
        args = parser.parse_args(["list-ambient"])
        assert args.detailed is False
        
        # Test parsing with --detailed
        args = parser.parse_args(["list-ambient", "--detailed"])
        assert args.detailed is True


class TestIntegration:
    """Integration tests for list_ambient command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.assets_dir = Path(self.temp_dir) / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_real_ambient_manager_integration(self, mock_get_ambient_manager):
        """Test with real ambient manager."""
        from sleepstack.ambient_manager import AmbientSoundManager
        
        # Use real ambient manager with temp directory
        real_manager = AmbientSoundManager(self.assets_dir)
        mock_get_ambient_manager.return_value = real_manager
        
        # Create args
        args = Mock()
        args.detailed = False
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()

    @patch('sleepstack.commands.list_ambient.get_ambient_manager')
    def test_real_ambient_manager_detailed_integration(self, mock_get_ambient_manager):
        """Test with real ambient manager in detailed mode."""
        from sleepstack.ambient_manager import AmbientSoundManager
        
        # Use real ambient manager with temp directory
        real_manager = AmbientSoundManager(self.assets_dir)
        mock_get_ambient_manager.return_value = real_manager
        
        # Create args
        args = Mock()
        args.detailed = True
        
        # Test command
        result = list_ambient_command(args)
        
        assert result == 0
        mock_get_ambient_manager.assert_called_once()

    def test_parser_integration(self):
        """Test parser integration with real argparse."""
        import argparse
        
        # Create main parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # Add list-ambient parser
        add_list_ambient_parser(subparsers)
        
        # Test that the parser can be created and used
        assert subparsers.choices is not None
        assert "list-ambient" in subparsers.choices

    def test_command_function_assignment(self):
        """Test that the command function is properly assigned."""
        import argparse
        
        # Create main parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        
        # Add list-ambient parser
        add_list_ambient_parser(subparsers)
        
        # Parse arguments
        args = parser.parse_args(["list-ambient"])
        
        # Check that the function is assigned
        assert hasattr(args, 'func')
        assert args.func == list_ambient_command
