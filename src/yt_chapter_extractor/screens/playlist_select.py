from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Label, Static

from ..models import PlaylistEntry


class PlaylistSelectScreen(Screen[list[PlaylistEntry]]):
    CSS = """
    #header-bar {
        height: 3;
        padding: 1 2;
    }

    #playlist-title {
        text-style: bold;
    }

    #button-bar {
        height: 3;
        padding: 0 2;
        align: left middle;
    }

    #button-bar Button {
        margin-right: 1;
    }

    #entry-list {
        height: 1fr;
        padding: 0 2;
    }

    .entry-checkbox {
        margin-bottom: 0;
    }

    #bottom-bar {
        height: 3;
        align: center middle;
        dock: bottom;
    }

    #next-btn {
        width: 30;
    }

    #error-label {
        color: $error;
        text-align: center;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("a", "select_all", "Select All"),
        ("n", "deselect_all", "Deselect All"),
    ]

    def __init__(
        self, playlist_title: str, entries: tuple[PlaylistEntry, ...]
    ) -> None:
        super().__init__()
        self._playlist_title = playlist_title
        self._entries = entries

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f" {self._playlist_title}", id="header-bar")
        with Horizontal(id="button-bar"):
            yield Button("Select All [a]", id="select-all-btn", variant="default")
            yield Button(
                "Deselect All [n]", id="deselect-all-btn", variant="default"
            )
        with VerticalScroll(id="entry-list"):
            for entry in self._entries:
                duration = f"  ({entry.duration_str})" if entry.duration > 0 else ""
                yield Checkbox(
                    f"{entry.index + 1}. {entry.title}{duration}",
                    value=True,
                    id=f"entry-{entry.index}",
                    classes="entry-checkbox",
                )
        with Horizontal(id="bottom-bar"):
            yield Label("", id="error-label")
            yield Button("Next", id="next-btn", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select-all-btn":
            self.action_select_all()
        elif event.button.id == "deselect-all-btn":
            self.action_deselect_all()
        elif event.button.id == "next-btn":
            self._proceed()

    def action_select_all(self) -> None:
        for checkbox in self.query(Checkbox):
            checkbox.value = True

    def action_deselect_all(self) -> None:
        for checkbox in self.query(Checkbox):
            checkbox.value = False

    def _proceed(self) -> None:
        selected = [
            self._entries[i]
            for i, checkbox in enumerate(self.query(Checkbox))
            if checkbox.value
        ]
        if not selected:
            self.query_one("#error-label", Label).update(
                "Please select at least one video."
            )
            return
        self.dismiss(selected)

    def action_go_back(self) -> None:
        self.dismiss([])
