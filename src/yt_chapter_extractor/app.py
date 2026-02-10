from textual import work
from textual.app import App

from .audio import check_ffmpeg
from .models import Chapter
from .screens.chapter_select import ChapterSelectScreen
from .screens.dir_input import DirInputScreen
from .screens.download import DownloadScreen
from .screens.metadata_edit import MetadataEditScreen
from .screens.mode_select import ModeSelectScreen
from .screens.norm_file_list import NormFileListScreen
from .screens.norm_settings import NormSettingsScreen
from .screens.norm_progress import NormProgressScreen
from .screens.url_input import UrlInputScreen
from .theme import CATPPUCCIN_MACCHIATO


class ChapterExtractorApp(App):
    TITLE = "Audio Tools"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def on_mount(self) -> None:
        self.register_theme(CATPPUCCIN_MACCHIATO)
        self.theme = "catppuccin-macchiato"

        if not check_ffmpeg():
            self.notify(
                "ffmpeg is not installed. Please install it first.",
                severity="error",
                timeout=10,
            )
            self.exit()
            return

        self._run_flow()

    @work
    async def _run_flow(self) -> None:
        while True:
            mode = await self.push_screen_wait(ModeSelectScreen())
            if mode is None:
                self.exit()
                return

            if mode == "youtube":
                await self._run_youtube_flow()
            elif mode == "normalize":
                await self._run_normalize_flow()

    async def _run_youtube_flow(self) -> None:
        while True:
            video_info = await self.push_screen_wait(UrlInputScreen())
            if video_info is None:
                return

            if video_info.chapters:
                await self._run_chapter_flow(video_info)
            else:
                await self._run_single_track_flow(video_info)
            return

    async def _run_chapter_flow(self, video_info) -> None:
        while True:
            selected_chapters = await self.push_screen_wait(
                ChapterSelectScreen(video_info.title, video_info.chapters)
            )
            if not selected_chapters:
                return

            tracks = await self.push_screen_wait(
                MetadataEditScreen(selected_chapters)
            )
            if not tracks:
                continue

            norm_result = await self.push_screen_wait(NormSettingsScreen())
            if norm_result is None:
                continue

            enabled, target_lufs = norm_result
            url = f"https://www.youtube.com/watch?v={video_info.video_id}"
            await self.push_screen_wait(
                DownloadScreen(
                    url, tracks, target_lufs=target_lufs if enabled else None
                )
            )
            return

    async def _run_single_track_flow(self, video_info) -> None:
        full_chapter = Chapter(
            index=0,
            title=video_info.title,
            start_time=0.0,
            end_time=video_info.duration,
        )

        while True:
            tracks = await self.push_screen_wait(
                MetadataEditScreen((full_chapter,))
            )
            if not tracks:
                return

            norm_result = await self.push_screen_wait(NormSettingsScreen())
            if norm_result is None:
                continue

            enabled, target_lufs = norm_result
            url = f"https://www.youtube.com/watch?v={video_info.video_id}"
            await self.push_screen_wait(
                DownloadScreen(
                    url, tracks, target_lufs=target_lufs if enabled else None
                )
            )
            return

    async def _run_normalize_flow(self) -> None:
        while True:
            dir_path = await self.push_screen_wait(DirInputScreen())
            if dir_path is None:
                return

            result = await self.push_screen_wait(
                NormFileListScreen(dir_path)
            )
            if result is None:
                continue

            files, target_lufs = result
            await self.push_screen_wait(
                NormProgressScreen(files, target_lufs)
            )
            return
