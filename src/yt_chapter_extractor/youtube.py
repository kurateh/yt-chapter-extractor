import re
from pathlib import Path

import yt_dlp

from .models import Chapter, VideoInfo


def extract_video_info(url: str) -> VideoInfo:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise ValueError(f"Could not extract info from: {url}")

    raw_chapters = info.get("chapters") or []
    if not raw_chapters:
        raise ValueError("This video has no chapters.")

    chapters = tuple(
        Chapter(
            index=i,
            title=ch["title"],
            start_time=ch["start_time"],
            end_time=ch["end_time"],
        )
        for i, ch in enumerate(raw_chapters)
    )

    return VideoInfo(
        video_id=info.get("id", ""),
        title=info.get("title", "Unknown"),
        duration=info.get("duration", 0.0),
        chapters=chapters,
    )


def download_audio(url: str, output_dir: Path) -> Path:
    output_template = str(output_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    if info is None:
        raise ValueError(f"Failed to download audio from: {url}")

    video_id = info.get("id", "unknown")
    output_path = output_dir / f"{video_id}.mp3"

    if not output_path.exists():
        raise FileNotFoundError(f"Downloaded file not found: {output_path}")

    return output_path


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    sanitized = sanitized.strip(". ")
    sanitized = re.sub(r"\.{2,}", "_", sanitized)
    return sanitized[:200] if sanitized else "untitled"
