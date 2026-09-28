from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from .config import AppConfig, Quality

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif",
    ".tif", ".tiff", ".ppm", ".pgm", ".pbm",
}


@dataclass(slots=True)
class LoadEvent:
    stage: str
    progress: float
    message: str


@dataclass(slots=True)
class LoadedImage:
    path: Path
    image: Image.Image
    original_size: tuple[int, int]
    mode: str
    file_bytes: int


class ProgressReader:
    def __init__(self, fp, total: int, callback: Callable[[float], None]) -> None:
        self._fp = fp
        self._total = max(total, 1)
        self._callback = callback
        self._last = -1.0

    def _report(self) -> None:
        try:
            pos = self._fp.tell()
        except (AttributeError, OSError):
            return
        value = max(0.0, min(1.0, pos / self._total))
        if value - self._last >= 0.01 or value >= 1.0:
            self._last = value
            self._callback(value)

    def read(self, size=-1):
        data = self._fp.read(size)
        self._report()
        return data

    def readinto(self, buffer):
        result = self._fp.readinto(buffer)
        self._report()
        return result

    def seek(self, offset, whence=0):
        result = self._fp.seek(offset, whence)
        self._report()
        return result

    def tell(self):
        return self._fp.tell()

    def seekable(self):
        return self._fp.seekable()

    def readable(self):
        return self._fp.readable()

    def fileno(self):
        return self._fp.fileno()

    def __getattr__(self, name):
        return getattr(self._fp, name)


class ImageLoader:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def load(
        self,
        path: Path,
        quality: Quality,
        terminal_cells: tuple[int, int],
        on_event: Callable[[LoadEvent], None] | None = None,
    ) -> LoadedImage:
        path = path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)

        file_bytes = path.stat().st_size
        is_large = file_bytes >= self.config.large_file_bytes

        def event(stage: str, progress: float, message: str) -> None:
            if on_event:
                on_event(
                    LoadEvent(
                        stage,
                        max(0.0, min(1.0, progress)),
                        message,
                    )
                )

        event("open", 0.0, "Reading image metadata...")

        with path.open("rb") as raw:
            reader = ProgressReader(
                raw,
                file_bytes,
                lambda p: event("decode", p, "Decoding image..."),
            )
            image = Image.open(reader)
            original_size = image.size

            pixel_count = original_size[0] * original_size[1]
            if pixel_count > self.config.max_pixels:
                raise ValueError(
                    f"Image is {original_size[0]:,}x{original_size[1]:,} pixels, "
                    f"above the safety limit of {self.config.max_pixels:,}. "
                    "Set IMAGERPI_MAX_PIXELS to raise it."
                )

            if is_large:
                event(
                    "decode",
                    0.08,
                    "Large image detected; using memory-friendly decode...",
                )

            image.seek(0)
            image.load()
            frame = image.copy()

        event("decode", 1.0, "Image decoded")
        event("prepare", 0.0, "Preparing terminal-sized preview...")

        frame = ImageOps.exif_transpose(frame)
        target_w, target_h = self._target_pixels(
            original_size,
            quality,
            terminal_cells,
        )

        if frame.mode not in {"RGB", "RGBA"}:
            frame = frame.convert("RGBA")
        else:
            frame = frame.copy()

        frame.thumbnail(
            (target_w, target_h),
            Image.Resampling.LANCZOS,
        )
        event("prepare", 0.75, "Fitting image to terminal")
        frame = self._composite_white(frame)
        event("prepare", 1.0, "Ready")

        return LoadedImage(
            path,
            frame,
            original_size,
            frame.mode,
            file_bytes,
        )

    @staticmethod
    def _target_pixels(
        original_size: tuple[int, int],
        quality: Quality,
        terminal_cells: tuple[int, int],
    ) -> tuple[int, int]:
        cols, rows = terminal_cells
        max_w = max(8, cols - 2)
        max_h = max(4, (rows - 5) * 2)
        scale = quality / 100.0
        source_w, source_h = original_size
        fit = min(max_w / source_w, max_h / source_h, 1.0)
        fit *= scale
        return max(8, int(source_w * fit)), max(4, int(source_h * fit))

    @staticmethod
    def _composite_white(image: Image.Image) -> Image.Image:
        if image.mode == "RGB":
            return image
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        background = Image.new(
            "RGBA",
            image.size,
            (255, 255, 255, 255),
        )
        return Image.alpha_composite(background, image).convert("RGB")


def list_images(directory: Path) -> list[Path]:
    try:
        entries = [
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
    except OSError:
        return []
    return sorted(entries, key=lambda p: p.name.casefold())
