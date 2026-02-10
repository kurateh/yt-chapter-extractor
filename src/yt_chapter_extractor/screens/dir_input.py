from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label


class DirInputScreen(Screen[Path | None]):
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

    #dir-input {
        margin-bottom: 1;
    }

    #load-btn {
        width: 100%;
        margin-top: 1;
    }

    #error-label {
        color: $error;
        text-align: center;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="container"):
                yield Label("Audio Decibel Normalization", id="title")
                yield Input(
                    placeholder="Enter directory path...",
                    id="dir-input",
                )
                yield Button(
                    "Load Directory", id="load-btn", variant="primary"
                )
                yield Label("", id="error-label")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#dir-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "dir-input":
            self._validate_and_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "load-btn":
            self._validate_and_submit()

    def _validate_and_submit(self) -> None:
        raw = self.query_one("#dir-input", Input).value.strip()
        if not raw:
            self._show_error("Please enter a directory path.")
            return

        dir_path = Path(raw).expanduser().resolve()

        if not dir_path.exists():
            self._show_error("Directory does not exist.")
            return

        if not dir_path.is_dir():
            self._show_error("Path is not a directory.")
            return

        mp3_files = list(dir_path.glob("*.mp3")) + list(
            dir_path.glob("*.MP3")
        )
        if not mp3_files:
            self._show_error("No MP3 files found in this directory.")
            return

        self.dismiss(dir_path)

    def _show_error(self, message: str) -> None:
        self.query_one("#error-label", Label).update(message)

    def action_back(self) -> None:
        self.dismiss(None)
