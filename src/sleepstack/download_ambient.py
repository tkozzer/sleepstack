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
from pathlib import Path
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import ffmpeg
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError


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
            "yt-dlp is required but not found. Please install it:\n"
            "  pip install yt-dlp"
        )


def validate_youtube_url(url: str) -> bool:
    """
    Validate that the provided URL is a valid YouTube URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if valid YouTube URL, False otherwise
    """
    if not url:
        return False
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Check if it's a valid YouTube domain
    youtube_domains = [
        'www.youtube.com',
        'youtube.com',
        'm.youtube.com',
        'youtu.be'
    ]
    
    if parsed.netloc not in youtube_domains:
        return False
    
    # Check for video ID patterns
    if parsed.netloc == 'youtu.be':
        # Short URL format: https://youtu.be/VIDEO_ID
        return bool(parsed.path.strip('/'))
    else:
        # Standard URL format: https://www.youtube.com/watch?v=VIDEO_ID
        return 'v=' in parsed.query or '/watch' in parsed.path


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
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'description': info.get('description', ''),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
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
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    # Replace multiple underscores with single underscore
    sanitized = re.sub(r'_+', '_', sanitized)
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'ambient_sound'
    
    return sanitized


def download_audio(url: str, output_path: Path, max_duration: int = 300) -> None:
    """
    Download audio from YouTube URL.
    
    Args:
        url: YouTube video URL
        output_path: Path where to save the downloaded audio
        max_duration: Maximum duration in seconds (default: 5 minutes)
        
    Raises:
        AmbientDownloadError: If download fails
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path),
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except (DownloadError, ExtractorError) as e:
        raise AmbientDownloadError(f"Failed to download audio: {str(e)}")


def process_audio(
    input_path: Path,
    output_path: Path,
    start_time: int = 60,
    duration: int = 60,
    sample_rate: int = 48000
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
            ffmpeg
            .input(str(input_path), ss=start_time, t=duration)
            .output(
                str(output_path),
                acodec='pcm_s16le',  # 16-bit PCM
                ac=2,  # Stereo
                ar=sample_rate,  # Sample rate
                af='volume=0.8'  # Slight volume reduction
            )
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise AmbientDownloadError(f"Failed to process audio: {str(e)}")


def download_and_process_ambient_sound(
    url: str,
    sound_name: str,
    assets_dir: Optional[Path] = None
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
    # Validate prerequisites
    validate_prerequisites()
    
    # Sanitize sound name
    sanitized_name = sanitize_sound_name(sound_name)
    
    # Determine assets directory
    if assets_dir is None:
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
    try:
        video_info = get_video_info(url)
        duration = video_info.get('duration', 0)
        
        if duration > 0 and duration < 60:
            raise AmbientDownloadError(
                f"Video is too short ({duration}s). Minimum 60 seconds required."
            )
    except AmbientDownloadError:
        # If we can't get video info, proceed anyway
        pass
    
    # Create temporary file for download (yt-dlp will add extension)
    # Use a unique name to avoid conflicts
    import uuid
    temp_base = Path(tempfile.gettempdir()) / f"sleepstack_download_{uuid.uuid4().hex}"
    
    try:
        # Download audio (yt-dlp will add the appropriate extension)
        download_audio(url, temp_base)
        
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
        
        # Process audio
        process_audio(actual_temp_path, output_file)
        
        return output_file
        
    finally:
        # Clean up temporary files
        if temp_base.exists():
            temp_base.unlink()
        # Clean up any files with extensions
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
