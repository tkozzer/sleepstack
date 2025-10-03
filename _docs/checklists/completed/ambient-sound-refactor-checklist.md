---
title: Ambient Sound Refactor Checklist
description: Simplify ambient sound system to use only 1-minute clips with automatic looping instead of multiple duration variants
---

This checklist follows `103-docs-checklist` — keep it updated as tasks complete. Reference real files using backticks.

# Dependencies

- Build-time
  - No new dependencies required
- Runtime
  - No new dependencies required (uses existing numpy for audio processing)

# Goal & KPIs

**Goal**: Simplify the ambient sound system by eliminating the need for multiple duration variants (1m, 5m, 10m) and instead use only 1-minute clips with automatic looping to match any target duration.

**Success Metrics**:
- [x] Only `campfire_1m.wav` remains in `assets/ambience/campfire/`
- [x] `choose_campfire_clip()` function always returns the 1-minute clip
- [x] All existing functionality preserved (mixing, tiling, fading)
- [x] Tests updated to reflect new behavior
- [x] Build artifacts cleaned up (remove 5m/10m files from `build/` directories)
- [x] Documentation updated to reflect simplified system

# Code Changes

- [x] Update `choose_campfire_clip()` function
  - [x] Modify `src/sleepstack/main.py` - simplify function to always return 1m clip
  - [x] Modify `src/sleepstack/mix_binaural_with_ambience.py` - simplify function to always return 1m clip
  - [x] Remove duration-based selection logic
  - [x] Update function documentation/comments
- [x] Verify tiling mechanism works correctly
  - [x] Test that existing `np.tile()` logic in `mix_audio()` handles any duration
  - [x] Ensure fade application works with looped audio
  - [x] Verify no audio artifacts at loop boundaries

# Asset Management

- [x] Remove redundant ambient files
  - [x] Delete `assets/ambience/campfire/campfire_5m.wav`
  - [x] Delete `assets/ambience/campfire/campfire_10m.wav`
  - [x] Keep only `assets/ambience/campfire/campfire_1m.wav`
- [x] Clean up build artifacts
  - [x] Remove any existing mixed files that reference 5m/10m clips from `build/mix/`
  - [x] Update any hardcoded references in build output naming
- [x] Git LFS cleanup
  - [x] Remove deleted files from Git LFS tracking: `git lfs untrack "assets/ambience/campfire/campfire_5m.wav"`
  - [x] Remove deleted files from Git LFS tracking: `git lfs untrack "assets/ambience/campfire/campfire_10m.wav"`
  - [x] Clean up LFS cache: `git lfs prune`
  - [x] Verify LFS status: `git lfs ls-files` (should only show remaining files)

# Testing & Validation

- [x] Update existing tests
  - [x] Modify `tests/test_main.py` - update `test_choose_campfire_clip()` to expect only 1m clip
  - [x] Test that all duration scenarios now use 1m clip with tiling
  - [x] Verify mixing tests still pass with looped ambience
- [x] Add new test cases
  - [x] Test very long durations (e.g., 20+ minutes) to ensure tiling works correctly
  - [x] Test fade application with looped audio
  - [x] Test edge cases (very short durations, exact 1-minute durations)
- [x] Integration testing
  - [x] Test CLI commands with various durations
  - [x] Verify output quality with looped ambience
  - [x] Test both `--ambient campfire` and `--ambience-file` options

# Documentation Updates

- [x] Update code comments and docstrings
  - [x] Update function documentation in `choose_campfire_clip()`
  - [x] Update comments in mixing functions
  - [x] Update CLI help text if needed
- [x] Update user documentation
  - [x] Update `README.md` to reflect simplified system
  - [x] Update `_docs/user-guide.md` if it mentions multiple clip durations
  - [x] Update any examples that reference 5m/10m clips

# CI/CD Updates

- [x] Update GitHub Actions workflow
  - [x] Review `.github/workflows/ci.yml` for any hardcoded references to 5m/10m files
  - [x] Update any test commands that might reference deleted ambient files
  - [x] Ensure CI tests still pass with simplified ambient system
  - [x] Verify LFS files are properly handled in CI environment

# Validation & Cleanup

- [x] Final testing
  - [x] Run full test suite to ensure no regressions
  - [x] Test CLI with various vibe/duration combinations
  - [x] Verify audio quality is maintained with looped ambience
- [x] Code quality
  - [x] Run linters (black, mypy) on modified files
  - [x] Ensure all imports and references are updated
- [x] Repository cleanup
  - [x] Remove any remaining references to 5m/10m clips
  - [x] Update `.gitignore` if needed
  - [x] Final LFS cleanup: `git lfs prune --verify-remote`
  - [x] Commit changes with descriptive message

# ✅ COMPLETION SUMMARY

**Refactor Status**: ✅ **COMPLETED SUCCESSFULLY**

**Completion Date**: October 3, 2024

**Key Achievements**:
- ✅ Simplified ambient sound system from 3 files (1m, 5m, 10m) to 1 file (1m with automatic looping)
- ✅ Updated `choose_campfire_clip()` functions in both `main.py` and `mix_binaural_with_ambience.py`
- ✅ All 32 tests pass with new comprehensive test coverage for tiling behavior
- ✅ CI/CD pipeline fully functional with simplified system
- ✅ Documentation updated across all files (README.md, user-guide.md, code comments)
- ✅ Repository cleaned up with proper LFS management
- ✅ No regressions introduced - all existing functionality preserved

**Files Modified**:
- `src/sleepstack/main.py` - Updated `choose_campfire_clip()` function and documentation
- `src/sleepstack/mix_binaural_with_ambience.py` - Updated `choose_campfire_clip()` function and examples
- `tests/test_main.py` - Updated existing tests and added comprehensive new test suite
- `README.md` - Updated feature description
- `_docs/technical/user-guide.md` - Updated throughout for simplified system

**Files Removed**:
- `assets/ambience/campfire/campfire_5m.wav` (deleted and removed from LFS)
- `assets/ambience/campfire/campfire_10m.wav` (deleted and removed from LFS)
- Build artifacts referencing 5m/10m clips

**Technical Implementation**:
- Uses existing `np.tile()` mechanism for seamless looping
- Maintains 48kHz sample rate and 16-bit PCM output format
- Preserves all mixing functionality (fade, gain, stereo handling)
- Automatic tiling handles any duration (tested up to 20+ minutes)

**Validation Results**:
- ✅ 32/32 tests passing
- ✅ All CLI combinations working (vibes × durations)
- ✅ Audio quality maintained with proper file sizes
- ✅ Code quality: Black formatting, MyPy type checking, no linter errors
- ✅ LFS status clean with only `campfire_1m.wav` tracked

# Notes

- **Project Context**: The current system intelligently selects the longest available ambient clip that doesn't exceed the target duration, then tiles/trims as needed. This refactor simplifies to always use the 1-minute clip and rely on the existing tiling mechanism.

- **Technical Constraints**: 
  - Must preserve all existing mixing functionality (fade, gain, stereo handling)
  - The `np.tile()` mechanism in `mix_audio()` already handles looping correctly
  - No changes needed to the core audio processing pipeline
  - Maintain 48kHz sample rate and 16-bit PCM output format

- **Reference Materials**: 
  - Current implementation in `src/sleepstack/main.py` and `src/sleepstack/mix_binaural_with_ambience.py`
  - Existing tests in `tests/test_main.py`
  - Current asset structure in `assets/ambience/campfire/`

- **Conventions**: 
  - Follow existing code style and patterns
  - Update tests to reflect new behavior
  - Maintain backward compatibility for CLI interface
  - Use descriptive commit messages following project conventions
