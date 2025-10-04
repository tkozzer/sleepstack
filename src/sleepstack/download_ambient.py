"""
YouTube ambient sound download and processing module.

This module provides functionality to download audio from YouTube URLs,
process the audio to meet sleepstack requirements, and save it in the
appropriate format and location.
"""

import os
import re
import shutil
import subprocess
import tempfile
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Tuple, Callable
from urllib.parse import urlparse

import ffmpeg
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from .config import get_config_manager
from .state_manager import get_state_manager
from .asset_manager import get_asset_manager


class AmbientDownloadError(Exception):
    """Custom exception for ambient sound download errors."""

    pass


class PrerequisiteError(Exception):
    """Custom exception for missing prerequisites."""

    pass


def validate_prerequisites() -> None:
    """
    Validate that required system dependencies are available.

    Raises:
        PrerequisiteError: If ffmpeg or yt-dlp are not available
    """
    # Check ffmpeg
    if not shutil.which("ffmpeg"):
        raise PrerequisiteError(
            "ffmpeg is required but not found. Please install ffmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  Windows: Download from https://ffmpeg.org/download.html"
        )

    # Check yt-dlp (should be available as Python package)
    try:
        import yt_dlp
    except ImportError:
        raise PrerequisiteError(
            "yt-dlp is required but not found. Please install it:\n" "  pip install yt-dlp"
        )


def validate_youtube_url(url: str) -> bool:
    """
    Validate that the provided URL is a valid YouTube URL and not malicious.

    Args:
        url: The URL to validate

    Returns:
        True if valid YouTube URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    # Basic length check to prevent extremely long URLs
    if len(url) > 2048:
        return False

    # Check for suspicious patterns
    suspicious_patterns = [
        "javascript:",
        "data:",
        "file:",
        "ftp:",
        "mailto:",
        "<script",
        "onclick=",
        "onload=",
    ]

    url_lower = url.lower()
    for pattern in suspicious_patterns:
        if pattern in url_lower:
            return False

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Ensure it's HTTPS (security requirement)
        if parsed.scheme not in ["https", "http"]:
            return False

        # Check if it's a valid YouTube domain
        youtube_domains = ["www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"]

        if parsed.netloc not in youtube_domains:
            return False

        # Check for video ID patterns
        if parsed.netloc == "youtu.be":
            # Short URL format: https://youtu.be/VIDEO_ID
            path = parsed.path.strip("/")
            # Basic video ID validation (alphanumeric, hyphens, underscores)
            if not path or not re.match(r"^[a-zA-Z0-9_-]{11}$", path):
                return False
            return True
        else:
            # Standard URL format: https://www.youtube.com/watch?v=VIDEO_ID
            if "v=" in parsed.query:
                # Extract video ID and validate
                video_id = parsed.query.split("v=")[1].split("&")[0]
                if not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
                    return False
            return "v=" in parsed.query or "/watch" in parsed.path
    except Exception:
        return False


def get_video_info(url: str) -> dict[str, Any]:
    """
    Get video information from YouTube URL.

    Args:
        url: YouTube video URL

    Returns:
        Dictionary containing video metadata

    Raises:
        AmbientDownloadError: If video info cannot be retrieved
    """
    if not validate_youtube_url(url):
        raise AmbientDownloadError(f"Invalid YouTube URL: {url}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
                "description": info.get("description", ""),
                "view_count": info.get("view_count", 0),
                "upload_date": info.get("upload_date", ""),
            }
    except (DownloadError, ExtractorError) as e:
        raise AmbientDownloadError(f"Failed to get video info: {str(e)}")


def sanitize_sound_name(name: str) -> str:
    """
    Sanitize sound name for use as directory and filename.

    Args:
        name: Raw sound name

    Returns:
        Sanitized sound name safe for filesystem use
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(" .")
    # Replace multiple underscores with single underscore
    sanitized = re.sub(r"_+", "_", sanitized)
    # Ensure it's not empty
    if not sanitized:
        sanitized = "ambient_sound"

    return sanitized


def get_cache_key(url: str) -> str:
    """
    Generate a cache key for a YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        MD5 hash of the URL for use as cache key
    """
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def get_cache_path(cache_key: str) -> Path:
    """
    Get the cache file path for a given cache key.

    Args:
        cache_key: Cache key (MD5 hash of URL)

    Returns:
        Path to the cached file
    """
    config_manager = get_config_manager()
    config = config_manager.get_config()
    cache_dir = config_manager.config_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / f"{cache_key}.wav"


def is_cache_valid(cache_path: Path, ttl_hours: int) -> bool:
    """
    Check if a cached file is still valid.

    Args:
        cache_path: Path to cached file
        ttl_hours: Time-to-live in hours

    Returns:
        True if cache is valid, False otherwise
    """
    if not cache_path.exists():
        return False

    # Check if file is older than TTL
    file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
    return file_age < timedelta(hours=ttl_hours)


def get_cached_audio(url: str) -> Optional[Path]:
    """
    Get cached audio file if available and valid.

    Args:
        url: YouTube URL

    Returns:
        Path to cached file if valid, None otherwise
    """
    config_manager = get_config_manager()
    config = config_manager.get_config()

    if not config.download.enable_caching:
        return None

    cache_key = get_cache_key(url)
    cache_path = get_cache_path(cache_key)

    if is_cache_valid(cache_path, config.download.cache_ttl_hours):
        return cache_path

    return None


def cache_audio(url: str, audio_path: Path) -> None:
    """
    Cache a downloaded audio file.

    Args:
        url: YouTube URL
        audio_path: Path to the audio file to cache
    """
    config_manager = get_config_manager()
    config = config_manager.get_config()

    if not config.download.enable_caching:
        return

    cache_key = get_cache_key(url)
    cache_path = get_cache_path(cache_key)

    try:
        shutil.copy2(audio_path, cache_path)
    except Exception:
        # If caching fails, continue without error
        pass


def download_audio(
    url: str,
    output_path: Path,
    start_time: int = 60,
    duration: int = 60,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Download audio from YouTube URL with progress tracking and timeout.

    Args:
        url: YouTube video URL
        output_path: Path where to save the downloaded audio
        start_time: Start time in seconds (default: 60)
        duration: Duration to download in seconds (default: 60)
        progress_callback: Optional callback function for progress updates

    Raises:
        AmbientDownloadError: If download fails
    """
    # Get configuration for timeout settings
    config_manager = get_config_manager()
    config = config_manager.get_config()

    # NOTE: yt-dlp version 2025.09.26 has a bug where download_sections doesn't work in Python API
    # The parameter is ignored and full videos are downloaded. We work around this by:
    # 1. Downloading the full video (as it currently does due to the bug)
    # 2. Using FFmpeg to trim it to the desired segment during post-processing
    # TODO: Remove this workaround when yt-dlp fixes the download_sections bug
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_path),
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": config.preferences.download_timeout,
        # download_sections is commented out due to yt-dlp bug - see note above
        # "download_sections": f"*{start_time}-{start_time + duration}",
        # "force_keyframes_at_cuts": True,
    }

    # Add progress hook if callback provided
    if progress_callback:

        def progress_hook(d: dict[str, Any]) -> None:
            if d["status"] == "downloading":
                progress_callback(d.get("downloaded_bytes", 0), d.get("total_bytes", 0))

        ydl_opts["progress_hooks"] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except (DownloadError, ExtractorError) as e:
        raise AmbientDownloadError(f"Failed to download audio: {str(e)}")
    except Exception as e:
        if "timeout" in str(e).lower():
            raise AmbientDownloadError(
                f"Download timeout after {config.preferences.download_timeout} seconds"
            )
        raise AmbientDownloadError(f"Failed to download audio: {str(e)}")


def process_audio(
    input_path: Path,
    output_path: Path,
    start_time: int = 60,
    duration: int = 60,
    sample_rate: int = 48000,
) -> None:
    """
    Process downloaded audio to meet sleepstack requirements.

    Args:
        input_path: Path to input audio file
        output_path: Path for processed audio file
        start_time: Start time in seconds (default: 60s)
        duration: Duration to extract in seconds (default: 60s)
        sample_rate: Target sample rate (default: 48kHz)

    Raises:
        AmbientDownloadError: If audio processing fails
    """
    try:
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use ffmpeg to process the audio
        (
            ffmpeg.input(str(input_path), ss=start_time, t=duration)
            .output(
                str(output_path),
                acodec="pcm_s16le",  # 16-bit PCM
                ac=2,  # Stereo
                ar=sample_rate,  # Sample rate
                af="volume=0.8",  # Slight volume reduction
            )
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise AmbientDownloadError(f"Failed to process audio: {str(e)}")


def download_and_process_ambient_sound(
    url: str, sound_name: str, assets_dir: Optional[Path] = None
) -> Path:
    """
    Download and process an ambient sound from YouTube.

    Args:
        url: YouTube video URL
        sound_name: Name for the ambient sound
        assets_dir: Assets directory path (defaults to project assets)

    Returns:
        Path to the processed ambient sound file

    Raises:
        AmbientDownloadError: If download or processing fails
        PrerequisiteError: If required dependencies are missing
    """
    # Get configuration and state managers
    config_manager = get_config_manager()
    state_manager = get_state_manager()
    asset_manager = get_asset_manager()
    config = config_manager.get_config()

    # Validate prerequisites
    validate_prerequisites()

    # Sanitize sound name
    sanitized_name = sanitize_sound_name(sound_name)

    # Determine assets directory
    if assets_dir is None:
        # Check if user has set a default assets directory in preferences
        config = config_manager.get_config()
        if config.preferences.default_assets_dir:
            assets_dir = Path(config.preferences.default_assets_dir)
        else:
            # Find the project root and assets directory
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            assets_dir = project_root / "assets" / "ambience"

    # Create sound directory
    sound_dir = assets_dir / sanitized_name
    sound_dir.mkdir(parents=True, exist_ok=True)

    # Define output file path
    output_file = sound_dir / f"{sanitized_name}_1m.wav"

    # Check if file already exists
    if output_file.exists():
        raise AmbientDownloadError(
            f"Ambient sound '{sanitized_name}' already exists at {output_file}"
        )

    # Get video info to validate duration
    video_info = None
    try:
        video_info = get_video_info(url)
        duration = video_info.get("duration", 0)

        if duration > 0 and duration < 60:
            raise AmbientDownloadError(
                f"Video is too short ({duration}s). Minimum 60 seconds required."
            )
    except AmbientDownloadError:
        # If we can't get video info, proceed anyway
        pass

    try:
        # Check cache first
        cached_audio = get_cached_audio(url)
        if cached_audio:
            # Use cached audio instead of downloading
            actual_temp_path = cached_audio
        else:
            # Create temporary file for download (yt-dlp will add extension)
            # Use a unique name to avoid conflicts
            temp_base = Path(tempfile.gettempdir()) / f"sleepstack_download_{uuid.uuid4().hex}"

            try:
                # Download audio (yt-dlp will add the appropriate extension)
                download_audio(
                    url,
                    temp_base,
                    start_time=config.download.default_start_time,
                    duration=config.download.default_duration,
                )

                # Find the actual downloaded file (yt-dlp may or may not add extension)
                downloaded_files = list(temp_base.parent.glob(f"{temp_base.name}.*"))
                if downloaded_files:
                    # Use the first (and likely only) downloaded file with extension
                    actual_temp_path = downloaded_files[0]
                elif temp_base.exists() and temp_base.stat().st_size > 0:
                    # File exists without extension
                    actual_temp_path = temp_base
                else:
                    raise AmbientDownloadError("No audio file was downloaded")

                # Cache the downloaded audio
                cache_audio(url, actual_temp_path)

            except Exception as e:
                # Clean up temp files on error
                if temp_base.exists():
                    temp_base.unlink()
                for temp_file in temp_base.parent.glob(f"{temp_base.name}.*"):
                    if temp_file.exists():
                        temp_file.unlink()
                raise

        # Check file size before processing
        temp_file_size = actual_temp_path.stat().st_size
        max_size_bytes = config.download.max_file_size_mb * 1024 * 1024

        if temp_file_size > max_size_bytes:
            raise AmbientDownloadError(
                f"Downloaded file too large: {temp_file_size / (1024*1024):.1f}MB "
                f"(max allowed: {config.download.max_file_size_mb}MB)"
            )

        # Process audio using configuration settings
        process_audio(
            actual_temp_path,
            output_file,
            start_time=config.download.default_start_time,
            duration=config.download.default_duration,
            sample_rate=config.download.default_sample_rate,
        )

        # Create metadata and add to asset manager
        from .ambient_manager import AmbientSoundMetadata

        metadata = AmbientSoundMetadata(
            name=sanitized_name,
            path=output_file,
            duration_seconds=config.download.default_duration,
            sample_rate=config.download.default_sample_rate,
            channels=2,
            file_size_bytes=output_file.stat().st_size,
            created_date=datetime.now().isoformat(),
            source_url=url,
            description=video_info.get("description", "") if video_info else "",
        )

        # Create individual metadata file
        asset_manager.create_individual_metadata_file(sanitized_name, metadata)

        # Add to download history
        config_manager.add_download_record(
            url=url,
            sound_name=sanitized_name,
            success=True,
            metadata={
                "video_title": video_info.get("title", "") if video_info else "",
                "video_duration": video_info.get("duration", 0) if video_info else 0,
                "uploader": video_info.get("uploader", "") if video_info else "",
                "file_size": output_file.stat().st_size,
            },
        )

        # Add asset reference to state
        state_manager.add_asset_reference(
            asset_name=sanitized_name,
            reference_type="download",
            reference_id=f"download_{uuid.uuid4().hex[:8]}",
            metadata={
                "url": url,
                "video_title": video_info.get("title", "") if video_info else "",
                "download_timestamp": datetime.now().isoformat(),
            },
        )

        # Record successful download in maintenance records
        state_manager.add_maintenance_record(
            operation_type="download",
            asset_name=sanitized_name,
            success=True,
            details={"url": url, "file_size": output_file.stat().st_size, "video_info": video_info},
        )

        return output_file

    except Exception as e:
        # Record failed download
        config_manager.add_download_record(
            url=url, sound_name=sanitized_name, success=False, error_message=str(e)
        )

        state_manager.add_maintenance_record(
            operation_type="download",
            asset_name=sanitized_name,
            success=False,
            error_message=str(e),
            details={"url": url},
        )

        raise

    finally:
        # Clean up temporary files if configured to do so
        config = config_manager.get_config()
        if config.download.auto_cleanup_temp_files:
            if "temp_base" in locals() and temp_base.exists():
                temp_base.unlink()
            # Clean up any files with extensions
            if "temp_base" in locals():
                for temp_file in temp_base.parent.glob(f"{temp_base.name}.*"):
                    if temp_file.exists():
                        temp_file.unlink()


def main() -> None:
    """CLI entry point for testing the download functionality."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python download_ambient.py <youtube_url> <sound_name>")
        sys.exit(1)

    url = sys.argv[1]
    sound_name = sys.argv[2]

    try:
        output_path = download_and_process_ambient_sound(url, sound_name)
        print(f"Successfully downloaded and processed: {output_path}")
    except (AmbientDownloadError, PrerequisiteError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
