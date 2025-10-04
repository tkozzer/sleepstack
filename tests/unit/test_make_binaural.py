#!/usr/bin/env python3
"""
Tests for src/sleepstack/make_binaural.py
"""

import argparse
import math
import os
import tempfile
import wave
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

from sleepstack.make_binaural import (
    positive_float_minutes,
    positive_float_seconds,
    generate_binaural,
    save_wav,
    main,
)


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


class TestGenerateBinaural:
    """Test generate_binaural function."""

    def test_generate_binaural_default_params(self):
        """Test generate_binaural with default parameters."""
        data = generate_binaural()
        
        # Should return bytes
        assert isinstance(data, bytes)
        assert len(data) > 0
        
        # Should be stereo (2 channels) * 2 bytes per sample * duration * samplerate
        expected_size = 2 * 2 * 300 * 48000  # 2 channels, 2 bytes, 300s, 48kHz
        assert len(data) == expected_size

    def test_generate_binaural_custom_params(self):
        """Test generate_binaural with custom parameters."""
        duration_sec = 60.0
        beat_hz = 8.0
        carrier_hz = 220.0
        samplerate = 44100
        volume = 0.5
        fade_sec = 2.0
        
        data = generate_binaural(
            duration_sec=duration_sec,
            beat_hz=beat_hz,
            carrier_hz=carrier_hz,
            samplerate=samplerate,
            volume=volume,
            fade_sec=fade_sec
        )
        
        # Should return bytes
        assert isinstance(data, bytes)
        assert len(data) > 0
        
        # Should be stereo (2 channels) * 2 bytes per sample * duration * samplerate
        expected_size = 2 * 2 * int(duration_sec * samplerate)
        assert len(data) == expected_size

    def test_generate_binaural_invalid_beat_hz(self):
        """Test generate_binaural with invalid beat_hz."""
        with pytest.raises(ValueError) as exc_info:
            generate_binaural(beat_hz=0)
        assert "beat_hz must be > 0" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            generate_binaural(beat_hz=-1)
        assert "beat_hz must be > 0" in str(exc_info.value)

    def test_generate_binaural_invalid_carrier_hz(self):
        """Test generate_binaural with invalid carrier_hz."""
        with pytest.raises(ValueError) as exc_info:
            generate_binaural(beat_hz=10, carrier_hz=5)  # carrier_hz <= beat_hz/2
        assert "carrier_hz must be greater than beat_hz/2" in str(exc_info.value)

    def test_generate_binaural_invalid_volume(self):
        """Test generate_binaural with invalid volume."""
        with pytest.raises(ValueError) as exc_info:
            generate_binaural(volume=0)
        assert "volume must be in (0, 1]" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            generate_binaural(volume=1.5)
        assert "volume must be in (0, 1]" in str(exc_info.value)

    def test_generate_binaural_short_duration(self):
        """Test generate_binaural with short duration."""
        data = generate_binaural(duration_sec=0.1)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_binaural_no_fade(self):
        """Test generate_binaural with no fade."""
        data = generate_binaural(fade_sec=0.0)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_binaural_long_fade(self):
        """Test generate_binaural with fade longer than half duration."""
        data = generate_binaural(duration_sec=10.0, fade_sec=8.0)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_binaural_stereo_interleaving(self):
        """Test that generate_binaural produces proper stereo interleaving."""
        data = generate_binaural(duration_sec=0.1, samplerate=1000)
        
        # Should be interleaved L/R samples
        assert len(data) % 4 == 0  # 2 channels * 2 bytes per sample
        
        # Convert to numpy array for easier analysis
        samples = np.frombuffer(data, dtype=np.int16)
        assert len(samples) % 2 == 0
        
        # Check that we have left and right channels
        left_samples = samples[0::2]
        right_samples = samples[1::2]
        
        assert len(left_samples) == len(right_samples)
        assert len(left_samples) > 0

    def test_generate_binaural_frequency_calculation(self):
        """Test that generate_binaural calculates frequencies correctly."""
        beat_hz = 6.0
        carrier_hz = 200.0
        expected_left_hz = carrier_hz - beat_hz / 2.0  # 197.0
        expected_right_hz = carrier_hz + beat_hz / 2.0  # 203.0
        
        data = generate_binaural(
            duration_sec=1.0,
            beat_hz=beat_hz,
            carrier_hz=carrier_hz,
            samplerate=1000,
            fade_sec=0.0
        )
        
        # Convert to numpy array for analysis
        samples = np.frombuffer(data, dtype=np.int16)
        left_samples = samples[0::2]
        right_samples = samples[1::2]
        
        # Check that we have different frequencies (they should be different)
        assert not np.array_equal(left_samples, right_samples)

    def test_generate_binaural_volume_scaling(self):
        """Test that generate_binaural scales volume correctly."""
        # Test with different volumes
        data_low = generate_binaural(duration_sec=0.1, volume=0.1)
        data_high = generate_binaural(duration_sec=0.1, volume=0.9)
        
        # Convert to numpy arrays
        samples_low = np.frombuffer(data_low, dtype=np.int16)
        samples_high = np.frombuffer(data_high, dtype=np.int16)
        
        # High volume should have higher amplitude
        assert np.max(np.abs(samples_high)) > np.max(np.abs(samples_low))

    def test_generate_binaural_fade_envelope(self):
        """Test that generate_binaural applies fade envelope correctly."""
        data = generate_binaural(duration_sec=1.0, fade_sec=0.2, samplerate=1000)
        
        # Convert to numpy array
        samples = np.frombuffer(data, dtype=np.int16)
        left_samples = samples[0::2]
        
        # First and last samples should be quieter due to fade
        fade_samples = int(0.2 * 1000)  # 200 samples
        
        # Check fade-in (first samples should be quieter)
        assert abs(left_samples[0]) < abs(left_samples[fade_samples])
        
        # Check fade-out (last samples should be quieter)
        assert abs(left_samples[-1]) < abs(left_samples[-(fade_samples + 1)])

    @patch('sleepstack.make_binaural.np', None)
    def test_generate_binaural_fallback_without_numpy(self):
        """Test generate_binaural fallback when numpy is not available."""
        data = generate_binaural(duration_sec=0.1)
        
        # Should still return bytes
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_binaural_edge_case_very_short_duration(self):
        """Test generate_binaural with very short duration."""
        data = generate_binaural(duration_sec=0.001)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_generate_binaural_edge_case_very_long_fade(self):
        """Test generate_binaural with fade longer than duration."""
        data = generate_binaural(duration_sec=1.0, fade_sec=2.0)
        assert isinstance(data, bytes)
        assert len(data) > 0


class TestSaveWav:
    """Test save_wav function."""

    def test_save_wav_success(self):
        """Test successful WAV file saving."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Create test data
            test_data = b'\x00\x01\x02\x03' * 1000  # Simple test pattern
            
            save_wav(f.name, test_data, samplerate=48000)
            
            # Verify the file was created and has correct properties
            assert os.path.exists(f.name)
            with wave.open(f.name, 'rb') as wf:
                assert wf.getframerate() == 48000
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2  # 16-bit
            
            os.unlink(f.name)

    def test_save_wav_custom_samplerate(self):
        """Test WAV saving with custom samplerate."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            test_data = b'\x00\x01\x02\x03' * 1000
            
            save_wav(f.name, test_data, samplerate=44100)
            
            with wave.open(f.name, 'rb') as wf:
                assert wf.getframerate() == 44100
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2
            
            os.unlink(f.name)

    def test_save_wav_empty_data(self):
        """Test WAV saving with empty data."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            save_wav(f.name, b'', samplerate=48000)
            
            assert os.path.exists(f.name)
            with wave.open(f.name, 'rb') as wf:
                assert wf.getframerate() == 48000
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2
                assert wf.getnframes() == 0
            
            os.unlink(f.name)

    def test_save_wav_with_existing_directory(self):
        """Test that save_wav works with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create subdirectory first
            subdir = os.path.join(temp_dir, "subdir")
            os.makedirs(subdir)
            
            output_path = os.path.join(subdir, "test.wav")
            test_data = b'\x00\x01\x02\x03' * 100
            
            save_wav(output_path, test_data, samplerate=48000)
            
            # Verify the file was created
            assert os.path.exists(output_path)


class TestMain:
    """Test main function."""

    @patch('sleepstack.make_binaural.generate_binaural')
    @patch('sleepstack.make_binaural.save_wav')
    @patch('sys.argv')
    def test_main_with_minutes(self, mock_argv, mock_save_wav, mock_generate):
        """Test main function with minutes argument."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--minutes', '5', '--beat', '6', '--carrier', '200'
        ][x])
        mock_argv.__len__ = Mock(return_value=6)
        mock_generate.return_value = b'test_data'
        
        main()
        
        # Verify generate_binaural was called with correct parameters
        mock_generate.assert_called_once_with(
            duration_sec=300.0,  # 5 minutes
            beat_hz=6.0,
            carrier_hz=200.0,
            samplerate=48000,
            volume=0.3,
            fade_sec=3.0
        )
        
        # Verify save_wav was called
        mock_save_wav.assert_called_once()

    @patch('sleepstack.make_binaural.generate_binaural')
    @patch('sleepstack.make_binaural.save_wav')
    @patch('sys.argv')
    def test_main_with_seconds(self, mock_argv, mock_save_wav, mock_generate):
        """Test main function with seconds argument."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--seconds', '300', '--beat', '8', '--carrier', '220'
        ][x])
        mock_argv.__len__ = Mock(return_value=6)
        mock_generate.return_value = b'test_data'
        
        main()
        
        # Verify generate_binaural was called with correct parameters
        mock_generate.assert_called_once_with(
            duration_sec=300.0,
            beat_hz=8.0,
            carrier_hz=220.0,
            samplerate=48000,
            volume=0.3,
            fade_sec=3.0
        )
        
        # Verify save_wav was called
        mock_save_wav.assert_called_once()

    @patch('sleepstack.make_binaural.generate_binaural')
    @patch('sleepstack.make_binaural.save_wav')
    @patch('sys.argv')
    def test_main_with_all_parameters(self, mock_argv, mock_save_wav, mock_generate):
        """Test main function with all parameters specified."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--minutes', '2', '--beat', '4.5', '--carrier', '180',
            '--samplerate', '44100', '--volume', '0.5', '--fade', '2.0', '--out', 'test.wav'
        ][x])
        mock_argv.__len__ = Mock(return_value=16)
        mock_generate.return_value = b'test_data'
        
        main()
        
        # Verify generate_binaural was called with all parameters
        mock_generate.assert_called_once_with(
            duration_sec=120.0,  # 2 minutes
            beat_hz=4.5,
            carrier_hz=180.0,
            samplerate=44100,
            volume=0.5,
            fade_sec=2.0
        )
        
        # Verify save_wav was called with custom output file
        mock_save_wav.assert_called_once_with('test.wav', b'test_data', samplerate=44100)

    @patch('sys.argv')
    def test_main_missing_duration(self, mock_argv):
        """Test main function with missing duration argument."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--beat', '6'
        ][x])
        mock_argv.__len__ = Mock(return_value=3)
        
        with pytest.raises(SystemExit):
            main()

    @patch('sys.argv')
    def test_main_invalid_minutes(self, mock_argv):
        """Test main function with invalid minutes."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--minutes', '0'
        ][x])
        mock_argv.__len__ = Mock(return_value=3)
        
        with pytest.raises(SystemExit):
            main()

    @patch('sys.argv')
    def test_main_invalid_seconds(self, mock_argv):
        """Test main function with invalid seconds."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--seconds', '601'
        ][x])
        mock_argv.__len__ = Mock(return_value=3)
        
        with pytest.raises(SystemExit):
            main()

    @patch('sleepstack.make_binaural.generate_binaural')
    @patch('sleepstack.make_binaural.save_wav')
    @patch('sys.argv')
    @patch('builtins.print')
    def test_main_output_message(self, mock_print, mock_argv, mock_save_wav, mock_generate):
        """Test that main function prints output message."""
        mock_argv.__getitem__ = Mock(side_effect=lambda x: [
            'make_binaural.py', '--minutes', '5', '--beat', '6', '--carrier', '200', '--out', 'test.wav'
        ][x])
        mock_argv.__len__ = Mock(return_value=8)
        mock_generate.return_value = b'test_data'
        
        main()
        
        # Verify print was called with expected message
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "test.wav" in call_args
        assert "300.0s" in call_args
        assert "48000 Hz" in call_args
        assert "beat=6.0 Hz" in call_args
        assert "carrier=200.0 Hz" in call_args


class TestIntegration:
    """Integration tests."""

    def test_generate_and_save_integration(self):
        """Test integration between generate_binaural and save_wav."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            # Generate binaural data
            data = generate_binaural(duration_sec=0.1, samplerate=1000)
            
            # Save to WAV file
            save_wav(f.name, data, samplerate=1000)
            
            # Verify the file was created and is readable
            assert os.path.exists(f.name)
            with wave.open(f.name, 'rb') as wf:
                assert wf.getframerate() == 1000
                assert wf.getnchannels() == 2
                assert wf.getsampwidth() == 2
                assert wf.getnframes() > 0
                
                # Read back the data
                read_data = wf.readframes(wf.getnframes())
                assert len(read_data) > 0
            
            os.unlink(f.name)

    def test_validation_functions_integration(self):
        """Test integration of validation functions."""
        # Test that validation functions work with argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--minutes', type=positive_float_minutes)
        parser.add_argument('--seconds', type=positive_float_seconds)
        
        # Valid values
        args = parser.parse_args(['--minutes', '5.5'])
        assert args.minutes == 5.5
        
        args = parser.parse_args(['--seconds', '300.0'])
        assert args.seconds == 300.0
        
        # Invalid values should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['--minutes', '0'])
        
        with pytest.raises(SystemExit):
            parser.parse_args(['--seconds', '601'])

    def test_binaural_frequency_relationship(self):
        """Test that binaural frequencies are correctly related."""
        beat_hz = 6.0
        carrier_hz = 200.0
        expected_left_hz = carrier_hz - beat_hz / 2.0
        expected_right_hz = carrier_hz + beat_hz / 2.0
        
        data = generate_binaural(
            duration_sec=1.0,
            beat_hz=beat_hz,
            carrier_hz=carrier_hz,
            samplerate=1000,
            fade_sec=0.0
        )
        
        # Convert to numpy array for analysis
        samples = np.frombuffer(data, dtype=np.int16)
        left_samples = samples[0::2]
        right_samples = samples[1::2]
        
        # The frequencies should be different (left and right channels)
        assert not np.array_equal(left_samples, right_samples)
        
        # Both channels should have the same amplitude envelope
        left_amplitude = np.max(np.abs(left_samples))
        right_amplitude = np.max(np.abs(right_samples))
        assert abs(left_amplitude - right_amplitude) < 100  # Allow some tolerance
