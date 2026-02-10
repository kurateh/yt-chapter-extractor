import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
)

from ..audio import measure_loudness
from ..models import Mp3FileInfo

_MAX_WORKERS = min(os.cpu_count() or 4, 8)


class NormFileListScreen(Screen[tuple[tuple[Mp3FileInfo, ...], float] | None]):
    CSS = """
    #file-table {
        height: 1fr;
        margin: 1 2;
    }

    #bottom-section {
        height: auto;
        padding: 1 2;
    }

    #target-row {
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }

    #target-label {
        width: auto;
        margin-right: 1;
    }

    #target-input {
        width: 20;
    }

    #target-unit {
        width: auto;
        margin-left: 1;
    }

    #error-label {
        color: $error;
        margin-bottom: 1;
    }

    #start-btn {
        width: 100%;
    }

    #scan-status {
        text-align: center;
        margin: 1 2;
        color: $text-muted;
    }

    #stats-label {
        text-align: center;
        margin: 0 2 1 2;
        color: $accent;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
    ]

    def __init__(self, dir_path: Path) -> None:
        super().__init__()
        self._dir_path = dir_path
        self._files: tuple[Mp3FileInfo, ...] = ()
        self._loudness_col_key = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(
            f"Directory: {self._dir_path}", id="scan-status"
        )
        yield DataTable(id="file-table")
        yield Label("", id="stats-label")
        with Vertical(id="bottom-section"):
            with Horizontal(id="target-row"):
                yield Label("Target Loudness:", id="target-label")
                yield Input(
                    value="-19.0",
                    id="target-input",
                    type="number",
                )
                yield Label("LUFS", id="target-unit")
            yield Label("", id="error-label")
            yield Button(
                "Start Normalization",
                id="start-btn",
                variant="primary",
                disabled=True,
            )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#file-table", DataTable)
        col_keys = table.add_columns("#", "Filename", "Size", "Loudness")
        self._loudness_col_key = col_keys[3]
        self._scan_files()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self._submit()

    def _submit(self) -> None:
        raw = self.query_one("#target-input", Input).value.strip()

        try:
            target = float(raw)
        except ValueError:
            self._show_error("Please enter a valid number.")
            return

        if not -70.0 <= target <= 0.0:
            self._show_error("Target must be between -70.0 and 0.0 LUFS.")
            return

        self.dismiss((self._files, target))

    @work(thread=True)
    def _scan_files(self) -> None:
        from textual.worker import get_current_worker

        worker = get_current_worker()

        mp3_paths = sorted(
            p
            for p in self._dir_path.iterdir()
            if p.suffix.lower() == ".mp3" and p.is_file()
        )

        collected: list[Mp3FileInfo] = []
        for i, mp3_path in enumerate(mp3_paths):
            if worker.is_cancelled:
                return

            info = Mp3FileInfo(
                path=mp3_path,
                filename=mp3_path.name,
                size_bytes=mp3_path.stat().st_size,
            )
            collected.append(info)

            self.app.call_from_thread(
                self._add_row, i, info, "Measuring..."
            )

        self._files = tuple(collected)

        self.app.call_from_thread(
            self._update_status,
            f"Measuring loudness... 0/{len(self._files)}",
        )

        updated: list[Mp3FileInfo] = list(self._files)
        done_count = 0

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            future_to_index = {
                pool.submit(measure_loudness, info.path): i
                for i, info in enumerate(updated)
            }

            for future in as_completed(future_to_index):
                if worker.is_cancelled:
                    pool.shutdown(wait=False, cancel_futures=True)
                    return

                i = future_to_index[future]
                done_count += 1

                try:
                    lufs = future.result()
                    updated[i] = updated[i].with_loudness(lufs)
                    self.app.call_from_thread(
                        self._update_row_loudness, i, updated[i].loudness_display
                    )
                except Exception:
                    self.app.call_from_thread(
                        self._update_row_loudness, i, "Error"
                    )

                self.app.call_from_thread(
                    self._update_status,
                    f"Measuring loudness... {done_count}/{len(updated)}",
                )

        self._files = tuple(updated)
        self.app.call_from_thread(self._scan_complete)

    def _add_row(self, index: int, info: Mp3FileInfo, loudness: str) -> None:
        table = self.query_one("#file-table", DataTable)
        table.add_row(
            str(index + 1),
            info.filename,
            info.size_display,
            loudness,
            key=str(index),
        )

    def _update_row_loudness(self, index: int, loudness: str) -> None:
        table = self.query_one("#file-table", DataTable)
        table.update_cell(str(index), self._loudness_col_key, loudness)

    def _update_status(self, text: str) -> None:
        self.query_one("#scan-status", Label).update(text)

    def _scan_complete(self) -> None:
        self._update_status(
            f"Found {len(self._files)} MP3 files in {self._dir_path}"
        )
        self._update_stats()
        self.query_one("#start-btn", Button).disabled = False
        self.query_one("#target-input", Input).focus()

    def _update_stats(self) -> None:
        values = [
            f.loudness_lufs
            for f in self._files
            if f.loudness_lufs is not None
        ]
        if not values:
            return

        mean = statistics.mean(values)
        median = statistics.median(values)
        self.query_one("#stats-label", Label).update(
            f"Average: {mean:.1f} LUFS  |  Median: {median:.1f} LUFS"
        )

    def _show_error(self, message: str) -> None:
        self.query_one("#error-label", Label).update(message)

    def action_back(self) -> None:
        self.dismiss(None)
