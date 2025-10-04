"""Tests for state_command.py (Click-based CLI)"""

import pytest
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner

from sleepstack.commands.state_command import (
    state,
    show,
    set,
    dependencies,
    references,
    maintenance,
    stats,
    health,
    validate,
    cleanup,
    export,
    import_state,
    clear,
)


class TestStateCommand:
    """Test the state command group."""

    def test_state_group(self):
        """Test the state command group."""
        # Test that the group is properly defined
        assert state.name == "state"
        assert state.help == "State management commands."


class TestStateShow:
    """Test the show command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_show_with_key(self, mock_get_manager):
        """Test show command with specific key."""
        mock_manager = Mock()
        mock_manager.get_state.return_value = "download"
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(show, ["--key", "last_operation"])
        assert result.exit_code == 0
        assert "last_operation: download" in result.output
        mock_manager.get_state.assert_called_once_with("last_operation")

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_show_without_key_empty_state(self, mock_get_manager):
        """Test show command without key and empty state."""
        mock_manager = Mock()
        mock_manager.get_state.return_value = {}
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(show)
        assert result.exit_code == 0
        assert "No application state found" in result.output

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_show_without_key_with_state(self, mock_get_manager):
        """Test show command without key and with state."""
        mock_manager = Mock()
        mock_manager.get_state.return_value = {
            "last_operation": "download",
            "total_assets": 5,
            "complex_data": {"nested": "value"},
        }
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(show)
        assert result.exit_code == 0
        assert "last_operation" in result.output
        assert "total_assets" in result.output


class TestStateSet:
    """Test the set command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_set_command(self, mock_get_manager):
        """Test set command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(set, ["last_operation", "download"])
        assert result.exit_code == 0
        assert "Set last_operation = download" in result.output
        mock_manager.set_state.assert_called_once_with("last_operation", "download")


class TestStateDependencies:
    """Test the dependencies command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_dependencies_with_asset(self, mock_get_manager):
        """Test dependencies command with specific asset."""
        mock_manager = Mock()
        mock_dep = Mock()
        mock_dep.dependency_type = "mix"
        mock_dep.source_asset = "source_asset"
        mock_dep.metadata = None
        mock_manager.get_dependencies.return_value = [mock_dep]
        mock_manager.get_dependents.return_value = []
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(dependencies, ["test_asset"])
        assert result.exit_code == 0
        assert "mix" in result.output
        mock_manager.get_dependencies.assert_called_once_with("test_asset")

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_dependencies_no_dependencies(self, mock_get_manager):
        """Test dependencies command with no dependencies."""
        mock_manager = Mock()
        mock_manager.get_dependencies.return_value = []
        mock_manager.get_dependents.return_value = []
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(dependencies, ["test_asset"])
        assert result.exit_code == 0
        assert "No dependencies found" in result.output


class TestStateReferences:
    """Test the references command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_references_command(self, mock_get_manager):
        """Test references command."""
        mock_manager = Mock()
        mock_ref = Mock()
        mock_ref.reference_type = "download"
        mock_ref.asset_path = "/path/to/asset"
        mock_ref.source_url = "https://youtube.com/watch?v=test"
        mock_ref.metadata = None
        mock_manager.get_asset_references.return_value = [mock_ref]
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(references, ["test_asset"])
        assert result.exit_code == 0
        assert "download" in result.output
        mock_manager.get_asset_references.assert_called_once_with("test_asset")


class TestStateMaintenance:
    """Test the maintenance command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_maintenance_command(self, mock_get_manager):
        """Test maintenance command."""
        mock_manager = Mock()
        mock_record = Mock()
        mock_record.success = True
        mock_record.operation_type = "download"
        mock_record.asset_name = "test_asset"
        mock_record.timestamp = "2024-01-01T00:00:00.000000"
        mock_record.error_message = None
        mock_record.details = None
        mock_manager.get_maintenance_records.return_value = [mock_record]
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(maintenance)
        assert result.exit_code == 0
        assert "download" in result.output
        mock_manager.get_maintenance_records.assert_called_once_with(20)


class TestStateStats:
    """Test the stats command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_stats_command(self, mock_get_manager):
        """Test stats command."""
        mock_manager = Mock()
        mock_manager.get_maintenance_stats.return_value = {
            "total_operations": 10,
            "successful_operations": 8,
            "failed_operations": 2,
            "success_rate": 0.8,
            "operation_types": {"download": 5, "validation": 3, "cleanup": 2},
        }
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(stats)
        assert result.exit_code == 0
        assert "10" in result.output
        mock_manager.get_maintenance_stats.assert_called_once()


class TestStateHealth:
    """Test the health command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_health_command(self, mock_get_manager):
        """Test health command."""
        mock_manager = Mock()
        mock_manager.get_asset_health_summary.return_value = {
            "total_assets": 10,
            "valid_assets": 8,
            "invalid_assets": 2,
            "health_percentage": 80.0,
            "issue_types": {"sample_rate": 1, "channels": 1},
            "assets": [],
        }
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(health)
        assert result.exit_code == 0
        assert "10" in result.output
        mock_manager.get_asset_health_summary.assert_called_once()


class TestStateValidate:
    """Test the validate command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_validate_command(self, mock_get_manager):
        """Test validate command."""
        mock_manager = Mock()
        mock_manager.validate_asset_integrity.return_value = (True, [])
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(validate, ["test_asset"])
        assert result.exit_code == 0
        assert "is valid" in result.output
        mock_manager.validate_asset_integrity.assert_called_once_with("test_asset")


class TestStateCleanup:
    """Test the cleanup command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_cleanup_command(self, mock_get_manager):
        """Test cleanup command."""
        mock_manager = Mock()
        mock_manager.cleanup_old_records.return_value = 5
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(cleanup)
        assert result.exit_code == 0
        assert "Removed 5 old maintenance records" in result.output
        mock_manager.cleanup_old_records.assert_called_once_with(30)  # default days


class TestStateExport:
    """Test the export command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.export_path = Path(self.temp_dir) / "state_export.json"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_export_command(self, mock_get_manager):
        """Test export command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        result = self.runner.invoke(export, [str(self.export_path)])
        assert result.exit_code == 0
        assert f"State exported to {self.export_path}" in result.output
        mock_manager.export_state.assert_called_once_with(self.export_path)


class TestStateImport:
    """Test the import command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.import_path = Path(self.temp_dir) / "state_import.json"
        self.import_path.write_text('{"test": "data"}')

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_import_command(self, mock_get_manager):
        """Test import command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Mock click.confirm to return True (user confirms)
        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(import_state, [str(self.import_path)])
            assert result.exit_code == 0
            assert f"State imported from {self.import_path}" in result.output
            mock_manager.import_state.assert_called_once()


class TestStateClear:
    """Test the clear command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("sleepstack.commands.state_command.get_state_manager")
    def test_clear_command(self, mock_get_manager):
        """Test clear command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Mock click.confirm to return True (user confirms)
        with patch("click.confirm", return_value=True):
            result = self.runner.invoke(clear)
            assert result.exit_code == 0
            assert "Application state cleared" in result.output
            mock_manager.clear_state.assert_called_once()
