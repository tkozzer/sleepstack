---
title: "Ambient Sound Download & Management"
description: "Add YouTube audio download functionality and multi-ambient sound support to sleepstack"
---

This checklist follows `103-docs-checklist` — keep it updated as tasks complete. Reference real files using backticks.

# Dependencies

- Build-time
  - uv add --dev pytest black mypy
- Runtime
  - uv add yt-dlp (YouTube audio downloader)
  - uv add ffmpeg-python (audio processing wrapper)
  - Note: Requires system ffmpeg installation

# Goal & KPIs

**Primary Goal**: Enable users to download ambient sounds from YouTube and use multiple ambient sounds per track.

**Success Metrics**:
- Users can download ambient sounds from YouTube URLs
- Support for 1+ ambient sounds per binaural track
- Maintain backward compatibility with existing campfire functionality
- Robust error handling for invalid URLs and missing prerequisites

# Core Infrastructure

- [x] Create YouTube audio download module
  - [x] Create `src/sleepstack/download_ambient.py` module
  - [x] Add yt-dlp dependency to `pyproject.toml`
  - [x] Add ffmpeg-python dependency to `pyproject.toml`
  - [x] Implement prerequisite validation (ffmpeg, yt-dlp)

- [x] YouTube integration
  - [x] URL validation and format detection
  - [x] Audio format selection (best quality available)
  - [x] 5-minute download limit implementation
  - [x] Handle videos shorter than 5 minutes
  - [x] Error handling for invalid URLs and network issues
  - [x] Handle YouTube API rate limiting and quota issues
  - [x] Validate downloaded audio quality and duration

- [x] Audio processing pipeline
  - [x] Download audio from YouTube
  - [x] Convert to WAV format using ffmpeg
  - [x] Trim audio: start at 60s, extract 1 minute
  - [x] Standardize to 48kHz sample rate
  - [x] Ensure stereo output
  - [x] Save to `assets/ambience/<sound_name>/<sound_name>_1m.wav`

# Multi-Ambient Support

- [x] Ambient sound discovery system
  - [x] Create dynamic ambient sound discovery from filesystem
  - [x] Replace hardcoded `choices=["campfire"]` with dynamic choices
  - [x] Create ambient sound registry with metadata (name, path, duration, etc.)
  - [x] Add validation for ambient sound files (WAV format, 48kHz, stereo)

- [x] Ambient sound management system
  - [x] Create ambient sound registry/listing functionality
  - [x] Update `src/sleepstack/main.py` to support multiple ambient sounds
  - [x] Modify mixing logic in `mix_binaural_with_ambience.py`
  - [x] Support comma-separated ambient sound lists (e.g., "campfire,rain,ocean")
  - [x] Handle individual volume controls per ambient sound

- [x] Enhanced mixing capabilities
  - [x] Create new `mix_multiple_ambient_sounds()` function
  - [x] Update `mix_binaural_and_ambience()` function for multiple inputs
  - [x] Implement ambient sound pre-mixing (mix all ambient sounds first, then mix with binaural)
  - [x] Individual volume control per ambient sound
  - [x] Automatic looping for longer tracks
  - [x] Maintain existing fade and level controls

# CLI Interface

- [x] CLI architecture updates
  - [x] Design subcommand system for new commands (download-ambient, list-ambient)
  - [x] Update `src/sleepstack/cli.py` to handle subcommands before passing to main.py
  - [x] Create separate command modules for download-ambient and list-ambient
  - [x] Maintain backward compatibility with existing single-command flow

- [x] New CLI commands
  - [x] Add `download-ambient` subcommand with URL validation and sound name input
  - [x] Add `list-ambient` subcommand to show available sounds with metadata
  - [x] Add `remove-ambient` subcommand for cleanup
  - [x] Update argument parsing for multiple ambient sounds in main flow
  - [x] Add help text and examples for new commands

- [x] Command examples
  - [x] `sleepstack download-ambient <youtube_url> <sound_name>`
  - [x] `sleepstack list-ambient`
  - [x] `sleepstack remove-ambient <sound_name>`
  - [x] `sleepstack --vibe calm -a campfire,rain,ocean -m 5`

# File Organization & Asset Management

- [x] Directory structure updates
  - [x] Maintain existing `assets/ambience/campfire/` structure
  - [x] Create new directories for downloaded sounds
  - [x] Ensure consistent naming convention: `<sound_name>_1m.wav`
  - [x] Update asset discovery logic in `find_assets_dir()`

- [x] Asset metadata management
  - [x] Create metadata file for each ambient sound (JSON format)
  - [x] Store original YouTube URL, download date, duration, etc.
  - [x] Add asset validation (file integrity, format compliance)
  - [x] Implement asset cleanup functionality

- [x] Error handling for assets
  - [x] Handle corrupted or invalid downloaded files
  - [x] Validate WAV file format and properties
  - [x] Handle missing or moved asset files
  - [x] Provide clear error messages for asset issues

# Testing & Validation

- [x] Unit tests
  - [x] Test YouTube URL validation (comprehensive test suite created and passing)
  - [x] Test audio download and processing (basic functionality tests implemented)
  - [x] Test multi-ambient mixing (real-world functionality tests implemented)
  - [x] Test CLI commands and subcommands (CLI help and command tests implemented)
  - [x] Test error handling scenarios (prerequisite validation tests implemented)
  - [x] Test asset validation and metadata management (ambient sound discovery tests implemented)
  - [x] Test ambient sound discovery system (real-world functionality tests implemented)

- [x] Integration tests
  - [x] End-to-end download and mixing workflow (real-world functionality tests implemented)
  - [x] Backward compatibility with existing campfire functionality (all 32 existing tests still passing)
  - [x] Performance testing with multiple ambient sounds (real-world functionality tests implemented)
  - [x] Test CLI subcommand integration (CLI help and command tests implemented)
  - [x] Test asset cleanup and management workflows (ambient sound management tests implemented)

- [x] Edge case testing
  - [x] Test with corrupted or invalid audio files (basic functionality tests implemented)
  - [x] Test with very short YouTube videos (< 60 seconds) (basic functionality tests implemented)
  - [x] Test with network failures during download (basic functionality tests implemented)
  - [x] Test with missing ffmpeg/yt-dlp dependencies (prerequisite validation tests implemented)
  - [x] Test with duplicate ambient sound names (real-world functionality tests implemented)

# Configuration & State Management

- [ ] Configuration system
  - [ ] Create configuration file for default download settings
  - [ ] Store user preferences (default sample rate, download quality, etc.)
  - [ ] Handle configuration file creation and validation
  - [ ] Provide configuration reset/restore functionality

- [ ] State management
  - [ ] Track download history and metadata
  - [ ] Handle ambient sound updates and re-downloads
  - [ ] Manage asset dependencies and references
  - [ ] Implement state cleanup and maintenance

# CI/CD & Deployment

- [ ] Update CI workflow
  - [ ] Add ffmpeg installation to CI environment (`.github/workflows/ci.yml`)
  - [ ] Add yt-dlp installation to CI environment
  - [ ] Update smoke tests to include new CLI subcommands
  - [ ] Test package installation with new dependencies
  - [ ] Ensure build artifacts include new dependencies

- [ ] Package distribution
  - [ ] Update `pyproject.toml` to include new runtime dependencies
  - [ ] Test package building with `uv build`
  - [ ] Verify wheel distribution includes all required files
  - [ ] Test installation from built package

# Documentation

- [ ] Update user documentation
  - [ ] Update `_docs/technical/user-guide.md` with new features
  - [ ] Add examples for downloading and using ambient sounds
  - [ ] Document prerequisite installation (ffmpeg, yt-dlp)
  - [ ] Update README.md with new functionality
  - [ ] Document CLI subcommand usage and examples
  - [ ] Add troubleshooting guide for common issues

# Performance & Security

- [ ] Performance considerations
  - [ ] Optimize multi-ambient mixing for memory usage
  - [ ] Consider streaming for large audio files
  - [ ] Add progress indicators for long downloads
  - [ ] Implement download caching to avoid re-downloading

- [ ] Security considerations
  - [ ] Validate YouTube URLs to prevent malicious links
  - [ ] Sanitize ambient sound names to prevent path traversal
  - [ ] Add file size limits for downloads
  - [ ] Implement download timeout to prevent hanging

# Notes

- **Prerequisites**: Users must have ffmpeg and yt-dlp installed on their system
- **Audio Quality**: Downloads best available audio quality, converts to 48kHz WAV
- **File Naming**: All ambient sounds follow `<name>_1m.wav` convention
- **Backward Compatibility**: Existing campfire functionality must remain unchanged
- **Error Handling**: Robust validation for URLs, file formats, and system requirements
- **Performance**: Efficient audio processing using existing numpy-based pipeline
