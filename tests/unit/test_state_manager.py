"""Tests for state_manager.py"""

import pytest
import tempfile
import json
import os
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta
from collections import defaultdict

from sleepstack.state_manager import (
    StateManager,
    AssetReference,
    AssetDependency,
    MaintenanceRecord,
    get_state_manager,
)
from sleepstack.config import ConfigManager
from sleepstack.asset_manager import AssetManager


class TestStateManagerDataClasses:
    """Test state manager dataclasses."""

    def test_asset_reference(self):
        """Test AssetReference dataclass."""
        ref = AssetReference(
            asset_name="test_asset",
            reference_type="download",
            reference_id="ref_123",
            created_at="2023-01-01T00:00:00",
            metadata={"key": "value"},
        )
        assert ref.asset_name == "test_asset"
        assert ref.reference_type == "download"
        assert ref.reference_id == "ref_123"
        assert ref.created_at == "2023-01-01T00:00:00"
        assert ref.metadata == {"key": "value"}

    def test_asset_dependency(self):
        """Test AssetDependency dataclass."""
        dep = AssetDependency(
            source_asset="source_asset",
            dependent_asset="dependent_asset",
            dependency_type="mix",
            created_at="2023-01-01T00:00:00",
            metadata={"key": "value"},
        )
        assert dep.source_asset == "source_asset"
        assert dep.dependent_asset == "dependent_asset"
        assert dep.dependency_type == "mix"
        assert dep.created_at == "2023-01-01T00:00:00"
        assert dep.metadata == {"key": "value"}

    def test_maintenance_record(self):
        """Test MaintenanceRecord dataclass."""
        record = MaintenanceRecord(
            operation_type="download",
            asset_name="test_asset",
            timestamp="2023-01-01T00:00:00",
            success=True,
            details={"key": "value"},
            error_message=None,
        )
        assert record.operation_type == "download"
        assert record.asset_name == "test_asset"
        assert record.timestamp == "2023-01-01T00:00:00"
        assert record.success is True
        assert record.details == {"key": "value"}
        assert record.error_message is None


class TestStateManager:
    """Test StateManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "sleepstack"
        self.config_dir.mkdir(parents=True)

        # Create mock config manager
        self.mock_config_manager = Mock(spec=ConfigManager)
        self.mock_config_manager.get_config_dir.return_value = self.config_dir

        # Create mock asset manager
        self.mock_asset_manager = Mock(spec=AssetManager)
        self.mock_asset_manager.list_all_assets_with_status.return_value = []

        self.manager = StateManager(
            config_manager=self.mock_config_manager, asset_manager=self.mock_asset_manager
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_init_default_managers(self):
        """Test initialization with default managers."""
        with patch("sleepstack.state_manager.get_config_manager") as mock_get_config:
            with patch("sleepstack.state_manager.get_asset_manager") as mock_get_asset:
                mock_config = Mock()
                mock_config.get_config_dir.return_value = Path("/test/config")
                mock_asset = Mock()
                mock_get_config.return_value = mock_config
                mock_get_asset.return_value = mock_asset

                manager = StateManager()
                assert manager.config_manager == mock_config
                assert manager.asset_manager == mock_asset

    def test_init_custom_managers(self):
        """Test initialization with custom managers."""
        assert self.manager.config_manager == self.mock_config_manager
        assert self.manager.asset_manager == self.mock_asset_manager

    def test_load_state_empty(self):
        """Test loading state when file doesn't exist."""
        state = self.manager._load_state()
        assert state == {}

    def test_load_state_existing(self):
        """Test loading state from existing file."""
        test_state = {"key1": "value1", "key2": {"nested": "value"}}

        with open(self.manager.state_file, "w") as f:
            json.dump(test_state, f)

        state = self.manager._load_state()
        assert state["key1"] == "value1"
        assert state["key2"]["nested"] == "value"

    def test_load_state_invalid_file(self):
        """Test loading state from invalid file."""
        with open(self.manager.state_file, "w") as f:
            f.write("invalid json")

        state = self.manager._load_state()
        assert state == {}

    def test_save_state(self):
        """Test saving state."""
        test_state = {"key1": "value1", "key2": "value2"}
        self.manager._state = test_state
        self.manager._save_state()

        assert self.manager.state_file.exists()
        with open(self.manager.state_file, "r") as f:
            data = json.load(f)
        assert data["key1"] == "value1"
        assert data["key2"] == "value2"
        assert "last_updated" in data

    def test_load_dependencies_empty(self):
        """Test loading dependencies when file doesn't exist."""
        deps = self.manager._load_dependencies()
        assert isinstance(deps, defaultdict)
        assert len(deps) == 0

    def test_load_dependencies_existing(self):
        """Test loading dependencies from existing file."""
        test_deps = {
            "asset1": [
                {
                    "source_asset": "source1",
                    "dependent_asset": "asset1",
                    "dependency_type": "mix",
                    "created_at": "2023-01-01T00:00:00",
                    "metadata": {"key": "value"},
                }
            ]
        }

        with open(self.manager.dependencies_file, "w") as f:
            json.dump(test_deps, f)

        deps = self.manager._load_dependencies()
        assert len(deps["asset1"]) == 1
        assert isinstance(deps["asset1"][0], AssetDependency)
        assert deps["asset1"][0].source_asset == "source1"

    def test_load_dependencies_invalid_file(self):
        """Test loading dependencies from invalid file."""
        with open(self.manager.dependencies_file, "w") as f:
            f.write("invalid json")

        deps = self.manager._load_dependencies()
        assert isinstance(deps, defaultdict)
        assert len(deps) == 0

    def test_save_dependencies(self):
        """Test saving dependencies."""
        dep = AssetDependency(
            source_asset="source1",
            dependent_asset="asset1",
            dependency_type="mix",
            created_at="2023-01-01T00:00:00",
            metadata={"key": "value"},
        )
        self.manager._dependencies["asset1"].append(dep)
        self.manager._save_dependencies()

        assert self.manager.dependencies_file.exists()
        with open(self.manager.dependencies_file, "r") as f:
            data = json.load(f)
        assert "asset1" in data
        assert len(data["asset1"]) == 1

    def test_load_maintenance_records_empty(self):
        """Test loading maintenance records when file doesn't exist."""
        records = self.manager._load_maintenance_records()
        assert records == []

    def test_load_maintenance_records_existing(self):
        """Test loading maintenance records from existing file."""
        test_records = [
            {
                "operation_type": "download",
                "asset_name": "test_asset",
                "timestamp": "2023-01-01T00:00:00",
                "success": True,
                "details": {"key": "value"},
                "error_message": None,
            }
        ]

        with open(self.manager.maintenance_file, "w") as f:
            json.dump(test_records, f)

        records = self.manager._load_maintenance_records()
        assert len(records) == 1
        assert isinstance(records[0], MaintenanceRecord)
        assert records[0].operation_type == "download"

    def test_load_maintenance_records_invalid_file(self):
        """Test loading maintenance records from invalid file."""
        with open(self.manager.maintenance_file, "w") as f:
            f.write("invalid json")

        records = self.manager._load_maintenance_records()
        assert records == []

    def test_save_maintenance_records(self):
        """Test saving maintenance records."""
        record = MaintenanceRecord(
            operation_type="download",
            asset_name="test_asset",
            timestamp="2023-01-01T00:00:00",
            success=True,
            details={"key": "value"},
        )
        self.manager._maintenance_records.append(record)
        self.manager._save_maintenance_records()

        assert self.manager.maintenance_file.exists()
        with open(self.manager.maintenance_file, "r") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["operation_type"] == "download"

    def test_save_maintenance_records_limit(self):
        """Test that maintenance records are limited to 1000."""
        # Add 1005 records
        for i in range(1005):
            record = MaintenanceRecord(
                operation_type="download",
                asset_name=f"asset_{i}",
                timestamp="2023-01-01T00:00:00",
                success=True,
                details={},
            )
            self.manager._maintenance_records.append(record)

        self.manager._save_maintenance_records()

        with open(self.manager.maintenance_file, "r") as f:
            data = json.load(f)
        assert len(data) == 1000
        # Should keep the most recent records
        assert data[-1]["asset_name"] == "asset_1004"

    def test_get_state_no_key(self):
        """Test getting all state."""
        self.manager._state = {"key1": "value1", "key2": "value2"}
        state = self.manager.get_state()
        assert state == {"key1": "value1", "key2": "value2"}

    def test_get_state_with_key(self):
        """Test getting specific state key."""
        self.manager._state = {"key1": "value1", "key2": "value2"}
        value = self.manager.get_state("key1")
        assert value == "value1"

    def test_set_state(self):
        """Test setting state."""
        self.manager.set_state("key1", "value1")
        assert self.manager._state["key1"] == "value1"
        assert self.manager.state_file.exists()

    def test_update_state(self):
        """Test updating multiple state values."""
        self.manager.update_state(key1="value1", key2="value2")
        assert self.manager._state["key1"] == "value1"
        assert self.manager._state["key2"] == "value2"

    def test_add_asset_reference(self):
        """Test adding asset reference."""
        self.manager.add_asset_reference(
            asset_name="test_asset",
            reference_type="download",
            reference_id="ref_123",
            metadata={"key": "value"},
        )

        assert "asset_references" in self.manager._state
        assert "test_asset" in self.manager._state["asset_references"]
        refs = self.manager._state["asset_references"]["test_asset"]
        assert len(refs) == 1
        assert refs[0]["reference_type"] == "download"

    def test_get_asset_references(self):
        """Test getting asset references."""
        self.manager.add_asset_reference(
            asset_name="test_asset", reference_type="download", reference_id="ref_123"
        )

        refs = self.manager.get_asset_references("test_asset")
        assert len(refs) == 1
        assert isinstance(refs[0], AssetReference)
        assert refs[0].reference_type == "download"

    def test_get_asset_references_empty(self):
        """Test getting asset references when none exist."""
        refs = self.manager.get_asset_references("nonexistent")
        assert refs == []

    def test_add_dependency(self):
        """Test adding asset dependency."""
        self.manager.add_dependency(
            source_asset="source1",
            dependent_asset="asset1",
            dependency_type="mix",
            metadata={"key": "value"},
        )

        deps = self.manager.get_dependencies("asset1")
        assert len(deps) == 1
        assert deps[0].source_asset == "source1"
        assert deps[0].dependency_type == "mix"

    def test_get_dependencies(self):
        """Test getting asset dependencies."""
        self.manager.add_dependency(
            source_asset="source1", dependent_asset="asset1", dependency_type="mix"
        )

        deps = self.manager.get_dependencies("asset1")
        assert len(deps) == 1
        assert isinstance(deps[0], AssetDependency)
        assert deps[0].source_asset == "source1"

    def test_get_dependencies_empty(self):
        """Test getting dependencies when none exist."""
        deps = self.manager.get_dependencies("nonexistent")
        assert deps == []

    def test_get_dependents(self):
        """Test getting assets that depend on given asset."""
        self.manager.add_dependency(
            source_asset="source1", dependent_asset="asset1", dependency_type="mix"
        )
        self.manager.add_dependency(
            source_asset="source1", dependent_asset="asset2", dependency_type="derived"
        )

        dependents = self.manager.get_dependents("source1")
        assert len(dependents) == 2
        assert dependents[0].dependent_asset == "asset1"
        assert dependents[1].dependent_asset == "asset2"

    def test_get_dependents_empty(self):
        """Test getting dependents when none exist."""
        dependents = self.manager.get_dependents("nonexistent")
        assert dependents == []

    def test_remove_dependencies(self):
        """Test removing all dependencies for an asset."""
        self.manager.add_dependency(
            source_asset="source1", dependent_asset="asset1", dependency_type="mix"
        )
        self.manager.add_dependency(
            source_asset="asset1", dependent_asset="asset2", dependency_type="derived"
        )

        # Remove dependencies for asset1
        self.manager.remove_dependencies("asset1")

        # Should remove both dependencies where asset1 is involved
        deps = self.manager.get_dependencies("asset1")
        assert len(deps) == 0

        dependents = self.manager.get_dependents("asset1")
        assert len(dependents) == 0

    def test_add_maintenance_record(self):
        """Test adding maintenance record."""
        self.manager.add_maintenance_record(
            operation_type="download",
            asset_name="test_asset",
            success=True,
            details={"key": "value"},
        )

        records = self.manager.get_maintenance_records()
        assert len(records) == 1
        assert records[0].operation_type == "download"
        assert records[0].success is True

    def test_add_maintenance_record_with_error(self):
        """Test adding maintenance record with error."""
        self.manager.add_maintenance_record(
            operation_type="download",
            asset_name="test_asset",
            success=False,
            error_message="Download failed",
        )

        records = self.manager.get_maintenance_records()
        assert len(records) == 1
        assert records[0].success is False
        assert records[0].error_message == "Download failed"

    def test_get_maintenance_records_with_limit(self):
        """Test getting maintenance records with limit."""
        # Add 5 records
        for i in range(5):
            self.manager.add_maintenance_record(
                operation_type="download", asset_name=f"asset_{i}", success=True
            )

        records = self.manager.get_maintenance_records(limit=3)
        assert len(records) == 3

    def test_get_maintenance_stats_empty(self):
        """Test getting maintenance stats when no records exist."""
        stats = self.manager.get_maintenance_stats()
        assert stats["total_operations"] == 0
        assert stats["successful_operations"] == 0
        assert stats["failed_operations"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["operation_types"] == {}
        assert stats["recent_operations"] == []

    def test_get_maintenance_stats_with_records(self):
        """Test getting maintenance stats with records."""
        # Add some records
        self.manager.add_maintenance_record("download", "asset1", True)
        self.manager.add_maintenance_record("download", "asset2", True)
        self.manager.add_maintenance_record("validation", "asset3", False)

        stats = self.manager.get_maintenance_stats()
        assert stats["total_operations"] == 3
        assert stats["successful_operations"] == 2
        assert stats["failed_operations"] == 1
        assert stats["success_rate"] == 2 / 3
        assert stats["operation_types"]["download"] == 2
        assert stats["operation_types"]["validation"] == 1
        assert len(stats["recent_operations"]) == 3

    def test_cleanup_old_records(self):
        """Test cleaning up old maintenance records."""
        # Add old record
        old_record = MaintenanceRecord(
            operation_type="download",
            asset_name="old_asset",
            timestamp=(datetime.now() - timedelta(days=35)).isoformat(),
            success=True,
            details={},
        )
        self.manager._maintenance_records.append(old_record)

        # Add recent record
        recent_record = MaintenanceRecord(
            operation_type="download",
            asset_name="recent_asset",
            timestamp=datetime.now().isoformat(),
            success=True,
            details={},
        )
        self.manager._maintenance_records.append(recent_record)

        removed = self.manager.cleanup_old_records(days=30)
        assert removed == 1

        records = self.manager.get_maintenance_records()
        assert len(records) == 1
        assert records[0].asset_name == "recent_asset"

    def test_cleanup_old_records_no_removal(self):
        """Test cleanup when no records need removal."""
        # Add recent record
        recent_record = MaintenanceRecord(
            operation_type="download",
            asset_name="recent_asset",
            timestamp=datetime.now().isoformat(),
            success=True,
            details={},
        )
        self.manager._maintenance_records.append(recent_record)

        removed = self.manager.cleanup_old_records(days=30)
        assert removed == 0

        records = self.manager.get_maintenance_records()
        assert len(records) == 1

    def test_validate_asset_integrity_success(self):
        """Test validating asset integrity successfully."""
        self.mock_asset_manager.validate_asset_integrity.return_value = (True, [])

        is_valid, issues = self.manager.validate_asset_integrity("test_asset")

        assert is_valid is True
        assert len(issues) == 0
        self.mock_asset_manager.validate_asset_integrity.assert_called_once_with("test_asset")

        # Should add maintenance record
        records = self.manager.get_maintenance_records()
        assert len(records) == 1
        assert records[0].operation_type == "validation"
        assert records[0].success is True

    def test_validate_asset_integrity_failure(self):
        """Test validating asset integrity with issues."""
        issues = ["Invalid sample rate", "Missing metadata"]
        self.mock_asset_manager.validate_asset_integrity.return_value = (False, issues)

        is_valid, issues_result = self.manager.validate_asset_integrity("test_asset")

        assert is_valid is False
        assert issues_result == issues

        # Should add maintenance record
        records = self.manager.get_maintenance_records()
        assert len(records) == 1
        assert records[0].operation_type == "validation"
        assert records[0].success is False
        assert records[0].error_message == "Invalid sample rate; Missing metadata"

    def test_get_asset_health_summary(self):
        """Test getting asset health summary."""
        mock_assets = [
            {"name": "asset1", "is_valid": True, "issues": []},
            {
                "name": "asset2",
                "is_valid": False,
                "issues": ["Invalid sample rate", "Missing metadata"],
            },
        ]
        self.mock_asset_manager.list_all_assets_with_status.return_value = mock_assets

        health = self.manager.get_asset_health_summary()

        assert health["total_assets"] == 2
        assert health["valid_assets"] == 1
        assert health["invalid_assets"] == 1
        assert health["health_percentage"] == 50.0
        assert health["issue_types"]["sample_rate"] == 1
        assert health["issue_types"]["metadata"] == 1
        assert health["assets"] == mock_assets

    def test_get_asset_health_summary_empty(self):
        """Test getting asset health summary with no assets."""
        self.mock_asset_manager.list_all_assets_with_status.return_value = []

        health = self.manager.get_asset_health_summary()

        assert health["total_assets"] == 0
        assert health["valid_assets"] == 0
        assert health["invalid_assets"] == 0
        assert health["health_percentage"] == 0

    def test_export_state(self):
        """Test exporting state data."""
        # Add some data
        self.manager._state = {"key1": "value1"}
        self.manager.add_dependency("source1", "asset1", "mix")
        self.manager.add_maintenance_record("download", "asset1", True)

        output_path = Path(self.temp_dir) / "export.json"
        self.manager.export_state(output_path)

        assert output_path.exists()
        with open(output_path, "r") as f:
            data = json.load(f)

        assert "export_timestamp" in data
        assert data["state"]["key1"] == "value1"
        assert "asset1" in data["dependencies"]
        assert len(data["maintenance_records"]) == 1

    def test_import_state(self):
        """Test importing state data."""
        # Create export data
        export_data = {
            "export_timestamp": "2023-01-01T00:00:00",
            "state": {"key1": "value1"},
            "dependencies": {
                "asset1": [
                    {
                        "source_asset": "source1",
                        "dependent_asset": "asset1",
                        "dependency_type": "mix",
                        "created_at": "2023-01-01T00:00:00",
                        "metadata": {},
                    }
                ]
            },
            "maintenance_records": [
                {
                    "operation_type": "download",
                    "asset_name": "asset1",
                    "timestamp": "2023-01-01T00:00:00",
                    "success": True,
                    "details": {},
                    "error_message": None,
                }
            ],
        }

        input_path = Path(self.temp_dir) / "import.json"
        with open(input_path, "w") as f:
            json.dump(export_data, f)

        self.manager.import_state(input_path)

        # Verify state was imported
        assert self.manager._state["key1"] == "value1"
        deps = self.manager.get_dependencies("asset1")
        assert len(deps) == 1
        records = self.manager.get_maintenance_records()
        assert len(records) == 1


class TestGetStateManager:
    """Test get_state_manager function."""

    def test_get_state_manager(self):
        """Test getting global state manager instance."""
        manager = get_state_manager()
        assert isinstance(manager, StateManager)


class TestStateManagerIntegration:
    """Integration tests for state manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "sleepstack"
        self.config_dir.mkdir(parents=True)

        # Create mock config manager
        self.mock_config_manager = Mock(spec=ConfigManager)
        self.mock_config_manager.get_config_dir.return_value = self.config_dir

        # Create mock asset manager
        self.mock_asset_manager = Mock(spec=AssetManager)
        self.mock_asset_manager.list_all_assets_with_status.return_value = []

        self.manager = StateManager(
            config_manager=self.mock_config_manager, asset_manager=self.mock_asset_manager
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_full_state_lifecycle(self):
        """Test complete state management lifecycle."""
        # Set state
        self.manager.set_state("test_key", "test_value")

        # Add asset reference
        self.manager.add_asset_reference(
            asset_name="test_asset", reference_type="download", reference_id="ref_123"
        )

        # Add dependency
        self.manager.add_dependency(
            source_asset="source1", dependent_asset="test_asset", dependency_type="mix"
        )

        # Add maintenance record
        self.manager.add_maintenance_record(
            operation_type="download", asset_name="test_asset", success=True
        )

        # Verify all data is present
        assert self.manager.get_state("test_key") == "test_value"
        refs = self.manager.get_asset_references("test_asset")
        assert len(refs) == 1
        deps = self.manager.get_dependencies("test_asset")
        assert len(deps) == 1
        records = self.manager.get_maintenance_records()
        assert len(records) == 1

        # Export state
        export_path = Path(self.temp_dir) / "export.json"
        self.manager.export_state(export_path)
        assert export_path.exists()

        # Create new manager and import state
        new_manager = StateManager(
            config_manager=self.mock_config_manager, asset_manager=self.mock_asset_manager
        )
        new_manager.import_state(export_path)

        # Verify imported data
        assert new_manager.get_state("test_key") == "test_value"
        refs = new_manager.get_asset_references("test_asset")
        assert len(refs) == 1
        deps = new_manager.get_dependencies("test_asset")
        assert len(deps) == 1
        records = new_manager.get_maintenance_records()
        assert len(records) == 1


class TestStateManagerMain:
    """Test the main() function in state_manager.py."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "sleepstack"
        self.config_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sys.argv", ["state_manager.py", "state"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_state_command_no_key(self, mock_get_manager):
        """Test main function with state command (no key)."""
        mock_manager = Mock()
        mock_manager.get_state.return_value = {"last_operation": "download", "total_assets": 5}
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Application State:" in output
            assert "last_operation: download" in output
            assert "total_assets: 5" in output

    @patch("sys.argv", ["state_manager.py", "state", "last_operation"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_state_command_with_key(self, mock_get_manager):
        """Test main function with state command (with key)."""
        mock_manager = Mock()
        mock_manager.get_state.return_value = "download"
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "last_operation: download" in output

    @patch("sys.argv", ["state_manager.py", "dependencies", "test_asset"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_dependencies_command_with_asset(self, mock_get_manager):
        """Test main function with dependencies command (with asset)."""
        mock_manager = Mock()
        mock_dep = Mock()
        mock_dep.dependency_type = "mix"
        mock_dep.source_asset = "source_asset"
        mock_manager.get_dependencies.return_value = [mock_dep]
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Dependencies for 'test_asset':" in output
            assert "- mix: source_asset" in output

    @patch("sys.argv", ["state_manager.py", "dependencies"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_dependencies_command_no_asset(self, mock_get_manager):
        """Test main function with dependencies command (no asset)."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Usage: python state_manager.py dependencies <asset_name>" in output

    @patch("sys.argv", ["state_manager.py", "maintenance"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_maintenance_command(self, mock_get_manager):
        """Test main function with maintenance command."""
        mock_manager = Mock()
        mock_manager.get_maintenance_stats.return_value = {
            "total_operations": 10,
            "successful_operations": 8,
            "failed_operations": 2,
            "success_rate": 0.8,
            "operation_types": {"download": 5, "validation": 3, "cleanup": 2},
        }
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Maintenance Statistics:" in output
            assert "Total Operations: 10" in output
            assert "Successful: 8" in output
            assert "Failed: 2" in output
            assert "Success Rate: 80.0%" in output
            assert "Operation Types: {'download': 5, 'validation': 3, 'cleanup': 2}" in output

    @patch("sys.argv", ["state_manager.py", "health"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_health_command(self, mock_get_manager):
        """Test main function with health command."""
        mock_manager = Mock()
        mock_manager.get_asset_health_summary.return_value = {
            "total_assets": 10,
            "valid_assets": 8,
            "invalid_assets": 2,
            "health_percentage": 80.0,
            "issue_types": {"sample_rate": 1, "channels": 1},
        }
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Asset Health Summary:" in output
            assert "Total Assets: 10" in output
            assert "Valid Assets: 8" in output
            assert "Invalid Assets: 2" in output
            assert "Health: 80.0%" in output
            assert "Issue Types:" in output
            assert "sample_rate: 1" in output
            assert "channels: 1" in output

    @patch("sys.argv", ["state_manager.py", "cleanup", "7"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_cleanup_command_with_days(self, mock_get_manager):
        """Test main function with cleanup command (with days)."""
        mock_manager = Mock()
        mock_manager.cleanup_old_records.return_value = 5
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Removed 5 old maintenance records" in output
            mock_manager.cleanup_old_records.assert_called_once_with(7)

    @patch("sys.argv", ["state_manager.py", "cleanup"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_cleanup_command_default_days(self, mock_get_manager):
        """Test main function with cleanup command (default days)."""
        mock_manager = Mock()
        mock_manager.cleanup_old_records.return_value = 3
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Removed 3 old maintenance records" in output
            mock_manager.cleanup_old_records.assert_called_once_with(30)

    @patch("sys.argv", ["state_manager.py", "unknown"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_unknown_command(self, mock_get_manager):
        """Test main function with unknown command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Unknown command" in output
            assert "state, dependencies, maintenance, health, cleanup" in output

    @patch("sys.argv", ["state_manager.py"])
    @patch("sleepstack.state_manager.get_state_manager")
    def test_main_no_command(self, mock_get_manager):
        """Test main function with no command."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from sleepstack.state_manager import main

            main()

            output = mock_stdout.getvalue()
            assert "Usage: python state_manager.py <command> [args]" in output
            assert "Commands: state, dependencies, maintenance, health, cleanup" in output


class TestStateManagerIssueTypes:
    """Test issue type categorization in get_asset_health_summary."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "sleepstack"
        self.config_dir.mkdir(parents=True)

        self.mock_config_manager = Mock(spec=ConfigManager)
        self.mock_config_manager.get_config_dir.return_value = self.config_dir

        self.mock_asset_manager = Mock(spec=AssetManager)
        self.mock_asset_manager.list_all_assets_with_status.return_value = []

        self.manager = StateManager(
            config_manager=self.mock_config_manager, asset_manager=self.mock_asset_manager
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_asset_health_summary_issue_types(self):
        """Test issue type categorization in health summary."""
        # Mock assets with different types of issues - need to return dict-like objects
        mock_assets = [
            {"is_valid": True, "issues": []},
            {"is_valid": False, "issues": ["Invalid sample rate: 22050 Hz"]},
            {"is_valid": False, "issues": ["Invalid channels: mono"]},
            {"is_valid": False, "issues": ["Invalid duration: 30 seconds"]},
            {"is_valid": False, "issues": ["File size too small: 100 bytes"]},
            {"is_valid": False, "issues": ["Metadata mismatch"]},
            {"is_valid": False, "issues": ["Unknown issue"]},
        ]

        self.mock_asset_manager.list_all_assets_with_status.return_value = mock_assets

        health = self.manager.get_asset_health_summary()

        assert health["total_assets"] == 7
        assert health["valid_assets"] == 1
        assert health["invalid_assets"] == 6
        assert health["issue_types"]["sample_rate"] == 1
        assert health["issue_types"]["channels"] == 1
        assert health["issue_types"]["duration"] == 1
        assert health["issue_types"]["file_size"] == 1
        assert health["issue_types"]["metadata"] == 1
        assert health["issue_types"]["other"] == 1
