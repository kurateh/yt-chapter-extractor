import shutil
import subprocess
from pathlib import Path

from mutagen.id3 import ID3, TIT2, TPE1, TALB
from mutagen.mp3 import MP3

from .models import TrackInfo


def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_chapter_audio(
    source_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
) -> Path:
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(source_path),
        "-ss", str(start_time),
        "-to", str(end_time),
        "-codec:a", "libmp3lame",
        "-q:a", "2",
        str(output_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return output_path


def set_metadata(mp3_path: Path, track: TrackInfo) -> None:
    audio = MP3(str(mp3_path))

    if audio.tags is None:
        audio.add_tags()

    tags = audio.tags
    if not isinstance(tags, ID3):
        return

    tags.add(TIT2(encoding=3, text=[track.effective_title]))

    if track.artist:
        tags.add(TPE1(encoding=3, text=[track.artist]))

    if track.album:
        tags.add(TALB(encoding=3, text=[track.album]))

    audio.save()


def process_track(
    source_path: Path,
    track: TrackInfo,
    output_dir: Path,
) -> Path:
    output_path = output_dir / f"{track.filename}.mp3"

    extract_chapter_audio(
        source_path=source_path,
        start_time=track.chapter.start_time,
        end_time=track.chapter.end_time,
        output_path=output_path,
    )

    set_metadata(output_path, track)

    return output_path
