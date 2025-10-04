#!/usr/bin/env python3
"""
Tests for src/sleepstack/main.py
"""

import argparse
import logging
import os
import sys
import tempfile
import wave
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, ANY
import pytest
import numpy as np

from sleepstack.main import (
    _module_from_path,
    project_root,
    find_assets_dir,
    _repo_root,
    _assets_dir,
    _build_dir,
    Preset,
    PRESETS,
    ALIASES,
    resolve_vibe,
    read_wav,
    write_wav,
    ensure_stereo,
    db_to_gain,
    apply_fade,
    generate_binaural_wav,
    choose_campfire_clip,
    mix_multiple_ambient_sounds,
    mix_binaural_and_multiple_ambience,
    mix_binaural_and_ambience,
    positive_float_minutes,
    positive_float_seconds,
    nonneg_float,
    main,
    run,
)


class TestModuleFromPath:
    """Test _module_from_path function."""

    def test_module_from_path_success(self):
        """Test successful module loading from path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("test_var = 42\n")
            temp_path = f.name
        
        try:
            result = _module_from_path("test_module", temp_path)
            assert result is not None
            assert hasattr(result, 'test_var')
            assert result.test_var == 42
        finally:
            os.unlink(temp_path)

    def test_module_from_path_nonexistent_file(self):
        """Test module loading from nonexistent file."""
        with pytest.raises(FileNotFoundError):
            _module_from_path("test_module", "/nonexistent/path.py")

    def test_module_from_path_invalid_file(self):
        """Test module loading from invalid Python file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("invalid syntax {")
            temp_path = f.name
        
        try:
            with pytest.raises(SyntaxError):
                _module_from_path("test_module", temp_path)
        finally:
            os.unlink(temp_path)


class TestProjectRoot:
    """Test project_root function."""

    def test_project_root(self):
        """Test project root calculation."""
        root = project_root()
        assert isinstance(root, Path)
        assert root.exists()
        # Should be the parent of src/
        assert (root / "src").exists()


class TestFindAssetsDir:
    """Test find_assets_dir function."""

    def test_find_assets_dir_returns_path(self):
        """Test that find_assets_dir returns a Path object."""
        result = find_assets_dir()
        assert isinstance(result, Path)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_repo_root(self):
        """Test _repo_root function."""
        result = _repo_root()
        assert isinstance(result, str)
        assert result == str(project_root())

    def test_assets_dir(self):
        """Test _assets_dir function."""
        result = _assets_dir("ambience", "campfire")
        assert isinstance(result, str)
        assert "ambience" in result
        assert "campfire" in result

    def test_build_dir(self):
        """Test _build_dir function."""
        result = _build_dir("binaural", "test.wav")
        assert isinstance(result, str)
        assert "build" in result
        assert "binaural" in result
        assert "test.wav" in result


class TestPreset:
    """Test Preset dataclass."""

    def test_preset_creation(self):
        """Test Preset creation with default values."""
        preset = Preset(beat=6.0, carrier=200.0)
        assert preset.beat == 6.0
        assert preset.carrier == 200.0
        assert preset.samplerate == 48000
        assert preset.volume == 0.28
        assert preset.fade == 2.0
        assert preset.desc == ""

    def test_preset_creation_with_all_values(self):
        """Test Preset creation with all values specified."""
        preset = Preset(
            beat=5.0,
            carrier=180.0,
            samplerate=44100,
            volume=0.3,
            fade=1.5,
            desc="Test preset"
        )
        assert preset.beat == 5.0
        assert preset.carrier == 180.0
        assert preset.samplerate == 44100
        assert preset.volume == 0.3
        assert preset.fade == 1.5
        assert preset.desc == "Test preset"


class TestPresets:
    """Test PRESETS dictionary."""

    def test_presets_contains_expected_keys(self):
        """Test that PRESETS contains expected vibe keys."""
        expected_keys = {"deep", "calm", "soothe", "dream", "focus", "flow", "alert", "meditate", "warm", "airy"}
        assert set(PRESETS.keys()) == expected_keys

    def test_presets_values_are_presets(self):
        """Test that all PRESETS values are Preset instances."""
        for key, preset in PRESETS.items():
            assert isinstance(preset, Preset)
            assert preset.beat > 0
            assert preset.carrier > 0
            assert preset.samplerate > 0
            assert 0 < preset.volume <= 1
            assert preset.fade >= 0


class TestAliases:
    """Test ALIASES dictionary."""

    def test_aliases_contains_expected_mappings(self):
        """Test that ALIASES contains expected mappings."""
        expected_mappings = {
            "sleep": "deep",
            "settle": "deep",
            "night": "calm",
            "study": "focus",
            "work": "focus",
            "creative": "flow",
            "energize": "alert",
            "presence": "meditate",
            "soft": "soothe",
            "rain": "warm",
            "fire": "warm",
            "bright": "airy",
        }
        assert ALIASES == expected_mappings

    def test_aliases_reference_valid_presets(self):
        """Test that all ALIASES values reference valid PRESETS keys."""
        for alias, preset_key in ALIASES.items():
            assert preset_key in PRESETS


class TestResolveVibe:
    """Test resolve_vibe function."""

    def test_resolve_vibe_direct_match(self):
        """Test resolving vibe with direct match."""
        assert resolve_vibe("calm") == "calm"
        assert resolve_vibe("deep") == "deep"
        assert resolve_vibe("focus") == "focus"

    def test_resolve_vibe_alias(self):
        """Test resolving vibe with alias."""
        assert resolve_vibe("sleep") == "deep"
        assert resolve_vibe("night") == "calm"
        assert resolve_vibe("study") == "focus"
        assert resolve_vibe("work") == "focus"

    def test_resolve_vibe_case_insensitive(self):
        """Test resolving vibe with different case."""
        assert resolve_vibe("CALM") == "calm"
        assert resolve_vibe("Deep") == "deep"
        assert resolve_vibe("FOCUS") == "focus"

    def test_resolve_vibe_whitespace(self):
        """Test resolving vibe with whitespace."""
        assert resolve_vibe(" calm ") == "calm"
        assert resolve_vibe("\tdeep\n") == "deep"

    def test_resolve_vibe_fuzzy_match(self):
        """Test resolving vibe with fuzzy match."""
        assert resolve_vibe("cal") == "calm"
        assert resolve_vibe("dee") == "deep"
        assert resolve_vibe("foc") == "focus"

    def test_resolve_vibe_unknown(self):
        """Test resolving unknown vibe raises SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_vibe("unknown")
        assert "Unknown vibe 'unknown'" in str(exc_info.value)

    def test_resolve_vibe_empty(self):
        """Test resolving empty vibe returns first preset."""
        result = resolve_vibe("")
        assert result == "deep"  # First preset alphabetically

    def test_resolve_vibe_none(self):
        """Test resolving None vibe returns first preset."""
        result = resolve_vibe(None)
        assert result == "deep"  # First preset alphabetically


class TestAudioIO:
    """Test audio I/O functions."""

    def test_read_wav_success(self):
        """Test successful WAV file reading."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create a simple WAV file
            with wave.open(f.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                # Write 1 second of silence
                silence = b'\x00\x00' * 2 * 48000  # 2 channels, 16-bit samples
                wf.writeframes(silence)
            
            try:
                data, sr, ch = read_wav(f.name)
                assert sr == 48000
                assert ch == 2
                assert data.shape == (48000, 2)
                assert np.all(data == 0.0)
            finally:
                os.unlink(f.name)

    def test_read_wav_nonexistent_file(self):
        """Test reading nonexistent WAV file."""
        with pytest.raises(FileNotFoundError):
            read_wav("/nonexistent/file.wav")

    def test_read_wav_empty_file(self):
        """Test reading empty WAV file."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create empty file
            pass
        
        try:
            with pytest.raises(ValueError) as exc_info:
                read_wav(f.name)
            assert "File is empty" in str(exc_info.value)
        finally:
            os.unlink(f.name)

    def test_read_wav_invalid_bit_depth(self):
        """Test reading WAV file with invalid bit depth."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create WAV file with 8-bit samples (invalid)
            with wave.open(f.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(48000)
                silence = b'\x00' * 2 * 48000
                wf.writeframes(silence)
            
            try:
                with pytest.raises(SystemExit) as exc_info:
                    read_wav(f.name)
                assert "only 16-bit PCM supported" in str(exc_info.value)
            finally:
                os.unlink(f.name)

    def test_write_wav_success(self):
        """Test successful WAV file writing."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create test data
            data = np.random.randn(1000, 2).astype(np.float32)
            sr = 48000
            
            write_wav(f.name, data, sr)
            
            # Verify the file was created and has correct properties
            assert os.path.exists(f.name)
            with wave.open(f.name, 'rb') as wf:
                assert wf.getframerate() == sr
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2  # 16-bit
            
            os.unlink(f.name)

    def test_write_wav_clipping(self):
        """Test WAV writing with clipping."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create data that exceeds [-1, 1] range
            data = np.array([[2.0, -2.0], [1.5, -1.5]], dtype=np.float32)
            sr = 48000
            
            write_wav(f.name, data, sr)
            
            # Verify the file was created
            assert os.path.exists(f.name)
            os.unlink(f.name)

    def test_write_wav_creates_directory(self):
        """Test WAV writing creates parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "subdir", "test.wav")
            data = np.random.randn(100, 2).astype(np.float32)
            sr = 48000
            
            write_wav(output_path, data, sr)
            
            # Verify the file and directory were created
            assert os.path.exists(output_path)
            assert os.path.exists(os.path.dirname(output_path))


class TestUtilityAudioFunctions:
    """Test utility audio functions."""

    def test_ensure_stereo_stereo_input(self):
        """Test ensure_stereo with stereo input."""
        data = np.random.randn(100, 2)
        result = ensure_stereo(data)
        assert np.array_equal(result, data)

    def test_ensure_stereo_mono_input(self):
        """Test ensure_stereo with mono input."""
        data = np.random.randn(100, 1)
        result = ensure_stereo(data)
        assert result.shape == (100, 2)
        assert np.array_equal(result[:, 0], data[:, 0])
        assert np.array_equal(result[:, 1], data[:, 0])

    def test_db_to_gain(self):
        """Test dB to gain conversion."""
        assert abs(db_to_gain(0) - 1.0) < 1e-6
        assert abs(db_to_gain(-6) - 0.5011872336272722) < 1e-6
        assert abs(db_to_gain(-20) - 0.1) < 1e-6
        assert abs(db_to_gain(-40) - 0.01) < 1e-6

    def test_apply_fade_no_fade(self):
        """Test apply_fade with no fade."""
        data = np.random.randn(1000, 2)
        result = apply_fade(data, 48000, 0.0)
        assert np.array_equal(result, data)

    def test_apply_fade_negative_fade(self):
        """Test apply_fade with negative fade."""
        data = np.random.randn(1000, 2)
        result = apply_fade(data, 48000, -1.0)
        assert np.array_equal(result, data)

    def test_apply_fade_normal_fade(self):
        """Test apply_fade with normal fade."""
        data = np.ones((1000, 2))
        sr = 48000
        fade_sec = 0.1  # 100ms fade
        result = apply_fade(data, sr, fade_sec)
        
        # Check that fade is applied
        fade_samples = int(fade_sec * sr)
        assert fade_samples > 0
        
        # First samples should be faded in
        assert result[0, 0] < 1.0
        assert result[0, 1] < 1.0
        
        # Last samples should be faded out
        assert result[-1, 0] < 1.0
        assert result[-1, 1] < 1.0

    def test_apply_fade_too_long(self):
        """Test apply_fade with fade longer than half signal."""
        data = np.ones((100, 2))
        sr = 48000
        fade_sec = 10.0  # Very long fade
        result = apply_fade(data, sr, fade_sec)
        
        # Should still apply fade but limited to half the signal
        assert result[0, 0] < 1.0
        assert result[-1, 0] < 1.0


class TestGenerateBinauralWav:
    """Test generate_binaural_wav function."""

    def test_generate_binaural_wav_function_exists(self):
        """Test that generate_binaural_wav function exists and is callable."""
        assert callable(generate_binaural_wav)


class TestChooseCampfireClip:
    """Test choose_campfire_clip function."""

    def test_choose_campfire_clip_function_exists(self):
        """Test that choose_campfire_clip function exists and is callable."""
        assert callable(choose_campfire_clip)


class TestMixMultipleAmbientSounds:
    """Test mix_multiple_ambient_sounds function."""

    @patch('sleepstack.main.read_wav')
    def test_mix_multiple_ambient_sounds_success(self, mock_read_wav):
        """Test successful mixing of multiple ambient sounds."""
        # Mock read_wav to return test data
        test_data = np.random.randn(1000, 2)
        mock_read_wav.return_value = (test_data, 48000, 2)
        
        ambient_paths = ["/path/to/sound1.wav", "/path/to/sound2.wav"]
        target_samples = 1000
        sr = 48000
        
        result = mix_multiple_ambient_sounds(ambient_paths, target_samples, sr)
        
        # Verify read_wav was called for each path
        assert mock_read_wav.call_count == 2
        
        # Verify result shape
        assert result.shape == (target_samples, 2)
        assert isinstance(result, np.ndarray)

    @patch('sleepstack.main.read_wav')
    def test_mix_multiple_ambient_sounds_empty_list(self, mock_read_wav):
        """Test mixing with empty ambient sounds list."""
        with pytest.raises(ValueError) as exc_info:
            mix_multiple_ambient_sounds([], 1000, 48000)
        assert "No ambient sounds provided" in str(exc_info.value)

    @patch('sleepstack.main.read_wav')
    def test_mix_multiple_ambient_sounds_short_audio(self, mock_read_wav):
        """Test mixing with audio shorter than target."""
        # Create short audio data
        short_data = np.random.randn(500, 2)
        mock_read_wav.return_value = (short_data, 48000, 2)
        
        ambient_paths = ["/path/to/short.wav"]
        target_samples = 1000
        sr = 48000
        
        result = mix_multiple_ambient_sounds(ambient_paths, target_samples, sr)
        
        # Should be tiled to match target length
        assert result.shape == (target_samples, 2)

    @patch('sleepstack.main.read_wav')
    def test_mix_multiple_ambient_sounds_long_audio(self, mock_read_wav):
        """Test mixing with audio longer than target."""
        # Create long audio data
        long_data = np.random.randn(2000, 2)
        mock_read_wav.return_value = (long_data, 48000, 2)
        
        ambient_paths = ["/path/to/long.wav"]
        target_samples = 1000
        sr = 48000
        
        result = mix_multiple_ambient_sounds(ambient_paths, target_samples, sr)
        
        # Should be trimmed to match target length
        assert result.shape == (target_samples, 2)

    @patch('sleepstack.main.read_wav')
    def test_mix_multiple_ambient_sounds_mono_input(self, mock_read_wav):
        """Test mixing with mono input audio."""
        # Create mono audio data
        mono_data = np.random.randn(1000, 1)
        mock_read_wav.return_value = (mono_data, 48000, 1)
        
        ambient_paths = ["/path/to/mono.wav"]
        target_samples = 1000
        sr = 48000
        
        result = mix_multiple_ambient_sounds(ambient_paths, target_samples, sr)
        
        # Should be converted to stereo
        assert result.shape == (target_samples, 2)

    @patch('sleepstack.main.read_wav')
    def test_mix_multiple_ambient_sounds_peak_limiting(self, mock_read_wav):
        """Test mixing with peak limiting."""
        # Create audio data that would exceed 0.999 when mixed
        loud_data = np.ones((1000, 2)) * 0.8  # Each sound at 0.8, mixed would be 1.6
        mock_read_wav.return_value = (loud_data, 48000, 2)
        
        ambient_paths = ["/path/to/loud1.wav", "/path/to/loud2.wav"]
        target_samples = 1000
        sr = 48000
        
        result = mix_multiple_ambient_sounds(ambient_paths, target_samples, sr)
        
        # Should be peak limited
        assert np.max(np.abs(result)) <= 0.999


class TestMixBinauralAndMultipleAmbience:
    """Test mix_binaural_and_multiple_ambience function."""

    @patch('sleepstack.main.read_wav')
    @patch('sleepstack.main.write_wav')
    @patch('sleepstack.main.mix_multiple_ambient_sounds')
    @patch('sleepstack.main.project_root')
    @patch('pathlib.Path.mkdir')
    def test_mix_binaural_and_multiple_ambience_success(self, mock_mkdir, mock_root, mock_mix_ambient, mock_write_wav, mock_read_wav):
        """Test successful mixing of binaural with multiple ambient sounds."""
        # Setup mocks
        mock_root.return_value = Path("/project")
        mock_mkdir.return_value = None
        binaural_data = np.random.randn(1000, 2)
        mock_read_wav.return_value = (binaural_data, 48000, 2)
        mixed_ambient = np.random.randn(1000, 2)
        mock_mix_ambient.return_value = mixed_ambient
        
        binaural_path = "/path/to/binaural.wav"
        ambient_paths = ["/path/to/ambient1.wav", "/path/to/ambient2.wav"]
        
        result = mix_binaural_and_multiple_ambience(binaural_path, ambient_paths)
        
        # Verify calls
        mock_read_wav.assert_called_once_with(binaural_path)
        mock_mix_ambient.assert_called_once()
        mock_write_wav.assert_called_once()
        
        # Verify return value
        assert isinstance(result, str)

    @patch('sleepstack.main.read_wav')
    def test_mix_binaural_and_multiple_ambience_mono_binaural(self, mock_read_wav):
        """Test mixing with mono binaural input."""
        # Create mono binaural data
        mono_data = np.random.randn(1000, 1)
        mock_read_wav.return_value = (mono_data, 48000, 1)
        
        binaural_path = "/path/to/mono_binaural.wav"
        ambient_paths = ["/path/to/ambient.wav"]
        
        with pytest.raises(SystemExit) as exc_info:
            mix_binaural_and_multiple_ambience(binaural_path, ambient_paths)
        assert "Binaural must be stereo" in str(exc_info.value)

    @patch('sleepstack.main.read_wav')
    @patch('sleepstack.main.write_wav')
    @patch('sleepstack.main.mix_multiple_ambient_sounds')
    def test_mix_binaural_and_multiple_ambience_custom_output(self, mock_mix_ambient, mock_write_wav, mock_read_wav):
        """Test mixing with custom output path."""
        binaural_data = np.random.randn(1000, 2)
        mock_read_wav.return_value = (binaural_data, 48000, 2)
        mixed_ambient = np.random.randn(1000, 2)
        mock_mix_ambient.return_value = mixed_ambient
        
        binaural_path = "/path/to/binaural.wav"
        ambient_paths = ["/path/to/ambient.wav"]
        custom_output = "/custom/output.wav"
        
        result = mix_binaural_and_multiple_ambience(binaural_path, ambient_paths, out_path=custom_output)
        
        assert result == custom_output
        mock_write_wav.assert_called_once_with(custom_output, ANY, 48000)


class TestMixBinauralAndAmbience:
    """Test mix_binaural_and_ambience function."""

    @patch('sleepstack.main.read_wav')
    @patch('sleepstack.main.write_wav')
    @patch('sleepstack.main.project_root')
    @patch('pathlib.Path.mkdir')
    def test_mix_binaural_and_ambience_success(self, mock_mkdir, mock_root, mock_write_wav, mock_read_wav):
        """Test successful mixing of binaural with single ambient sound."""
        # Setup mocks
        mock_root.return_value = Path("/project")
        mock_mkdir.return_value = None
        binaural_data = np.random.randn(1000, 2)
        ambient_data = np.random.randn(1000, 2)
        mock_read_wav.side_effect = [(binaural_data, 48000, 2), (ambient_data, 48000, 2)]
        
        binaural_path = "/path/to/binaural.wav"
        ambience_path = "/path/to/ambient.wav"
        
        result = mix_binaural_and_ambience(binaural_path, ambience_path)
        
        # Verify calls
        assert mock_read_wav.call_count == 2
        mock_write_wav.assert_called_once()
        
        # Verify return value
        assert isinstance(result, str)

    @patch('sleepstack.main.read_wav')
    def test_mix_binaural_and_ambience_mono_binaural(self, mock_read_wav):
        """Test mixing with mono binaural input."""
        # Create mono binaural data
        mono_data = np.random.randn(1000, 1)
        mock_read_wav.return_value = (mono_data, 48000, 1)
        
        binaural_path = "/path/to/mono_binaural.wav"
        ambience_path = "/path/to/ambient.wav"
        
        with pytest.raises(SystemExit) as exc_info:
            mix_binaural_and_ambience(binaural_path, ambience_path)
        assert "Binaural must be stereo" in str(exc_info.value)

    @patch('sleepstack.main.read_wav')
    def test_mix_binaural_and_ambience_samplerate_mismatch(self, mock_read_wav):
        """Test mixing with samplerate mismatch."""
        binaural_data = np.random.randn(1000, 2)
        ambient_data = np.random.randn(1000, 2)
        mock_read_wav.side_effect = [(binaural_data, 48000, 2), (ambient_data, 44100, 2)]
        
        binaural_path = "/path/to/binaural.wav"
        ambience_path = "/path/to/ambient.wav"
        
        with pytest.raises(SystemExit) as exc_info:
            mix_binaural_and_ambience(binaural_path, ambience_path)
        assert "Samplerate mismatch" in str(exc_info.value)

    @patch('sleepstack.main.read_wav')
    @patch('sleepstack.main.write_wav')
    def test_mix_binaural_and_ambience_custom_output(self, mock_write_wav, mock_read_wav):
        """Test mixing with custom output path."""
        binaural_data = np.random.randn(1000, 2)
        ambient_data = np.random.randn(1000, 2)
        mock_read_wav.side_effect = [(binaural_data, 48000, 2), (ambient_data, 48000, 2)]
        
        binaural_path = "/path/to/binaural.wav"
        ambience_path = "/path/to/ambient.wav"
        custom_output = "/custom/output.wav"
        
        result = mix_binaural_and_ambience(binaural_path, ambience_path, out_path=custom_output)
        
        assert result == custom_output
        mock_write_wav.assert_called_once_with(custom_output, ANY, 48000)


class TestValidationFunctions:
    """Test validation functions."""

    def test_positive_float_minutes_valid(self):
        """Test positive_float_minutes with valid values."""
        assert positive_float_minutes("1.0") == 1.0
        assert positive_float_minutes("5.5") == 5.5
        assert positive_float_minutes("10.0") == 10.0

    def test_positive_float_minutes_invalid(self):
        """Test positive_float_minutes with invalid values."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_float_minutes("0")
        assert "must be > 0" in str(exc_info.value)
        
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_float_minutes("-1")
        assert "must be > 0" in str(exc_info.value)
        
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_float_minutes("11")
        assert "must be <= 10 minutes" in str(exc_info.value)

    def test_positive_float_seconds_valid(self):
        """Test positive_float_seconds with valid values."""
        assert positive_float_seconds("60.0") == 60.0
        assert positive_float_seconds("300.5") == 300.5
        assert positive_float_seconds("600.0") == 600.0

    def test_positive_float_seconds_invalid(self):
        """Test positive_float_seconds with invalid values."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_float_seconds("0")
        assert "must be > 0" in str(exc_info.value)
        
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_float_seconds("-1")
        assert "must be > 0" in str(exc_info.value)
        
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            positive_float_seconds("601")
        assert "must be <= 600 seconds" in str(exc_info.value)

    def test_nonneg_float_valid(self):
        """Test nonneg_float with valid values."""
        assert nonneg_float("0.0") == 0.0
        assert nonneg_float("1.5") == 1.5
        assert nonneg_float("10.0") == 10.0

    def test_nonneg_float_invalid(self):
        """Test nonneg_float with invalid values."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            nonneg_float("-1")
        assert "must be >= 0" in str(exc_info.value)
        
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            nonneg_float("-0.1")
        assert "must be >= 0" in str(exc_info.value)


class TestMain:
    """Test main function."""

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.get_available_ambient_sounds')
    @patch('sleepstack.main.validate_ambient_sound')
    @patch('sleepstack.main.get_ambient_sound_path')
    @patch('sleepstack.main.mix_binaural_and_ambience')
    @patch('sleepstack.main.mix_binaural_and_multiple_ambience')
    def test_main_single_ambient_success(self, mock_mix_multiple, mock_mix_single, mock_get_path, mock_validate, mock_get_available, mock_generate, mock_resolve):
        """Test main function with single ambient sound."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_get_available.return_value = ["campfire", "rain"]
        mock_validate.return_value = True
        mock_get_path.return_value = Path("/path/to/campfire.wav")
        mock_mix_single.return_value = "/path/to/output.wav"
        
        argv = ["--vibe", "calm", "--minutes", "5", "--ambient", "campfire"]
        result = main(argv)
        
        assert result == 0
        mock_resolve.assert_called_once_with("calm")
        mock_generate.assert_called_once()
        mock_validate.assert_called_once_with("campfire")
        mock_get_path.assert_called_once_with("campfire")
        mock_mix_single.assert_called_once()
        mock_mix_multiple.assert_not_called()

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.get_available_ambient_sounds')
    @patch('sleepstack.main.validate_ambient_sound')
    @patch('sleepstack.main.get_ambient_sound_path')
    @patch('sleepstack.main.mix_binaural_and_ambience')
    @patch('sleepstack.main.mix_binaural_and_multiple_ambience')
    def test_main_multiple_ambient_success(self, mock_mix_multiple, mock_mix_single, mock_get_path, mock_validate, mock_get_available, mock_generate, mock_resolve):
        """Test main function with multiple ambient sounds."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_get_available.return_value = ["campfire", "rain"]
        mock_validate.return_value = True
        mock_get_path.return_value = Path("/path/to/ambient.wav")
        mock_mix_multiple.return_value = "/path/to/output.wav"
        
        argv = ["--vibe", "calm", "--minutes", "5", "--ambient", "campfire,rain"]
        result = main(argv)
        
        assert result == 0
        mock_resolve.assert_called_once_with("calm")
        mock_generate.assert_called_once()
        assert mock_validate.call_count == 2  # Called for each ambient sound
        assert mock_get_path.call_count == 2  # Called for each ambient sound
        mock_mix_multiple.assert_called_once()
        mock_mix_single.assert_not_called()

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.mix_binaural_and_ambience')
    def test_main_ambience_file_success(self, mock_mix, mock_generate, mock_resolve):
        """Test main function with ambience file."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_mix.return_value = "/path/to/output.wav"
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create a dummy WAV file
            with wave.open(f.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b'\x00\x00' * 2 * 1000)
            
            try:
                argv = ["--vibe", "calm", "--minutes", "5", "--ambience-file", f.name]
                result = main(argv)
                
                assert result == 0
                mock_resolve.assert_called_once_with("calm")
                mock_generate.assert_called_once()
                mock_mix.assert_called_once()
            finally:
                os.unlink(f.name)

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.get_available_ambient_sounds')
    @patch('sleepstack.main.validate_ambient_sound')
    def test_main_invalid_ambient_sound(self, mock_validate, mock_get_available, mock_generate, mock_resolve):
        """Test main function with invalid ambient sound."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_get_available.return_value = ["campfire", "rain"]
        mock_validate.return_value = False
        
        argv = ["--vibe", "calm", "--minutes", "5", "--ambient", "invalid"]
        
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        assert "Unknown ambient sound 'invalid'" in str(exc_info.value)

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.get_available_ambient_sounds')
    @patch('sleepstack.main.validate_ambient_sound')
    @patch('sleepstack.main.get_ambient_sound_path')
    def test_main_ambient_sound_file_not_found(self, mock_get_path, mock_validate, mock_get_available, mock_generate, mock_resolve):
        """Test main function when ambient sound file is not found."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_get_available.return_value = ["campfire", "rain"]
        mock_validate.return_value = True
        mock_get_path.return_value = None  # File not found
        
        argv = ["--vibe", "calm", "--minutes", "5", "--ambient", "campfire"]
        
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        assert "Ambient sound file not found: campfire" in str(exc_info.value)

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    def test_main_ambience_file_not_found(self, mock_generate, mock_resolve):
        """Test main function when ambience file is not found."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        
        argv = ["--vibe", "calm", "--minutes", "5", "--ambience-file", "/nonexistent/file.wav"]
        
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        assert "Ambience file not found: /nonexistent/file.wav" in str(exc_info.value)

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.get_available_ambient_sounds')
    @patch('sleepstack.main.validate_ambient_sound')
    @patch('sleepstack.main.get_ambient_sound_path')
    @patch('sleepstack.main.mix_binaural_and_ambience')
    def test_main_with_overrides(self, mock_mix, mock_get_path, mock_validate, mock_get_available, mock_generate, mock_resolve):
        """Test main function with parameter overrides."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_get_available.return_value = ["campfire"]
        mock_validate.return_value = True
        mock_get_path.return_value = Path("/path/to/campfire.wav")
        mock_mix.return_value = "/path/to/output.wav"
        
        argv = [
            "--vibe", "calm",
            "--minutes", "5",
            "--ambient", "campfire",
            "--beat", "8.0",
            "--carrier", "220.0",
            "--samplerate", "44100",
            "--volume", "0.3",
            "--fade", "1.5",
            "--binaural-db", "-12.0",
            "--ambience-db", "-18.0",
            "--ambience-fade", "3.0",
            "--out", "/custom/output.wav"
        ]
        result = main(argv)
        
        assert result == 0
        
        # Verify generate_binaural_wav was called with overrides
        call_args = mock_generate.call_args
        assert call_args[1]['beat'] == 8.0
        assert call_args[1]['carrier'] == 220.0
        assert call_args[1]['samplerate'] == 44100
        assert call_args[1]['volume'] == 0.3
        assert call_args[1]['fade'] == 1.5
        
        # Verify mix_binaural_and_ambience was called with overrides
        call_args = mock_mix.call_args
        assert call_args[1]['binaural_db'] == -12.0
        assert call_args[1]['ambience_db'] == -18.0
        assert call_args[1]['ambience_fade'] == 3.0
        assert call_args[1]['out_path'] == "/custom/output.wav"

    @patch('sleepstack.main.resolve_vibe')
    @patch('sleepstack.main.generate_binaural_wav')
    @patch('sleepstack.main.get_available_ambient_sounds')
    @patch('sleepstack.main.validate_ambient_sound')
    @patch('sleepstack.main.get_ambient_sound_path')
    @patch('sleepstack.main.mix_binaural_and_ambience')
    def test_main_with_loop_flag(self, mock_mix, mock_get_path, mock_validate, mock_get_available, mock_generate, mock_resolve):
        """Test main function with loop flag."""
        # Setup mocks
        mock_resolve.return_value = "calm"
        mock_generate.return_value = ("/path/to/binaural.wav", 48000)
        mock_get_available.return_value = ["campfire"]
        mock_validate.return_value = True
        mock_get_path.return_value = Path("/path/to/campfire.wav")
        mock_mix.return_value = "/path/to/output.wav"
        
        argv = ["--vibe", "calm", "--minutes", "5", "--ambient", "campfire", "--loop"]
        result = main(argv)
        
        assert result == 0
        
        # Verify generate_binaural_wav was called with loop=True
        call_args = mock_generate.call_args
        assert call_args[1]['loop'] is True

    def test_main_missing_required_args(self):
        """Test main function with missing required arguments."""
        argv = ["--vibe", "calm"]  # Missing duration and ambient
        
        with pytest.raises(SystemExit):
            main(argv)

    def test_main_invalid_vibe(self):
        """Test main function with invalid vibe."""
        argv = ["--vibe", "invalid", "--minutes", "5", "--ambient", "campfire"]
        
        with pytest.raises(SystemExit) as exc_info:
            main(argv)
        assert "Unknown vibe 'invalid'" in str(exc_info.value)


class TestRun:
    """Test run function."""

    @patch('sleepstack.main.main')
    def test_run_calls_main(self, mock_main):
        """Test that run function calls main."""
        mock_main.return_value = 0
        argv = ["--vibe", "calm", "--minutes", "5", "--ambient", "campfire"]
        
        result = run(argv)
        
        assert result == 0
        mock_main.assert_called_once_with(argv)

    @patch('sleepstack.main.main')
    def test_run_with_none_argv(self, mock_main):
        """Test run function with None argv."""
        mock_main.return_value = 0
        
        result = run(None)
        
        assert result == 0
        mock_main.assert_called_once_with(None)
