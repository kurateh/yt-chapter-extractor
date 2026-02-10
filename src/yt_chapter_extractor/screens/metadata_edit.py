from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from ..models import Chapter, TrackInfo
from ..youtube import sanitize_filename


class MetadataEditScreen(Screen[list[TrackInfo]]):
    CSS = """
    #mode-bar {
        height: 3;
        padding: 0 2;
        align: left middle;
    }

    #mode-bar Button {
        margin-right: 1;
    }

    #edit-area {
        height: 1fr;
        padding: 0 2;
    }

    .track-row {
        height: auto;
        padding: 1 0;
        border-bottom: dashed $surface-lighten-2;
    }

    .track-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .field-row {
        height: 3;
        margin-bottom: 0;
    }

    .field-label {
        width: 12;
        padding-top: 1;
    }

    .field-input {
        width: 1fr;
    }

    #bulk-area {
        padding: 2;
        height: auto;
    }

    #bulk-area .field-row {
        height: 3;
        margin-bottom: 1;
    }

    #bottom-bar {
        height: 3;
        align: center middle;
        dock: bottom;
    }

    #start-btn {
        width: 30;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, chapters: list[Chapter]) -> None:
        super().__init__()
        self._chapters = chapters

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="mode-bar"):
            yield Button(
                "Individual Edit",
                id="individual-btn",
                variant="primary",
            )
            yield Button(
                "Bulk Edit",
                id="bulk-btn",
                variant="default",
            )

        with VerticalScroll(id="edit-area"):
            for chapter in self._chapters:
                default_name = sanitize_filename(chapter.title)
                with Vertical(classes="track-row", id=f"track-{chapter.index}"):
                    yield Static(
                        f"Chapter {chapter.index + 1}: {chapter.title}",
                        classes="track-title",
                    )
                    with Horizontal(classes="field-row"):
                        yield Label("Filename *", classes="field-label")
                        yield Input(
                            value=default_name,
                            placeholder="Filename (required)",
                            id=f"filename-{chapter.index}",
                            classes="field-input",
                        )
                    with Horizontal(classes="field-row"):
                        yield Label("Title", classes="field-label")
                        yield Input(
                            placeholder="Song title (defaults to filename)",
                            id=f"title-{chapter.index}",
                            classes="field-input",
                        )
                    with Horizontal(classes="field-row"):
                        yield Label("Artist", classes="field-label")
                        yield Input(
                            placeholder="Artist name",
                            id=f"artist-{chapter.index}",
                            classes="field-input",
                        )
                    with Horizontal(classes="field-row"):
                        yield Label("Album", classes="field-label")
                        yield Input(
                            placeholder="Album name",
                            id=f"album-{chapter.index}",
                            classes="field-input",
                        )

        with Vertical(id="bulk-area"):
            yield Static("Apply to all selected chapters:", classes="track-title")
            with Horizontal(classes="field-row"):
                yield Label("Title", classes="field-label")
                yield Input(
                    placeholder="Song title for all",
                    id="bulk-title",
                    classes="field-input",
                )
            with Horizontal(classes="field-row"):
                yield Label("Artist", classes="field-label")
                yield Input(
                    placeholder="Artist for all",
                    id="bulk-artist",
                    classes="field-input",
                )
            with Horizontal(classes="field-row"):
                yield Label("Album", classes="field-label")
                yield Input(
                    placeholder="Album for all",
                    id="bulk-album",
                    classes="field-input",
                )
            yield Button(
                "Apply to All",
                id="apply-bulk-btn",
                variant="warning",
            )

        with Horizontal(id="bottom-bar"):
            yield Button("Start Download", id="start-btn", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#bulk-area").display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "individual-btn":
            self._set_individual_mode()
        elif event.button.id == "bulk-btn":
            self._set_bulk_mode()
        elif event.button.id == "apply-bulk-btn":
            self._apply_bulk()
        elif event.button.id == "start-btn":
            self._proceed()

    def _set_individual_mode(self) -> None:
        self.query_one("#individual-btn", Button).variant = "primary"
        self.query_one("#bulk-btn", Button).variant = "default"
        self.query_one("#edit-area").display = True
        self.query_one("#bulk-area").display = False

    def _set_bulk_mode(self) -> None:
        self.query_one("#individual-btn", Button).variant = "default"
        self.query_one("#bulk-btn", Button).variant = "primary"
        self.query_one("#edit-area").display = True
        self.query_one("#bulk-area").display = True

    def _apply_bulk(self) -> None:
        bulk_title = self.query_one("#bulk-title", Input).value.strip()
        bulk_artist = self.query_one("#bulk-artist", Input).value.strip()
        bulk_album = self.query_one("#bulk-album", Input).value.strip()

        for chapter in self._chapters:
            if bulk_title:
                self.query_one(
                    f"#title-{chapter.index}", Input
                ).value = bulk_title
            if bulk_artist:
                self.query_one(
                    f"#artist-{chapter.index}", Input
                ).value = bulk_artist
            if bulk_album:
                self.query_one(
                    f"#album-{chapter.index}", Input
                ).value = bulk_album

        if not any([bulk_title, bulk_artist, bulk_album]):
            self.notify("No bulk values to apply.", severity="warning")
            return

        self.notify("Bulk values applied to all chapters.")

    def _proceed(self) -> None:
        tracks: list[TrackInfo] = []

        for chapter in self._chapters:
            filename = self.query_one(
                f"#filename-{chapter.index}", Input
            ).value.strip()

            if not filename:
                self.notify(
                    f"Filename is required for chapter: {chapter.title}",
                    severity="error",
                )
                return

            title = self.query_one(
                f"#title-{chapter.index}", Input
            ).value.strip()
            artist = self.query_one(
                f"#artist-{chapter.index}", Input
            ).value.strip()
            album = self.query_one(
                f"#album-{chapter.index}", Input
            ).value.strip()

            tracks.append(
                TrackInfo(
                    chapter=chapter,
                    filename=sanitize_filename(filename),
                    title=title,
                    artist=artist,
                    album=album,
                )
            )

        self.dismiss(tracks)

    def action_go_back(self) -> None:
        self.dismiss([])
