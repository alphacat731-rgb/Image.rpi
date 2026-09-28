from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import select
import threading
import time

from .config import (
    AppConfig,
    ColorDepth,
    DisplayMode,
    FONT_PRESETS,
    Language,
    Palette,
    Quality,
    save_user_config,
)
from .i18n import tr
from .loader import ImageLoader, LoadEvent, LoadedImage, ScanEvent, list_images
from .renderer import Renderer
from .terminal import terminal_session, terminal_size


@dataclass(slots=True)
class LoadedResult:
    image: LoadedImage | None
    error: Exception | None


@dataclass(slots=True)
class ScanResult:
    entries: list[Path] | None
    error: Exception | None


class ImageApp:
    STARTUP = "startup"
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
        self.color_depth = self.config.color_depth
        self.language = self.config.language
        self.recursive_scan = self.config.recursive_scan
        self.touch_controls = self.config.touch_controls

        self.config.apply_palette(self.palette)

        self.current: LoadedImage | None = None
        self.current_dir = Path.cwd().resolve()
        self.library_root = self.current_dir
        self.pending_open: Path | None = None

        raw_path = Path(initial).expanduser().resolve() if initial else None
        if raw_path is not None:
            if raw_path.is_file():
                self.current_dir = raw_path.parent
                self.pending_open = raw_path
            elif raw_path.is_dir():
                self.current_dir = raw_path

        self.entries: list[Path] = []
        self.index = 0

        self.screen = self.STARTUP
        self.menu_index = 0
        self.options_index = 0

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.help_overlay = False
        self.info_overlay = False
        self.status = ""

        self.work_queue: queue.Queue[
            ScanEvent | ScanResult | LoadEvent | LoadedResult
        ] = queue.Queue()

        self.scanning = False
        self._scan_again = False
        self.loading = False
        self.running = True

        self._scan_progress = 0.0
        self._scan_message = "Scanning..."
        self._scan_found = 0

        self._progress = LoadEvent("open", 0.0, "Opening image...")
        self._last_signature: tuple | None = None
        self._last_render_time = 0.0
        self._last_terminal_size = terminal_size()

        self._start_scan()

    def run(self) -> None:
        try:
            with terminal_session(
                self.config.terminal_font,
                mouse=self.touch_controls,
            ) as term:
                force = True

                while self.running:
                    self._drain_work()
                    self._check_terminal_resize()

                    signature = self._render_signature()
                    now = time.monotonic()
                    render_allowed = (
                        not (self.scanning or self.loading)
                        or now - self._last_render_time >= 1.0 / 12.0
                    )

                    if force or (
                        signature != self._last_signature
                        and render_allowed
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
        finally:
            self._save_settings()

    def _save_settings(self) -> None:
        overrides: dict[str, dict[str, str]] = {}
        raw_overrides = self.config.palette_overrides or {}

        for palette_name, colors in raw_overrides.items():
            overrides[palette_name] = {
                key: "#{:02X}{:02X}{:02X}".format(*value)
                for key, value in colors.items()
            }

        save_user_config(
            palette=self.palette,
            display_mode=self.display_mode,
            quality=self.quality,
            language=self.language,
            color_depth=self.color_depth,
            recursive_scan=self.recursive_scan,
            touch_controls=self.touch_controls,
            terminal_font=self.config.terminal_font,
            palette_overrides=overrides,
        )

    def _start_scan(self) -> None:
        if self.scanning:
            self._scan_again = True
            return

        self.scanning = True
        self._scan_progress = 0.0
        self._scan_found = 0
        self._scan_message = str(self.current_dir)

        root = self.current_dir
        recursive = self.recursive_scan

        def worker() -> None:
            try:
                entries = list_images(
                    root,
                    recursive=recursive,
                    on_event=self.work_queue.put,
                )
                self.work_queue.put(ScanResult(entries, None))
            except Exception as exc:
                self.work_queue.put(ScanResult(None, exc))

        threading.Thread(
            target=worker,
            name="library-scanner",
            daemon=True,
        ).start()

    def _start_load(self, path: Path) -> None:
        if self.loading:
            return

        self.loading = True
        self._progress = LoadEvent(
            "open",
            0.0,
            tr(self.language, "opening"),
        )
        cells = (terminal_size().columns, terminal_size().lines)
        quality = self.quality

        def worker() -> None:
            try:
                loaded = self.loader.load(
                    path,
                    quality,
                    cells,
                    self.work_queue.put,
                )
                self.work_queue.put(LoadedResult(loaded, None))
            except Exception as exc:
                self.work_queue.put(LoadedResult(None, exc))

        threading.Thread(
            target=worker,
            name="image-loader",
            daemon=True,
        ).start()

    def _drain_work(self) -> None:
        while True:
            try:
                item = self.work_queue.get_nowait()
            except queue.Empty:
                return

            if isinstance(item, ScanEvent):
                self._scan_progress = item.progress
                self._scan_message = item.message
                self._scan_found = item.found
                continue

            if isinstance(item, ScanResult):
                self.scanning = False
                if item.error:
                    self.status = f"Scan error: {item.error}"
                    self.entries = []
                else:
                    self.entries = item.entries or []
                    self.library_root = self.current_dir
                    self._sync_index()

                if self._scan_again:
                    self._scan_again = False
                    self._start_scan()

                if self.screen == self.STARTUP:
                    if self.pending_open is not None:
                        try:
                            self.index = self.entries.index(self.pending_open)
                            pending = self.pending_open
                            self.pending_open = None
                            self._start_load(pending)
                        except ValueError:
                            self.pending_open = None
                            self.status = "Requested image was not found in the library."
                            self.screen = self.MAIN
                    else:
                        self.screen = self.MAIN

                continue

            if isinstance(item, LoadEvent):
                self._progress = item
                continue

            self.loading = False
            if item.error:
                self.status = f"Load error: {item.error}"
                self.info_overlay = False
                continue

            self.current = item.image
            self.current_dir = self.current.path.parent
            self._sync_index()
            self.zoom = 1.0
            self.pan_x = 0.0
            self.pan_y = 0.0
            self.screen = self.VIEWER
            self.status = f"{self.current.path.name}"

    def _sync_index(self) -> None:
        if not self.entries:
            self.index = 0
            return
        if self.current is not None:
            try:
                self.index = self.entries.index(self.current.path)
                return
            except ValueError:
                pass
        self.index = max(0, min(self.index, len(self.entries) - 1))

    def _check_terminal_resize(self) -> None:
        size = terminal_size()
        old = self._last_terminal_size
        if size == old:
            return

        self._last_terminal_size = size
        if (
            self.current is not None
            and self.screen == self.VIEWER
            and not self.loading
        ):
            self._start_load(self.current.path)

    def _render_signature(self) -> tuple:
        size = terminal_size()
        progress = (
            self._progress.stage,
            round(self._progress.progress, 3),
            self._progress.message,
        ) if self.loading else None
        scan = (
            round(self._scan_progress, 3),
            self._scan_message,
            self._scan_found,
        ) if self.scanning else None

        return (
            self.screen,
            self.scanning,
            scan,
            self.loading,
            progress,
            self.index,
            self.menu_index,
            self.options_index,
            self.help_overlay,
            self.info_overlay,
            self.status,
            self.quality,
            self.display_mode,
            self.palette,
            self.color_depth,
            self.language,
            self.recursive_scan,
            self.touch_controls,
            self.zoom,
            round(self.pan_x, 3),
            round(self.pan_y, 3),
            str(self.current.path) if self.current else None,
            len(self.entries),
            size.columns,
            size.lines,
        )

    def _render(self) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)

        if self.scanning:
            return self.renderer.progress(
                "library",
                self._scan_progress,
                tr(
                    self.language,
                    "scanning",
                    path=self._scan_message,
                ) + f"  [{self._scan_found}]",
                language=self.language,
            )

        if self.loading:
            return self.renderer.progress(
                "image",
                self._progress.progress,
                self._progress.message,
                language=self.language,
            )

        if self.screen == self.STARTUP:
            return self.renderer.progress(
                "library",
                1.0,
                tr(self.language, "ready"),
                language=self.language,
            )

        if self.screen == self.MAIN:
            return self.renderer.main_menu(
                cols,
                rows,
                self.menu_index,
                image_count=len(self.entries),
                language=self.language,
                palette=self.palette,
            )

        if self.screen == self.OPTIONS:
            return self.renderer.options_menu(
                cols,
                rows,
                self.options_index,
                quality=self.quality,
                display_mode=self.display_mode,
                palette=self.palette,
                recursive_scan=self.recursive_scan,
                touch_controls=self.touch_controls,
                language=self.language,
                color_depth=self.color_depth,
                terminal_font=self.config.terminal_font,
                image_count=len(self.entries),
            )

        if self.screen == self.BROWSER:
            return self.renderer.browser(
                cols,
                rows,
                self.entries,
                self.index,
                language=self.language,
                root=self.library_root,
            )

        return self.renderer.frame(
            self.current,
            self.quality,
            self.status,
            display_mode=self.display_mode,
            language=self.language,
            browser_index=self.index,
            image_count=len(self.entries),
            zoom=self.zoom,
            pan_x=self.pan_x,
            pan_y=self.pan_y,
            info_overlay=self.info_overlay,
            help_overlay=self.help_overlay,
        )

    def _read_key_with_timeout(self, term, timeout: float) -> str:
        if not term.enabled:
            return "q"
        ready, _, _ = select.select([term.fd], [], [], timeout)
        return term.read_key() if ready else ""

    def _handle_key(self, key: str) -> None:
        if key.startswith("MOUSE:PRESS:"):
            self._handle_mouse(key)
            return

        if self.screen == self.MAIN:
            self._handle_main_key(key)
            return

        if self.screen == self.OPTIONS:
            self._handle_options_key(key)
            return

        if key == "F5" and self.screen in {self.MAIN, self.BROWSER, self.OPTIONS}:
            self._start_scan()
            self.status = tr(self.language, "loading_library")
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

        if key in {"a", "A"}:
            self.display_mode = DisplayMode.next(self.display_mode)
            self.status = self.display_mode.label
            return

        if key in {"p", "P"}:
            self.palette = Palette.next(self.palette)
            self.config.apply_palette(self.palette)
            self.status = self.palette.label
            return

        if key in {"+", "="}:
            self._zoom(1)
            return

        if key in {"-", "_"}:
            self._zoom(-1)
            return

        if key == "0":
            self._fit()
            return

        if self.zoom > 1.0:
            if key == "LEFT":
                self.pan_x = max(-1.0, self.pan_x - 0.15)
            elif key == "RIGHT":
                self.pan_x = min(1.0, self.pan_x + 0.15)
            elif key == "UP":
                self.pan_y = max(-1.0, self.pan_y - 0.15)
            elif key == "DOWN":
                self.pan_y = min(1.0, self.pan_y + 0.15)
            return

        if key in {"r", "R"}:
            self.quality = Quality.next(self.quality)
            self._start_load(self.current.path) if self.current else None
            return

        if key in {"o", "O"}:
            self._open_browser()
            return

        if self.current is None or self.loading:
            return

        if key in {"RIGHT", "n", "N", " "}:
            self._step_image(1)
        elif key in {"LEFT", "b", "B"}:
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
            self.options_index = (self.options_index - 1) % 10
            return
        if key == "DOWN":
            self.options_index = (self.options_index + 1) % 10
            return

        if key not in {"LEFT", "RIGHT", "\n", "\r", " "}:
            return

        direction = -1 if key == "LEFT" else 1

        if self.options_index == 0:
            self.quality = self._cycle(Quality, self.quality, direction)
            self.status = f"{tr(self.language, 'image_quality')}: {self.quality.label}"

        elif self.options_index == 1:
            self.display_mode = self._cycle(
                DisplayMode,
                self.display_mode,
                direction,
            )
            self.status = f"{tr(self.language, 'display_mode')}: {self.display_mode.label}"

        elif self.options_index == 2:
            self.palette = self._cycle(Palette, self.palette, direction)
            self.config.apply_palette(self.palette)
            self.status = f"{tr(self.language, 'color_palette')}: {self.palette.label}"

        elif self.options_index == 3:
            self.color_depth = self._cycle(ColorDepth, self.color_depth, direction)
            self.config.color_depth = self.color_depth
            self.renderer = Renderer(self.config)
            self.status = f"{tr(self.language, 'color_depth')}: {self.color_depth.label}"

        elif self.options_index == 4:
            self.recursive_scan = not self.recursive_scan
            self.status = f"{tr(self.language, 'recursive_scan')}: {tr(self.language, 'on') if self.recursive_scan else tr(self.language, 'off')}"
            self._start_scan()

        elif self.options_index == 5:
            self.touch_controls = not self.touch_controls
            self.config.touch_controls = self.touch_controls
            self.status = "Touch setting will apply next launch."

        elif self.options_index == 6:
            self.language = self._cycle(Language, self.language, direction)
            self.config.language = self.language
            self.status = self.language.label

        elif self.options_index == 7:
            current = self.config.terminal_font
            try:
                current_index = FONT_PRESETS.index(current)
            except ValueError:
                current_index = 0
            next_index = (current_index + direction) % len(FONT_PRESETS)
            self.config.terminal_font = FONT_PRESETS[next_index]
            self.status = (
                f"{tr(self.language, 'font')}: "
                f"{self.config.terminal_font or 'Terminal default'}"
                f" — {tr(self.language, 'font_next_launch')}"
            )

        elif self.options_index == 8:
            self._reset_settings()

        elif self.options_index == 9:
            self._go_main()

    @staticmethod
    def _cycle(enum_type, current, direction):
        values = list(enum_type)
        index = values.index(current)
        return values[(index + direction) % len(values)]

    def _reset_settings(self) -> None:
        self.quality = Quality.ULTRA
        self.display_mode = DisplayMode.FULL_BLOCK
        self.palette = Palette.LIGHT
        self.color_depth = ColorDepth.AUTO
        self.language = Language.ENGLISH
        self.recursive_scan = True
        self.touch_controls = True
        self.config.color_depth = self.color_depth
        self.config.language = self.language
        self.config.recursive_scan = self.recursive_scan
        self.config.touch_controls = self.touch_controls
        self.config.terminal_font = ""
        self.config.palette_overrides = {}
        self.config.apply_palette(self.palette)
        self.renderer = Renderer(self.config)
        self.status = tr(self.language, "settings_saved")

    def _handle_browser_key(self, key: str) -> None:
        if key == "UP":
            self.index = max(0, self.index - 1)
        elif key == "DOWN":
            self.index = min(max(0, len(self.entries) - 1), self.index + 1)
        elif key == "PAGEUP":
            self.index = max(0, self.index - 8)
        elif key == "PAGEDOWN":
            self.index = min(max(0, len(self.entries) - 1), self.index + 8)
        elif key in {"ENTER", "\n", "\r", "RIGHT"} and self.entries:
            self._start_load(self.entries[self.index])

    def _handle_mouse(self, key: str) -> None:
        parts = key.split(":")
        if len(parts) != 5:
            return

        try:
            x = int(parts[3])
            y = int(parts[4])
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
            hit = self.renderer.options_menu_hit(
                x,
                y,
                cols,
                rows,
                self.options_index,
            )
            if hit is not None:
                self.options_index = hit
                self._handle_options_key("\n")
            return

        if self.screen == self.BROWSER:
            hit = self.renderer.browser_hit(
                x,
                y,
                cols,
                rows,
                len(self.entries),
                self.index,
            )
            if hit is not None:
                if hit < 0:
                    self._go_main()
                elif 0 <= hit < len(self.entries):
                    self.index = hit
                    self._start_load(self.entries[hit])
            return

        if self.screen == self.VIEWER:
            action = self.renderer.viewer_hit(
                x,
                y,
                cols,
                rows,
                self.language,
            )
            if action == "prev":
                self._step_image(-1)
            elif action == "next":
                self._step_image(1)
            elif action == "browse":
                self._open_browser()
            elif action == "fit":
                self._fit()
            elif action == "info":
                self.info_overlay = not self.info_overlay
                self.help_overlay = False
            elif action == "menu":
                self._go_main()
            elif action == "zoom_in":
                self._zoom(1)
            elif action == "zoom_out":
                self._zoom(-1)

    def _open_browser(self) -> None:
        self.help_overlay = False
        self.info_overlay = False
        self._sync_index()
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

    def _zoom(self, direction: int) -> None:
        steps = [1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
        index = steps.index(self.zoom) if self.zoom in steps else 0
        index = max(0, min(len(steps) - 1, index + direction))
        self.zoom = steps[index]
        if self.zoom == 1.0:
            self.pan_x = 0.0
            self.pan_y = 0.0
        self.status = tr(
            self.language,
            "fit_screen" if self.zoom == 1.0 else "zoom",
            value=f"{self.zoom:g}",
        )

    def _fit(self) -> None:
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.status = tr(self.language, "fit_screen")


def main(path: str | None = None) -> None:
    ImageApp(path).run()
