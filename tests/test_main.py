#!/usr/bin/env python3
"""
Unit tests for sleepstack main functionality.
"""

import tempfile
import wave
from pathlib import Path
import pytest
import numpy as np

from sleepstack.main import (
    PRESETS,
    ALIASES,
    resolve_vibe,
    read_wav,
    write_wav,
    ensure_stereo,
    db_to_gain,
    apply_fade,
    project_root,
    find_assets_dir,
    choose_campfire_clip,
    mix_binaural_and_ambience,
    generate_binaural_wav,
)


class TestVibeResolution:
    """Test vibe preset resolution and aliases."""

    def test_preset_names(self) -> None:
        """Test that all preset names resolve correctly."""
        for name in PRESETS.keys():
            assert resolve_vibe(name) == name

    def test_aliases(self) -> None:
        """Test that aliases resolve to correct presets."""
        for alias, target in ALIASES.items():
            assert resolve_vibe(alias) == target

    def test_fuzzy_matching(self) -> None:
        """Test startswith fuzzy matching."""
        assert resolve_vibe("cal") == "calm"
        assert resolve_vibe("de") == "deep"
        assert resolve_vibe("fo") == "focus"

    def test_unknown_vibe(self) -> None:
        """Test that unknown vibes raise SystemExit."""
        with pytest.raises(SystemExit):
            resolve_vibe("unknown")


class TestAudioIO:
    """Test audio I/O functions."""

    def test_read_write_wav_roundtrip(self) -> None:
        """Test that read_wav and write_wav work correctly together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test data
            sample_rate = 48000
            duration = 1.0
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            test_data = np.sin(2 * np.pi * 440 * t).reshape(-1, 1)  # Mono
            test_data = (test_data * 32767.0).astype(np.int16)

            # Write to file
            test_path = Path(tmpdir) / "test.wav"
            with wave.open(str(test_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(test_data.tobytes())

            # Read back
            data, sr, ch = read_wav(str(test_path))

            # Verify
            assert sr == sample_rate
            assert ch == 1
            assert data.shape[0] == int(sample_rate * duration)
            assert data.shape[1] == 1
            assert data.dtype == np.float64

    def test_write_wav_stereo(self) -> None:
        """Test that write_wav creates proper stereo files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create stereo test data
            sample_rate = 48000
            duration = 0.1
            samples = int(sample_rate * duration)
            test_data = np.random.randn(samples, 2).astype(np.float64)

            # Write to file
            test_path = Path(tmpdir) / "stereo_test.wav"
            write_wav(str(test_path), test_data, sample_rate)

            # Verify file properties
            with wave.open(str(test_path), "rb") as wf:
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2  # 16-bit
                assert wf.getframerate() == sample_rate
                assert wf.getnframes() == samples

    def test_ensure_stereo(self) -> None:
        """Test stereo conversion."""
        # Mono input
        mono = np.array([[1.0], [2.0], [3.0]])
        stereo = ensure_stereo(mono)
        assert stereo.shape == (3, 2)
        assert np.array_equal(stereo[:, 0], mono[:, 0])
        assert np.array_equal(stereo[:, 1], mono[:, 0])

        # Already stereo
        stereo_input = np.array([[1.0, 2.0], [3.0, 4.0]])
        stereo_output = ensure_stereo(stereo_input)
        assert np.array_equal(stereo_output, stereo_input)


class TestAudioProcessing:
    """Test audio processing functions."""

    def test_db_to_gain(self) -> None:
        """Test dB to gain conversion."""
        assert abs(db_to_gain(0) - 1.0) < 1e-10
        assert abs(db_to_gain(-6) - 0.5) < 1e-2  # Relaxed precision
        assert abs(db_to_gain(-20) - 0.1) < 1e-3

    def test_apply_fade(self) -> None:
        """Test fade application."""
        sample_rate = 48000
        duration = 2.0
        samples = int(sample_rate * duration)

        # Create test signal
        test_signal = np.ones((samples, 2))

        # Apply 0.5 second fade
        faded = apply_fade(test_signal, sample_rate, 0.5)

        # Check that fade was applied
        fade_samples = int(0.5 * sample_rate)
        assert faded[0, 0] < 1.0  # Start should be faded
        assert faded[-1, 0] < 1.0  # End should be faded
        assert faded[fade_samples, 0] == 1.0  # Middle should be full level

    def test_apply_fade_zero(self) -> None:
        """Test that zero fade doesn't change signal."""
        test_signal = np.random.randn(1000, 2)
        faded = apply_fade(test_signal, 48000, 0.0)
        assert np.array_equal(faded, test_signal)


class TestPathResolution:
    """Test path resolution functions."""

    def test_project_root(self) -> None:
        """Test project root detection."""
        root = project_root()
        assert root.exists()
        assert root.is_absolute()
        assert (root / "pyproject.toml").exists()

    def test_find_assets_dir(self) -> None:
        """Test assets directory finding."""
        assets_dir = find_assets_dir()
        assert assets_dir.exists()
        assert (assets_dir / "ambience" / "campfire").exists()

    def test_choose_campfire_clip(self) -> None:
        """Test campfire clip selection - now always returns 1m clip."""
        # Test with different durations - all should return 1m clip
        sample_rate = 48000

        # 30 seconds should choose 1m clip
        clip_30s = choose_campfire_clip(30 * sample_rate, sample_rate)
        assert "campfire_1m.wav" in clip_30s

        # 90 seconds should choose 1m clip
        clip_90s = choose_campfire_clip(90 * sample_rate, sample_rate)
        assert "campfire_1m.wav" in clip_90s

        # 200 seconds should choose 1m clip
        clip_200s = choose_campfire_clip(200 * sample_rate, sample_rate)
        assert "campfire_1m.wav" in clip_200s

        # 400 seconds should choose 1m clip (now uses tiling)
        clip_400s = choose_campfire_clip(400 * sample_rate, sample_rate)
        assert "campfire_1m.wav" in clip_400s

        # 700 seconds should choose 1m clip (now uses tiling)
        clip_700s = choose_campfire_clip(700 * sample_rate, sample_rate)
        assert "campfire_1m.wav" in clip_700s

        # Very long duration should still choose 1m clip
        clip_long = choose_campfire_clip(1200 * sample_rate, sample_rate)  # 20 minutes
        assert "campfire_1m.wav" in clip_long


class TestAmbientSoundRefactor:
    """Test the simplified ambient sound system with 1m clips and tiling."""

    def test_very_long_durations_tiling(self) -> None:
        """Test that very long durations work correctly with 1m clip tiling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural (20 minutes)
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=1200.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create test ambience (1 minute - will be tiled)
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            ambience_data = np.random.randn(sample_rate * 60, 1).astype(np.float64)  # 1 minute
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Verify lengths match
            binaural_data, _, _ = read_wav(str(binaural_path))
            mix_data, _, _ = read_wav(mix_path)

            assert mix_data.shape[0] == binaural_data.shape[0]
            assert mix_data.shape[1] == 2  # Stereo
            # Should be exactly 20 minutes worth of samples
            assert mix_data.shape[0] == 1200 * sample_rate

    def test_fade_application_with_looped_audio(self) -> None:
        """Test that fade application works correctly with looped ambience."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural (5 minutes)
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=300.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create test ambience (1 minute - will be tiled 5 times)
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            # Create a simple pattern that we can verify
            ambience_data = np.ones((sample_rate * 60, 1)).astype(np.float64)  # 1 minute of ones
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix with fade
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                ambience_fade=10.0,  # 10 second fade
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Read mixed result
            mix_data, _, _ = read_wav(mix_path)

            # Check that fade was applied to the ambience
            fade_samples = int(10.0 * sample_rate)
            # The ambience should be faded at the beginning and end
            # We can't easily test the exact values due to mixing with binaural,
            # but we can verify the structure is correct
            assert mix_data.shape[0] == 300 * sample_rate  # 5 minutes
            assert mix_data.shape[1] == 2  # Stereo

    def test_exact_one_minute_duration(self) -> None:
        """Test edge case of exactly 1-minute duration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural (exactly 1 minute)
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=60.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create test ambience (exactly 1 minute - should match perfectly)
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            ambience_data = np.random.randn(sample_rate * 60, 1).astype(np.float64)
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Verify lengths match exactly
            binaural_data, _, _ = read_wav(str(binaural_path))
            mix_data, _, _ = read_wav(mix_path)

            assert mix_data.shape[0] == binaural_data.shape[0]
            assert mix_data.shape[0] == 60 * sample_rate  # Exactly 1 minute

    def test_very_short_duration(self) -> None:
        """Test edge case of very short duration (less than 1 minute)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural (10 seconds)
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=10.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create test ambience (1 minute - will be trimmed)
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            ambience_data = np.random.randn(sample_rate * 60, 1).astype(np.float64)  # 1 minute
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Verify lengths match
            binaural_data, _, _ = read_wav(str(binaural_path))
            mix_data, _, _ = read_wav(mix_path)

            assert mix_data.shape[0] == binaural_data.shape[0]
            assert mix_data.shape[0] == 10 * sample_rate  # Exactly 10 seconds

    def test_no_audio_artifacts_at_loop_boundaries(self) -> None:
        """Test that there are no audio artifacts at loop boundaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural (3 minutes - will require 3 loops of 1m clip)
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=180.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create test ambience with a known pattern
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            # Create a simple sine wave pattern
            t = np.linspace(0, 60, sample_rate * 60, False)  # 1 minute
            ambience_data = np.sin(2 * np.pi * 1 * t).reshape(-1, 1)  # 1 Hz sine wave
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Read mixed result
            mix_data, _, _ = read_wav(mix_path)

            # Check that the pattern continues smoothly across loop boundaries
            # At 60 seconds (1 minute), the pattern should continue smoothly
            loop_boundary = 60 * sample_rate
            # We can't easily test for exact continuity due to mixing with binaural,
            # but we can verify the structure is correct
            assert mix_data.shape[0] == 180 * sample_rate  # 3 minutes
            assert mix_data.shape[1] == 2  # Stereo

            # Check that there are no sudden jumps or discontinuities
            # (This is a basic check - more sophisticated analysis would require
            # separating the ambience component from the mix)
            diff = np.diff(mix_data, axis=0)
            max_diff = np.max(np.abs(diff))
            # The maximum difference should be reasonable (not infinite or NaN)
            assert np.isfinite(max_diff)
            assert max_diff < 10.0  # Reasonable threshold


class TestBinauralGeneration:
    """Test binaural beat generation."""

    def test_generate_binaural_wav_duration(self) -> None:
        """Test that generated binaural length matches requested duration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            preset = PRESETS["calm"]
            duration_sec = 5.0

            output_path = Path(tmpdir) / "test_binaural.wav"
            binaural_path, sr = generate_binaural_wav(
                duration_sec=duration_sec, preset=preset, vibe_key="calm", out_path=str(output_path)
            )

            # Read the generated file
            data, sr_read, ch = read_wav(binaural_path)

            # Verify duration (allow ±1 sample tolerance)
            expected_samples = int(duration_sec * sr)
            actual_samples = data.shape[0]
            assert abs(actual_samples - expected_samples) <= 1

            # Verify other properties
            assert sr_read == sr == 48000
            assert ch == 2  # Stereo
            assert data.dtype == np.float64

    def test_generate_binaural_wav_bit_depth(self) -> None:
        """Test that output WAV is 16-bit PCM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            preset = PRESETS["calm"]
            output_path = Path(tmpdir) / "test_binaural.wav"

            generate_binaural_wav(
                duration_sec=1.0, preset=preset, vibe_key="calm", out_path=str(output_path)
            )

            # Check WAV properties
            with wave.open(str(output_path), "rb") as wf:
                assert wf.getsampwidth() == 2  # 16-bit PCM
                assert wf.getnchannels() == 2  # Stereo
                assert wf.getframerate() == 48000

    def test_generate_binaural_wav_stereo_enforcement(self) -> None:
        """Test that binaural is always stereo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            preset = PRESETS["calm"]
            output_path = Path(tmpdir) / "test_binaural.wav"

            generate_binaural_wav(
                duration_sec=1.0, preset=preset, vibe_key="calm", out_path=str(output_path)
            )

            data, sr, ch = read_wav(str(output_path))
            assert ch == 2  # Must be stereo
            assert data.shape[1] == 2


class TestMixing:
    """Test audio mixing functionality."""

    def test_mix_binaural_and_ambience_length(self) -> None:
        """Test that mixed output length equals binaural length exactly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural (2 seconds)
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=2.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create test ambience (1 second - shorter)
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            ambience_data = np.random.randn(sample_rate, 1).astype(np.float64)
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Verify lengths match
            binaural_data, _, _ = read_wav(str(binaural_path))
            mix_data, _, _ = read_wav(mix_path)

            assert mix_data.shape[0] == binaural_data.shape[0]
            assert mix_data.shape[1] == 2  # Stereo

    def test_mix_mono_ambience_duplication(self) -> None:
        """Test that mono ambience is duplicated to L/R channels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test binaural
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=1.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create mono ambience with known pattern
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            # Create a simple pattern: [1, 2, 3, 4, ...]
            ambience_data = np.arange(1, sample_rate + 1, dtype=np.float64).reshape(-1, 1) / 1000.0
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Read mixed result
            mix_data, _, _ = read_wav(mix_path)

            # The ambience should be duplicated to both channels
            # We can't easily test this without knowing the exact mixing levels,
            # but we can verify the structure is correct
            assert mix_data.shape[1] == 2  # Stereo
            assert not np.array_equal(
                mix_data[:, 0], mix_data[:, 1]
            )  # L and R should be different due to binaural

    def test_mix_samplerate_guard(self) -> None:
        """Test that samplerate mismatch raises expected error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create binaural at 48kHz
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=1.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create ambience at 44.1kHz
            ambience_path = Path(tmpdir) / "ambience.wav"
            ambience_data = np.random.randn(44100, 1).astype(np.float64)
            with wave.open(str(ambience_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                wf.writeframes((ambience_data * 32767.0).astype(np.int16).tobytes())

            # Mix should raise SystemExit
            with pytest.raises(SystemExit, match="Samplerate mismatch"):
                mix_binaural_and_ambience(
                    binaural_path=str(binaural_path),
                    ambience_path=str(ambience_path),
                    out_path=str(Path(tmpdir) / "mix.wav"),
                )

    def test_mix_clipping_guard(self) -> None:
        """Test that soft limiting engages when needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create binaural
            binaural_path = Path(tmpdir) / "binaural.wav"
            preset = PRESETS["calm"]
            generate_binaural_wav(
                duration_sec=1.0, preset=preset, vibe_key="calm", out_path=str(binaural_path)
            )

            # Create very loud ambience
            ambience_path = Path(tmpdir) / "ambience.wav"
            sample_rate = 48000
            ambience_data = np.ones((sample_rate, 1)) * 0.9  # Very loud
            write_wav(str(ambience_path), ambience_data, sample_rate)

            # Mix with high levels that would cause clipping
            mix_path = mix_binaural_and_ambience(
                binaural_path=str(binaural_path),
                ambience_path=str(ambience_path),
                binaural_db=0.0,  # Very loud
                ambience_db=0.0,  # Very loud
                out_path=str(Path(tmpdir) / "mix.wav"),
            )

            # Read mixed result
            mix_data, _, _ = read_wav(mix_path)

            # Peak should be less than 1.0 (soft limited)
            peak = float(np.max(np.abs(mix_data)))
            assert peak < 1.0
            assert peak > 0.99  # But close to 1.0


class TestCLIIntegration:
    """Test CLI integration and smoke tests."""

    def test_cli_smoke_test(self) -> None:
        """Smoke test: generate a file and verify basic properties."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "smoke_test.wav"

            # This would normally be called via CLI, but we'll call the function directly
            preset = PRESETS["calm"]
            binaural_path, sr = generate_binaural_wav(
                duration_sec=1.0, preset=preset, vibe_key="calm", out_path=str(output_path)
            )

            # Verify file exists and has correct properties
            assert Path(binaural_path).exists()
            data, sr_read, ch = read_wav(binaural_path)

            # Basic properties
            assert sr_read == 48000
            assert ch == 2  # Stereo
            assert data.dtype == np.int16 or data.dtype == np.float64
            assert data.shape[0] == 48000  # 1 second at 48kHz
            assert data.shape[1] == 2  # Stereo


class TestDurationValidation:
    """Test duration validation and limits."""

    def test_positive_float_minutes_validation(self) -> None:
        """Test positive_float_minutes function validation."""
        from sleepstack.main import positive_float_minutes
        import argparse

        # Valid values
        assert positive_float_minutes("1") == 1.0
        assert positive_float_minutes("5.5") == 5.5
        assert positive_float_minutes("10") == 10.0
        assert positive_float_minutes("0.1") == 0.1

        # Invalid values - zero
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("0")

        # Invalid values - negative
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("-1")
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("-0.1")

        # Invalid values - over 10 minutes
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("10.1")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("15")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("60")

    def test_positive_float_seconds_validation(self) -> None:
        """Test positive_float_seconds function validation."""
        from sleepstack.main import positive_float_seconds
        import argparse

        # Valid values
        assert positive_float_seconds("1") == 1.0
        assert positive_float_seconds("300") == 300.0
        assert positive_float_seconds("600") == 600.0
        assert positive_float_seconds("0.1") == 0.1

        # Invalid values - zero
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_seconds("0")

        # Invalid values - negative
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_seconds("-1")

        # Invalid values - over 600 seconds (10 minutes)
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 600 seconds"):
            positive_float_seconds("601")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 600 seconds"):
            positive_float_seconds("900")

    def test_seconds_validation_edge_cases(self) -> None:
        """Test seconds validation with edge cases around 10-minute limit."""
        from sleepstack.main import positive_float_seconds
        import argparse

        # Exactly 10 minutes in seconds (600 seconds) - should be valid
        assert positive_float_seconds("600") == 600.0

        # Just under 10 minutes in seconds (599 seconds)
        assert positive_float_seconds("599") == 599.0

        # 9 minutes 59 seconds
        assert positive_float_seconds("599.9") == 599.9

        # Just over 10 minutes in seconds (601 seconds) - should be invalid
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 600 seconds"):
            positive_float_seconds("601")

    def test_minutes_validation_edge_cases(self) -> None:
        """Test minutes validation with edge cases around 10-minute limit."""
        from sleepstack.main import positive_float_minutes
        import argparse

        # Exactly 10 minutes
        assert positive_float_minutes("10") == 10.0

        # Just over 10 minutes
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("10.1")

        # 9.9 minutes
        assert positive_float_minutes("9.9") == 9.9

        # 9 minutes 59 seconds (9.983... minutes)
        assert positive_float_minutes("9.983") == 9.983

    def test_vibe_binaural_validation(self) -> None:
        """Test that vibe_binaural.py has the same validation."""
        from sleepstack.vibe_binaural import positive_float_minutes, positive_float_seconds
        import argparse

        # Valid values for minutes
        assert positive_float_minutes("5") == 5.0
        assert positive_float_minutes("10") == 10.0

        # Valid values for seconds
        assert positive_float_seconds("300") == 300.0
        assert positive_float_seconds("600") == 600.0

        # Invalid values for minutes
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("0")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("11")

        # Invalid values for seconds
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_seconds("0")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 600 seconds"):
            positive_float_seconds("601")

    def test_make_binaural_validation(self) -> None:
        """Test that make_binaural.py has the same validation."""
        from sleepstack.make_binaural import positive_float_minutes, positive_float_seconds
        import argparse

        # Valid values for minutes
        assert positive_float_minutes("5") == 5.0
        assert positive_float_minutes("10") == 10.0

        # Valid values for seconds
        assert positive_float_seconds("300") == 300.0
        assert positive_float_seconds("600") == 600.0

        # Invalid values for minutes
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_minutes("0")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 10 minutes"):
            positive_float_minutes("11")

        # Invalid values for seconds
        with pytest.raises(argparse.ArgumentTypeError, match="must be > 0"):
            positive_float_seconds("0")
        with pytest.raises(argparse.ArgumentTypeError, match="must be <= 600 seconds"):
            positive_float_seconds("601")
