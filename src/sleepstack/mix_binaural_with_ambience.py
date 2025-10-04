#!/usr/bin/env python3
"""
mix_binaural_with_ambience.py
Mix a stereo binaural WAV with an ambience bed (e.g., campfire), preserving stereo separation.

Flow you asked for:
1) Record narration in GarageBand.
2) Generate binaural WAV matching narration length.
3) Run THIS script to auto-mix binaural + ambience (e.g., campfire) to a single WAV.
   - Auto-picks a suitable campfire clip (1m / 5m / 10m) and tiles/trims to match binaural length.
   - Saves into build/mix/ by default (or use --out for a custom location).

Usage (auto-campfire):
  python mix_binaural_with_ambience.py \
    --binaural build/binaural/meta_core_theta4p5_5min.wav \
    --ambient campfire \
    --binaural-db -15 --ambience-db -21 --fade 2

Usage (explicit ambience file):
  python mix_binaural_with_ambience.py \
    --binaural build/binaural/meta_core_theta6_5min.wav \
    --ambience-file assets/ambience/campfire/campfire_1m.wav \
    --out build/mix/meta_core_theta6_5min__campfire.wav

Notes:
- Keep all files at the same samplerate (e.g., 48000 Hz) to avoid resampling here.
- If ambience is mono, it will be duplicated to L/R; binaural MUST remain stereo.
- Output is 16-bit PCM stereo.
"""

from __future__ import annotations

import argparse
import os
import sys
import wave
import numpy as np
from typing import Tuple

from .ambient_manager import get_available_ambient_sounds, get_ambient_sound_path, validate_ambient_sound

# ---------- Utility ----------


def db_to_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def read_wav(path: str) -> Tuple[np.ndarray, int, int]:
    """Read 16-bit PCM WAV -> (float64 array in [-1,1], sr, channels)."""
    import time
    import os

    # Retry mechanism for file system synchronization issues in CI
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Check if file exists and has content
            if not os.path.exists(path):
                raise FileNotFoundError(f"File does not exist: {path}")

            file_size = os.path.getsize(path)
            if file_size == 0:
                raise ValueError(f"File is empty: {path}")

            with wave.open(path, "rb") as wf:
                sr = wf.getframerate()
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                if sw != 2:
                    raise SystemExit(f"{path}: Only 16-bit PCM supported (got {sw*8}-bit).")
                frames = wf.getnframes()
                raw = wf.readframes(frames)
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
            data = data.reshape(-1, ch)
            data /= 32767.0
            return data, sr, ch
        except Exception as e:
            if attempt < max_retries - 1:
                # Wait with longer delays for CI environments
                delay = 0.5 * (2**attempt)  # 0.5s, 1s, 2s, 4s
                print(f"Read attempt {attempt + 1} failed for {path}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                continue
            else:
                # Re-raise the original exception on final attempt
                print(f"All {max_retries} read attempts failed for {path}. Last error: {e}")
                raise e

    # This should never be reached, but satisfies mypy
    raise RuntimeError("Unexpected end of retry loop")


def write_wav(path: str, data: np.ndarray, sr: int) -> None:
    """Write float array in [-1,1] as 16-bit PCM stereo WAV."""
    y = np.clip(data, -1.0, 1.0)
    y_i16 = (y * 32767.0).astype(np.int16)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(y_i16.tobytes())


def ensure_stereo(x: np.ndarray) -> np.ndarray:
    if x.shape[1] == 2:
        return x
    return np.repeat(x, 2, axis=1)


def apply_fade(x: np.ndarray, sr: int, fade_sec: float) -> np.ndarray:
    """Linear fade in/out applied to ambience only."""
    if fade_sec <= 0:
        return x
    n = x.shape[0]
    f = min(int(fade_sec * sr), n // 2)
    if f <= 0:
        return x
    fade_in = np.linspace(0.0, 1.0, f)
    fade_out = np.linspace(1.0, 0.0, f)
    y = x.copy()
    y[:f, :] *= fade_in[:, None]
    y[-f:, :] *= fade_out[:, None]
    return y


def duration_sec(samples: int, sr: int) -> float:
    return samples / float(sr)


# ---------- Campfire Auto-Pick ----------


def project_root() -> str:
    """Get the project root directory (parent of src/)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def campfire_dir() -> str:
    return os.path.join(project_root(), "assets", "ambience", "campfire")


def choose_campfire_clip(target_samples: int, sr: int) -> str:
    """
    Always return the 1-minute campfire clip for automatic looping.
    The existing tiling mechanism will handle any duration.
    """
    chosen = "campfire_1m.wav"
    path = os.path.join(campfire_dir(), chosen)
    if not os.path.exists(path):
        raise SystemExit(
            f"Could not find {path}. Make sure your campfire clips are in assets/ambience/campfire/"
        )
    return path


# ---------- Mixer ----------


def mix_audio(
    binaural: np.ndarray,
    ambience: np.ndarray,
    sr: int,
    binaural_db: float,
    ambience_db: float,
    fade_sec: float,
) -> np.ndarray:
    """Stereo mix: binaural at level, ambience at level with optional fade, soft limit."""
    # Ensure shapes
    if binaural.shape[1] != 2:
        raise SystemExit("Binaural must be stereo to preserve the binaural effect.")
    ambience = ensure_stereo(ambience)

    # Match lengths by tiling or trimming ambience
    n = binaural.shape[0]
    if ambience.shape[0] < n:
        reps = int(np.ceil(n / ambience.shape[0]))
        ambience = np.tile(ambience, (reps, 1))[:n, :]
    else:
        ambience = ambience[:n, :]

    # Apply fade to ambience only
    ambience = apply_fade(ambience, sr, fade_sec)

    # Gain stage
    g_b = db_to_gain(binaural_db)
    g_a = db_to_gain(ambience_db)
    mix = binaural * g_b + ambience * g_a

    # Soft limiter (gentle)
    peak = float(np.max(np.abs(mix)))
    if peak > 0.999:
        mix = mix / peak * 0.999

    return mix


# ---------- Defaults & Paths ----------


def default_out_path(binaural_path: str, ambient_key: str | None) -> str:
    """
    Build a default output path under build/mix/
    Name: <binaural_basename>__<ambient>.wav  (ambient defaults to 'mix' if None)
    """
    root = project_root()
    out_dir = os.path.join(root, "build", "mix")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(binaural_path))[0]
    tag = ambient_key if ambient_key else "mix"
    return os.path.join(out_dir, f"{base}__{tag}.wav")


# ---------- CLI ----------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Mix a binaural WAV with ambience, preserving stereo separation."
    )
    ap.add_argument(
        "--binaural",
        required=True,
        help="Path to binaural WAV (stereo, same samplerate as ambience).",
    )
    # Choose either an ambient keyword (auto-pick clip) OR a specific ambience file
    ap.add_argument(
        "-a",
        "--ambient",
        help="Ambient keyword (e.g., campfire, rain, ocean). Use comma-separated list for multiple sounds.",
    )
    ap.add_argument("--ambience-file", help="Explicit ambience WAV path (mono or stereo).")
    ap.add_argument(
        "--out",
        help="Output WAV path. Default: build/mix/<binaural>__<ambient>.wav",
    )
    ap.add_argument(
        "--binaural-db",
        type=float,
        default=-15.0,
        help="Binaural level in dBFS (e.g., -15)",
    )
    ap.add_argument(
        "--ambience-db",
        type=float,
        default=-21.0,
        help="Ambience level in dBFS (e.g., -21)",
    )
    ap.add_argument(
        "--fade",
        type=float,
        default=2.0,
        help="Ambience fade in/out seconds (applied to ambience only)",
    )
    args = ap.parse_args(argv)

    if not os.path.exists(args.binaural):
        raise SystemExit(f"Binaural file not found: {args.binaural}")

    # Read binaural
    b, sr_b, ch_b = read_wav(args.binaural)
    if ch_b != 2:
        raise SystemExit("Binaural must be stereo (2 channels).")

    # Resolve ambience source
    ambience_path = None
    ambient_key = None
    if args.ambient and args.ambience_file:
        raise SystemExit("Use either --ambient or --ambience-file, not both.")
    if args.ambient:
        # Parse comma-separated ambient sounds
        ambient_names = [name.strip() for name in args.ambient.split(',')]
        
        # Validate all ambient sounds
        for name in ambient_names:
            if not validate_ambient_sound(name):
                available = get_available_ambient_sounds()
                raise SystemExit(f"Unknown ambient sound '{name}'. Available: {', '.join(available)}")
        
        # For now, use the first ambient sound (will be enhanced for multi-ambient support)
        ambient_key = ambient_names[0]
        ambience_path_obj = get_ambient_sound_path(ambient_key)
        if not ambience_path_obj:
            raise SystemExit(f"Ambient sound file not found: {ambient_key}")
        ambience_path = str(ambience_path_obj)
    elif args.ambience_file:
        ambience_path = args.ambience_file
    else:
        raise SystemExit("Provide --ambient <sound_name> or --ambience-file <path>")

    if not os.path.exists(ambience_path):
        raise SystemExit(f"Ambience file not found: {ambience_path}")

    # Read ambience
    a, sr_a, ch_a = read_wav(ambience_path)

    # Samplerate check (no resampling here)
    if sr_b != sr_a:
        raise SystemExit(
            f"Sample rate mismatch: binaural={sr_b}, ambience={sr_a}. "
            "Resample externally (e.g., ffmpeg -ar 48000) or regenerate to match."
        )

    # Mix
    out_data = mix_audio(
        binaural=b,
        ambience=a,
        sr=sr_b,
        binaural_db=args.binaural_db,
        ambience_db=args.ambience_db,
        fade_sec=args.fade,
    )

    # Output path
    out_path = args.out or default_out_path(
        args.binaural,
        ambient_key or os.path.splitext(os.path.basename(ambience_path))[0],
    )
    write_wav(out_path, out_data, sr_b)
    print(f"✓ Wrote {out_path} @ {sr_b} Hz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
