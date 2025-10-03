#!/usr/bin/env python3
"""
make_binaural.py — generate a stereo WAV binaural beats track.

Default is a theta-ish beat (6 Hz) at a 200 Hz carrier.
Left = carrier - beat/2, Right = carrier + beat/2

Examples:
  # 5 minutes, theta 6 Hz, 200 Hz carrier
  python make_binaural.py --minutes 5 --beat 6 --carrier 200 --out theta_6hz_5min.wav

  # 10 minutes, deeper theta 4.5 Hz, quieter volume
  python make_binaural.py --minutes 10 --beat 4.5 --carrier 180 --volume 0.2 --out theta_4p5hz_10min.wav
"""

import argparse, math, struct, wave, sys

try:
    import numpy as np
except ImportError:
    np = None  # Fallback when numpy is not available


def positive_float_minutes(v: str) -> float:
    x = float(v)
    if x <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    if x > 10:
        raise argparse.ArgumentTypeError("must be <= 10 minutes")
    return x


def positive_float_seconds(v: str) -> float:
    x = float(v)
    if x <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    if x > 600:  # 10 minutes * 60 seconds
        raise argparse.ArgumentTypeError("must be <= 600 seconds (10 minutes)")
    return x


def generate_binaural(
    duration_sec: float = 300.0,
    beat_hz: float = 6.0,
    carrier_hz: float = 200.0,
    samplerate: int = 48000,
    volume: float = 0.3,
    fade_sec: float = 3.0,
) -> bytes:
    """Return interleaved int16 stereo samples for a binaural beat track."""
    if beat_hz <= 0:
        raise ValueError("beat_hz must be > 0")
    if carrier_hz <= beat_hz / 2:
        raise ValueError("carrier_hz must be greater than beat_hz/2")
    if not (0.0 < volume <= 1.0):
        raise ValueError("volume must be in (0, 1]")

    n = int(duration_sec * samplerate)
    left_hz = carrier_hz - beat_hz / 2.0
    right_hz = carrier_hz + beat_hz / 2.0

    # Envelope (fade-in/out) to avoid clicks
    n_fade = int(max(0.0, min(fade_sec, duration_sec / 2.0)) * samplerate)

    if np is not None:
        t = np.arange(n, dtype=np.float64) / samplerate
        left = np.sin(2.0 * math.pi * left_hz * t)
        right = np.sin(2.0 * math.pi * right_hz * t)

        # Fade in/out envelope
        env = np.ones(n, dtype=np.float64)
        if n_fade > 0:
            fade_in = np.linspace(0.0, 1.0, n_fade, dtype=np.float64)
            fade_out = np.linspace(1.0, 0.0, n_fade, dtype=np.float64)
            env[:n_fade] *= fade_in
            env[-n_fade:] *= fade_out

        left *= env
        right *= env

        # Scale to int16
        peak = 32767 * volume
        left_i16 = np.clip((left * peak), -32767, 32767).astype(np.int16)
        right_i16 = np.clip((right * peak), -32767, 32767).astype(np.int16)

        # Interleave L/R
        stereo = np.empty(n * 2, dtype=np.int16)
        stereo[0::2] = left_i16
        stereo[1::2] = right_i16
        return bytes(stereo.tobytes())

    # ---- Fallback: pure stdlib (slower for long tracks, but fine) ----
    frames = bytearray()
    two_pi = 2.0 * math.pi
    peak = int(32767 * volume)

    def env_gain(i: int) -> float:
        if n_fade == 0:
            return 1.0
        if i < n_fade:
            return i / n_fade
        if i >= n - n_fade:
            return (n - i - 1) / n_fade
        return 1.0

    for i in range(n):
        t = i / samplerate
        l = math.sin(two_pi * left_hz * t) * env_gain(i)
        r = math.sin(two_pi * right_hz * t) * env_gain(i)
        li = max(-32767, min(32767, int(l * peak)))
        ri = max(-32767, min(32767, int(r * peak)))
        frames += struct.pack("<hh", li, ri)
    return bytes(frames)


def save_wav(path: str, data_bytes: bytes, samplerate: int = 48000) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(samplerate)
        wf.writeframes(data_bytes)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate a stereo binaural beats WAV.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--minutes", type=positive_float_minutes, help="Duration in minutes")
    g.add_argument("--seconds", type=positive_float_seconds, help="Duration in seconds")
    p.add_argument("--beat", type=float, default=6.0, help="Beat frequency in Hz (theta ~4–8)")
    p.add_argument(
        "--carrier", type=float, default=200.0, help="Carrier frequency in Hz (e.g., 180–300)"
    )
    p.add_argument(
        "--samplerate", type=int, default=48000, help="Sample rate (e.g., 44100 or 48000)"
    )
    p.add_argument("--volume", type=float, default=0.3, help="Output volume scalar (0–1]")
    p.add_argument("--fade", type=float, default=3.0, help="Fade in/out seconds")
    p.add_argument("--out", default="binaural.wav", help="Output WAV filename")
    args = p.parse_args()

    duration = (args.minutes * 60.0) if args.minutes is not None else args.seconds
    data = generate_binaural(
        duration_sec=duration,
        beat_hz=args.beat,
        carrier_hz=args.carrier,
        samplerate=args.samplerate,
        volume=args.volume,
        fade_sec=args.fade,
    )
    save_wav(args.out, data, samplerate=args.samplerate)
    print(
        f"Wrote {args.out} — {duration:.1f}s @ {args.samplerate} Hz | beat={args.beat} Hz, carrier={args.carrier} Hz"
    )


if __name__ == "__main__":
    main()
