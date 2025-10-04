"""Tests for vibe_binaural.py"""

import pytest
import tempfile
import os
import sys
import argparse
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

from sleepstack.vibe_binaural import (
    Preset,
    PRESETS,
    ALIASES,
    _script_dir,
    _module_from_path,
    _import_make_binaural,
    _call_make_binaural_subprocess,
    resolve_vibe,
    list_vibes,
    positive_float_minutes,
    positive_float_seconds,
    nonneg_float,
    main,
)


class TestPreset:
    """Test Preset dataclass."""

    def test_preset_creation(self):
        """Test creating a Preset."""
        preset = Preset(
            beat=6.0,
            carrier=200,
            samplerate=48000,
            volume=0.28,
            fade=2.0,
            description="Test preset",
        )

        assert preset.beat == 6.0
        assert preset.carrier == 200
        assert preset.samplerate == 48000
        assert preset.volume == 0.28
        assert preset.fade == 2.0
        assert preset.description == "Test preset"

    def test_preset_defaults(self):
        """Test Preset with default values."""
        preset = Preset(beat=6.0, carrier=200)

        assert preset.beat == 6.0
        assert preset.carrier == 200
        assert preset.samplerate == 48000
        assert preset.volume == 0.28
        assert preset.fade == 2.0
        assert preset.description == ""


class TestPresets:
    """Test PRESETS dictionary."""

    def test_presets_contain_expected_keys(self):
        """Test that PRESETS contains expected vibe keys."""
        expected_keys = {
            "deep",
            "calm",
            "soothe",
            "dream",
            "focus",
            "flow",
            "alert",
            "meditate",
            "warm",
            "airy",
        }
        assert set(PRESETS.keys()) == expected_keys

    def test_presets_have_valid_values(self):
        """Test that all presets have valid values."""
        for name, preset in PRESETS.items():
            assert isinstance(preset, Preset)
            assert preset.beat > 0
            assert preset.carrier > 0
            assert preset.samplerate > 0
            assert 0 < preset.volume <= 1
            assert preset.fade >= 0
            assert isinstance(preset.description, str)

    def test_specific_presets(self):
        """Test specific preset values."""
        # Test deep preset
        deep = PRESETS["deep"]
        assert deep.beat == 4.5
        assert deep.carrier == 180
        assert deep.volume == 0.25
        assert deep.fade == 2
        assert "theta" in deep.description.lower()

        # Test calm preset
        calm = PRESETS["calm"]
        assert calm.beat == 6.0
        assert calm.carrier == 200
        assert calm.volume == 0.28
        assert calm.fade == 2
        assert "theta" in calm.description.lower()

        # Test alert preset
        alert = PRESETS["alert"]
        assert alert.beat == 8.0
        assert alert.carrier == 240
        assert alert.volume == 0.26
        assert alert.fade == 2
        assert "alpha" in alert.description.lower()


class TestAliases:
    """Test ALIASES dictionary."""

    def test_aliases_contain_expected_keys(self):
        """Test that ALIASES contains expected alias keys."""
        expected_aliases = {
            "sleep",
            "deeper",
            "settle",
            "night",
            "study",
            "work",
            "creative",
            "energize",
            "presence",
            "soft",
            "rain",
            "fire",
            "bright",
        }
        assert set(ALIASES.keys()) == expected_aliases

    def test_aliases_map_to_valid_presets(self):
        """Test that all aliases map to valid preset keys."""
        for alias, preset_key in ALIASES.items():
            assert preset_key in PRESETS, f"Alias '{alias}' maps to invalid preset '{preset_key}'"

    def test_specific_aliases(self):
        """Test specific alias mappings."""
        assert ALIASES["sleep"] == "deep"
        assert ALIASES["night"] == "calm"
        assert ALIASES["study"] == "focus"
        assert ALIASES["creative"] == "flow"
        assert ALIASES["energize"] == "alert"
        assert ALIASES["presence"] == "meditate"
        assert ALIASES["soft"] == "soothe"
        assert ALIASES["rain"] == "warm"
        assert ALIASES["fire"] == "warm"
        assert ALIASES["bright"] == "airy"


class TestScriptDir:
    """Test _script_dir function."""

    def test_script_dir_returns_string(self):
        """Test that _script_dir returns a string."""
        result = _script_dir()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_script_dir_is_absolute_path(self):
        """Test that _script_dir returns an absolute path."""
        result = _script_dir()
        assert os.path.isabs(result)


class TestModuleFromPath:
    """Test _module_from_path function."""

    def test_module_from_path_nonexistent_file(self):
        """Test _module_from_path with nonexistent file."""
        # The function will try to load the file and fail with an exception
        with pytest.raises(FileNotFoundError):
            _module_from_path("test_module", "/nonexistent/path.py")

    def test_module_from_path_invalid_file(self):
        """Test _module_from_path with invalid Python file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("invalid python syntax {")
            temp_path = f.name

        try:
            # The function will try to load the file and fail with a syntax error
            with pytest.raises(SyntaxError):
                _module_from_path("test_module", temp_path)
        finally:
            os.unlink(temp_path)


class TestImportMakeBinaural:
    """Test _import_make_binaural function."""

    @patch("sleepstack.vibe_binaural._script_dir")
    @patch("sleepstack.vibe_binaural._module_from_path")
    @patch("os.path.exists")
    def test_import_make_binaural_local_file_exists(
        self, mock_exists, mock_module_from_path, mock_script_dir
    ):
        """Test _import_make_binaural when local file exists."""
        mock_script_dir.return_value = "/test/script/dir"
        mock_exists.return_value = True
        mock_module = Mock()
        mock_module_from_path.return_value = mock_module

        result = _import_make_binaural()

        assert result == mock_module
        mock_exists.assert_called_once_with("/test/script/dir/make_binaural.py")
        mock_module_from_path.assert_called_once_with(
            "make_binaural", "/test/script/dir/make_binaural.py"
        )

    @patch("sleepstack.vibe_binaural._script_dir")
    @patch("sleepstack.vibe_binaural._module_from_path")
    @patch("os.path.exists")
    def test_import_make_binaural_fallback_import(
        self, mock_exists, mock_module_from_path, mock_script_dir
    ):
        """Test _import_make_binaural fallback to regular import."""
        mock_script_dir.return_value = "/test/script/dir"
        mock_exists.return_value = False
        mock_module_from_path.return_value = None

        # Since make_binaural.py actually exists in the project, we need to patch the import
        with patch("importlib.import_module") as mock_import_module:
            mock_module = Mock()
            mock_import_module.return_value = mock_module

            result = _import_make_binaural()

            assert result == mock_module
            mock_exists.assert_called_once_with("/test/script/dir/make_binaural.py")
            mock_import_module.assert_called_once_with("make_binaural")

    @patch("sleepstack.vibe_binaural._script_dir")
    @patch("sleepstack.vibe_binaural._module_from_path")
    @patch("os.path.exists")
    def test_import_make_binaural_all_fail(
        self, mock_exists, mock_module_from_path, mock_script_dir
    ):
        """Test _import_make_binaural when all methods fail."""
        mock_script_dir.return_value = "/test/script/dir"
        mock_exists.return_value = False
        mock_module_from_path.return_value = None

        # Since make_binaural.py actually exists in the project, we need to patch the import
        with patch("importlib.import_module") as mock_import_module:
            mock_import_module.side_effect = ImportError("Module not found")

            result = _import_make_binaural()

            assert result is None
            mock_exists.assert_called_once_with("/test/script/dir/make_binaural.py")
            mock_import_module.assert_called_once_with("make_binaural")


class TestCallMakeBinauralSubprocess:
    """Test _call_make_binaural_subprocess function."""

    @patch("sleepstack.vibe_binaural._script_dir")
    @patch("os.path.exists")
    @patch("subprocess.call")
    def test_call_make_binaural_subprocess_with_minutes(
        self, mock_subprocess_call, mock_exists, mock_script_dir
    ):
        """Test _call_make_binaural_subprocess with minutes."""
        mock_script_dir.return_value = "/test/script/dir"
        mock_exists.return_value = True
        mock_subprocess_call.return_value = 0

        result = _call_make_binaural_subprocess(
            minutes=5.0,
            seconds=None,
            beat=6.0,
            carrier=200,
            samplerate=48000,
            volume=0.28,
            fade=2.0,
            out="test.wav",
        )

        assert result == 0
        mock_subprocess_call.assert_called_once()
        call_args = mock_subprocess_call.call_args[0][0]
        assert "--minutes" in call_args
        assert "5.0" in call_args
        assert "--beat" in call_args
        assert "6.0" in call_args
        assert "--carrier" in call_args
        assert "200" in call_args
        assert "--out" in call_args
        assert "test.wav" in call_args

    @patch("sleepstack.vibe_binaural._script_dir")
    @patch("os.path.exists")
    @patch("subprocess.call")
    def test_call_make_binaural_subprocess_with_seconds(
        self, mock_subprocess_call, mock_exists, mock_script_dir
    ):
        """Test _call_make_binaural_subprocess with seconds."""
        mock_script_dir.return_value = "/test/script/dir"
        mock_exists.return_value = True
        mock_subprocess_call.return_value = 0

        result = _call_make_binaural_subprocess(
            minutes=None,
            seconds=300.0,
            beat=6.0,
            carrier=200,
            samplerate=48000,
            volume=0.28,
            fade=2.0,
            out="test.wav",
        )

        assert result == 0
        mock_subprocess_call.assert_called_once()
        call_args = mock_subprocess_call.call_args[0][0]
        assert "--seconds" in call_args
        assert "300.0" in call_args
        assert "--minutes" not in call_args

    @patch("sleepstack.vibe_binaural._script_dir")
    @patch("os.path.exists")
    @patch("subprocess.call")
    def test_call_make_binaural_subprocess_file_not_exists(
        self, mock_subprocess_call, mock_exists, mock_script_dir
    ):
        """Test _call_make_binaural_subprocess when make_binaural.py doesn't exist locally."""
        mock_script_dir.return_value = "/test/script/dir"
        mock_exists.return_value = False
        mock_subprocess_call.return_value = 0

        result = _call_make_binaural_subprocess(
            minutes=5.0,
            seconds=None,
            beat=6.0,
            carrier=200,
            samplerate=48000,
            volume=0.28,
            fade=2.0,
            out="test.wav",
        )

        assert result == 0
        mock_subprocess_call.assert_called_once()
        call_args = mock_subprocess_call.call_args[0][0]
        assert call_args[1] == "make_binaural.py"  # Should use module name instead of path


class TestResolveVibe:
    """Test resolve_vibe function."""

    def test_resolve_vibe_none(self):
        """Test resolve_vibe with None input."""
        result = resolve_vibe(None)
        assert result == "calm"

    def test_resolve_vibe_direct_preset(self):
        """Test resolve_vibe with direct preset name."""
        result = resolve_vibe("deep")
        assert result == "deep"

        result = resolve_vibe("calm")
        assert result == "calm"

    def test_resolve_vibe_alias(self):
        """Test resolve_vibe with alias."""
        result = resolve_vibe("sleep")
        assert result == "deep"

        result = resolve_vibe("night")
        assert result == "calm"

        result = resolve_vibe("study")
        assert result == "focus"

    def test_resolve_vibe_case_insensitive(self):
        """Test resolve_vibe with different cases."""
        result = resolve_vibe("DEEP")
        assert result == "deep"

        result = resolve_vibe("Sleep")
        assert result == "deep"

    def test_resolve_vibe_whitespace(self):
        """Test resolve_vibe with whitespace."""
        result = resolve_vibe("  deep  ")
        assert result == "deep"

    def test_resolve_vibe_fuzzy_match(self):
        """Test resolve_vibe with fuzzy matching."""
        result = resolve_vibe("de")
        assert result == "deep"

        result = resolve_vibe("cal")
        assert result == "calm"

    def test_resolve_vibe_unknown(self):
        """Test resolve_vibe with unknown vibe."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_vibe("unknown")
        assert "Unknown vibe 'unknown'" in str(exc_info.value)


class TestListVibes:
    """Test list_vibes function."""

    @patch("builtins.print")
    def test_list_vibes(self, mock_print):
        """Test list_vibes function."""
        list_vibes()

        # Should print available vibes
        assert mock_print.call_count > 0

        # Check that all presets are listed
        printed_text = " ".join(str(call) for call in mock_print.call_args_list)
        for preset_name in PRESETS.keys():
            assert preset_name in printed_text

        # Check that aliases are listed
        for alias in ALIASES.keys():
            assert alias in printed_text


class TestValidationFunctions:
    """Test validation functions."""

    def test_positive_float_minutes_valid(self):
        """Test positive_float_minutes with valid values."""
        assert positive_float_minutes("1.0") == 1.0
        assert positive_float_minutes("5.5") == 5.5
        assert positive_float_minutes("10.0") == 10.0

    def test_positive_float_minutes_invalid(self):
        """Test positive_float_minutes with invalid values."""
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("0")

        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("-1")

        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("11")

    def test_positive_float_seconds_valid(self):
        """Test positive_float_seconds with valid values."""
        assert positive_float_seconds("60.0") == 60.0
        assert positive_float_seconds("300.0") == 300.0
        assert positive_float_seconds("600.0") == 600.0

    def test_positive_float_seconds_invalid(self):
        """Test positive_float_seconds with invalid values."""
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_seconds("0")

        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_seconds("-1")

        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 600 seconds"):
            positive_float_seconds("601")

    def test_nonneg_float_valid(self):
        """Test nonneg_float with valid values."""
        assert nonneg_float("0.0") == 0.0
        assert nonneg_float("1.0") == 1.0
        assert nonneg_float("2.5") == 2.5

    def test_nonneg_float_invalid(self):
        """Test nonneg_float with invalid values."""
        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 0"):
            nonneg_float("-1")


class TestMain:
    """Test main function."""

    def test_main_list_flag(self):
        """Test main with --list flag."""
        with patch("sleepstack.vibe_binaural.list_vibes") as mock_list_vibes:
            result = main(["--list"])
            assert result == 0
            mock_list_vibes.assert_called_once()

    def test_main_default_vibe(self):
        """Test main with default vibe."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--dry-run"])
            assert result == 0

            # Should use calm as default
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "calm" in printed_text

    def test_main_with_vibe(self):
        """Test main with specific vibe."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--vibe", "deep", "--dry-run"])
            assert result == 0

            # Should use deep vibe
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "deep" in printed_text

    def test_main_with_alias(self):
        """Test main with alias."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--vibe", "sleep", "--dry-run"])
            assert result == 0

            # Should resolve to deep
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "deep" in printed_text

    def test_main_with_minutes(self):
        """Test main with --minutes."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--minutes", "3", "--dry-run"])
            assert result == 0

            # Should show 3 minutes duration
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "180.0 s" in printed_text

    def test_main_with_seconds(self):
        """Test main with --seconds."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--seconds", "120", "--dry-run"])
            assert result == 0

            # Should show 120 seconds duration
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "120.0 s" in printed_text

    def test_main_with_overrides(self):
        """Test main with parameter overrides."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(
                [
                    "--vibe",
                    "calm",
                    "--beat",
                    "7.0",
                    "--carrier",
                    "220",
                    "--volume",
                    "0.3",
                    "--fade",
                    "1.0",
                    "--dry-run",
                ]
            )
            assert result == 0

            # Should show overridden values
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "7.0 Hz" in printed_text
            assert "220.0 Hz" in printed_text
            assert "0.3" in printed_text
            assert "1.0 s" in printed_text

    def test_main_with_loop(self):
        """Test main with --loop flag."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--loop", "--dry-run"])
            assert result == 0

            # Should show fade=0
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "0.0 s" in printed_text

    def test_main_with_output_filename(self):
        """Test main with --out."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_module.generate_binaural.return_value = Mock()
            mock_import.return_value = mock_module

            result = main(["--out", "custom.wav", "--dry-run"])
            assert result == 0

            # Should show custom filename
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "custom.wav" in printed_text

    def test_main_generate_binaural_success(self):
        """Test main with successful binaural generation."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("builtins.print") as mock_print,
        ):

            # Mock the module
            mock_module = Mock()
            mock_data = Mock()
            mock_module.generate_binaural.return_value = mock_data
            mock_import.return_value = mock_module

            result = main(["--minutes", "1"])
            assert result == 0

            # Should call generate_binaural and save_wav
            mock_module.generate_binaural.assert_called_once()
            mock_module.save_wav.assert_called_once()

    def test_main_fallback_to_subprocess(self):
        """Test main fallback to subprocess when import fails."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("sleepstack.vibe_binaural._call_make_binaural_subprocess") as mock_subprocess,
            patch("builtins.print") as mock_print,
        ):

            # Mock import failure
            mock_import.return_value = None
            mock_subprocess.return_value = 0

            result = main(["--minutes", "1"])
            assert result == 0

            # Should call subprocess
            mock_subprocess.assert_called_once()

    def test_main_subprocess_failure(self):
        """Test main when subprocess fails."""
        with (
            patch("sleepstack.vibe_binaural._import_make_binaural") as mock_import,
            patch("sleepstack.vibe_binaural._call_make_binaural_subprocess") as mock_subprocess,
            patch("builtins.print") as mock_print,
        ):

            # Mock import failure
            mock_import.return_value = None
            mock_subprocess.return_value = 1

            result = main(["--minutes", "1"])
            assert result == 1

            # Should call subprocess
            mock_subprocess.assert_called_once()

    def test_main_invalid_vibe(self):
        """Test main with invalid vibe."""
        with pytest.raises(SystemExit):
            main(["--vibe", "invalid"])

    def test_main_invalid_minutes(self):
        """Test main with invalid minutes."""
        with pytest.raises(SystemExit):
            main(["--minutes", "0"])

    def test_main_invalid_seconds(self):
        """Test main with invalid seconds."""
        with pytest.raises(SystemExit):
            main(["--seconds", "-1"])

    def test_main_invalid_fade(self):
        """Test main with invalid fade."""
        with pytest.raises(SystemExit):
            main(["--fade", "-1"])


class TestIntegration:
    """Integration tests for vibe_binaural."""

    def test_preset_consistency(self):
        """Test that all presets have consistent properties."""
        for name, preset in PRESETS.items():
            # Beat should be in reasonable range for binaural beats
            assert 1.0 <= preset.beat <= 20.0, f"Preset {name} has unreasonable beat frequency"

            # Carrier should be in reasonable range
            assert (
                50.0 <= preset.carrier <= 500.0
            ), f"Preset {name} has unreasonable carrier frequency"

            # Volume should be reasonable
            assert 0.0 < preset.volume <= 1.0, f"Preset {name} has unreasonable volume"

            # Fade should be non-negative
            assert preset.fade >= 0.0, f"Preset {name} has negative fade"

    def test_alias_consistency(self):
        """Test that all aliases map to existing presets."""
        for alias, preset_key in ALIASES.items():
            assert (
                preset_key in PRESETS
            ), f"Alias '{alias}' maps to non-existent preset '{preset_key}'"

    def test_vibe_resolution_consistency(self):
        """Test that vibe resolution is consistent."""
        # Test all direct presets
        for preset_name in PRESETS.keys():
            assert resolve_vibe(preset_name) == preset_name

        # Test all aliases
        for alias, expected_preset in ALIASES.items():
            assert resolve_vibe(alias) == expected_preset
