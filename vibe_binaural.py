#!/usr/bin/env python3
"""
vibe_binaural.py — Plain-English presets that route to make_binaural.py

Usage examples:
  # 5-min "deep settle" (theta-delta border), seamless loop
  python vibe_binaural.py --vibe deep --minutes 5 --loop --out meta_core_deep_5m.wav

  # 5-min calm default (mid-theta), slightly louder
  python vibe_binaural.py --vibe calm --minutes 5 --volume 0.32 --out calm_theta_5m.wav

  # Alert-ish alpha/theta edge for daytime pep talk (NOT for sleep)
  python vibe_binaural.py --vibe alert --minutes 5 --out alert_edge_5m.wav

  # List vibes & exact settings
  python vibe_binaural.py --list

Notes:
- “Loop” sets fade=0 for seamless looping. For single-play tracks, leave fade at preset (usually 2s).
- You can override any preset parameter via flags (--beat, --carrier, --samplerate, --volume, --fade).
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass

# ---------- Presets ----------
# Each vibe maps to: beat Hz (binaural difference), carrier Hz, samplerate, volume, fade seconds.
# Keep beats in ~4–10 Hz for comfort; lower beats (≈4–5) feel sleepier, higher (≈7–9) feel more alert.


@dataclass
class Preset:
    beat: float
    carrier: float
    samplerate: int = 48000
    volume: float = 0.28
    fade: float = 2.0
    description: str = ""


PRESETS = {
    # Night-safe presets first
    "deep": Preset(
        beat=4.5,
        carrier=180,
        volume=0.25,
        fade=2,
        description="Deeper settle (theta–delta border). Soothing; may get drowsy sooner.",
    ),
    "calm": Preset(
        beat=6.0,
        carrier=200,
        volume=0.28,
        fade=2,
        description="Mid-theta calm & clear. Great under narration.",
    ),
    "soothe": Preset(
        beat=5.0,
        carrier=190,
        volume=0.26,
        fade=2,
        description="Gentle settle (softer than calm, lighter than deep).",
    ),
    "dream": Preset(
        beat=4.0,
        carrier=170,
        volume=0.24,
        fade=2,
        description="Very sleepy. Use when you want to drift off near the end.",
    ),
    # Day/nap/focus-ish (not ideal for falling asleep during instructions)
    "focus": Preset(
        beat=6.5,
        carrier=210,
        volume=0.27,
        fade=2,
        description="Light, steady focus. Good for scripting practice when awake.",
    ),
    "flow": Preset(
        beat=7.0,
        carrier=220,
        volume=0.27,
        fade=2,
        description="Slightly more energy; creative flow vibe.",
    ),
    "alert": Preset(
        beat=8.0,
        carrier=240,
        volume=0.26,
        fade=2,
        description="Alpha–theta edge; peppy. Use for daytime pep talks.",
    ),
    "meditate": Preset(
        beat=5.5,
        carrier=200,
        volume=0.26,
        fade=2,
        description="Balanced presence; good for breath work.",
    ),
    "warm": Preset(
        beat=5.5,
        carrier=180,
        volume=0.27,
        fade=2,
        description="Warmer timbre. Nice under fireplace/rain.",
    ),
    "airy": Preset(
        beat=6.0,
        carrier=260,
        volume=0.26,
        fade=2,
        description="Brighter timbre that leaves more space for deep voices.",
    ),
}

# Aliases map to one of the keys above
ALIASES = {
    "sleep": "deep",
    "deeper": "deep",
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


# ---------- Import or subprocess wiring ----------
def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _module_from_path(module_name: str, path: str):
    """Load a module from an explicit file path."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    return None


def _import_make_binaural():
    """
    Try to import make_binaural.py as a module next to this script.
    Returns the module or None.
    """
    script_dir = _script_dir()
    candidate = os.path.join(script_dir, "make_binaural.py")

    # Try local file path first
    if os.path.exists(candidate):
        try:
            return _module_from_path("make_binaural", candidate)
        except Exception:
            pass

    # Fallback: try regular import if in PYTHONPATH
    try:
        return importlib.import_module("make_binaural")
    except Exception:
        return None


def _call_make_binaural_subprocess(
    minutes: float | None,
    seconds: float | None,
    beat: float,
    carrier: float,
    samplerate: int,
    volume: float,
    fade: float,
    out: str,
) -> int:
    """Invoke make_binaural.py via subprocess with the resolved parameters."""
    script_dir = _script_dir()
    make_path = os.path.join(script_dir, "make_binaural.py")
    if not os.path.exists(make_path):
        # Try to call by module in case it's installed
        make_path = "make_binaural.py"

    cmd = [sys.executable, make_path]
    if minutes is not None:
        cmd += ["--minutes", f"{minutes}"]
    else:
        cmd += ["--seconds", f"{seconds}"]
    cmd += [
        "--beat",
        f"{beat}",
        "--carrier",
        f"{carrier}",
        "--samplerate",
        f"{samplerate}",
        "--volume",
        f"{volume}",
        "--fade",
        f"{fade}",
        "--out",
        out,
    ]

    print("→ Running:", " ".join(cmd))
    return subprocess.call(cmd)


# ---------- Helpers ----------
def resolve_vibe(name: str | None) -> str:
    if not name:
        return "calm"
    key = name.strip().lower()
    if key in PRESETS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    # fuzzy-ish: try startswith
    for k in PRESETS.keys():
        if k.startswith(key):
            return k
    raise SystemExit(f"Unknown vibe '{name}'. Use --list to see options.")


def list_vibes():
    print("Available vibes:\n")
    for k, p in PRESETS.items():
        print(
            f"  {k:<9} beat={p.beat:>4} Hz  carrier={p.carrier:>3} Hz  "
            f"samplerate={p.samplerate}  volume={p.volume:.2f}  fade={p.fade:.1f}"
        )
        if p.description:
            print(f"           {p.description}")
    if ALIASES:
        print("\nAliases:")
        for a, k in ALIASES.items():
            print(f"  {a:<9} → {k}")


def positive_float(x: str) -> float:
    v = float(x)
    if v <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return v


def nonneg_float(x: str) -> float:
    v = float(x)
    if v < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return v


# ---------- Main ----------
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Generate a binaural-beats WAV using human-friendly vibes that map to make_binaural.py presets."
    )
    p.add_argument("--vibe", help="One of: " + ", ".join(PRESETS.keys()))
    p.add_argument("--list", action="store_true", help="List vibes and exit")

    # Duration
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--minutes", "-m", type=positive_float, help="Duration in minutes")
    g.add_argument("--seconds", "-s", type=positive_float, help="Duration in seconds")

    # Overrides
    p.add_argument("--beat", type=positive_float, help="Override beat frequency in Hz")
    p.add_argument(
        "--carrier", type=positive_float, help="Override carrier frequency in Hz"
    )
    p.add_argument(
        "--samplerate", type=int, help="Override samplerate (e.g., 44100 or 48000)"
    )
    p.add_argument(
        "--volume", type=positive_float, help="Override output volume scalar (0–1]"
    )
    p.add_argument("--fade", type=nonneg_float, help="Override fade in/out seconds")
    p.add_argument(
        "--out", default=None, help="Output filename (e.g., theta_6hz_5min.wav)"
    )
    p.add_argument(
        "--loop", action="store_true", help="Set fade=0 for seamless looping"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved settings and exit without generating",
    )

    args = p.parse_args(argv)

    if args.list:
        list_vibes()
        return 0

    vibe_key = resolve_vibe(args.vibe or "calm")
    preset = PRESETS[vibe_key]

    # Resolve duration
    if args.minutes is None and args.seconds is None:
        duration_sec = 300.0  # default 5 minutes
        used_minutes = 5.0
        used_seconds = None
    else:
        if args.minutes is not None:
            used_minutes = args.minutes
            used_seconds = None
            duration_sec = args.minutes * 60.0
        else:
            used_minutes = None
            used_seconds = args.seconds
            duration_sec = args.seconds

    # Start with preset values
    beat = preset.beat
    carrier = preset.carrier
    samplerate = preset.samplerate
    volume = preset.volume
    fade = preset.fade

    # Apply overrides
    if args.beat is not None:
        beat = args.beat
    if args.carrier is not None:
        carrier = args.carrier
    if args.samplerate is not None:
        samplerate = args.samplerate
    if args.volume is not None:
        volume = args.volume
    if args.fade is not None:
        fade = args.fade

    # Loop handling
    if args.loop:
        fade = 0.0

    # Output filename
    if args.out:
        out = args.out
    else:
        dur_tag = (
            f"{int(duration_sec // 60)}m"
            if duration_sec % 60 == 0
            else f"{int(duration_sec)}s"
        )
        out = f"{vibe_key}_beat{beat:g}_car{carrier:g}_{dur_tag}.wav"

    # Show resolved config
    print("\nResolved settings:")
    print(f"  vibe        : {vibe_key}")
    print(f"  description : {preset.description}")
    print(f"  duration    : {duration_sec:.1f} s")
    print(f"  beat        : {beat} Hz")
    print(f"  carrier     : {carrier} Hz")
    print(f"  samplerate  : {samplerate} Hz")
    print(f"  volume      : {volume}")
    print(f"  fade        : {fade} s")
    print(f"  out         : {out}\n")

    if args.dry_run:
        return 0

    # Try to import make_binaural and call directly (fast path)
    mod = _import_make_binaural()
    if (
        mod is not None
        and hasattr(mod, "generate_binaural")
        and hasattr(mod, "save_wav")
    ):
        print("→ Using in-process make_binaural.generate_binaural()")
        data = mod.generate_binaural(
            duration_sec=duration_sec,
            beat_hz=beat,
            carrier_hz=carrier,
            samplerate=samplerate,
            volume=volume,
            fade_sec=fade,
        )
        mod.save_wav(out, data, samplerate=samplerate)
        print(f"✓ Wrote {out}")
        return 0

    # Fallback: use subprocess to call the script
    print("→ make_binaural.py not imported; falling back to subprocess")
    rc = _call_make_binaural_subprocess(
        minutes=used_minutes,
        seconds=used_seconds,
        beat=beat,
        carrier=carrier,
        samplerate=samplerate,
        volume=volume,
        fade=fade,
        out=out,
    )
    if rc == 0:
        print(f"✓ Wrote {out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
