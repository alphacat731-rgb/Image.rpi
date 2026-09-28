from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import os


class Quality(IntEnum):
    VERY_LOW = 25
    LOW = 40
    MEDIUM = 60
    HIGH = 75
    VERY_HIGH = 90
    ULTRA = 100

    @property
    def label(self) -> str:
        return {
            Quality.VERY_LOW: "Very Low",
            Quality.LOW: "Low",
            Quality.MEDIUM: "Medium",
            Quality.HIGH: "High",
            Quality.VERY_HIGH: "Very High",
            Quality.ULTRA: "Ultra",
        }[self]

    @classmethod
    def next(cls, current: "Quality") -> "Quality":
        values = list(cls)
        return values[(values.index(current) + 1) % len(values)]


@dataclass(slots=True)
class AppConfig:
    background: tuple[int, int, int] = (255, 255, 255)
    foreground: tuple[int, int, int] = (20, 20, 24)
    muted: tuple[int, int, int] = (105, 105, 112)
    panel: tuple[int, int, int] = (244, 245, 247)
    border: tuple[int, int, int] = (215, 217, 222)
    accent: tuple[int, int, int] = (42, 90, 255)
    selection: tuple[int, int, int] = (25, 30, 45)
    max_pixels: int = 60_000_000
    large_file_bytes: int = 24 * 1024 * 1024
    render_fps: int = 20
    default_quality: Quality = Quality.ULTRA

    @classmethod
    def from_environment(cls) -> "AppConfig":
        max_pixels = _positive_int(
            os.getenv("IMAGERPI_MAX_PIXELS"), 60_000_000
        )
        large_file = _positive_int(
            os.getenv("IMAGERPI_LARGE_FILE_MB"), 24
        ) * 1024 * 1024
        fps = max(8, min(30, _positive_int(os.getenv("IMAGERPI_FPS"), 20)))
        quality_name = os.getenv("IMAGERPI_QUALITY", "ULTRA").upper()
        quality = getattr(Quality, quality_name, Quality.ULTRA)
        return cls(
            max_pixels=max_pixels,
            large_file_bytes=large_file,
            render_fps=fps,
            default_quality=quality,
        )


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value or "")
        return parsed if parsed > 0 else default
    except ValueError:
        return default
