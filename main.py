#!/usr/bin/env python3
"""
main.py — one-command pipeline:
1) Generate a binaural bed by vibe & duration
2) Mix with ambience (e.g., campfire)
3) Write to sounds/binaural/mix/ (or --out)

Required:
  --vibe <name>          (e.g., calm, deep, soothe, meditate, airy, warm, focus, flow, alert)
  --minutes/-m or --seconds/-s
  exactly one of:
    --ambient/-a campfire
    --ambience-file <WAV path>

Examples:
  python main.py --vibe calm -a campfire -m 5
  python main.py --vibe deep --ambience-file sounds/ambient/campfire/campfire_10m.wav -m 10

Optional highlights:
  --beat, --carrier, --samplerate, --volume, --fade, --loop    # binaural generation
  --binaural-out <WAV>                                        # where to save the raw binaural (default auto path)
  --binaural-db, --ambience-db, --ambience-fade               # mixing levels/fade
  --out <WAV>                                                 # final mixed output path

Assumptions:
- Repo layout has:
  - make_binaural.py (with generate_binaural() and save_wav())
  - sounds/ambient/campfire/{campfire_1m.wav, campfire_5m.wav, campfire_10m.wav}
- No resampling here. Keep all audio at the same samplerate (e.g., 48000 Hz).
- Requires numpy for mixing.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import wave
from dataclasses import dataclass
from typing import Tuple, Optional

import numpy as np

# ---------- Helpers for dynamic imports ----------


def _module_from_path(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _repo_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _sounds_dir(*parts: str) -> str:
    return os.path.join(_repo_root(), "sounds", *parts)


# ---------- Presets (vibes) ----------


@dataclass
class Preset:
    beat: float
    carrier: float
    samplerate: int = 48000
    volume: float = 0.28
    fade: float = 2.0
    desc: str = ""


PRESETS = {
    # Night-safe
    "deep": Preset(4.5, 180, 48000, 0.25, 2.0, "Deeper settle (theta–delta border)."),
    "calm": Preset(6.0, 200, 48000, 0.28, 2.0, "Mid-theta calm & clear (default)."),
    "soothe": Preset(5.0, 190, 48000, 0.26, 2.0, "Gentle settle."),
    "dream": Preset(4.0, 170, 48000, 0.24, 2.0, "Very sleepy."),
    # Awake/focus (not bedtime)
    "focus": Preset(6.5, 210, 48000, 0.27, 2.0, "Light focus."),
    "flow": Preset(7.0, 220, 48000, 0.27, 2.0, "Creative energy."),
    "alert": Preset(8.0, 240, 48000, 0.26, 2.0, "Alpha–theta edge; peppy."),
    "meditate": Preset(5.5, 200, 48000, 0.26, 2.0, "Balanced presence."),
    "warm": Preset(5.5, 180, 48000, 0.27, 2.0, "Warmer timbre; good under fire/rain."),
    "airy": Preset(
        6.0, 260, 48000, 0.26, 2.0, "Brighter; leaves space for deep voices."
    ),
}

ALIASES = {
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


def resolve_vibe(v: str) -> str:
    key = (v or "").strip().lower()
    if key in PRESETS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    # startswith fuzzy
    for k in PRESETS:
        if k.startswith(key):
            return k
    raise SystemExit(f"Unknown vibe '{v}'. Choices: {', '.join(PRESETS.keys())}")


# ---------- Audio I/O (WAV, 16-bit PCM) ----------


def read_wav(path: str) -> Tuple[np.ndarray, int, int]:
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        if sw != 2:
            raise SystemExit(f"{path}: only 16-bit PCM supported (got {sw*8}-bit).")
        frames = wf.getnframes()
        raw = wf.readframes(frames)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float64).reshape(-1, ch)
    data /= 32767.0
    return data, sr, ch


def write_wav(path: str, data: np.ndarray, sr: int) -> None:
    y = np.clip(data, -1.0, 1.0)
    y_i16 = (y * 32767.0).astype(np.int16)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(y_i16.tobytes())


def ensure_stereo(x: np.ndarray) -> np.ndarray:
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def db_to_gain(db: float) -> float:
    return 10.0 ** (db / 20.0)


def apply_fade(x: np.ndarray, sr: int, fade_sec: float) -> np.ndarray:
    if fade_sec <= 0:
        return x
    n = x.shape[0]
    f = min(int(fade_sec * sr), n // 2)
    if f <= 0:
        return x
    fi = np.linspace(0.0, 1.0, f)
    fo = np.linspace(1.0, 0.0, f)
    y = x.copy()
    y[:f, :] *= fi[:, None]
    y[-f:, :] *= fo[:, None]
    return y


# ---------- Binaural generation via make_binaural.py ----------


def generate_binaural_wav(
    duration_sec: float,
    preset: Preset,
    vibe_key: str,
    *,
    beat: Optional[float] = None,
    carrier: Optional[float] = None,
    samplerate: Optional[int] = None,
    volume: Optional[float] = None,
    fade: Optional[float] = None,
    loop: bool = False,
    out_path: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Import make_binaural.py next to this file and call generate_binaural() + save_wav().
    Returns (binaural_path, sr).
    """
    root = _repo_root()
    make_path = os.path.join(root, "make_binaural.py")
    mod = _module_from_path("make_binaural", make_path)
    if (
        mod is None
        or not hasattr(mod, "generate_binaural")
        or not hasattr(mod, "save_wav")
    ):
        raise SystemExit(
            "Could not import make_binaural.py (need generate_binaural() and save_wav())."
        )

    # Resolve params
    b = beat if beat is not None else preset.beat
    c = carrier if carrier is not None else preset.carrier
    sr = samplerate if samplerate is not None else preset.samplerate
    vol = volume if volume is not None else preset.volume
    fd = 0.0 if loop else (fade if fade is not None else preset.fade)

    # Output path
    if out_path:
        binaural_path = out_path
    else:
        dur_tag = (
            f"{int(duration_sec // 60)}min"
            if duration_sec % 60 == 0
            else f"{int(duration_sec)}sec"
        )
        base = f"{vibe_key}_beat{b:g}_car{c:g}_{dur_tag}.wav"
        binaural_path = os.path.join(_sounds_dir("binaural"), base)
        os.makedirs(os.path.dirname(binaural_path), exist_ok=True)

    data = mod.generate_binaural(
        duration_sec=duration_sec,
        beat_hz=b,
        carrier_hz=c,
        samplerate=sr,
        volume=vol,
        fade_sec=fd,
    )
    mod.save_wav(binaural_path, data, samplerate=sr)
    print(
        f"✓ Binaural: {binaural_path} ({duration_sec:.1f}s @ {sr} Hz, beat={b} Hz, carrier={c} Hz, vol={vol}, fade={fd})"
    )
    return binaural_path, sr


# ---------- Ambience selection (campfire) ----------


def choose_campfire_clip(target_samples: int, sr: int) -> str:
    """Pick longest clip <= target (10m, 5m, else 1m) under sounds/ambient/campfire/"""
    camp_dir = _sounds_dir("ambient", "campfire")
    options = [
        ("campfire_10m.wav", 600),
        ("campfire_5m.wav", 300),
        ("campfire_1m.wav", 60),
    ]
    target_sec = target_samples / sr
    chosen = "campfire_1m.wav"
    for name, secs in options:
        if target_sec >= secs:
            chosen = name
            break
    path = os.path.join(camp_dir, chosen)
    if not os.path.exists(path):
        raise SystemExit(f"Missing ambience clip: {path}")
    return path


# ---------- Mixing ----------


def mix_binaural_and_ambience(
    binaural_path: str,
    ambience_path: str,
    *,
    binaural_db: float = -15.0,
    ambience_db: float = -21.0,
    ambience_fade: float = 2.0,
    out_path: Optional[str] = None,
) -> str:
    b, sr_b, ch_b = read_wav(binaural_path)
    a, sr_a, ch_a = read_wav(ambience_path)
    if ch_b != 2:
        raise SystemExit("Binaural must be stereo (2 channels).")
    if sr_b != sr_a:
        raise SystemExit(
            f"Samplerate mismatch: binaural={sr_b}, ambience={sr_a}. Resample externally."
        )

    b = ensure_stereo(b)
    a = ensure_stereo(a)

    # Tile/trim ambience to exact length
    n = b.shape[0]
    if a.shape[0] < n:
        reps = int(np.ceil(n / a.shape[0]))
        a = np.tile(a, (reps, 1))[:n, :]
    else:
        a = a[:n, :]

    # Ambience fade only
    a = apply_fade(a, sr_b, ambience_fade)

    # Gains
    g_b = db_to_gain(binaural_db)
    g_a = db_to_gain(ambience_db)
    mix = b * g_b + a * g_a

    # Soft limit
    peak = float(np.max(np.abs(mix)))
    if peak > 0.999:
        mix = mix / peak * 0.999

    # Output path
    if out_path:
        out = out_path
    else:
        base = os.path.splitext(os.path.basename(binaural_path))[0]
        amb_tag = os.path.splitext(os.path.basename(ambience_path))[0]
        out = os.path.join(_sounds_dir("binaural", "mix"), f"{base}__{amb_tag}.wav")
        os.makedirs(os.path.dirname(out), exist_ok=True)

    write_wav(out, mix, sr_b)
    print(
        f"✓ Mixed : {out} @ {sr_b} Hz  (binaural {binaural_db} dB, ambience {ambience_db} dB, fade {ambience_fade}s)"
    )
    return out


# ---------- CLI ----------


def positive_float(v: str) -> float:
    x = float(v)
    if x <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return x


def nonneg_float(v: str) -> float:
    x = float(v)
    if x < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return x


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="One-shot: generate binaural by vibe and mix with ambience."
    )
    # Required (user’s desired flow)
    ap.add_argument(
        "--vibe",
        required=True,
        help="Vibe name (e.g., calm, deep, soothe, meditate, airy, warm, focus, flow, alert)",
    )
    dur = ap.add_mutually_exclusive_group(required=True)
    dur.add_argument("--minutes", "-m", type=positive_float, help="Duration in minutes")
    dur.add_argument("--seconds", "-s", type=positive_float, help="Duration in seconds")
    amb = ap.add_mutually_exclusive_group(required=True)
    amb.add_argument(
        "--ambient",
        "-a",
        choices=["campfire"],
        help="Ambient keyword (currently: campfire)",
    )
    amb.add_argument(
        "--ambience-file", help="Explicit ambience WAV path (mono or stereo)"
    )

    # Optional binaural overrides
    ap.add_argument("--beat", type=positive_float, help="Override beat Hz")
    ap.add_argument("--carrier", type=positive_float, help="Override carrier Hz")
    ap.add_argument("--samplerate", type=int, help="Override samplerate (e.g., 48000)")
    ap.add_argument(
        "--volume", type=positive_float, help="Override output volume scalar (0–1]"
    )
    ap.add_argument("--fade", type=nonneg_float, help="Override binaural fade sec")
    ap.add_argument(
        "--loop", action="store_true", help="Set binaural fade=0 for seamless looping"
    )

    # Paths
    ap.add_argument(
        "--binaural-out",
        help="Where to save the generated binaural WAV (default: sounds/binaural/<auto-name>.wav)",
    )
    ap.add_argument(
        "--out",
        help="Final mixed WAV path (default: sounds/binaural/mix/<binaural>__<ambience>.wav)",
    )

    # Mix levels
    ap.add_argument(
        "--binaural-db",
        type=float,
        default=-15.0,
        help="Binaural level in dBFS (default -15)",
    )
    ap.add_argument(
        "--ambience-db",
        type=float,
        default=-21.0,
        help="Ambience level in dBFS (default -21)",
    )
    ap.add_argument(
        "--ambience-fade",
        type=float,
        default=2.0,
        help="Ambience fade in/out seconds (default 2.0)",
    )

    args = ap.parse_args(argv)

    # Resolve vibe
    vibe_key = resolve_vibe(args.vibe)
    preset = PRESETS[vibe_key]

    # Duration seconds
    duration_sec = args.minutes * 60.0 if args.minutes is not None else args.seconds

    # 1) Generate binaural
    binaural_path, sr_b = generate_binaural_wav(
        duration_sec=duration_sec,
        preset=preset,
        vibe_key=vibe_key,
        beat=args.beat,
        carrier=args.carrier,
        samplerate=args.samplerate,
        volume=args.volume,
        fade=args.fade,
        loop=args.loop,
        out_path=args.binaural_out,
    )

    # 2) Resolve ambience path
    if args.ambient:
        # Auto-pick campfire clip by binaural length
        # Read binaural to get length in samples
        b, sr_check, ch = read_wav(binaural_path)
        if sr_check != sr_b:
            raise SystemExit("Internal samplerate mismatch after generation.")
        target_samples = b.shape[0]
        ambience_path = choose_campfire_clip(target_samples, sr_b)
    else:
        ambience_path = args.ambience_file
        if not os.path.exists(ambience_path):
            raise SystemExit(f"Ambience file not found: {ambience_path}")

    # 3) Mix
    mix_path = mix_binaural_and_ambience(
        binaural_path=binaural_path,
        ambience_path=ambience_path,
        binaural_db=args.binaural_db,
        ambience_db=args.ambience_db,
        ambience_fade=args.ambience_fade,
        out_path=args.out,
    )

    print("\nAll done ✅")
    print(f"Binaural : {binaural_path}")
    print(f"Ambience : {ambience_path}")
    print(f"Mixed    : {mix_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
