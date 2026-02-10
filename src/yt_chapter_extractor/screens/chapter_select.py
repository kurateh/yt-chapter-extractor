from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Label, Static

from ..models import Chapter


class ChapterSelectScreen(Screen[list[Chapter]]):
    CSS = """
    #header-bar {
        height: 3;
        padding: 1 2;
    }

    #video-title {
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

    #chapter-list {
        height: 1fr;
        padding: 0 2;
    }

    .chapter-checkbox {
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

    def __init__(self, video_title: str, chapters: tuple[Chapter, ...]) -> None:
        super().__init__()
        self._video_title = video_title
        self._chapters = chapters

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f" {self._video_title}", id="header-bar")
        with Horizontal(id="button-bar"):
            yield Button("Select All [a]", id="select-all-btn", variant="default")
            yield Button("Deselect All [n]", id="deselect-all-btn", variant="default")
        with VerticalScroll(id="chapter-list"):
            for chapter in self._chapters:
                yield Checkbox(
                    f"{chapter.title}  ({chapter.duration_str})",
                    value=True,
                    id=f"chapter-{chapter.index}",
                    classes="chapter-checkbox",
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
            self._chapters[i]
            for i, checkbox in enumerate(self.query(Checkbox))
            if checkbox.value
        ]
        if not selected:
            self.query_one("#error-label", Label).update(
                "Please select at least one chapter."
            )
            return
        self.dismiss(selected)

    def action_go_back(self) -> None:
        self.dismiss([])
