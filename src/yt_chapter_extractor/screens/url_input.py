import re

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, LoadingIndicator

from ..models import VideoInfo
from ..youtube import extract_video_info

_YOUTUBE_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
)


class UrlInputScreen(Screen[VideoInfo | None]):
    CSS = """
    #container {
        align: center middle;
        width: 80;
        height: auto;
        padding: 2 4;
    }

    #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #url-input {
        margin-bottom: 1;
    }

    #load-btn {
        width: 100%;
        margin-top: 1;
    }

    #error-label {
        color: red;
        text-align: center;
        margin-top: 1;
    }

    #loading {
        height: 3;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="container"):
                yield Label("YouTube Chapter Extractor", id="title")
                yield Input(
                    placeholder="Enter YouTube video URL...",
                    id="url-input",
                )
                yield Button("Load Video", id="load-btn", variant="primary")
                yield LoadingIndicator(id="loading")
                yield Label("", id="error-label")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#url-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            self._load_video()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "load-btn":
            self._load_video()

    def _load_video(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            self._show_error("Please enter a URL.")
            return
        if not _YOUTUBE_URL_PATTERN.match(url):
            self._show_error("Please enter a valid YouTube URL.")
            return
        self._fetch_info(url)

    @work(exclusive=True, thread=True)
    def _fetch_info(self, url: str) -> None:
        from textual.worker import get_current_worker

        worker = get_current_worker()

        self.app.call_from_thread(self._set_loading, True)

        try:
            video_info = extract_video_info(url)
            if not worker.is_cancelled:
                self.app.call_from_thread(self.dismiss, video_info)
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._show_error, str(e))
        finally:
            if not worker.is_cancelled:
                self.app.call_from_thread(self._set_loading, False)

    def _set_loading(self, loading: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = loading
        self.query_one("#load-btn", Button).disabled = loading
        if loading:
            self.query_one("#error-label", Label).update("")

    def _show_error(self, message: str) -> None:
        self.query_one("#error-label", Label).update(message)

    def action_quit(self) -> None:
        self.dismiss(None)
