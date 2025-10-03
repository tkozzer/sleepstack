<<<<<<< HEAD
# sleepstack
A Python tool for generating binaural beats and mixing them with ambient sounds for sleep and focus
=======
# SleepStack

Binaural beats + ambience mixer for narration-ready sleep tracks.

## Quick Start

```bash
# Generate a 5-minute calm track with campfire ambience
uv run sleepstack --vibe calm -a campfire -m 5
```

## Installation

### Option 1: Run directly with uv (recommended for development)
```bash
uv run sleepstack --help
uv run sleepstack --list-vibes
```

### Option 2: Install globally
```bash
uv tool install .
sleepstack --help
```

### Option 3: Install in a virtual environment
```bash
uv sync
uv run sleepstack --help
```

## Documentation

- [User Guide](_docs/user-guide.md) - Complete usage guide with examples and troubleshooting
- [Sleep Affirmation Primer](_docs/sleep-affirmation-primer.md) - Background on sleep programming techniques

## Features

- **10 vibe presets**: calm, deep, soothe, meditate, airy, warm, focus, flow, alert, dream
- **Ambient mixing**: Automatic mixing with campfire sounds and custom ambience files
- **Customizable parameters**: Beat frequency, carrier frequency, volume, fade settings
- **Duration limits**: Maximum 10 minutes per track (prevents excessive file sizes and memory usage)
- **High-quality output**: 48kHz stereo WAV files optimized for narration
- **CLI interface**: Easy command-line usage with helpful flags (`--list-vibes`, `--version`, `--verbose`)

## Examples

```bash
# List all available vibe presets
uv run sleepstack --list-vibes

# Generate a 1-minute test track
uv run sleepstack --vibe calm -a campfire -m 1

# Use custom ambience file (300 seconds = 5 minutes)
uv run sleepstack --vibe deep --ambience-file my_ambience.wav -s 300

# Generate with custom output path
uv run sleepstack --vibe focus -a campfire -m 5 --out my_track.wav

# Maximum duration examples (10 minutes)
uv run sleepstack --vibe calm -a campfire -m 10
uv run sleepstack --vibe deep -a campfire -s 600
```

## Testing

### Run Tests
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_main.py
```

### Code Quality
```bash
# Format code
uv run black src/ tests/

# Type checking
uv run mypy src/

# Run all quality checks
uv run black src/ tests/ && uv run mypy src/ && uv run pytest
```

### Test Coverage
The test suite includes:
- **Audio quality tests**: Duration, bit depth, stereo enforcement, sample rate validation
- **Duration validation**: Maximum 10-minute limit enforcement with clear error messages
- **CLI functionality**: All vibe presets, custom options, error handling
- **Package installation**: Global and local installation verification
- **Audio generation**: End-to-end binaural beat and mixing functionality

## CI/CD

This project uses GitHub Actions for continuous integration:

- **Multi-platform testing**: Ubuntu and macOS with Python 3.11 and 3.12
- **Automated testing**: Runs on every push and pull request
- **Code quality**: Black formatting and mypy type checking
- **Package building**: Creates wheel and source distributions
- **CLI smoke tests**: Verifies all command-line functionality

[![CI](https://github.com/your-username/subconscious-metaprogramming/workflows/CI/badge.svg)](https://github.com/your-username/subconscious-metaprogramming/actions)

## Requirements

- Python 3.11+
- uv package manager
- Stereo headphones (binaural beats require stereo separation)
>>>>>>> 8022590 (refactor(package): complete migration to uv package structure)
