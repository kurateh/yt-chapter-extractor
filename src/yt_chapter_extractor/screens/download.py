import tempfile
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, Static

from ..audio import process_track
from ..models import TrackInfo
from ..youtube import download_audio


class DownloadScreen(Screen[bool]):
    CSS = """
    #progress-section {
        height: auto;
        padding: 1 2;
    }

    #overall-label {
        text-style: bold;
        margin-bottom: 1;
    }

    #current-label {
        margin-top: 1;
        margin-bottom: 1;
    }

    #log-area {
        height: 1fr;
        padding: 0 2;
        border: solid $surface-lighten-2;
        margin: 1 2;
    }

    .log-line {
        margin: 0;
    }

    .log-success {
        color: green;
    }

    .log-error {
        color: red;
    }

    .log-info {
        color: $text;
    }

    #bottom-bar {
        height: 3;
        align: center middle;
        dock: bottom;
    }

    #done-btn {
        width: 30;
    }
    """

    def __init__(self, url: str, tracks: list[TrackInfo]) -> None:
        super().__init__()
        self._url = url
        self._tracks = tracks

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="progress-section"):
            yield Label(
                f"Processing {len(self._tracks)} tracks...",
                id="overall-label",
            )
            yield ProgressBar(total=len(self._tracks), id="overall-progress")
            yield Label("Preparing...", id="current-label")
        with VerticalScroll(id="log-area"):
            yield Static("")
        with Vertical(id="bottom-bar"):
            yield Button("Done", id="done-btn", variant="primary", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self._start_processing()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "done-btn":
            self.dismiss(True)

    def _log(self, message: str, style: str = "log-info") -> None:
        log_area = self.query_one("#log-area", VerticalScroll)
        label = Label(message, classes=f"log-line {style}")
        log_area.mount(label)
        label.scroll_visible()

    @work(thread=True)
    def _start_processing(self) -> None:
        from textual.worker import get_current_worker

        worker = get_current_worker()
        output_dir = Path.cwd()

        self.app.call_from_thread(self._log, "Downloading audio from YouTube...")
        self.app.call_from_thread(
            self._update_current, "Downloading full audio..."
        )

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                source_path = download_audio(self._url, tmp_path)

                self.app.call_from_thread(
                    self._log, "Download complete.", "log-success"
                )

                for i, track in enumerate(self._tracks):
                    if worker.is_cancelled:
                        return

                    self.app.call_from_thread(
                        self._update_current,
                        f"Extracting: {track.filename} ({i + 1}/{len(self._tracks)})",
                    )
                    self.app.call_from_thread(
                        self._log, f"Processing: {track.filename}..."
                    )

                    try:
                        result_path = process_track(
                            source_path, track, output_dir
                        )
                        self.app.call_from_thread(
                            self._log,
                            f"  Saved: {result_path.name}",
                            "log-success",
                        )
                    except Exception as e:
                        self.app.call_from_thread(
                            self._log,
                            f"  Error: {track.filename} - {e}",
                            "log-error",
                        )

                    self.app.call_from_thread(self._advance_progress)

        except Exception as e:
            self.app.call_from_thread(
                self._log, f"Fatal error: {e}", "log-error"
            )

        self.app.call_from_thread(self._finish)

    def _update_current(self, text: str) -> None:
        self.query_one("#current-label", Label).update(text)

    def _advance_progress(self) -> None:
        self.query_one("#overall-progress", ProgressBar).advance(1)

    def _finish(self) -> None:
        self.query_one("#current-label", Label).update("Complete!")
        self.query_one("#overall-label", Label).update("All tracks processed.")
        self.query_one("#done-btn", Button).disabled = False
        self._log("All done!", "log-success")
