"""Tests for mix_binaural_with_ambience.py"""

import pytest
import tempfile
import os
import wave
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from sleepstack.mix_binaural_with_ambience import (
    db_to_gain,
    read_wav,
    write_wav,
    ensure_stereo,
    apply_fade,
    duration_sec,
    project_root,
    campfire_dir,
    choose_campfire_clip,
    mix_audio,
    default_out_path,
    main,
)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_db_to_gain(self):
        """Test dB to gain conversion."""
        # Test common values
        assert abs(db_to_gain(0) - 1.0) < 1e-6
        assert abs(db_to_gain(-6) - 0.5011872336272722) < 1e-6  # Actual value for -6dB
        assert abs(db_to_gain(-20) - 0.1) < 1e-6
        assert abs(db_to_gain(-40) - 0.01) < 1e-6

    def test_duration_sec(self):
        """Test duration calculation."""
        assert duration_sec(48000, 48000) == 1.0
        assert duration_sec(24000, 48000) == 0.5
        assert duration_sec(96000, 48000) == 2.0

    def test_ensure_stereo(self):
        """Test stereo conversion."""
        # Already stereo
        stereo_data = np.array([[1, 2], [3, 4], [5, 6]])
        result = ensure_stereo(stereo_data)
        np.testing.assert_array_equal(result, stereo_data)
        
        # Mono to stereo
        mono_data = np.array([[1], [2], [3]])
        result = ensure_stereo(mono_data)
        expected = np.array([[1, 1], [2, 2], [3, 3]])
        np.testing.assert_array_equal(result, expected)

    def test_apply_fade(self):
        """Test fade application."""
        # Test with no fade
        data = np.ones((100, 2))
        result = apply_fade(data, 48000, 0)
        np.testing.assert_array_equal(result, data)
        
        # Test with fade
        data = np.ones((100, 2))
        result = apply_fade(data, 48000, 0.01)  # 10ms fade
        # First and last samples should be faded
        assert result[0, 0] < 1.0
        assert result[-1, 0] < 1.0
        # Middle samples should be unchanged
        assert result[50, 0] == 1.0

    def test_apply_fade_negative(self):
        """Test fade with negative value."""
        data = np.ones((100, 2))
        result = apply_fade(data, 48000, -1.0)
        np.testing.assert_array_equal(result, data)

    def test_apply_fade_too_long(self):
        """Test fade longer than half the signal."""
        data = np.ones((100, 2))
        result = apply_fade(data, 48000, 1.0)  # 1 second fade on 100 samples
        # Should not crash, but will apply fade since f = min(48000, 50) = 50
        # The function applies fade when f > 0, so this will actually fade the signal
        assert result.shape == data.shape
        # First and last samples should be faded
        assert result[0, 0] < 1.0
        assert result[-1, 0] < 1.0


class TestPathFunctions:
    """Test path-related functions."""

    def test_project_root(self):
        """Test project root detection."""
        root = project_root()
        assert isinstance(root, str)
        assert os.path.exists(root)
        assert os.path.exists(os.path.join(root, "src"))

    def test_campfire_dir(self):
        """Test campfire directory path."""
        campfire_path = campfire_dir()
        assert isinstance(campfire_path, str)
        assert "campfire" in campfire_path
        assert "ambience" in campfire_path

    @patch('sleepstack.mix_binaural_with_ambience.campfire_dir')
    def test_choose_campfire_clip(self, mock_campfire_dir):
        """Test campfire clip selection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            campfire_path = os.path.join(temp_dir, "campfire")
            os.makedirs(campfire_path)
            campfire_file = os.path.join(campfire_path, "campfire_1m.wav")
            
            # Create a dummy WAV file
            with wave.open(campfire_file, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b'\x00' * 48000 * 2 * 2)  # 1 second of silence
            
            mock_campfire_dir.return_value = campfire_path
            
            result = choose_campfire_clip(48000, 48000)
            assert result == campfire_file

    @patch('sleepstack.mix_binaural_with_ambience.campfire_dir')
    def test_choose_campfire_clip_missing(self, mock_campfire_dir):
        """Test campfire clip selection when file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_campfire_dir.return_value = temp_dir
            
            with pytest.raises(SystemExit):
                choose_campfire_clip(48000, 48000)

    def test_default_out_path(self):
        """Test default output path generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            binaural_path = os.path.join(temp_dir, "test_binaural.wav")
            
            with patch('sleepstack.mix_binaural_with_ambience.project_root') as mock_root:
                mock_root.return_value = temp_dir
                
                result = default_out_path(binaural_path, "campfire")
                expected = os.path.join(temp_dir, "build", "mix", "test_binaural__campfire.wav")
                assert result == expected
                
                # Test with None ambient
                result = default_out_path(binaural_path, None)
                expected = os.path.join(temp_dir, "build", "mix", "test_binaural__mix.wav")
                assert result == expected


class TestAudioIO:
    """Test audio I/O functions."""

    def test_read_wav(self):
        """Test WAV file reading."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a test WAV file with known values
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                # Write 1 second of stereo audio with known values
                frames = np.array([[16383, -16383], [0, 0]], dtype=np.int16)  # Known values
                wf.writeframes(frames.tobytes())
            
            try:
                data, sr, channels = read_wav(temp_file.name)
                assert sr == 48000
                assert channels == 2
                assert data.shape == (2, 2)  # Only 2 frames written
                # Check that values are in expected range after normalization
                assert np.all(data >= -1.0) and np.all(data <= 1.0)
                # Check specific values: 16383/32767 ≈ 0.5, -16383/32767 ≈ -0.5
                assert abs(data[0, 0] - 0.5) < 1e-4
                assert abs(data[0, 1] - (-0.5)) < 1e-4
            finally:
                os.unlink(temp_file.name)

    def test_read_wav_nonexistent(self):
        """Test reading nonexistent WAV file."""
        with pytest.raises(FileNotFoundError):
            read_wav("/nonexistent/file.wav")

    def test_read_wav_empty(self):
        """Test reading empty WAV file."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create empty file
            temp_file.write(b'')
            temp_file.flush()
            
            try:
                with pytest.raises(ValueError, match="File is empty"):
                    read_wav(temp_file.name)
            finally:
                os.unlink(temp_file.name)

    def test_read_wav_wrong_bit_depth(self):
        """Test reading WAV with wrong bit depth."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create 8-bit WAV (not supported)
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(48000)
                wf.writeframes(b'\x00' * 48000 * 2)
            
            try:
                with pytest.raises(SystemExit, match="Only 16-bit PCM supported"):
                    read_wav(temp_file.name)
            finally:
                os.unlink(temp_file.name)

    def test_write_wav(self):
        """Test WAV file writing."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create test data
            data = np.random.rand(1000, 2) * 0.5  # Small amplitude
            sr = 48000
            
            write_wav(temp_file.name, data, sr)
            
            # Verify the file was written correctly
            with wave.open(temp_file.name, 'rb') as wf:
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == sr
                assert wf.getnframes() == 1000

    def test_write_wav_clipping(self):
        """Test WAV writing with clipping."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create data that exceeds [-1, 1] range
            data = np.array([[2.0, -2.0], [1.5, -1.5]])
            sr = 48000
            
            write_wav(temp_file.name, data, sr)
            
            # Verify the file was written (clipping should have occurred)
            with wave.open(temp_file.name, 'rb') as wf:
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == sr


class TestMixAudio:
    """Test audio mixing function."""

    def test_mix_audio_basic(self):
        """Test basic audio mixing."""
        # Create test data
        binaural = np.ones((100, 2)) * 0.5
        ambience = np.ones((100, 2)) * 0.3
        sr = 48000
        
        result = mix_audio(binaural, ambience, sr, -6, -12, 0)
        
        assert result.shape == (100, 2)
        # Should be mixed (0.5 * 0.5 + 0.3 * 0.25 = 0.25 + 0.075 = 0.325)
        expected_gain_b = db_to_gain(-6)  # 0.5
        expected_gain_a = db_to_gain(-12)  # 0.25
        expected = binaural * expected_gain_b + ambience * expected_gain_a
        np.testing.assert_array_almost_equal(result, expected)

    def test_mix_audio_mono_ambience(self):
        """Test mixing with mono ambience."""
        binaural = np.ones((100, 2)) * 0.5
        ambience = np.ones((100, 1)) * 0.3  # Mono
        sr = 48000
        
        result = mix_audio(binaural, ambience, sr, -6, -12, 0)
        
        assert result.shape == (100, 2)
        # Ambience should be duplicated to stereo

    def test_mix_audio_different_lengths(self):
        """Test mixing with different length audio."""
        binaural = np.ones((100, 2)) * 0.5
        ambience = np.ones((50, 2)) * 0.3  # Shorter
        sr = 48000
        
        result = mix_audio(binaural, ambience, sr, -6, -12, 0)
        
        assert result.shape == (100, 2)
        # Ambience should be tiled to match binaural length

    def test_mix_audio_longer_ambience(self):
        """Test mixing with longer ambience."""
        binaural = np.ones((50, 2)) * 0.5
        ambience = np.ones((100, 2)) * 0.3  # Longer
        sr = 48000
        
        result = mix_audio(binaural, ambience, sr, -6, -12, 0)
        
        assert result.shape == (50, 2)
        # Ambience should be trimmed to match binaural length

    def test_mix_audio_clipping(self):
        """Test mixing with clipping protection."""
        binaural = np.ones((100, 2)) * 0.8
        ambience = np.ones((100, 2)) * 0.8
        sr = 48000
        
        result = mix_audio(binaural, ambience, sr, 0, 0, 0)  # No attenuation
        
        # Should be clipped to prevent overflow
        assert np.max(np.abs(result)) <= 0.999

    def test_mix_audio_binaural_not_stereo(self):
        """Test mixing with non-stereo binaural."""
        binaural = np.ones((100, 1))  # Mono
        ambience = np.ones((100, 2))
        sr = 48000
        
        with pytest.raises(SystemExit, match="Binaural must be stereo"):
            mix_audio(binaural, ambience, sr, -6, -12, 0)


class TestMainFunction:
    """Test main CLI function."""

    def test_main_help(self):
        """Test main function help."""
        with pytest.raises(SystemExit):
            main(["--help"])

    def test_main_missing_binaural(self):
        """Test main function with missing binaural file."""
        with pytest.raises(SystemExit, match="Binaural file not found"):
            main(["--binaural", "/nonexistent.wav", "--ambient", "campfire"])

    def test_main_both_ambient_and_file(self):
        """Test main function with both ambient and ambience-file."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a dummy binaural file
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b'\x00' * 48000 * 2 * 2)
            
            try:
                with pytest.raises(SystemExit, match="Use either --ambient or --ambience-file"):
                    main([
                        "--binaural", temp_file.name,
                        "--ambient", "campfire",
                        "--ambience-file", "/some/file.wav"
                    ])
            finally:
                os.unlink(temp_file.name)

    def test_main_no_ambient_source(self):
        """Test main function with no ambient source."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a dummy binaural file
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b'\x00' * 48000 * 2 * 2)
            
            try:
                with pytest.raises(SystemExit, match="Provide --ambient"):
                    main(["--binaural", temp_file.name])
            finally:
                os.unlink(temp_file.name)

    def test_main_mono_binaural(self):
        """Test main function with mono binaural."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a mono binaural file
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b'\x00' * 48000 * 2)
            
            try:
                with pytest.raises(SystemExit, match="Binaural must be stereo"):
                    main(["--binaural", temp_file.name, "--ambient", "campfire"])
            finally:
                os.unlink(temp_file.name)

    @patch('sleepstack.mix_binaural_with_ambience.validate_ambient_sound')
    @patch('sleepstack.mix_binaural_with_ambience.get_ambient_sound_path')
    def test_main_invalid_ambient(self, mock_get_path, mock_validate):
        """Test main function with invalid ambient sound."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a dummy binaural file
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b'\x00' * 48000 * 2 * 2)
            
            mock_validate.return_value = False
            
            try:
                with pytest.raises(SystemExit, match="Unknown ambient sound"):
                    main(["--binaural", temp_file.name, "--ambient", "invalid"])
            finally:
                os.unlink(temp_file.name)

    @patch('sleepstack.mix_binaural_with_ambience.validate_ambient_sound')
    @patch('sleepstack.mix_binaural_with_ambience.get_ambient_sound_path')
    def test_main_samplerate_mismatch(self, mock_get_path, mock_validate):
        """Test main function with samplerate mismatch."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as binaural_file:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as ambience_file:
                # Create binaural file at 48000 Hz
                with wave.open(binaural_file.name, 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(48000)
                    wf.writeframes(b'\x00' * 48000 * 2 * 2)
                
                # Create ambience file at 44100 Hz
                with wave.open(ambience_file.name, 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(44100)
                    wf.writeframes(b'\x00' * 44100 * 2 * 2)
                
                mock_validate.return_value = True
                mock_get_path.return_value = Path(ambience_file.name)
                
                try:
                    with pytest.raises(SystemExit, match="Sample rate mismatch"):
                        main(["--binaural", binaural_file.name, "--ambient", "campfire"])
                finally:
                    os.unlink(binaural_file.name)
                    os.unlink(ambience_file.name)
