"""
Configuration management system for sleepstack.

This module provides configuration file management, user preferences,
and default settings for the ambient sound download and processing system.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DownloadConfig:
    """Configuration for ambient sound downloads."""

    default_sample_rate: int = 48000
    default_duration: int = 60
    default_start_time: int = 60
    max_download_duration: int = 300
    download_quality: str = "bestaudio"
    volume_adjustment: float = 0.8
    auto_cleanup_temp_files: bool = True
    max_file_size_mb: int = 600  # Maximum file size in MB
    enable_caching: bool = True  # Enable download caching
    cache_ttl_hours: int = 24  # Cache time-to-live in hours


@dataclass
class ProcessingConfig:
    """Configuration for audio processing."""

    output_format: str = "wav"
    output_codec: str = "pcm_s16le"
    channels: int = 2
    fade_in_duration: float = 2.0
    fade_out_duration: float = 2.0
    normalize_audio: bool = True


@dataclass
class UserPreferences:
    """User preferences and settings."""

    default_assets_dir: Optional[str] = None
    auto_validate_downloads: bool = True
    show_download_progress: bool = True
    backup_original_files: bool = False
    preferred_audio_quality: str = "high"
    download_timeout: int = 300


@dataclass
class AppConfig:
    """Main application configuration."""

    download: DownloadConfig
    processing: ProcessingConfig
    preferences: UserPreferences
    version: str = "0.1.0"
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()


class ConfigManager:
    """Manages application configuration and user preferences."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory to store configuration files (defaults to user config)
        """
        if config_dir is None:
            # Use standard user config directory
            if os.name == "nt":  # Windows
                base_dir = Path(os.environ.get("APPDATA", ""))
            else:  # Unix-like systems
                base_dir = Path.home() / ".config"

            config_dir = base_dir / "sleepstack"

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self.download_history_file = self.config_dir / "download_history.json"
        self.state_file = self.config_dir / "state.json"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load or create default configuration
        self._config = self._load_or_create_config()

    def _load_or_create_config(self) -> AppConfig:
        """Load existing configuration or create default configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                return self._dict_to_config(data)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Warning: Invalid configuration file, creating default: {e}")

        # Create default configuration
        default_config = AppConfig(
            download=DownloadConfig(), processing=ProcessingConfig(), preferences=UserPreferences()
        )
        self.save_config(default_config)
        return default_config

    def _dict_to_config(self, data: Dict[str, Any]) -> AppConfig:
        """Convert dictionary to AppConfig object."""
        return AppConfig(
            download=DownloadConfig(**data.get("download", {})),
            processing=ProcessingConfig(**data.get("processing", {})),
            preferences=UserPreferences(**data.get("preferences", {})),
            version=data.get("version", "0.1.0"),
            last_updated=data.get("last_updated", ""),
        )

    def _config_to_dict(self, config: AppConfig) -> Dict[str, Any]:
        """Convert AppConfig object to dictionary."""
        return {
            "download": asdict(config.download),
            "processing": asdict(config.processing),
            "preferences": asdict(config.preferences),
            "version": config.version,
            "last_updated": config.last_updated,
        }

    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config

    def save_config(self, config: Optional[AppConfig] = None) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save (uses current config if None)
        """
        if config is None:
            config = self._config

        config.last_updated = datetime.now().isoformat()

        with open(self.config_file, "w") as f:
            json.dump(self._config_to_dict(config), f, indent=2)

        self._config = config

    def update_config(self, **kwargs: Any) -> None:
        """
        Update configuration with new values.

        Args:
            **kwargs: Configuration updates
        """
        config_dict = self._config_to_dict(self._config)

        for key, value in kwargs.items():
            if "." in key:
                # Handle nested updates like 'download.default_sample_rate'
                parts = key.split(".")
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                config_dict[key] = value

        self._config = self._dict_to_config(config_dict)
        self.save_config()

    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        default_config = AppConfig(
            download=DownloadConfig(), processing=ProcessingConfig(), preferences=UserPreferences()
        )
        self.save_config(default_config)

    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate the current configuration.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Validate download config
        if self._config.download.default_sample_rate <= 0:
            issues.append("Invalid default_sample_rate: must be positive")

        if self._config.download.default_duration <= 0:
            issues.append("Invalid default_duration: must be positive")

        if self._config.download.max_download_duration <= 0:
            issues.append("Invalid max_download_duration: must be positive")

        if not 0.0 <= self._config.download.volume_adjustment <= 2.0:
            issues.append("Invalid volume_adjustment: must be between 0.0 and 2.0")

        # Validate processing config
        if self._config.processing.channels not in [1, 2]:
            issues.append("Invalid channels: must be 1 (mono) or 2 (stereo)")

        if self._config.processing.fade_in_duration < 0:
            issues.append("Invalid fade_in_duration: must be non-negative")

        if self._config.processing.fade_out_duration < 0:
            issues.append("Invalid fade_out_duration: must be non-negative")

        # Validate preferences
        if self._config.preferences.download_timeout <= 0:
            issues.append("Invalid download_timeout: must be positive")

        return len(issues) == 0, issues

    def get_download_history(self) -> list[dict[str, Any]]:
        """Get download history."""
        if not self.download_history_file.exists():
            return []

        try:
            with open(self.download_history_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def add_download_record(
        self,
        url: str,
        sound_name: str,
        success: bool,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Add a record to download history.

        Args:
            url: YouTube URL that was downloaded
            sound_name: Name of the ambient sound
            success: Whether download was successful
            error_message: Error message if download failed
            metadata: Additional metadata about the download
        """
        history = self.get_download_history()

        record = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "sound_name": sound_name,
            "success": success,
            "error_message": error_message,
            "metadata": metadata or {},
        }

        history.append(record)

        # Keep only last 100 records
        if len(history) > 100:
            history = history[-100:]

        with open(self.download_history_file, "w") as f:
            json.dump(history, f, indent=2)

    def get_state(self) -> dict[str, Any]:
        """Get application state."""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}

    def update_state(self, **kwargs: Any) -> None:
        """
        Update application state.

        Args:
            **kwargs: State updates
        """
        state = self.get_state()
        state.update(kwargs)
        state["last_updated"] = datetime.now().isoformat()

        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def clear_state(self) -> None:
        """Clear application state."""
        if self.state_file.exists():
            self.state_file.unlink()

    def get_config_path(self) -> Path:
        """Get the path to the configuration file."""
        return self.config_file

    def get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self.config_dir


def get_config_manager() -> ConfigManager:
    """Get a global configuration manager instance."""
    return ConfigManager()


def main() -> None:
    """CLI entry point for testing the configuration manager."""
    import sys

    manager = get_config_manager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "show":
            config = manager.get_config()
            print("Current Configuration:")
            print(f"  Sample Rate: {config.download.default_sample_rate}")
            print(f"  Duration: {config.download.default_duration}")
            print(f"  Max Download Duration: {config.download.max_download_duration}")
            print(f"  Volume Adjustment: {config.download.volume_adjustment}")
            print(f"  Auto Validate: {config.preferences.auto_validate_downloads}")
            print(f"  Show Progress: {config.preferences.show_download_progress}")

        elif command == "validate":
            is_valid, issues = manager.validate_config()
            if is_valid:
                print("Configuration is valid")
            else:
                print("Configuration has issues:")
                for issue in issues:
                    print(f"  - {issue}")

        elif command == "reset":
            manager.reset_config()
            print("Configuration reset to defaults")

        elif command == "history":
            history = manager.get_download_history()
            if not history:
                print("No download history")
            else:
                print("Download History:")
                for record in history[-10:]:  # Show last 10
                    status = "✓" if record["success"] else "✗"
                    print(f"  {status} {record['sound_name']} ({record['timestamp']})")
                    if not record["success"] and record["error_message"]:
                        print(f"    Error: {record['error_message']}")

        elif command == "state":
            state = manager.get_state()
            if not state:
                print("No application state")
            else:
                print("Application State:")
                for key, value in state.items():
                    print(f"  {key}: {value}")

        else:
            print("Unknown command. Available: show, validate, reset, history, state")
    else:
        print("Usage: python config.py <command>")
        print("Commands: show, validate, reset, history, state")


if __name__ == "__main__":
    main()
