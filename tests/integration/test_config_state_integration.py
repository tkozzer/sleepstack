"""Integration tests for configuration and state management with download system"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta

from sleepstack.config import ConfigManager, get_config_manager
from sleepstack.state_manager import StateManager, get_state_manager, MaintenanceRecord
from sleepstack.asset_manager import AssetManager, get_asset_manager
from sleepstack.download_ambient import download_and_process_ambient_sound
from sleepstack.ambient_manager import AmbientSoundMetadata


class TestConfigStateIntegration:
    """Integration tests for configuration and state management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "sleepstack"
        self.config_dir.mkdir(parents=True)
        self.assets_dir = Path(self.temp_dir) / "assets" / "ambience"
        self.assets_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_config_manager_integration(self):
        """Test ConfigManager integration with file system."""
        # Create manager
        manager = ConfigManager(self.config_dir)

        # Verify default config is created
        assert manager.config_file.exists()
        config = manager.get_config()
        assert config.download.default_sample_rate == 48000

        # Update configuration
        manager.update_config(**{"download.default_sample_rate": 44100})
        assert manager.get_config().download.default_sample_rate == 44100

        # Verify configuration persists
        new_manager = ConfigManager(self.config_dir)
        assert new_manager.get_config().download.default_sample_rate == 44100

    def test_state_manager_integration(self):
        """Test StateManager integration with file system."""
        # Create mock managers
        mock_config_manager = Mock()
        mock_config_manager.get_config_dir.return_value = self.config_dir
        mock_asset_manager = Mock()

        # Create state manager
        manager = StateManager(mock_config_manager, mock_asset_manager)

        # Add some state
        manager.set_state("test_key", "test_value")
        manager.add_asset_reference("asset1", "download", "ref_123")
        manager.add_dependency("source1", "asset1", "mix")
        manager.add_maintenance_record("download", "asset1", True)

        # Verify state persists
        new_manager = StateManager(mock_config_manager, mock_asset_manager)
        assert new_manager.get_state("test_key") == "test_value"
        refs = new_manager.get_asset_references("asset1")
        assert len(refs) == 1
        deps = new_manager.get_dependencies("asset1")
        assert len(deps) == 1
        records = new_manager.get_maintenance_records()
        assert len(records) == 1

    def test_config_state_export_import(self):
        """Test exporting and importing configuration and state."""
        # Create managers
        config_manager = ConfigManager(self.config_dir)
        mock_asset_manager = Mock()
        mock_asset_manager.list_all_assets_with_status.return_value = []
        state_manager = StateManager(config_manager, mock_asset_manager)

        # Set up some data
        config_manager.update_config(**{"download.default_sample_rate": 44100})
        state_manager.set_state("test_key", "test_value")
        state_manager.add_maintenance_record("download", "asset1", True)

        # Export state
        export_path = Path(self.temp_dir) / "export.json"
        state_manager.export_state(export_path)
        assert export_path.exists()

        # Create new managers and import
        new_config_dir = Path(self.temp_dir) / "new_config"
        new_config_dir.mkdir()
        new_config_manager = ConfigManager(new_config_dir)
        new_state_manager = StateManager(new_config_manager, mock_asset_manager)

        new_state_manager.import_state(export_path)

        # Verify imported data
        assert new_state_manager.get_state("test_key") == "test_value"
        records = new_state_manager.get_maintenance_records()
        assert len(records) == 1

    def test_download_integration_with_config(self):
        """Test download system integration with configuration."""
        # Create config manager with custom settings
        config_manager = ConfigManager(self.config_dir)
        config_manager.update_config(
            **{
                "download.default_sample_rate": 44100,
                "download.default_duration": 30,
                "download.volume_adjustment": 0.9,
            }
        )

        # Mock the download process
        with patch("sleepstack.download_ambient.validate_prerequisites"):
            with patch("sleepstack.download_ambient.get_video_info") as mock_get_info:
                with patch("sleepstack.download_ambient.download_audio") as mock_download:
                    with patch("sleepstack.download_ambient.process_audio") as mock_process:
                        with patch(
                            "sleepstack.download_ambient.get_asset_manager"
                        ) as mock_get_asset:
                            with patch(
                                "sleepstack.download_ambient.get_config_manager",
                                return_value=config_manager,
                            ):
                                with patch(
                                    "sleepstack.download_ambient.get_state_manager"
                                ) as mock_get_state:
                                    # Mock video info
                                    mock_get_info.return_value = {
                                        "title": "Test Video",
                                        "duration": 120,
                                        "uploader": "Test User",
                                        "description": "Test description",
                                    }

                                    # Mock asset manager
                                    mock_asset_manager = Mock()
                                    mock_asset_manager.create_individual_metadata_file.return_value = Path(
                                        "metadata.json"
                                    )
                                    mock_get_asset.return_value = mock_asset_manager

                                    # Mock state manager
                                    mock_state_manager = Mock()
                                    mock_get_state.return_value = mock_state_manager

                                    # Mock download_audio to create a temporary file
                                    def mock_download_side_effect(url, temp_path):
                                        # Create a temporary file that the download function can find
                                        temp_file = Path(str(temp_path) + ".webm")
                                        temp_file.write_bytes(b"fake audio content")

                                    mock_download.side_effect = mock_download_side_effect

                                    # Mock process_audio to create the final output file
                                    def mock_process_side_effect(
                                        input_path,
                                        output_path,
                                        start_time=60,
                                        duration=60,
                                        sample_rate=48000,
                                    ):
                                        # Create the final output file
                                        output_path.write_bytes(b"fake processed audio content")

                                    mock_process.side_effect = mock_process_side_effect

                                    # Test download (file will be created by the download function)
                                    result = download_and_process_ambient_sound(
                                        "https://youtube.com/watch?v=test",
                                        "test_sound",
                                        self.assets_dir,
                                    )

                                    # Verify configuration was used
                                    expected_path = (
                                        self.assets_dir / "test_sound" / "test_sound_1m.wav"
                                    )
                                    assert result == expected_path

                                    # Verify the download completed successfully
                                    assert result.exists()
                                    assert result.stat().st_size > 0

    def test_asset_health_monitoring(self):
        """Test asset health monitoring integration."""
        # Create managers
        config_manager = ConfigManager(self.config_dir)
        asset_manager = AssetManager(self.assets_dir)
        state_manager = StateManager(config_manager, asset_manager)

        # Create a test asset
        test_asset_dir = self.assets_dir / "test_asset"
        test_asset_dir.mkdir()
        test_wav = test_asset_dir / "test_asset_1m.wav"
        test_wav.write_bytes(b"fake wav content")

        # Create metadata
        metadata = AmbientSoundMetadata(
            name="test_asset",
            path=test_wav,
            duration_seconds=60,
            sample_rate=48000,
            channels=2,
            file_size_bytes=len(b"fake wav content"),
            created_date=datetime.now().isoformat(),
            source_url="https://youtube.com/watch?v=test",
            description="Test asset",
        )
        asset_manager.create_individual_metadata_file("test_asset", metadata)

        # Validate asset integrity
        is_valid, issues = state_manager.validate_asset_integrity("test_asset")

        # Should have issues due to fake WAV content
        assert is_valid is False
        assert len(issues) > 0

        # Check maintenance records
        records = state_manager.get_maintenance_records()
        assert len(records) == 1
        assert records[0].operation_type == "validation"
        assert records[0].asset_name == "test_asset"
        assert records[0].success is False

        # Get health summary
        health = state_manager.get_asset_health_summary()
        assert health["total_assets"] == 1
        assert health["invalid_assets"] == 1
        assert health["health_percentage"] == 0.0

    def test_maintenance_operations_tracking(self):
        """Test tracking of maintenance operations."""
        # Create managers
        config_manager = ConfigManager(self.config_dir)
        asset_manager = AssetManager(self.assets_dir)
        state_manager = StateManager(config_manager, asset_manager)

        # Add various maintenance records
        state_manager.add_maintenance_record("download", "asset1", True)
        state_manager.add_maintenance_record(
            "download", "asset2", False, error_message="Network error"
        )
        state_manager.add_maintenance_record("validation", "asset1", True)
        state_manager.add_maintenance_record("repair", "asset2", True)
        state_manager.add_maintenance_record("cleanup", None, True)

        # Get maintenance stats
        stats = state_manager.get_maintenance_stats()
        assert stats["total_operations"] == 5
        assert stats["successful_operations"] == 4
        assert stats["failed_operations"] == 1
        assert stats["success_rate"] == 0.8
        assert stats["operation_types"]["download"] == 2
        assert stats["operation_types"]["validation"] == 1
        assert stats["operation_types"]["repair"] == 1
        assert stats["operation_types"]["cleanup"] == 1

    def test_dependency_tracking(self):
        """Test asset dependency tracking."""
        # Create managers
        config_manager = ConfigManager(self.config_dir)
        asset_manager = AssetManager(self.assets_dir)
        state_manager = StateManager(config_manager, asset_manager)

        # Add dependencies
        state_manager.add_dependency("source1", "mixed1", "mix")
        state_manager.add_dependency("source2", "mixed1", "mix")
        state_manager.add_dependency("mixed1", "final1", "derived")

        # Check dependencies
        deps = state_manager.get_dependencies("mixed1")
        assert len(deps) == 2
        assert deps[0].source_asset == "source1"
        assert deps[1].source_asset == "source2"

        # Check dependents
        dependents = state_manager.get_dependents("mixed1")
        assert len(dependents) == 1
        assert dependents[0].dependent_asset == "final1"

        # Remove dependencies
        state_manager.remove_dependencies("mixed1")
        deps = state_manager.get_dependencies("mixed1")
        assert len(deps) == 0
        dependents = state_manager.get_dependents("mixed1")
        assert len(dependents) == 0

    def test_configuration_validation_integration(self):
        """Test configuration validation integration."""
        # Create manager
        manager = ConfigManager(self.config_dir)

        # Test valid configuration
        is_valid, issues = manager.validate_config()
        assert is_valid is True
        assert len(issues) == 0

        # Test invalid configuration
        manager._config.download.default_sample_rate = -1
        manager._config.download.volume_adjustment = 3.0
        manager._config.processing.channels = 3

        is_valid, issues = manager.validate_config()
        assert is_valid is False
        assert len(issues) == 3
        assert any("default_sample_rate" in issue for issue in issues)
        assert any("volume_adjustment" in issue for issue in issues)
        assert any("channels" in issue for issue in issues)

    def test_download_history_tracking(self):
        """Test download history tracking integration."""
        # Create manager
        manager = ConfigManager(self.config_dir)

        # Add download records
        manager.add_download_record(
            url="https://youtube.com/watch?v=test1",
            sound_name="sound1",
            success=True,
            metadata={"file_size": 1000000, "video_title": "Test Video 1"},
        )

        manager.add_download_record(
            url="https://youtube.com/watch?v=test2",
            sound_name="sound2",
            success=False,
            error_message="Download failed",
        )

        # Get history
        history = manager.get_download_history()
        assert len(history) == 2

        # Check first record
        assert history[0]["sound_name"] == "sound1"
        assert history[0]["success"] is True
        assert history[0]["metadata"]["file_size"] == 1000000

        # Check second record
        assert history[1]["sound_name"] == "sound2"
        assert history[1]["success"] is False
        assert history[1]["error_message"] == "Download failed"

    def test_cleanup_operations(self):
        """Test cleanup operations integration."""
        # Create managers
        config_manager = ConfigManager(self.config_dir)
        asset_manager = AssetManager(self.assets_dir)
        state_manager = StateManager(config_manager, asset_manager)

        # Add old maintenance records
        old_timestamp = (datetime.now() - timedelta(days=35)).isoformat()
        for i in range(5):
            record = MaintenanceRecord(
                operation_type="download",
                asset_name=f"asset_{i}",
                timestamp=old_timestamp,
                success=True,
                details={},
            )
            state_manager._maintenance_records.append(record)

        # Add recent maintenance records
        recent_timestamp = datetime.now().isoformat()
        for i in range(3):
            record = MaintenanceRecord(
                operation_type="download",
                asset_name=f"recent_asset_{i}",
                timestamp=recent_timestamp,
                success=True,
                details={},
            )
            state_manager._maintenance_records.append(record)

        # Cleanup old records
        removed = state_manager.cleanup_old_records(days=30)
        assert removed == 5

        # Verify only recent records remain
        records = state_manager.get_maintenance_records()
        assert len(records) == 3
        for record in records:
            assert "recent_asset" in record.asset_name

    def test_full_workflow_integration(self):
        """Test complete workflow integration."""
        # Create managers
        config_manager = ConfigManager(self.config_dir)
        asset_manager = AssetManager(self.assets_dir)
        state_manager = StateManager(config_manager, asset_manager)

        # Configure system
        config_manager.update_config(
            **{
                "download.default_sample_rate": 44100,
                "download.default_duration": 30,
                "preferences.auto_validate_downloads": True,
            }
        )

        # Simulate download workflow
        with patch("sleepstack.download_ambient.validate_prerequisites"):
            with patch("sleepstack.download_ambient.get_video_info") as mock_get_info:
                with patch("sleepstack.download_ambient.download_audio") as mock_download:
                    with patch("sleepstack.download_ambient.process_audio") as mock_process:
                        with patch(
                            "sleepstack.download_ambient.get_asset_manager",
                            return_value=asset_manager,
                        ):
                            with patch(
                                "sleepstack.download_ambient.get_config_manager",
                                return_value=config_manager,
                            ):
                                with patch(
                                    "sleepstack.download_ambient.get_state_manager",
                                    return_value=state_manager,
                                ):
                                    # Mock video info
                                    mock_get_info.return_value = {
                                        "title": "Test Video",
                                        "duration": 120,
                                        "uploader": "Test User",
                                        "description": "Test description",
                                    }

                                    # Mock download_audio to create a temporary file
                                    def mock_download_side_effect(url, temp_path):
                                        # Create a temporary file that the download function can find
                                        temp_file = Path(str(temp_path) + ".webm")
                                        temp_file.write_bytes(b"fake audio content")

                                    mock_download.side_effect = mock_download_side_effect

                                    # Mock process_audio to create the final output file
                                    def mock_process_side_effect(
                                        input_path,
                                        output_path,
                                        start_time=60,
                                        duration=60,
                                        sample_rate=48000,
                                    ):
                                        # Create the final output file
                                        output_path.write_bytes(b"fake processed audio content")

                                    mock_process.side_effect = mock_process_side_effect

                                    # Test download (file will be created by the download function)
                                    result = download_and_process_ambient_sound(
                                        "https://youtube.com/watch?v=workflow_test",
                                        "workflow_test",
                                        self.assets_dir,
                                    )

                                    # Verify download completed
                                    expected_path = (
                                        self.assets_dir / "workflow_test" / "workflow_test_1m.wav"
                                    )
                                    assert result == expected_path

                                    # Verify configuration was used
                                    config = config_manager.get_config()
                                    assert config.download.default_sample_rate == 44100

                                    # Verify download history
                                    history = config_manager.get_download_history()
                                    assert len(history) == 1
                                    assert history[0]["sound_name"] == "workflow_test"

                                    # Verify state tracking
                                    refs = state_manager.get_asset_references("workflow_test")
                                    assert len(refs) == 1

                                    # Verify maintenance records
                                    records = state_manager.get_maintenance_records()
                                    assert len(records) == 1
                                    assert records[0].operation_type == "download"

                                    # Verify asset health
                                    health = state_manager.get_asset_health_summary()
                                    assert health["total_assets"] == 1
