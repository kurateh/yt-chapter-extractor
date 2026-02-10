import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, Static

from ..audio import normalize_audio
from ..models import Mp3FileInfo

_MAX_WORKERS = min(os.cpu_count() or 4, 8)


class NormProgressScreen(Screen[bool]):
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
        self, files: tuple[Mp3FileInfo, ...], target_lufs: float
    ) -> None:
        super().__init__()
        self._files = files
        self._target_lufs = target_lufs

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="progress-section"):
            yield Label(
                f"Normalizing {len(self._files)} files to {self._target_lufs:.1f} LUFS...",
                id="overall-label",
            )
            yield ProgressBar(total=len(self._files), id="overall-progress")
            yield Label("Preparing...", id="current-label")
        with VerticalScroll(id="log-area"):
            yield Static("")
        with Vertical(id="bottom-bar"):
            yield Button(
                "Done", id="done-btn", variant="primary", disabled=True
            )
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
        success_count = 0
        error_count = 0
        done_count = 0

        self.app.call_from_thread(
            self._update_current,
            f"Normalizing {len(self._files)} files ({_MAX_WORKERS} threads)...",
        )

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            future_to_file = {
                pool.submit(
                    normalize_audio, file_info.path, self._target_lufs
                ): file_info
                for file_info in self._files
            }

            for future in as_completed(future_to_file):
                if worker.is_cancelled:
                    pool.shutdown(wait=False, cancel_futures=True)
                    return

                file_info = future_to_file[future]
                done_count += 1

                try:
                    future.result()
                    self.app.call_from_thread(
                        self._log,
                        f"  Done: {file_info.filename}",
                        "log-success",
                    )
                    success_count += 1
                except Exception as e:
                    self.app.call_from_thread(
                        self._log,
                        f"  Error: {file_info.filename} - {e}",
                        "log-error",
                    )
                    error_count += 1

                self.app.call_from_thread(self._advance_progress)
                self.app.call_from_thread(
                    self._update_current,
                    f"Normalizing... {done_count}/{len(self._files)}",
                )

        summary = f"Complete! {success_count} succeeded"
        if error_count > 0:
            summary += f", {error_count} failed"
        self.app.call_from_thread(self._finish, summary)

    def _update_current(self, text: str) -> None:
        self.query_one("#current-label", Label).update(text)

    def _advance_progress(self) -> None:
        self.query_one("#overall-progress", ProgressBar).advance(1)

    def _finish(self, summary: str) -> None:
        self.query_one("#current-label", Label).update("Complete!")
        self.query_one("#overall-label", Label).update(summary)
        self.query_one("#done-btn", Button).disabled = False
        self._log("All done!", "log-success")
