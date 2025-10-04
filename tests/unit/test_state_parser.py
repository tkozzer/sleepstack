"""Tests for state_parser.py CLI commands"""

import pytest
import tempfile
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from io import StringIO

from sleepstack.commands.state_parser import (
    add_state_parser,
    state_show,
    state_set,
    state_dependencies,
    state_references,
    state_maintenance,
    state_stats,
    state_health,
    state_validate,
    state_cleanup,
    state_export,
    state_import,
    state_clear,
)


class TestStateParser:
    """Test state parser functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "sleepstack"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_add_state_parser(self):
        """Test adding state parser to subparsers."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        state_parser = add_state_parser(subparsers)

        # Test that subcommands are available
        args = parser.parse_args(["state", "show"])
        assert args.state_command == "show"

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_show_with_key(self, mock_get_state_manager):
        """Test state show with specific key."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.get_state.return_value = "test_value"
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.key = "test_key"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_show(args)

        assert result == 0
        mock_state_manager.get_state.assert_called_once_with("test_key")
        output = mock_stdout.getvalue()
        assert "test_key: test_value" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_show_all(self, mock_get_state_manager):
        """Test state show with all state."""
        # Mock state manager
        mock_state_manager = Mock()
        test_state = {"key1": "value1", "key2": {"nested": "value"}}
        mock_state_manager.get_state.return_value = test_state
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.key = None

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_show(args)

        assert result == 0
        mock_state_manager.get_state.assert_called_once_with()
        output = mock_stdout.getvalue()
        assert "Application State:" in output
        assert "key1" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_show_empty(self, mock_get_state_manager):
        """Test state show with empty state."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.get_state.return_value = {}
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.key = None

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_show(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "No application state found" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_set_json_value(self, mock_get_state_manager):
        """Test state set with JSON value."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.key = "test_key"
        args.value = '{"nested": "value"}'

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_set(args)

        assert result == 0
        mock_state_manager.set_state.assert_called_once_with("test_key", {"nested": "value"})
        output = mock_stdout.getvalue()
        assert "Set test_key = {'nested': 'value'}" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_set_string_value(self, mock_get_state_manager):
        """Test state set with string value."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.key = "test_key"
        args.value = "simple_string"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_set(args)

        assert result == 0
        mock_state_manager.set_state.assert_called_once_with("test_key", "simple_string")
        output = mock_stdout.getvalue()
        assert "Set test_key = simple_string" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_dependencies_with_deps(self, mock_get_state_manager):
        """Test state dependencies with dependencies."""
        # Mock state manager
        mock_state_manager = Mock()
        from sleepstack.state_manager import AssetDependency

        deps = [
            AssetDependency(
                source_asset="source1",
                dependent_asset="asset1",
                dependency_type="mix",
                created_at="2023-01-01T00:00:00",
                metadata={"key": "value"},
            )
        ]
        dependents = [
            AssetDependency(
                source_asset="asset1",
                dependent_asset="dependent1",
                dependency_type="derived",
                created_at="2023-01-01T00:00:00",
                metadata={},
            )
        ]

        mock_state_manager.get_dependencies.return_value = deps
        mock_state_manager.get_dependents.return_value = dependents
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.asset_name = "asset1"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_dependencies(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Dependencies for 'asset1':" in output
        assert "mix: source1" in output
        assert "Assets depending on 'asset1':" in output
        assert "derived: dependent1" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_dependencies_empty(self, mock_get_state_manager):
        """Test state dependencies with no dependencies."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.get_dependencies.return_value = []
        mock_state_manager.get_dependents.return_value = []
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.asset_name = "asset1"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_dependencies(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "No dependencies found for 'asset1'" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_references_with_refs(self, mock_get_state_manager):
        """Test state references with references."""
        # Mock state manager
        mock_state_manager = Mock()
        from sleepstack.state_manager import AssetReference

        refs = [
            AssetReference(
                asset_name="asset1",
                reference_type="download",
                reference_id="ref_123",
                created_at="2023-01-01T00:00:00",
                metadata={"key": "value"},
            )
        ]

        mock_state_manager.get_asset_references.return_value = refs
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.asset_name = "asset1"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_references(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "References for 'asset1':" in output
        assert "download: ref_123" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_references_empty(self, mock_get_state_manager):
        """Test state references with no references."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.get_asset_references.return_value = []
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.asset_name = "asset1"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_references(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "No references found for 'asset1'" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_maintenance_with_records(self, mock_get_state_manager):
        """Test state maintenance with records."""
        # Mock state manager
        mock_state_manager = Mock()
        from sleepstack.state_manager import MaintenanceRecord

        records = [
            MaintenanceRecord(
                operation_type="download",
                asset_name="asset1",
                timestamp="2023-01-01T00:00:00",
                success=True,
                details={"key": "value"},
            ),
            MaintenanceRecord(
                operation_type="validation",
                asset_name="asset2",
                timestamp="2023-01-01T00:00:00",
                success=False,
                details={},
                error_message="Validation failed",
            ),
        ]

        mock_state_manager.get_maintenance_records.return_value = records
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.limit = 20

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_maintenance(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Maintenance Records" in output
        assert "✓ download (asset1)" in output
        assert "✗ validation (asset2)" in output
        assert "Validation failed" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_maintenance_empty(self, mock_get_state_manager):
        """Test state maintenance with no records."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.get_maintenance_records.return_value = []
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.limit = 20

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_maintenance(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "No maintenance records found" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_stats_with_operations(self, mock_get_state_manager):
        """Test state stats with operations."""
        # Mock state manager
        mock_state_manager = Mock()
        stats = {
            "total_operations": 10,
            "successful_operations": 8,
            "failed_operations": 2,
            "success_rate": 0.8,
            "operation_types": {"download": 5, "validation": 3, "repair": 2},
        }

        mock_state_manager.get_maintenance_stats.return_value = stats
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_stats(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Maintenance Statistics:" in output
        assert "Total Operations: 10" in output
        assert "Successful: 8" in output
        assert "Failed: 2" in output
        assert "Success Rate: 80.0%" in output
        assert "download: 5" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_stats_no_operations(self, mock_get_state_manager):
        """Test state stats with no operations."""
        # Mock state manager
        mock_state_manager = Mock()
        stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "success_rate": 0.0,
            "operation_types": {},
        }

        mock_state_manager.get_maintenance_stats.return_value = stats
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_stats(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Maintenance Statistics:" in output
        assert "Total Operations: 0" in output
        assert "Success Rate: N/A (no operations)" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_health_with_assets(self, mock_get_state_manager):
        """Test state health with assets."""
        # Mock state manager
        mock_state_manager = Mock()
        health = {
            "total_assets": 5,
            "valid_assets": 4,
            "invalid_assets": 1,
            "health_percentage": 80.0,
            "issue_types": {"sample_rate": 1, "metadata": 1},
            "assets": [
                {"name": "asset1", "is_valid": True, "issues": []},
                {"name": "asset2", "is_valid": False, "issues": ["Invalid sample rate"]},
            ],
        }

        mock_state_manager.get_asset_health_summary.return_value = health
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_health(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Asset Health Summary:" in output
        assert "Total Assets: 5" in output
        assert "Valid Assets: 4" in output
        assert "Invalid Assets: 1" in output
        assert "Health: 80.0%" in output
        assert "sample_rate: 1" in output
        assert "✗ asset2" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_health_no_invalid_assets(self, mock_get_state_manager):
        """Test state health with no invalid assets."""
        # Mock state manager
        mock_state_manager = Mock()
        health = {
            "total_assets": 3,
            "valid_assets": 3,
            "invalid_assets": 0,
            "health_percentage": 100.0,
            "issue_types": {},
            "assets": [
                {"name": "asset1", "is_valid": True, "issues": []},
                {"name": "asset2", "is_valid": True, "issues": []},
            ],
        }

        mock_state_manager.get_asset_health_summary.return_value = health
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_health(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Asset Health Summary:" in output
        assert "Health: 100.0%" in output
        # Note: "Invalid Assets: 0" is still shown even when there are no invalid assets
        assert "Invalid Assets: 0" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_validate_valid(self, mock_get_state_manager):
        """Test state validate with valid asset."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.validate_asset_integrity.return_value = (True, [])
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.asset_name = "asset1"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_validate(args)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "✓ Asset 'asset1' is valid" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_validate_invalid(self, mock_get_state_manager):
        """Test state validate with invalid asset."""
        # Mock state manager
        mock_state_manager = Mock()
        issues = ["Invalid sample rate", "Missing metadata"]
        mock_state_manager.validate_asset_integrity.return_value = (False, issues)
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.asset_name = "asset1"

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_validate(args)

        assert result == 1
        output = mock_stdout.getvalue()
        assert "✗ Asset 'asset1' has issues:" in output
        assert "Invalid sample rate" in output
        assert "Missing metadata" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_cleanup(self, mock_get_state_manager):
        """Test state cleanup."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_state_manager.cleanup_old_records.return_value = 5
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.days = 30

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_cleanup(args)

        assert result == 0
        mock_state_manager.cleanup_old_records.assert_called_once_with(30)
        output = mock_stdout.getvalue()
        assert "Removed 5 old maintenance records" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_export(self, mock_get_state_manager):
        """Test state export."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.output_file = str(Path(self.temp_dir) / "export.json")

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = state_export(args)

        assert result == 0
        mock_state_manager.export_state.assert_called_once()
        output = mock_stdout.getvalue()
        assert "State exported to" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_import_confirmed(self, mock_get_state_manager):
        """Test state import with user confirmation."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Create test import file
        import_file = Path(self.temp_dir) / "import.json"
        test_data = {"state": {"key1": "value1"}}
        with open(import_file, "w") as f:
            json.dump(test_data, f)

        # Mock args
        args = Mock()
        args.input_file = str(import_file)

        with patch("builtins.input", return_value="y"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = state_import(args)

        assert result == 0
        mock_state_manager.import_state.assert_called_once()
        output = mock_stdout.getvalue()
        assert "State imported from" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_import_cancelled(self, mock_get_state_manager):
        """Test state import with user cancellation."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()
        args.input_file = "test.json"

        with patch("builtins.input", return_value="n"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = state_import(args)

        assert result == 0
        mock_state_manager.import_state.assert_not_called()
        output = mock_stdout.getvalue()
        assert "State import cancelled" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_clear_confirmed(self, mock_get_state_manager):
        """Test state clear with user confirmation."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()

        with patch("builtins.input", return_value="y"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = state_clear(args)

        assert result == 0
        mock_state_manager.clear_state.assert_called_once()
        output = mock_stdout.getvalue()
        assert "Application state cleared" in output

    @patch("sleepstack.commands.state_parser.get_state_manager")
    def test_state_clear_cancelled(self, mock_get_state_manager):
        """Test state clear with user cancellation."""
        # Mock state manager
        mock_state_manager = Mock()
        mock_get_state_manager.return_value = mock_state_manager

        # Mock args
        args = Mock()

        with patch("builtins.input", return_value="n"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = state_clear(args)

        assert result == 0
        mock_state_manager.clear_state.assert_not_called()
        output = mock_stdout.getvalue()
        assert "State clear cancelled" in output
