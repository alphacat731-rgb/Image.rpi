from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import select
import threading

from .config import AppConfig, Quality
from .loader import ImageLoader, LoadEvent, LoadedImage, list_images
from .renderer import Renderer
from .terminal import terminal_session, terminal_size


@dataclass(slots=True)
class LoadedResult:
    image: LoadedImage | None
    error: Exception | None


class ImageApp:
    def __init__(self, initial: str | None = None) -> None:
        self.config = AppConfig.from_environment()
        self.renderer = Renderer(self.config)
        self.loader = ImageLoader(self.config)
        self.quality = self.config.default_quality
        self.current: LoadedImage | None = None

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

        self.browser = False
        self.help_overlay = False
        self.info_overlay = False
        self.status = ""
        self.load_queue: queue.Queue[LoadEvent | LoadedResult] = queue.Queue()
        self.loading = False
        self.running = True
        self._progress = LoadEvent("open", 0.0, "Loading...")

    def run(self) -> None:
        with terminal_session() as term:
            if self.entries and self.current is None:
                self._start_load(self.entries[self.index])
            else:
                term.write(
                    self.renderer.frame(
                        None,
                        self.quality,
                        "Press O to browse",
                    )
                )

            while self.running:
                self._drain_load()
                term.write(self._render())
                key = self._read_key_with_timeout(
                    term,
                    1.0 / self.config.render_fps,
                )
                if key:
                    self._handle_key(key)

    def _render(self) -> str:
        if self.loading:
            return self.renderer.progress(
                self._progress.stage,
                self._progress.progress,
                self._progress.message,
            )

        return self.renderer.frame(
            self.current,
            self.quality,
            self.status,
            browser=self.browser,
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
                continue

            self.current = item.image
            self.status = f"Loaded {self.current.path.name}"
            self.entries = list_images(self.current.path.parent)
            self.current_dir = self.current.path.parent

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

        if key in {"q", "Q", "ESC"}:
            self.running = False
            return

        if key in {"h", "H"}:
            self.help_overlay = not self.help_overlay
            self.info_overlay = False
            return

        if key in {"i", "I"}:
            self.info_overlay = not self.info_overlay
            self.help_overlay = False
            return

        if key in {"r", "R"} and not self.loading:
            self.quality = Quality.next(self.quality)
            if self.current is not None:
                self._start_load(self.current.path)
            return

        if key in {"o", "O"}:
            self.browser = not self.browser
            self.help_overlay = False
            self.info_overlay = False
            self.entries = list_images(self.current_dir)

            if self.entries:
                self.index = min(
                    self.index,
                    len(self.entries) - 1,
                )
            return

        if self.help_overlay or self.info_overlay:
            return

        if self.browser:
            if key == "UP":
                self.index = max(0, self.index - 1)
            elif key == "DOWN":
                self.index = min(
                    max(0, len(self.entries) - 1),
                    self.index + 1,
                )
            elif key in {"\n", "\r", "RIGHT"} and self.entries:
                self.browser = False
                self._start_load(self.entries[self.index])
            return

        if self.current is None or self.loading:
            return

        if key == "RIGHT":
            self._step_image(1)
        elif key == "LEFT":
            self._step_image(-1)

    def _step_image(self, delta: int) -> None:
        if not self.entries:
            return
        self.index = (self.index + delta) % len(self.entries)
        self._start_load(self.entries[self.index])


def main(path: str | None = None) -> None:
    ImageApp(path).run()
