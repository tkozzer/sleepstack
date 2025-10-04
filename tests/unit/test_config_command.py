"""Tests for config_command.py (Click-based CLI)"""

import pytest
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from click.testing import CliRunner

from sleepstack.commands.config_command import (
    config,
    show,
    set,
    get,
    validate,
    reset,
    export,
    import_config,
    history,
    state,
)


class TestConfigCommand:
    """Test the config command group."""

    def test_config_group(self):
        """Test the config command group."""
        # Test that the group is properly defined
        assert config.name == "config"
        assert config.help == "Configuration management commands."


class TestConfigShow:
    """Test the show command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_manager = Mock()
        self.mock_config = Mock()
        self.mock_config.last_updated = "2024-01-01T00:00:00"
        self.mock_config.download = Mock()
        self.mock_config.download.default_sample_rate = 48000
        self.mock_config.download.default_duration = 60
        self.mock_config.download.max_download_duration = 300
        self.mock_config.download.volume_adjustment = 1.0
        self.mock_config.download.auto_cleanup_temp_files = True
        self.mock_config.processing = Mock()
        self.mock_config.processing.output_format = "wav"
        self.mock_config.processing.output_codec = "pcm_s16le"
        self.mock_config.processing.channels = 2
        self.mock_config.processing.fade_in_duration = 2.0
        self.mock_config.processing.fade_out_duration = 2.0
        self.mock_config.processing.normalize_audio = True
        self.mock_config.preferences = Mock()
        self.mock_config.preferences.default_assets_dir = ""
        self.mock_config.preferences.auto_validate_downloads = True
        self.mock_config.preferences.show_download_progress = True
        self.mock_config.preferences.backup_original_files = False
        self.mock_config.preferences.preferred_audio_quality = "high"
        self.mock_config.preferences.download_timeout = 300

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_show_table_format(self, mock_get_manager):
        """Test show command with table format."""
        self.mock_manager.get_config.return_value = self.mock_config
        self.mock_manager.get_config_path.return_value = "/path/to/config.json"
        mock_get_manager.return_value = self.mock_manager

        result = self.runner.invoke(show, ["--format", "table"])
        assert result.exit_code == 0
        assert "Current Configuration:" in result.output

    @patch("sleepstack.commands.config_command.get_config_manager")
    @patch("dataclasses.asdict")
    def test_show_json_format(self, mock_asdict, mock_get_manager):
        """Test show command with JSON format."""
        self.mock_manager.get_config.return_value = self.mock_config
        mock_get_manager.return_value = self.mock_manager
        mock_asdict.return_value = {"test": "data"}

        result = self.runner.invoke(show, ["--format", "json"])
        assert result.exit_code == 0
        assert '"test": "data"' in result.output

    @patch("sleepstack.commands.config_command.get_config_manager")
    @patch("dataclasses.asdict")
    def test_show_yaml_format_success(self, mock_asdict, mock_get_manager):
        """Test show command with YAML format (success)."""
        self.mock_manager.get_config.return_value = self.mock_config
        mock_get_manager.return_value = self.mock_manager
        mock_asdict.return_value = {"test": "data"}

        mock_yaml = Mock()
        mock_yaml.dump.return_value = "test: data\n"

        with patch.dict("sys.modules", {"yaml": mock_yaml}):
            result = self.runner.invoke(show, ["--format", "yaml"])
            assert result.exit_code == 0
            assert "test: data" in result.output

    @pytest.mark.skip(reason="Complex mocking of yaml import error")
    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_show_yaml_format_import_error(self, mock_get_manager):
        """Test show command with YAML format (import error)."""
        self.mock_manager.get_config.return_value = self.mock_config
        mock_get_manager.return_value = self.mock_manager

        # Mock the yaml import to raise ImportError
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args, **kwargs: (
                (_ for _ in ()).throw(ImportError("No module named 'yaml'"))
                if name == "yaml"
                else __import__(name, *args, **kwargs)
            ),
        ):
            result = self.runner.invoke(show, ["--format", "yaml"])
            assert result.exit_code != 0
            assert "PyYAML package" in result.output


class TestConfigSet:
    """Test the set command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_set_command(self, mock_get_manager):
        """Test set command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(set, ["download.default_sample_rate", "44100"])
        assert result.exit_code == 0
        assert "Set download.default_sample_rate = 44100" in result.output
        mock_manager.update_config.assert_called_once_with(
            **{"download.default_sample_rate": 44100}
        )


class TestConfigGet:
    """Test the get command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_get_command(self, mock_get_manager):
        """Test get command."""
        mock_manager = Mock()
        mock_config = Mock()
        mock_config.download.default_sample_rate = 48000
        mock_manager.get_config.return_value = mock_config
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(get, ["download.default_sample_rate"])
        assert result.exit_code == 0
        assert "download.default_sample_rate = 48000" in result.output


class TestConfigValidate:
    """Test the validate command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_validate_valid_config(self, mock_get_manager):
        """Test validate command with valid config."""
        mock_manager = Mock()
        mock_manager.validate_config.return_value = (True, [])
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(validate)
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_validate_invalid_config(self, mock_get_manager):
        """Test validate command with invalid config."""
        mock_manager = Mock()
        mock_manager.validate_config.return_value = (False, ["Invalid sample rate"])
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(validate)
        assert result.exit_code != 0  # Should exit with error for invalid config
        assert "Invalid sample rate" in result.output


class TestConfigReset:
    """Test the reset command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_reset_command(self, mock_get_manager):
        """Test reset command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Mock click.confirm to return True (user confirms)
        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(reset)
            assert result.exit_code == 0
            assert "Configuration reset to defaults" in result.output
            mock_manager.reset_config.assert_called_once()


class TestConfigExport:
    """Test the export command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.export_path = Path(self.temp_dir) / "config_export.json"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.config_command.get_config_manager")
    @patch("dataclasses.asdict")
    def test_export_command(self, mock_asdict, mock_get_manager):
        """Test export command."""
        mock_manager = Mock()
        mock_config = Mock()
        mock_config.last_updated = "2024-01-01T00:00:00"
        mock_manager.get_config.return_value = mock_config
        mock_get_manager.return_value = mock_manager
        mock_asdict.return_value = {"test": "data"}

        result = self.runner.invoke(export, ["--output", str(self.export_path)])
        assert result.exit_code == 0
        assert f"Configuration exported to {self.export_path}" in result.output


class TestConfigImport:
    """Test the import command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.import_path = Path(self.temp_dir) / "config_import.json"
        self.import_path.write_text('{"test": "data"}')

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_import_command(self, mock_get_manager):
        """Test import command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Mock click.confirm to return True (user confirms)
        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(import_config, [str(self.import_path)])
            assert result.exit_code == 0
            assert f"Configuration imported from {self.import_path}" in result.output
            mock_manager.save_config.assert_called_once()


class TestConfigHistory:
    """Test the history command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_history_command_empty(self, mock_get_manager):
        """Test history command with no history."""
        mock_manager = Mock()
        mock_manager.get_download_history.return_value = []
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(history)
        assert result.exit_code == 0
        assert "No download history found" in result.output

    @patch("sleepstack.commands.config_command.get_config_manager")
    def test_history_command_with_records(self, mock_get_manager):
        """Test history command with history records."""
        mock_manager = Mock()
        mock_manager.get_download_history.return_value = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "url": "https://youtube.com/watch?v=test",
                "sound_name": "test_sound",
                "success": True,
                "file_size": 1024,
                "metadata": {"title": "Test Video", "duration": 60},
            }
        ]
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(history)
        assert result.exit_code == 0
        assert "test_sound" in result.output


class TestConfigState:
    """Test the state command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.config_command.get_state_manager")
    def test_state_command(self, mock_get_state_manager):
        """Test state command."""
        mock_state_manager = Mock()
        mock_state_manager.get_state.return_value = {
            "last_operation": "download",
            "total_assets": 5,
        }
        mock_get_state_manager.return_value = mock_state_manager

        result = self.runner.invoke(state)
        assert result.exit_code == 0
        assert "last_operation" in result.output
