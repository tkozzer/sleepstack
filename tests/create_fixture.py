#!/usr/bin/env python3
"""
Create test fixture audio files for testing.
"""

import numpy as np
import wave
from pathlib import Path


def create_sine_wav(
    output_path: str, frequency: float = 440.0, duration: float = 1.0, sample_rate: int = 48000
) -> None:
    """Create a 1-second sine wave WAV file."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate sine wave
    sine_wave = np.sin(2 * np.pi * frequency * t)
    # Convert to 16-bit PCM
    sine_wave_i16 = (sine_wave * 32767.0).astype(np.int16)

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Write WAV file
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(sine_wave_i16.tobytes())


if __name__ == "__main__":
    # Create test fixtures
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    # Create a 1-second 440Hz sine wave (mono)
    create_sine_wav(str(fixtures_dir / "sine_440hz_1sec.wav"), frequency=440.0, duration=1.0)

    # Create a 1-second 220Hz sine wave (mono)
    create_sine_wav(str(fixtures_dir / "sine_220hz_1sec.wav"), frequency=220.0, duration=1.0)

    print(f"Created test fixtures in {fixtures_dir}")
