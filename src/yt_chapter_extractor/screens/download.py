import tempfile
import time
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, Static

from ..audio import normalize_audio, process_track
from ..models import DownloadTask
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
        color: $success;
    }

    .log-error {
        color: $error;
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

    def __init__(
        self,
        tasks: tuple[DownloadTask, ...],
        target_lufs: float | None = None,
    ) -> None:
        super().__init__()
        self._tasks = tasks
        self._target_lufs = target_lufs
        self._total_tracks = sum(len(t.tracks) for t in tasks)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="progress-section"):
            yield Label(
                f"Processing {self._total_tracks} tracks...",
                id="overall-label",
            )
            yield ProgressBar(total=self._total_tracks, id="overall-progress")
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
        output_dir = Path.cwd() / "output"
        output_dir.mkdir(exist_ok=True)

        multi_task = len(self._tasks) > 1
        track_num = 0

        try:
            for task_idx, task in enumerate(self._tasks):
                if worker.is_cancelled:
                    return

                if multi_task:
                    self.app.call_from_thread(
                        self._log,
                        f"Downloading video {task_idx + 1}/{len(self._tasks)}...",
                    )
                else:
                    self.app.call_from_thread(
                        self._log, "Downloading audio from YouTube..."
                    )

                self.app.call_from_thread(
                    self._update_current, "Downloading audio..."
                )

                with tempfile.TemporaryDirectory() as tmp_dir:
                    last_update = 0.0

                    def on_progress(pct: float, speed: str) -> None:
                        nonlocal last_update
                        now = time.monotonic()
                        if now - last_update < 0.5:
                            return
                        last_update = now
                        msg = f"Downloading audio... {pct:.1f}%"
                        if speed:
                            msg += f" ({speed})"
                        self.app.call_from_thread(self._update_current, msg)

                    source_path = download_audio(
                        task.url, Path(tmp_dir), on_progress
                    )

                    if worker.is_cancelled:
                        return

                    self.app.call_from_thread(
                        self._log, "Download complete.", "log-success"
                    )

                    for i, track in enumerate(task.tracks):
                        if worker.is_cancelled:
                            return

                        track_num += 1
                        self.app.call_from_thread(
                            self._update_current,
                            f"Extracting: {track.filename} ({track_num}/{self._total_tracks})",
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

                            if self._target_lufs is not None:
                                self.app.call_from_thread(
                                    self._update_current,
                                    f"Normalizing: {track.filename} ({track_num}/{self._total_tracks})",
                                )
                                self.app.call_from_thread(
                                    self._log,
                                    f"  Normalizing to {self._target_lufs:.1f} LUFS...",
                                )
                                normalize_audio(result_path, self._target_lufs)
                                self.app.call_from_thread(
                                    self._log,
                                    f"  Normalized: {result_path.name}",
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
