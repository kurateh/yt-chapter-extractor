from textual import work
from textual.app import App

from .audio import check_ffmpeg
from .screens.chapter_select import ChapterSelectScreen
from .screens.download import DownloadScreen
from .screens.metadata_edit import MetadataEditScreen
from .screens.url_input import UrlInputScreen
from .theme import CATPPUCCIN_MACCHIATO


class ChapterExtractorApp(App):
    TITLE = "YouTube Chapter Extractor"

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
            video_info = await self.push_screen_wait(UrlInputScreen())
            if video_info is None:
                self.exit()
                return

            while True:
                selected_chapters = await self.push_screen_wait(
                    ChapterSelectScreen(video_info.title, video_info.chapters)
                )
                if not selected_chapters:
                    break

                tracks = await self.push_screen_wait(
                    MetadataEditScreen(selected_chapters)
                )
                if not tracks:
                    continue

                url = f"https://www.youtube.com/watch?v={video_info.video_id}"
                await self.push_screen_wait(DownloadScreen(url, tracks))
                self.exit()
                return
