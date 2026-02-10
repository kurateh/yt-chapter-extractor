from dataclasses import dataclass, field


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
