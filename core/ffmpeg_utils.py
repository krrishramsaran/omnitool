import os
import shutil
import subprocess
import re

_CACHED_FFMPEG_PATH = None

def get_ffmpeg_path() -> str:
    global _CACHED_FFMPEG_PATH
    if _CACHED_FFMPEG_PATH and os.path.exists(_CACHED_FFMPEG_PATH):
        return _CACHED_FFMPEG_PATH

    # Check system PATH first
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        _CACHED_FFMPEG_PATH = system_ffmpeg
        return _CACHED_FFMPEG_PATH

    # Try imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            _CACHED_FFMPEG_PATH = exe
            return exe
    except Exception:
        pass

    raise RuntimeError("FFmpeg executable could not be found.")

def run_ffmpeg(args: list, timeout: int = None) -> subprocess.CompletedProcess:
    ffmpeg_exe = get_ffmpeg_path()
    cmd = [ffmpeg_exe] + args
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=creationflags,
        check=True
    )

def get_media_info(input_path: str) -> dict:
    '''Get basic media info: duration (seconds), video resolution, bitrate.'''
    ffmpeg_exe = get_ffmpeg_path()
    cmd = [ffmpeg_exe, "-i", input_path]
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", creationflags=creationflags)
    output = p.stderr

    info = {"duration": 0.0, "width": 0, "height": 0, "bitrate": ""}

    # Parse Duration: 00:01:23.45
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", output)
    if dur_match:
        h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
        info["duration"] = h * 3600 + m * 60 + s

    # Parse Video stream resolution: e.g. 1920x1080
    res_match = re.search(r"Stream.*Video:.*,\s*(\d{2,5})x(\d{2,5})", output)
    if res_match:
        info["width"] = int(res_match.group(1))
        info["height"] = int(res_match.group(2))

    bitrate_match = re.search(r"bitrate:\s*(\d+\s*kb/s)", output)
    if bitrate_match:
        info["bitrate"] = bitrate_match.group(1)

    return info
