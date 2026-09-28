from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from .config import AppConfig, MAX_SOURCE_PIXELS, MAX_ZOOM, Quality

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif",
    ".tif", ".tiff", ".ppm", ".pgm", ".pbm",
}

IGNORED_DIRS = {
    ".git", ".github", "__pycache__", ".venv", "venv",
    "node_modules", "dist", "build",
}

# Enough source samples for every renderer currently supported:
# 2 horizontal samples/cell and 4 vertical samples/cell.
MAX_SOURCE_X = 2
MAX_SOURCE_Y = 4


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
    source_size: tuple[int, int]


@dataclass(slots=True)
class ScanEvent:
    progress: float
    message: str
    found: int


class ProgressReader:
    def __init__(
        self,
        fp,
        total: int,
        callback: Callable[[float], None],
    ) -> None:
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
        if value - self._last >= 0.02 or value >= 1.0:
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
                lambda p: event("decode", p * 0.65, "Decoding image..."),
            )
            source = Image.open(reader)

            raw_size = source.size
            if raw_size[0] <= 0 or raw_size[1] <= 0:
                raise ValueError("Image has invalid dimensions.")

            pixel_count = raw_size[0] * raw_size[1]
            if pixel_count > self.config.max_pixels:
                raise ValueError(
                    f"Image is {raw_size[0]:,}x{raw_size[1]:,} pixels, "
                    f"above the safety limit of {self.config.max_pixels:,}."
                )

            raw_size = source.size
            orientation = source.getexif().get(274, 1)
            oriented_size = (
                (raw_size[1], raw_size[0])
                if orientation in {5, 6, 7, 8}
                else raw_size
            )

            target_oriented = self._target_pixels(
                oriented_size,
                quality,
                terminal_cells,
            )
            target = (
                (target_oriented[1], target_oriented[0])
                if orientation in {5, 6, 7, 8}
                else target_oriented
            )

            if is_large:
                event(
                    "decode",
                    0.08,
                    "Large image detected; using a reduced decode target...",
                )

            # JPEG decoders can avoid creating the full original raster.
            try:
                source.draft("RGB", target)
            except (AttributeError, OSError):
                pass

            event("prepare", 0.0, "Preparing terminal-sized preview...")
            source.thumbnail(target, Image.Resampling.LANCZOS)
            source.load()

            if source.mode not in {"RGB", "RGBA"}:
                source = source.convert("RGBA")
            else:
                source = source.copy()

            source = ImageOps.exif_transpose(source)
            original_size = oriented_size
            frame = self._composite_white(source)

        event("decode", 1.0, "Image decoded")
        event("prepare", 0.75, "Preview fitted")
        event("prepare", 1.0, "Ready")

        return LoadedImage(
            path=path,
            image=frame,
            original_size=original_size,
            mode=frame.mode,
            file_bytes=file_bytes,
            source_size=frame.size,
        )

    @staticmethod
    def _target_pixels(
        original_size: tuple[int, int],
        quality: Quality,
        terminal_cells: tuple[int, int],
    ) -> tuple[int, int]:
        cols, rows = terminal_cells

        # Keep enough source detail for the viewer's maximum zoom instead of
        # throwing away detail during the initial decode.
        max_w = max(16, (cols - 2) * MAX_SOURCE_X) * MAX_ZOOM
        max_h = max(8, (rows - 7) * MAX_SOURCE_Y) * MAX_ZOOM

        source_w, source_h = original_size
        fit = min(max_w / source_w, max_h / source_h, 1.0)
        fit *= quality / 100.0

        target_w = max(8, int(source_w * fit))
        target_h = max(4, int(source_h * fit))

        # A very large terminal or a huge source image must not turn an image
        # preview into a multi-hundred-megapixel allocation.
        pixels = target_w * target_h
        if pixels > MAX_SOURCE_PIXELS:
            cap_scale = (MAX_SOURCE_PIXELS / pixels) ** 0.5
            target_w = max(8, int(target_w * cap_scale))
            target_h = max(4, int(target_h * cap_scale))

        return target_w, target_h

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


def list_images(
    directory: Path,
    *,
    recursive: bool = True,
    on_event: Callable[[ScanEvent], None] | None = None,
) -> list[Path]:
    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        return []

    found: list[Path] = []

    def report(progress: float, message: str) -> None:
        if on_event:
            on_event(
                ScanEvent(
                    max(0.0, min(1.0, progress)),
                    message,
                    len(found),
                )
            )

    if not recursive:
        try:
            candidates = sorted(directory.iterdir(), key=lambda p: p.name.casefold())
        except OSError:
            return []

        total = max(1, len(candidates))
        for i, path in enumerate(candidates, 1):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                found.append(path)
            report(i / total, f"Scanning: {path.name}")

        return sorted(found, key=lambda p: str(p.relative_to(directory)).casefold())

    # Walk without following symlinks so a linked directory cannot create a loop.
    import os

    root_text = str(directory)
    dirs_seen = 0
    for root, dirs, files in os.walk(root_text, topdown=True, followlinks=False):
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIRS and not d.startswith(".")
        ]
        dirs_seen += 1

        for name in files:
            path = Path(root) / name
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                found.append(path)

        relative = Path(root).relative_to(directory)
        label = "." if str(relative) == "." else str(relative)
        report(min(0.98, dirs_seen / max(dirs_seen + len(dirs) + 1, 1)), f"Scanning: {label}")

    found.sort(key=lambda p: str(p.relative_to(directory)).casefold())
    report(1.0, f"Found {len(found)} image(s)")
    return found
