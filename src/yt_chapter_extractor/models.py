from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    start_time: float
    end_time: float

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def duration_str(self) -> str:
        total_seconds = int(self.duration)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


@dataclass(frozen=True)
class TrackInfo:
    chapter: Chapter
    filename: str
    title: str = ""
    artist: str = ""
    album: str = ""

    @property
    def effective_title(self) -> str:
        return self.title if self.title else self.filename

    def with_filename(self, filename: str) -> "TrackInfo":
        return TrackInfo(
            chapter=self.chapter,
            filename=filename,
            title=self.title,
            artist=self.artist,
            album=self.album,
        )

    def with_metadata(
        self,
        title: str = "",
        artist: str = "",
        album: str = "",
    ) -> "TrackInfo":
        return TrackInfo(
            chapter=self.chapter,
            filename=self.filename,
            title=title,
            artist=artist,
            album=album,
        )


@dataclass(frozen=True)
class VideoInfo:
    video_id: str
    title: str
    duration: float
    chapters: tuple[Chapter, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Mp3FileInfo:
    path: Path
    filename: str
    size_bytes: int
    loudness_lufs: float | None = None

    @property
    def loudness_display(self) -> str:
        if self.loudness_lufs is None:
            return "N/A"
        return f"{self.loudness_lufs:.1f} LUFS"

    @property
    def size_display(self) -> str:
        if self.size_bytes >= 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        return f"{self.size_bytes / 1024:.1f} KB"

    def with_loudness(self, loudness_lufs: float) -> "Mp3FileInfo":
        return Mp3FileInfo(
            path=self.path,
            filename=self.filename,
            size_bytes=self.size_bytes,
            loudness_lufs=loudness_lufs,
        )
