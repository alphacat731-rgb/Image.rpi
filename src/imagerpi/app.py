from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import select
import threading
import time

from .config import AppConfig, DisplayMode, Palette, Quality
from .loader import ImageLoader, LoadEvent, LoadedImage, list_images
from .renderer import Renderer
from .terminal import terminal_session, terminal_size


@dataclass(slots=True)
class LoadedResult:
    image: LoadedImage | None
    error: Exception | None


class ImageApp:
    MAIN = "main"
    OPTIONS = "options"
    BROWSER = "browser"
    VIEWER = "viewer"

    def __init__(self, initial: str | None = None) -> None:
        self.config = AppConfig.from_environment()
        self.renderer = Renderer(self.config)
        self.loader = ImageLoader(self.config)

        self.quality = self.config.default_quality
        self.display_mode = self.config.default_display_mode
        self.palette = self.config.default_palette
        self.config.apply_palette(self.palette)

        self.current: LoadedImage | None = None
        self.screen = self.MAIN
        self.menu_index = 0
        self.options_index = 0

        raw_path = Path(initial).expanduser().resolve() if initial else Path.cwd()
        self.current_dir = raw_path.parent if raw_path.is_file() else raw_path

        self.entries = list_images(self.current_dir)
        self.index = 0

        if initial and raw_path.is_file():
            try:
                self.index = self.entries.index(raw_path)
            except ValueError:
                self.entries.append(raw_path)
                self.entries.sort(key=lambda p: p.name.casefold())
                self.index = self.entries.index(raw_path)

        self.help_overlay = False
        self.info_overlay = False
        self.status = ""

        self.load_queue: queue.Queue[LoadEvent | LoadedResult] = queue.Queue()
        self.loading = False
        self.running = True
        self._progress = LoadEvent("open", 0.0, "Loading...")
        self._last_signature: tuple | None = None
        self._last_render_time = 0.0

    def run(self) -> None:
        with terminal_session(self.config.terminal_font) as term:
            force = True

            while self.running:
                self._drain_load()
                signature = self._render_signature()

                now = time.monotonic()
                render_allowed = (
                    not self.loading
                    or now - self._last_render_time >= 1.0 / 12.0
                    or self._progress.progress >= 1.0
                )

                if force or (
                    signature != self._last_signature and render_allowed
                ):
                    term.write(self._render())
                    self._last_signature = signature
                    self._last_render_time = now
                    force = False

                key = self._read_key_with_timeout(
                    term,
                    1.0 / self.config.render_fps,
                )
                if key:
                    self._handle_key(key)
                    force = True

    def _render_signature(self) -> tuple:
        current_path = str(self.current.path) if self.current else None
        size = terminal_size()

        progress = (
            self._progress.stage,
            round(self._progress.progress, 3),
            self._progress.message,
        ) if self.loading else None

        return (
            self.screen,
            self.loading,
            progress,
            current_path,
            len(self.entries),
            self.index,
            self.menu_index,
            self.options_index,
            self.help_overlay,
            self.info_overlay,
            self.status,
            self.quality,
            self.display_mode,
            self.palette,
            size.columns,
            size.lines,
        )

    def _render(self) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)

        if self.loading:
            return self.renderer.progress(
                self._progress.stage,
                self._progress.progress,
                self._progress.message,
            )

        if self.screen == self.MAIN:
            return self.renderer.main_menu(cols, rows, self.menu_index)

        if self.screen == self.OPTIONS:
            return self.renderer.options_menu(
                cols,
                rows,
                self.options_index,
                self.quality,
                self.display_mode,
                self.palette,
            )

        return self.renderer.frame(
            self.current,
            self.quality,
            self.status,
            display_mode=self.display_mode,
            browser=self.screen == self.BROWSER,
            browser_entries=self.entries,
            browser_index=self.index,
            help_overlay=self.help_overlay,
            info_overlay=self.info_overlay,
        )

    def _start_load(self, path: Path) -> None:
        if self.loading:
            return

        self.loading = True
        self.status = f"Loading {path.name}..."
        self._progress = LoadEvent("open", 0.0, "Opening image...")
        cells = (terminal_size().columns, terminal_size().lines)

        def worker() -> None:
            try:
                loaded = self.loader.load(
                    path,
                    self.quality,
                    cells,
                    self.load_queue.put,
                )
                self.load_queue.put(LoadedResult(loaded, None))
            except Exception as exc:
                self.load_queue.put(LoadedResult(None, exc))

        threading.Thread(
            target=worker,
            name="image-loader",
            daemon=True,
        ).start()

    def _drain_load(self) -> None:
        while True:
            try:
                item = self.load_queue.get_nowait()
            except queue.Empty:
                return

            if isinstance(item, LoadEvent):
                self._progress = item
                continue

            self.loading = False
            if item.error:
                self.status = f"Load error: {item.error}"
                self.screen = self.VIEWER
                continue

            self.current = item.image
            self.status = f"Loaded {self.current.path.name}"
            self.entries = list_images(self.current.path.parent)
            self.current_dir = self.current.path.parent
            self.screen = self.VIEWER

            try:
                self.index = self.entries.index(self.current.path)
            except ValueError:
                self.index = 0

    def _read_key_with_timeout(self, term, timeout: float) -> str:
        if not term.enabled:
            return "q"

        ready, _, _ = select.select([term.fd], [], [], timeout)
        return term.read_key() if ready else ""

    def _handle_key(self, key: str) -> None:
        self.status = ""

        if key.startswith("MOUSE:PRESS:"):
            self._handle_mouse(key)
            return

        if self.screen == self.MAIN:
            self._handle_main_key(key)
            return

        if self.screen == self.OPTIONS:
            self._handle_options_key(key)
            return

        if key in {"q", "Q"}:
            self.running = False
            return

        if key == "ESC":
            self._go_main()
            return

        if key in {"h", "H"}:
            self.help_overlay = not self.help_overlay
            self.info_overlay = False
            return

        if key in {"i", "I"}:
            self.info_overlay = not self.info_overlay
            self.help_overlay = False
            return

        if self.screen == self.BROWSER:
            self._handle_browser_key(key)
            return

        if key in {"a", "A"} and not self.loading:
            self.display_mode = DisplayMode.next(self.display_mode)
            self.status = f"Display mode: {self.display_mode.label}"
            return

        if key in {"p", "P"} and not self.loading:
            self.palette = Palette.next(self.palette)
            self.config.apply_palette(self.palette)
            self.status = f"Palette: {self.palette.label}"
            return

        if key in {"r", "R"} and not self.loading:
            self.quality = Quality.next(self.quality)
            self.status = f"Quality: {self.quality.label}"
            if self.current is not None:
                self._start_load(self.current.path)
            return

        if key in {"o", "O"}:
            self._open_browser()
            return

        if self.current is None or self.loading:
            return

        if key == "RIGHT":
            self._step_image(1)
        elif key == "LEFT":
            self._step_image(-1)

    def _handle_main_key(self, key: str) -> None:
        if key in {"q", "Q", "ESC"}:
            self.running = False
            return

        if key == "UP":
            self.menu_index = (self.menu_index - 1) % 3
        elif key == "DOWN":
            self.menu_index = (self.menu_index + 1) % 3
        elif key in {"1", "2", "3"}:
            self.menu_index = int(key) - 1
            self._activate_main()
        elif key in {"\n", "\r", "RIGHT"}:
            self._activate_main()

    def _activate_main(self) -> None:
        if self.menu_index == 0:
            self._open_browser()
        elif self.menu_index == 1:
            self.screen = self.OPTIONS
            self.options_index = 0
        else:
            self.running = False

    def _handle_options_key(self, key: str) -> None:
        if key in {"ESC", "b", "B"}:
            self._go_main()
            return

        if key == "UP":
            self.options_index = (self.options_index - 1) % 4
        elif key == "DOWN":
            self.options_index = (self.options_index + 1) % 4
        elif key in {"LEFT", "RIGHT", "\n", "\r"}:
            if self.options_index == 0:
                self.quality = (
                    Quality.next(self.quality)
                    if key != "LEFT"
                    else list(Quality)[
                        (list(Quality).index(self.quality) - 1) % len(Quality)
                    ]
                )
                self.status = f"Quality: {self.quality.label}"
            elif self.options_index == 1:
                self.display_mode = (
                    DisplayMode.next(self.display_mode)
                    if key != "LEFT"
                    else list(DisplayMode)[
                        (list(DisplayMode).index(self.display_mode) - 1) % len(DisplayMode)
                    ]
                )
                self.status = f"Display mode: {self.display_mode.label}"
            elif self.options_index == 2:
                self.palette = (
                    Palette.next(self.palette)
                    if key != "LEFT"
                    else list(Palette)[
                        (list(Palette).index(self.palette) - 1) % len(Palette)
                    ]
                )
                self.config.apply_palette(self.palette)
                self.status = f"Palette: {self.palette.label}"
            elif self.options_index == 3:
                self._go_main()

    def _handle_browser_key(self, key: str) -> None:
        if key == "UP":
            self.index = max(0, self.index - 1)
        elif key == "DOWN":
            self.index = min(
                max(0, len(self.entries) - 1),
                self.index + 1,
            )
        elif key in {"\n", "\r", "RIGHT"} and self.entries:
            self._start_load(self.entries[self.index])

    def _handle_mouse(self, key: str) -> None:
        parts = key.split(":")
        if len(parts) != 5:
            return

        try:
            _, _, _, x_text, y_text = parts
            x = int(x_text)
            y = int(y_text)
        except ValueError:
            return

        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)

        if self.screen == self.MAIN:
            hit = self.renderer.main_menu_hit(x, y, cols, rows)
            if hit is not None:
                self.menu_index = hit
                self._activate_main()
            return

        if self.screen == self.OPTIONS:
            first_row = max(6, rows // 2 - 4)
            left = max(2, (cols - min(68, max(32, cols - 10))) // 2)
            panel_w = min(68, max(32, cols - 10))
            if left <= x <= left + panel_w:
                for i in range(4):
                    row = first_row + i * 2
                    if row <= y <= row + 1:
                        self.options_index = i
                        if i == 3:
                            self._go_main()
                        else:
                            self._change_option(1)
                        return
            return

        if self.screen == self.BROWSER:
            visible = max(1, rows - 4 - 2)
            start = max(
                0,
                min(
                    self.index - visible // 2,
                    max(0, len(self.entries) - visible),
                ),
            )
            clicked_row = y - 6
            if clicked_row >= 0:
                idx = start + clicked_row
                if 0 <= idx < len(self.entries):
                    self.index = idx
                    self._start_load(self.entries[idx])

    def _change_option(self, direction: int) -> None:
        if self.options_index == 0:
            values = list(Quality)
            self.quality = values[
                (values.index(self.quality) + direction) % len(values)
            ]
            self.status = f"Quality: {self.quality.label}"
        elif self.options_index == 1:
            values = list(DisplayMode)
            self.display_mode = values[
                (values.index(self.display_mode) + direction) % len(values)
            ]
            self.status = f"Display mode: {self.display_mode.label}"
        elif self.options_index == 2:
            values = list(Palette)
            self.palette = values[
                (values.index(self.palette) + direction) % len(values)
            ]
            self.config.apply_palette(self.palette)
            self.status = f"Palette: {self.palette.label}"

    def _open_browser(self) -> None:
        self.help_overlay = False
        self.info_overlay = False
        self.entries = list_images(self.current_dir)

        if self.entries:
            self.index = min(self.index, len(self.entries) - 1)
        self.screen = self.BROWSER

    def _go_main(self) -> None:
        if self.loading:
            return
        self.help_overlay = False
        self.info_overlay = False
        self.status = ""
        self.screen = self.MAIN

    def _step_image(self, delta: int) -> None:
        if not self.entries:
            return
        self.index = (self.index + delta) % len(self.entries)
        self._start_load(self.entries[self.index])


def main(path: str | None = None) -> None:
    ImageApp(path).run()
