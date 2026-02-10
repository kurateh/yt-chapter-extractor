from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label


class NormSettingsScreen(Screen[tuple[bool, float] | None]):
    CSS = """
    #norm-container {
        height: auto;
        padding: 2 4;
    }

    #description {
        margin-bottom: 2;
    }

    #enable-checkbox {
        margin-bottom: 1;
    }

    #lufs-row {
        height: auto;
        align: left middle;
        margin-top: 1;
        margin-bottom: 1;
        padding-left: 4;
    }

    #lufs-label {
        width: auto;
        margin-right: 1;
    }

    #lufs-input {
        width: 20;
    }

    #lufs-unit {
        width: auto;
        margin-left: 1;
    }

    #error-label {
        color: $error;
        margin-top: 1;
        padding-left: 4;
    }

    #bottom-bar {
        height: 3;
        align: center middle;
        dock: bottom;
    }

    #next-btn {
        width: 30;
    }
    """

    BINDINGS = [
        ("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="norm-container"):
            yield Label(
                "Audio Loudness Normalization",
                id="description",
            )
            yield Checkbox(
                "Enable loudness normalization",
                id="enable-checkbox",
            )
            with Horizontal(id="lufs-row"):
                yield Label("Target Loudness:", id="lufs-label")
                yield Input(
                    value="-19.0",
                    id="lufs-input",
                    type="number",
                    disabled=True,
                )
                yield Label("LUFS", id="lufs-unit")
            yield Label("", id="error-label")
        with Vertical(id="bottom-bar"):
            yield Button("Next", id="next-btn", variant="primary")
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "enable-checkbox":
            self.query_one("#lufs-input", Input).disabled = not event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next-btn":
            self._submit()

    def _submit(self) -> None:
        enabled = self.query_one("#enable-checkbox", Checkbox).value

        if not enabled:
            self.dismiss((False, 0.0))
            return

        raw = self.query_one("#lufs-input", Input).value.strip()

        try:
            target = float(raw)
        except ValueError:
            self._show_error("Please enter a valid number.")
            return

        if not -70.0 <= target <= 0.0:
            self._show_error("Target must be between -70.0 and 0.0 LUFS.")
            return

        self.dismiss((True, target))

    def _show_error(self, message: str) -> None:
        self.query_one("#error-label", Label).update(message)

    def action_back(self) -> None:
        self.dismiss(None)
