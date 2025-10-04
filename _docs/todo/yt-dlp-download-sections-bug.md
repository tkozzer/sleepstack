# yt-dlp Bug Report: download_sections Parameter Not Working in Python API

## Summary

The `download_sections` parameter in yt-dlp Python API is completely ignored, causing full videos to be downloaded instead of the specified segments. This affects version 2025.09.26 and potentially other recent versions.

## System Information

- **OS**: macOS 24.6.0 (darwin)
- **Python**: 3.12+ (via uv)
- **yt-dlp version**: 2025.09.26
- **Shell**: /bin/zsh
- **Package manager**: uv

## Verbose Output

### Command Line (Working)
```bash
$ yt-dlp -vU --download-sections "*60-120" --output "/tmp/test_cli.%(ext)s" "https://www.youtube.com/watch?v=8KrLtLr-Gy8"
[debug] Command-line config: ['-vU', '--download-sections', '*60-120', '--output', '/tmp/test_cli.%(ext)s', 'https://www.youtube.com/watch?v=8KrLtLr-Gy8']
[debug] Encodings: locale UTF-8, fs utf-8, pref UTF-8, out UTF-8, error UTF-8, screen UTF-8
[debug] yt-dlp version 2025.09.26 [1a176d874] (pip)
[debug] Python 3.12.7 (CPython 64bit) - Darwin-24.6.0-x86_64-i386-64bit (OpenSSL 3.0.13 30 Jan 2024)
[debug] exe versions: ffmpeg 6.1.1 (setts), ffprobe 6.1.1
[debug] Optional libraries: Cryptodome-3.21.0, brotli-1.1.0, certifi-2024.08.30, curl_cffi-0.5.10, mutagen-1.47.0, requests-2.32.3, sqlite3-3.40.1, urllib3-2.2.3, websockets-13.1
[debug] Proxy map: {}
[debug] Request Handlers: urllib, requests, websockets, curl_cffi
[debug] Loaded 1838 extractors
[youtube] Extracting URL: https://www.youtube.com/watch?v=8KrLtLr-Gy8
[youtube] 8KrLtLr-Gy8: Downloading webpage
[youtube] 8KrLtLr-Gy8: Downloading tv client config
[youtube] 8KrLtLr-Gy8: Downloading tv player API JSON
[youtube] 8KrLtLr-Gy8: Downloading web safari player API JSON
[youtube] 8KrLtLr-Gy8: Downloading m3u8 information
[info] 8KrLtLr-Gy8: Downloading 1 format(s): 251
[info] 8KrLtLr-Gy8: Downloading 1 time ranges: 60.0-120.0
[download] Sleeping 3.00 seconds as required by the site...
[download] Destination: /tmp/test_cli.webm
[download] 100% of    1.14MiB in 00:00:37 at 30.92KiB/s
```

### Python API (Broken)
```python
import yt_dlp

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': '/tmp/test_python_api.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 30,
    'download_sections': '*60-120',
    'force_keyframes_at_cuts': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(['https://www.youtube.com/watch?v=8KrLtLr-Gy8'])
```

**Output:**
```
[download]   0.0% of  169.63MiB at  Unknown B/s ETA Unknown
[download] 100% of  169.63MiB in 00:00:16 at 10.29MiB/s
```

## Bug Description

When using the yt-dlp Python API with the `download_sections` parameter, the parameter is completely ignored and the full video is downloaded instead of the specified segment.

### Expected Behavior
- Download only the specified time segment (e.g., 60-120 seconds)
- File size should be proportional to segment duration
- Processing should be faster due to smaller download

### Actual Behavior
- Full video is downloaded regardless of `download_sections` parameter
- File size matches full video duration
- No error messages or warnings about the ignored parameter

## Reproduction Steps

1. **Test Command Line (WORKS)**:
   ```bash
   yt-dlp -vU --download-sections "*60-120" --output "/tmp/test_cli.%(ext)s" "https://www.youtube.com/watch?v=8KrLtLr-Gy8"
   ```
   Result: Downloads 1.1MB file, 60-second duration ✅

2. **Test Python API (BROKEN)**:
   ```python
   import yt_dlp
   
   ydl_opts = {
       'format': 'bestaudio/best',
       'outtmpl': '/tmp/test_python_api.%(ext)s',
       'quiet': True,
       'no_warnings': True,
       'socket_timeout': 30,
       'download_sections': '*60-120',
       'force_keyframes_at_cuts': True,
   }
   
   with yt_dlp.YoutubeDL(ydl_opts) as ydl:
       ydl.download(['https://www.youtube.com/watch?v=8KrLtLr-Gy8'])
   ```
   Result: Downloads 170MB file, 3-hour duration ❌

## Test Results

| Method | File Size | Duration | Expected | Status |
|--------|-----------|----------|----------|---------|
| CLI `--download-sections` | 1.1MB | 60s | 60s | ✅ Works |
| Python API `download_sections` | 170MB | 3h | 60s | ❌ Broken |

## Impact

This bug significantly impacts applications that rely on segment downloads for performance and bandwidth optimization:

- **Bandwidth waste**: Downloads full videos instead of segments
- **Storage waste**: Cache files are unnecessarily large  
- **Performance**: Slower downloads and processing
- **User experience**: Longer wait times for downloads

## Requested Fix

Please fix the `download_sections` parameter in the Python API to match the behavior of the command line interface. The parameter should:

1. Respect the specified time ranges
2. Download only the requested segments
3. Provide appropriate error messages if the parameter is malformed
4. Work consistently across all format selections

## Additional Notes

- The bug affects all tested formats (`bestaudio/best`, specific format IDs)
- The bug affects all tested options (`force_keyframes_at_cuts`, `quiet`, `no_warnings`)
- The bug is consistent across different YouTube URLs and video lengths
- No error messages or warnings are generated when the parameter is ignored
- This appears to be a regression in recent yt-dlp versions

## Use Case

This bug affects applications like ambient sound downloaders that need to extract short segments from long videos (e.g., 60-second clips from 3+ hour videos) for performance and bandwidth optimization.
