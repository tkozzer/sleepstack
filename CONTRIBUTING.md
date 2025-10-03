# Contributing to SleepStack

Thank you for your interest in contributing to SleepStack! This guide will help you get started with the development workflow.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd subconscious-metaprogramming
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Verify installation**
   ```bash
   uv run sleepstack --help
   uv run sleepstack --list-vibes
   ```

## Project Structure

```
src/sleepstack/          # Main package code
├── __init__.py         # Package initialization
├── cli.py              # CLI entry point and argument parsing
├── main.py             # Main orchestrator and core logic
├── make_binaural.py    # Binaural beat generation
├── mix_binaural_with_ambience.py  # Audio mixing functionality
└── vibe_binaural.py    # Vibe presets and aliases

assets/                 # Audio assets (not in package)
└── ambience/
    └── campfire/       # Ambient sound files

build/                  # Generated output files
├── binaural/          # Raw binaural beat files
└── mix/               # Mixed binaural + ambience files

tests/                  # Test suite
├── fixtures/          # Test audio files
└── test_main.py       # Main test file

_docs/                  # Documentation
├── user-guide.md      # User documentation
└── uv-restructure-checklist.md  # Development checklist
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_main.py
```

### Code Quality

```bash
# Format code with black
uv run black src/ tests/

# Type checking with mypy
uv run mypy src/

# Run all quality checks
uv run black src/ tests/ && uv run mypy src/ && uv run pytest
```

### Testing CLI Functionality

```bash
# Test basic functionality
uv run sleepstack --vibe calm -a campfire -m 1

# Test with verbose output
uv run sleepstack --verbose --vibe deep -a campfire -s 30

# Test custom output path
uv run sleepstack --vibe focus -a campfire -m 1 --out test_output.wav
```

## Adding New Features

### Adding New Vibe Presets

1. Edit `src/sleepstack/vibe_binaural.py`
2. Add your preset to the `PRESETS` dictionary
3. Update tests in `tests/test_main.py`
4. Update documentation in `_docs/user-guide.md`

### Adding New CLI Options

1. Edit `src/sleepstack/cli.py` for argument parsing
2. Update `src/sleepstack/main.py` to handle new options
3. Add tests for new functionality
4. Update documentation

### Adding New Audio Assets

1. Place audio files in `assets/ambience/` directory
2. Update code to reference new assets
3. Add tests for new asset functionality

## Testing Guidelines

### Audio Quality Tests

- **Duration**: Generated binaural length matches requested seconds ± 1 sample
- **Bit depth**: Output WAV is 16-bit PCM (`sampwidth == 2`)
- **Stereo enforcement**: Binaural must be 2-channel; mono ambience → duplicated to L/R
- **Sample rate**: All audio must be 48kHz
- **Clipping guard**: Output peak < 0 dBFS

### CLI Tests

- Test all vibe presets work correctly
- Test custom ambience file option
- Test output path customization
- Test error handling for invalid inputs

## Building and Distribution

### Build Package

```bash
# Build wheel and source distribution
uv build
```

### Install Globally for Testing

```bash
# Install the package globally
uv tool install .

# Test global installation
sleepstack --help
```

## Commit Guidelines

- Use clear, descriptive commit messages
- Include tests for new functionality
- Update documentation as needed
- Ensure all tests pass before committing

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with appropriate tests
3. Ensure all quality checks pass
4. Update documentation if needed
5. Submit a pull request with a clear description

## Audio Development Notes

- **Sample Rate**: Always use 48kHz for consistency
- **Bit Depth**: Output should be 16-bit PCM
- **Stereo**: Binaural beats require stereo separation
- **Headphones**: All testing should be done with stereo headphones
- **Mixing Levels**: Default binaural at -15 dB, ambience at -21 dB

## Troubleshooting

### Common Issues

- **Import errors**: Ensure you're running from the project root and have run `uv sync`
- **Audio not playing**: Verify you're using stereo headphones
- **File not found**: Check that assets are in the correct `assets/` directory
- **Sample rate errors**: Ensure all audio files are 48kHz

### Getting Help

- Check the [User Guide](_docs/user-guide.md) for usage examples
- Review the [Development Checklist](_docs/uv-restructure-checklist.md) for project status
- Open an issue for bugs or feature requests

## License

This project is licensed under the MIT License. By contributing, you agree that your contributions will be licensed under the same license.
