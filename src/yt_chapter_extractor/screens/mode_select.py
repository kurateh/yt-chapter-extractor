from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label


class ModeSelectScreen(Screen[str | None]):
    CSS = """
    #container {
        align: center middle;
        width: 60;
        height: auto;
        padding: 2 4;
    }

    #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
    }

    .mode-btn {
        width: 100%;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="container"):
                yield Label("Select Mode", id="title")
                yield Button(
                    "YouTube MP3 Extraction",
                    id="youtube-btn",
                    variant="primary",
                    classes="mode-btn",
                )
                yield Button(
                    "Audio Decibel Normalization",
                    id="normalize-btn",
                    variant="warning",
                    classes="mode-btn",
                )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#youtube-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "youtube-btn":
            self.dismiss("youtube")
        elif event.button.id == "normalize-btn":
            self.dismiss("normalize")

    def action_quit(self) -> None:
        self.dismiss(None)
