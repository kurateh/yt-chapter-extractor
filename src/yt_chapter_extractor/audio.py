import json
import os
import re
import shutil
import subprocess
import tempfile
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
    convert_entire_file = start_time == 0 and end_time <= 0

    if convert_entire_file:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(source_path),
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(output_path),
        ]
    else:
        duration = end_time - start_time
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(start_time),
            "-i", str(source_path),
            "-t", str(duration),
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


_LOUDNORM_JSON_PATTERN = re.compile(
    r"\{[^{}]*\"input_i\"[^{}]*\}", re.DOTALL
)


def measure_loudness(mp3_path: Path) -> float:
    cmd = [
        "ffmpeg",
        "-i", str(mp3_path),
        "-af", "loudnorm=print_format=json",
        "-f", "null",
        "-",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # loudnorm always outputs to stderr even on success, so check for JSON first
    match = _LOUDNORM_JSON_PATTERN.search(result.stderr)
    if not match:
        raise RuntimeError(
            f"ffmpeg loudness measurement failed for {mp3_path.name}: {result.stderr[:200]}"
        )

    try:
        data = json.loads(match.group())
        return float(data["input_i"])
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise RuntimeError(
            f"Failed to parse loudness data for {mp3_path.name}: {e}"
        ) from e


def normalize_audio(mp3_path: Path, target_lufs: float) -> Path:
    dir_path = mp3_path.parent
    fd, tmp_path_str = tempfile.mkstemp(suffix=".mp3", dir=dir_path)
    os.close(fd)
    tmp_path = Path(tmp_path_str)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(mp3_path),
            "-af", f"loudnorm=I={target_lufs}:LRA=11:TP=-1.5",
            "-codec:a", "libmp3lame",
            "-q:a", "2",
            str(tmp_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        os.replace(tmp_path, mp3_path)
        return mp3_path
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
