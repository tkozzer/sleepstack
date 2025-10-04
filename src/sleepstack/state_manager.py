"""
State management system for sleepstack.

This module provides state tracking for ambient sounds, asset dependencies,
download history, and maintenance operations.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from .config import ConfigManager, get_config_manager
from .asset_manager import AssetManager, get_asset_manager


@dataclass
class AssetReference:
    """Represents a reference to an asset."""

    asset_name: str
    reference_type: str  # 'download', 'mix', 'backup', etc.
    reference_id: str
    created_at: str
    metadata: Dict[str, Any]


@dataclass
class AssetDependency:
    """Represents a dependency between assets."""

    source_asset: str
    dependent_asset: str
    dependency_type: str  # 'mix', 'derived', 'backup', etc.
    created_at: str
    metadata: Dict[str, Any]


@dataclass
class MaintenanceRecord:
    """Record of maintenance operations."""

    operation_type: str
    asset_name: Optional[str]
    timestamp: str
    success: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None


class StateManager:
    """Manages application state, asset dependencies, and maintenance records."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        asset_manager: Optional[AssetManager] = None,
    ):
        """
        Initialize the state manager.

        Args:
            config_manager: Configuration manager instance
            asset_manager: Asset manager instance
        """
        self.config_manager = config_manager or get_config_manager()
        self.asset_manager = asset_manager or get_asset_manager()

        self.state_file = self.config_manager.get_config_dir() / "state.json"
        self.dependencies_file = self.config_manager.get_config_dir() / "dependencies.json"
        self.maintenance_file = self.config_manager.get_config_dir() / "maintenance.json"

        # Load existing state
        self._state = self._load_state()
        self._dependencies = self._load_dependencies()
        self._maintenance_records = self._load_maintenance_records()

    def _load_state(self) -> Dict[str, Any]:
        """Load application state from file."""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_state(self) -> None:
        """Save application state to file."""
        self._state["last_updated"] = datetime.now().isoformat()

        with open(self.state_file, "w") as f:
            json.dump(self._state, f, indent=2)

    def _load_dependencies(self) -> Dict[str, List[AssetDependency]]:
        """Load asset dependencies from file."""
        if not self.dependencies_file.exists():
            return defaultdict(list)

        try:
            with open(self.dependencies_file, "r") as f:
                data = json.load(f)
                dependencies = defaultdict(list)

                for asset_name, deps in data.items():
                    for dep_data in deps:
                        dep = AssetDependency(**dep_data)
                        dependencies[asset_name].append(dep)

                return dependencies
        except (json.JSONDecodeError, IOError, TypeError):
            return defaultdict(list)

    def _save_dependencies(self) -> None:
        """Save asset dependencies to file."""
        # Convert defaultdict to regular dict for JSON serialization
        data = {}
        for asset_name, deps in self._dependencies.items():
            data[asset_name] = [asdict(dep) for dep in deps]

        with open(self.dependencies_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_maintenance_records(self) -> List[MaintenanceRecord]:
        """Load maintenance records from file."""
        if not self.maintenance_file.exists():
            return []

        try:
            with open(self.maintenance_file, "r") as f:
                data = json.load(f)
                return [MaintenanceRecord(**record) for record in data]
        except (json.JSONDecodeError, IOError, TypeError):
            return []

    def _save_maintenance_records(self) -> None:
        """Save maintenance records to file."""
        # Keep only last 1000 records
        records_to_save = self._maintenance_records[-1000:]

        with open(self.maintenance_file, "w") as f:
            json.dump([asdict(record) for record in records_to_save], f, indent=2)

    def get_state(self, key: Optional[str] = None) -> Any:
        """
        Get application state.

        Args:
            key: Specific state key to retrieve (returns all state if None)

        Returns:
            State value or entire state dictionary
        """
        if key is None:
            return self._state.copy()
        return self._state.get(key)

    def set_state(self, key: str, value: Any) -> None:
        """
        Set application state.

        Args:
            key: State key
            value: State value
        """
        self._state[key] = value
        self._save_state()

    def update_state(self, **kwargs: Any) -> None:
        """
        Update multiple state values.

        Args:
            **kwargs: State updates
        """
        self._state.update(kwargs)
        self._save_state()

    def add_asset_reference(
        self,
        asset_name: str,
        reference_type: str,
        reference_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a reference to an asset.

        Args:
            asset_name: Name of the asset
            reference_type: Type of reference (e.g., 'download', 'mix')
            reference_id: Unique identifier for the reference
            metadata: Additional metadata
        """
        if "asset_references" not in self._state:
            self._state["asset_references"] = {}

        if asset_name not in self._state["asset_references"]:
            self._state["asset_references"][asset_name] = []

        reference = AssetReference(
            asset_name=asset_name,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )

        self._state["asset_references"][asset_name].append(asdict(reference))
        self._save_state()

    def get_asset_references(self, asset_name: str) -> List[AssetReference]:
        """
        Get all references for an asset.

        Args:
            asset_name: Name of the asset

        Returns:
            List of asset references
        """
        references = self._state.get("asset_references", {}).get(asset_name, [])
        return [AssetReference(**ref) for ref in references]

    def add_dependency(
        self,
        source_asset: str,
        dependent_asset: str,
        dependency_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a dependency between assets.

        Args:
            source_asset: Name of the source asset
            dependent_asset: Name of the dependent asset
            dependency_type: Type of dependency (e.g., 'mix', 'derived')
            metadata: Additional metadata
        """
        dependency = AssetDependency(
            source_asset=source_asset,
            dependent_asset=dependent_asset,
            dependency_type=dependency_type,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )

        self._dependencies[dependent_asset].append(dependency)
        self._save_dependencies()

    def get_dependencies(self, asset_name: str) -> List[AssetDependency]:
        """
        Get all dependencies for an asset.

        Args:
            asset_name: Name of the asset

        Returns:
            List of asset dependencies
        """
        return self._dependencies.get(asset_name, [])

    def get_dependents(self, asset_name: str) -> List[AssetDependency]:
        """
        Get all assets that depend on the given asset.

        Args:
            asset_name: Name of the asset

        Returns:
            List of dependencies where the given asset is the source
        """
        dependents = []
        for deps in self._dependencies.values():
            for dep in deps:
                if dep.source_asset == asset_name:
                    dependents.append(dep)
        return dependents

    def remove_dependencies(self, asset_name: str) -> None:
        """
        Remove all dependencies for an asset.

        Args:
            asset_name: Name of the asset
        """
        # Remove dependencies where this asset is the dependent
        if asset_name in self._dependencies:
            del self._dependencies[asset_name]

        # Remove dependencies where this asset is the source
        for deps in self._dependencies.values():
            deps[:] = [dep for dep in deps if dep.source_asset != asset_name]

        self._save_dependencies()

    def add_maintenance_record(
        self,
        operation_type: str,
        asset_name: Optional[str],
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Add a maintenance operation record.

        Args:
            operation_type: Type of maintenance operation
            asset_name: Name of the asset (if applicable)
            success: Whether the operation was successful
            details: Additional operation details
            error_message: Error message if operation failed
        """
        record = MaintenanceRecord(
            operation_type=operation_type,
            asset_name=asset_name,
            timestamp=datetime.now().isoformat(),
            success=success,
            details=details or {},
            error_message=error_message,
        )

        self._maintenance_records.append(record)
        self._save_maintenance_records()

    def get_maintenance_records(self, limit: Optional[int] = None) -> List[MaintenanceRecord]:
        """
        Get maintenance records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of maintenance records
        """
        records = self._maintenance_records
        if limit:
            records = records[-limit:]
        return records

    def get_maintenance_stats(self) -> Dict[str, Any]:
        """
        Get maintenance operation statistics.

        Returns:
            Dictionary with maintenance statistics
        """
        if not self._maintenance_records:
            return {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "success_rate": 0.0,
                "operation_types": {},
                "recent_operations": [],
            }

        total = len(self._maintenance_records)
        successful = sum(1 for record in self._maintenance_records if record.success)
        failed = total - successful

        # Count operation types
        operation_types: dict[str, int] = defaultdict(int)
        for record in self._maintenance_records:
            operation_types[record.operation_type] += 1

        # Get recent operations (last 10)
        recent = self._maintenance_records[-10:]

        return {
            "total_operations": total,
            "successful_operations": successful,
            "failed_operations": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "operation_types": dict(operation_types),
            "recent_operations": [asdict(record) for record in recent],
        }

    def cleanup_old_records(self, days: int = 30) -> int:
        """
        Clean up old maintenance records.

        Args:
            days: Number of days to keep records

        Returns:
            Number of records removed
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        original_count = len(self._maintenance_records)
        self._maintenance_records = [
            record for record in self._maintenance_records if record.timestamp >= cutoff_str
        ]

        removed_count = original_count - len(self._maintenance_records)
        if removed_count > 0:
            self._save_maintenance_records()

        return removed_count

    def validate_asset_integrity(self, asset_name: str) -> Tuple[bool, List[str]]:
        """
        Validate asset integrity and update state.

        Args:
            asset_name: Name of the asset to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        is_valid, issues = self.asset_manager.validate_asset_integrity(asset_name)

        # Record validation in maintenance records
        self.add_maintenance_record(
            operation_type="validation",
            asset_name=asset_name,
            success=is_valid,
            details={"issues": issues},
            error_message=None if is_valid else "; ".join(issues),
        )

        return is_valid, issues

    def get_asset_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of asset health across all assets.

        Returns:
            Dictionary with asset health summary
        """
        assets = self.asset_manager.list_all_assets_with_status()

        total_assets = len(assets)
        valid_assets = sum(1 for asset in assets if asset["is_valid"])
        invalid_assets = total_assets - valid_assets

        # Group issues by type
        issue_types: dict[str, int] = defaultdict(int)
        for asset in assets:
            for issue in asset["issues"]:
                # Extract issue type from issue message
                if "sample rate" in issue.lower():
                    issue_types["sample_rate"] += 1
                elif "channel" in issue.lower():
                    issue_types["channels"] += 1
                elif "duration" in issue.lower():
                    issue_types["duration"] += 1
                elif "file size" in issue.lower():
                    issue_types["file_size"] += 1
                elif "metadata" in issue.lower():
                    issue_types["metadata"] += 1
                else:
                    issue_types["other"] += 1

        return {
            "total_assets": total_assets,
            "valid_assets": valid_assets,
            "invalid_assets": invalid_assets,
            "health_percentage": (valid_assets / total_assets * 100) if total_assets > 0 else 0,
            "issue_types": dict(issue_types),
            "assets": assets,
        }

    def export_state(self, output_path: Path) -> None:
        """
        Export all state data to a file.

        Args:
            output_path: Path to export file
        """
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "state": self._state,
            "dependencies": {
                name: [asdict(dep) for dep in deps] for name, deps in self._dependencies.items()
            },
            "maintenance_records": [asdict(record) for record in self._maintenance_records],
            "asset_health": self.get_asset_health_summary(),
            "maintenance_stats": self.get_maintenance_stats(),
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

    def import_state(self, input_path: Path) -> None:
        """
        Import state data from a file.

        Args:
            input_path: Path to import file
        """
        with open(input_path, "r") as f:
            import_data = json.load(f)

        # Import state
        if "state" in import_data:
            self._state = import_data["state"]
            self._save_state()

        # Import dependencies
        if "dependencies" in import_data:
            self._dependencies = defaultdict(list)
            for asset_name, deps in import_data["dependencies"].items():
                for dep_data in deps:
                    dep = AssetDependency(**dep_data)
                    self._dependencies[asset_name].append(dep)
            self._save_dependencies()

        # Import maintenance records
        if "maintenance_records" in import_data:
            self._maintenance_records = [
                MaintenanceRecord(**record) for record in import_data["maintenance_records"]
            ]
            self._save_maintenance_records()

    def clear_state(self) -> None:
        """Clear all application state."""
        self._state = {}
        self._asset_references: dict[str, list[AssetReference]] = {}
        self._asset_dependencies: dict[str, list[AssetDependency]] = {}
        self._maintenance_records = []
        self._save_state()
        self._save_dependencies()
        self._save_maintenance_records()


def get_state_manager() -> StateManager:
    """Get a global state manager instance."""
    return StateManager()


def main() -> None:
    """CLI entry point for testing the state manager."""
    import sys

    manager = get_state_manager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "state":
            if len(sys.argv) > 2:
                key = sys.argv[2]
                value = manager.get_state(key)
                print(f"{key}: {value}")
            else:
                state = manager.get_state()
                print("Application State:")
                for key, value in state.items():
                    print(f"  {key}: {value}")

        elif command == "dependencies":
            if len(sys.argv) > 2:
                asset_name = sys.argv[2]
                deps = manager.get_dependencies(asset_name)
                print(f"Dependencies for '{asset_name}':")
                for dep in deps:
                    print(f"  - {dep.dependency_type}: {dep.source_asset}")
            else:
                print("Usage: python state_manager.py dependencies <asset_name>")

        elif command == "maintenance":
            stats = manager.get_maintenance_stats()
            print("Maintenance Statistics:")
            print(f"  Total Operations: {stats['total_operations']}")
            print(f"  Successful: {stats['successful_operations']}")
            print(f"  Failed: {stats['failed_operations']}")
            print(f"  Success Rate: {stats['success_rate']:.1%}")
            print(f"  Operation Types: {stats['operation_types']}")

        elif command == "health":
            health = manager.get_asset_health_summary()
            print("Asset Health Summary:")
            print(f"  Total Assets: {health['total_assets']}")
            print(f"  Valid Assets: {health['valid_assets']}")
            print(f"  Invalid Assets: {health['invalid_assets']}")
            print(f"  Health: {health['health_percentage']:.1f}%")
            if health["issue_types"]:
                print("  Issue Types:")
                for issue_type, count in health["issue_types"].items():
                    print(f"    {issue_type}: {count}")

        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            removed = manager.cleanup_old_records(days)
            print(f"Removed {removed} old maintenance records")

        else:
            print("Unknown command. Available: state, dependencies, maintenance, health, cleanup")
    else:
        print("Usage: python state_manager.py <command> [args]")
        print("Commands: state, dependencies, maintenance, health, cleanup")


if __name__ == "__main__":
    main()
