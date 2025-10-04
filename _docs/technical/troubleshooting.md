# Troubleshooting Guide

This guide covers common issues and solutions for SleepStack, including the new ambient sound download and management features.

## Installation Issues

### Python Version Problems

**Error**: `Python 3.11+ is required`

**Solution**: 
- Check your Python version: `python --version`
- Install Python 3.11+ from https://python.org
- Use `python3` instead of `python` if you have multiple versions

### uv Package Manager Issues

**Error**: `uv: command not found`

**Solution**:
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Restart your terminal
- Verify installation: `uv --version`

## Ambient Sound Download Issues

### ffmpeg Not Found

**Error**: `ffmpeg: command not found` or `FFmpeg not found in PATH`

**Solution**:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
1. Download ffmpeg from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH
4. Restart your terminal

**Verify installation:**
```bash
ffmpeg -version
```

### YouTube Download Failures

**Error**: `Failed to download audio from YouTube`

**Common causes and solutions:**

1. **Invalid URL**: Ensure the YouTube URL is correct and accessible
   ```bash
   # Test with a known working video
   uv run sleepstack download-ambient "https://www.youtube.com/watch?v=dQw4w9WgXcQ" test
   ```

2. **Video too short**: Video must be at least 2 minutes long
   - SleepStack needs 60 seconds + 1 minute of content
   - Try a longer video

3. **Video restrictions**: Some videos have download restrictions
   - Try a different video
   - Look for videos marked as "Creative Commons" or "Public Domain"

4. **Network issues**: Check your internet connection
   ```bash
   # Test with verbose output
   uv run sleepstack download-ambient "https://www.youtube.com/watch?v=example" test --verbose
   ```

5. **yt-dlp version issues**: Update yt-dlp
   ```bash
   uv add yt-dlp@latest
   ```

### Audio Processing Failures

**Error**: `Failed to process audio` or `Audio conversion failed`

**Solutions:**

1. **Check file permissions**: Ensure SleepStack can write to the assets directory
   ```bash
   ls -la assets/ambience/
   chmod 755 assets/ambience/
   ```

2. **Disk space**: Ensure you have enough free disk space
   ```bash
   df -h
   ```

3. **Corrupted download**: Re-download the audio
   ```bash
   uv run sleepstack remove-ambient <sound_name>
   uv run sleepstack download-ambient <url> <sound_name>
   ```

## Audio Quality Issues

### Poor Audio Quality

**Symptoms**: Distorted, low-quality, or noisy audio

**Solutions:**

1. **Source quality**: Try a different YouTube video with better audio quality
2. **Check file size**: Very small files may indicate low quality
   ```bash
   ls -lh assets/ambience/<sound_name>/<sound_name>_1m.wav
   ```

3. **Re-download**: Sometimes re-downloading improves quality
   ```bash
   uv run sleepstack remove-ambient <sound_name>
   uv run sleepstack download-ambient <url> <sound_name>
   ```

### Audio Format Issues

**Error**: `Sample rate mismatch` or `Invalid audio format`

**Solutions:**

1. **Check audio properties**:
   ```bash
   uv run sleepstack list-ambient --detailed
   ```

2. **Re-download**: SleepStack automatically converts to 48kHz stereo
   ```bash
   uv run sleepstack remove-ambient <sound_name>
   uv run sleepstack download-ambient <url> <sound_name>
   ```

## Mixing Issues

### Missing Ambient Sounds

**Error**: `Ambient sound not found: <name>`

**Solutions:**

1. **List available sounds**:
   ```bash
   uv run sleepstack list-ambient
   ```

2. **Check directory structure**:
   ```bash
   ls -la assets/ambience/
   ```

3. **Re-download missing sounds**:
   ```bash
   uv run sleepstack download-ambient <url> <sound_name>
   ```

### Mixing Failures

**Error**: `Failed to mix audio` or `Audio mixing error`

**Solutions:**

1. **Check file integrity**:
   ```bash
   uv run sleepstack state health
   ```

2. **Validate assets**:
   ```bash
   uv run sleepstack state validate
   ```

3. **Check file permissions**:
   ```bash
   ls -la assets/ambience/*/
   chmod 644 assets/ambience/*/*.wav
   ```

4. **Use verbose output**:
   ```bash
   uv run sleepstack --vibe calm -a campfire -m 5 --verbose
   ```

### Performance Issues

**Symptoms**: Slow processing, high memory usage, or crashes

**Solutions:**

1. **Reduce number of ambient sounds**: Limit to 3-5 sounds maximum
2. **Check system resources**:
   ```bash
   # Check memory usage
   free -h
   # Check CPU usage
   top
   ```

3. **Use shorter durations for testing**:
   ```bash
   uv run sleepstack --vibe calm -a campfire,rain -m 1
   ```

## Configuration Issues

### Configuration File Problems

**Error**: `Invalid configuration` or `Configuration file corrupted`

**Solutions:**

1. **Reset configuration**:
   ```bash
   uv run sleepstack config reset
   ```

2. **Validate configuration**:
   ```bash
   uv run sleepstack config validate
   ```

3. **Show current configuration**:
   ```bash
   uv run sleepstack config show
   ```

### State Management Issues

**Error**: `State file corrupted` or `Failed to load state`

**Solutions:**

1. **Check state health**:
   ```bash
   uv run sleepstack state health
   ```

2. **Clear corrupted state**:
   ```bash
   uv run sleepstack state clear
   ```

3. **Export/import state**:
   ```bash
   uv run sleepstack state export backup.json
   uv run sleepstack state import backup.json
   ```

## CLI Issues

### Command Not Found

**Error**: `sleepstack: command not found`

**Solutions:**

1. **Use uv run**:
   ```bash
   uv run sleepstack --help
   ```

2. **Install globally**:
   ```bash
   uv tool install .
   sleepstack --help
   ```

3. **Check installation**:
   ```bash
   uv run sleepstack --version
   ```

### Subcommand Issues

**Error**: `Unknown subcommand` or `Invalid subcommand`

**Solutions:**

1. **Check available subcommands**:
   ```bash
   uv run sleepstack --help
   uv run sleepstack download-ambient --help
   uv run sleepstack list-ambient --help
   uv run sleepstack config --help
   uv run sleepstack state --help
   ```

2. **Update SleepStack**:
   ```bash
   uv sync
   ```

## File System Issues

### Permission Denied

**Error**: `Permission denied` when accessing files

**Solutions:**

1. **Check file permissions**:
   ```bash
   ls -la assets/ambience/
   chmod 755 assets/ambience/
   chmod 644 assets/ambience/*/*.wav
   ```

2. **Run with appropriate permissions**:
   ```bash
   # Don't use sudo unless absolutely necessary
   uv run sleepstack --help
   ```

### Disk Space Issues

**Error**: `No space left on device`

**Solutions:**

1. **Check disk space**:
   ```bash
   df -h
   ```

2. **Clean up old files**:
   ```bash
   uv run sleepstack state cleanup
   ```

3. **Remove unused ambient sounds**:
   ```bash
   uv run sleepstack list-ambient
   uv run sleepstack remove-ambient <unused_sound>
   ```

## Getting Help

### Debug Information

When reporting issues, include:

1. **System information**:
   ```bash
   python --version
   uv --version
   ffmpeg -version
   ```

2. **SleepStack version**:
   ```bash
   uv run sleepstack --version
   ```

3. **Verbose output**:
   ```bash
   uv run sleepstack <command> --verbose
   ```

4. **Configuration**:
   ```bash
   uv run sleepstack config show
   ```

5. **State information**:
   ```bash
   uv run sleepstack state show
   uv run sleepstack state health
   ```

### Common Workarounds

1. **Reset everything**: If all else fails, reset configuration and state
   ```bash
   uv run sleepstack config reset
   uv run sleepstack state clear
   ```

2. **Clean reinstall**: Remove and reinstall SleepStack
   ```bash
   rm -rf ~/.config/sleepstack/
   uv sync
   ```

3. **Test with minimal setup**: Start with basic functionality
   ```bash
   uv run sleepstack --vibe calm -a campfire -m 1
   ```

### Reporting Issues

When reporting issues:

1. Include the exact error message
2. Provide system information (OS, Python version, etc.)
3. Include the command that caused the issue
4. Attach verbose output if available
5. Describe what you were trying to accomplish

For more help, check the [User Guide](user-guide.md) or create an issue on the project repository.
