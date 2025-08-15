from typing import Tuple
import re
import os
from tempfile import TemporaryDirectory
from yt_dlp import YoutubeDL

_SAFE = re.compile(r'[^\w\- .\[\]\(\)]', re.UNICODE)

def _sanitize_filename(name: str) -> str:
    name = name.replace("\n", " ").replace("\r", " ").strip()
    name = re.sub(r"\s+", " ", name)
    return _SAFE.sub("_", name)[:150] or "audio"

def get_direct_audio(video_id: str) -> Tuple[str, str, str]:
    """
    Returns (stream_url, download_filename, mime_type) for the best available audio.
    We do NOT download the file to disk; instead, we return a signed CDN URL suitable for proxy streaming.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        # Setting 'extract_flat' to False ensures full formats are resolved.
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title") or "audio"
        best = None
        # Prefer pure audio formats (vcodec=='none'), highest abr first.
        for f in sorted(info.get("formats", []), key=lambda x: (x.get("vcodec") == "none", x.get("abr") or 0, x.get("tbr") or 0)):
            # The sort puts lower first; iterate reversed for highest
            pass
        # Manual pick: iterate and choose best audio-only with highest abr
        best_abr = -1.0
        for f in info.get("formats", []):
            if f.get("vcodec") and f["vcodec"] != "none":
                continue
            if f.get("acodec") in (None, "none"):
                continue
            abr = f.get("abr") or f.get("tbr") or 0
            if abr > best_abr and f.get("url"):
                best = f
                best_abr = abr

        # Fallback: if nothing picked (rare), use top-level url/ext
        if not best:
            stream_url = info.get("url")
            ext = info.get("ext") or "m4a"
            mime = f"audio/{'mp4' if ext in ('m4a','mp4') else ext}"
        else:
            stream_url = best.get("url")
            ext = (best.get("ext") or "m4a").lower()
            # Map a few common containers to mime
            if ext in ("m4a", "mp4", "mp4a"):
                mime = "audio/mp4"
            elif ext in ("webm", "weba", "opus"):
                mime = "audio/webm"
            elif ext in ("mp3", ):
                mime = "audio/mpeg"
            else:
                mime = "application/octet-stream"

        filename = f"{_sanitize_filename(title)} [{video_id}].{ext}"
        return stream_url, filename, mime


def download_mp3(video_id: str) -> Tuple[bytes, str]:
    """
    Download audio from YouTube and convert it to MP3 using yt-dlp.
    Returns (data_bytes, filename).
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    with TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            temp_path = ydl.prepare_filename(info)
        mp3_path = os.path.splitext(temp_path)[0] + ".mp3"
        with open(mp3_path, "rb") as f:
            data = f.read()
    title = info.get("title") or "audio"
    filename = f"{_sanitize_filename(title)} [{video_id}].mp3"
    return data, filename
