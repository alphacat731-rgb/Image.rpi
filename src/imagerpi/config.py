from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
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


class DisplayMode(str, Enum):
    HALF_BLOCK = "half"
    FULL_BLOCK = "full"
    LOWER_BLOCK = "lower"
    DARK_SHADE = "dark"
    MEDIUM_SHADE = "medium"
    LIGHT_SHADE = "light"
    DOT = "dot"
    SMALL_DOT = "small_dot"
    BRAILLE = "braille"
    ASCII = "ascii"

    @property
    def label(self) -> str:
        return {
            DisplayMode.HALF_BLOCK: "Half Block (▀)",
            DisplayMode.FULL_BLOCK: "Full Block (█)",
            DisplayMode.LOWER_BLOCK: "Lower Block (▄)",
            DisplayMode.DARK_SHADE: "Dark Shade (▓)",
            DisplayMode.MEDIUM_SHADE: "Medium Shade (▒)",
            DisplayMode.LIGHT_SHADE: "Light Shade (░)",
            DisplayMode.DOT: "Dot (●)",
            DisplayMode.SMALL_DOT: "Small Dot (·)",
            DisplayMode.BRAILLE: "Braille (⠿)",
            DisplayMode.ASCII: "ASCII",
        }[self]

    @classmethod
    def next(cls, current: "DisplayMode") -> "DisplayMode":
        values = list(cls)
        return values[(values.index(current) + 1) % len(values)]


class Palette(str, Enum):
    LIGHT = "light"
    ARCTIC = "arctic"
    OCEAN = "ocean"
    COBALT = "cobalt"
    TERMINAL_GREEN = "terminal_green"
    LIME = "lime"
    AMBER = "amber"
    SUNSET = "sunset"
    PURPLE = "purple"
    PINK = "pink"
    MONO = "mono"
    SLATE = "slate"
    SOLAR = "solar"
    PAPER = "paper"

    @property
    def label(self) -> str:
        return {
            Palette.LIGHT: "Light",
            Palette.ARCTIC: "Arctic",
            Palette.OCEAN: "Ocean",
            Palette.COBALT: "Cobalt",
            Palette.TERMINAL_GREEN: "Terminal Green",
            Palette.LIME: "Lime",
            Palette.AMBER: "Amber CRT",
            Palette.SUNSET: "Sunset",
            Palette.PURPLE: "Purple",
            Palette.PINK: "Pink",
            Palette.MONO: "Mono",
            Palette.SLATE: "Slate",
            Palette.SOLAR: "Solar",
            Palette.PAPER: "Paper",
        }[self]

    @classmethod
    def next(cls, current: "Palette") -> "Palette":
        values = list(cls)
        return values[(values.index(current) + 1) % len(values)]


PALETTE_COLORS: dict[Palette, dict[str, tuple[int, int, int]]] = {
    Palette.LIGHT: {
        "background": (255, 255, 255),
        "foreground": (20, 20, 24),
        "muted": (105, 105, 112),
        "panel": (244, 245, 247),
        "border": (215, 217, 222),
        "accent": (42, 90, 255),
        "selection": (25, 30, 45),
    },
    Palette.ARCTIC: {
        "background": (238, 248, 255),
        "foreground": (15, 35, 48),
        "muted": (75, 110, 125),
        "panel": (218, 238, 249),
        "border": (170, 210, 225),
        "accent": (0, 145, 190),
        "selection": (24, 82, 105),
    },
    Palette.OCEAN: {
        "background": (8, 23, 38),
        "foreground": (225, 245, 255),
        "muted": (120, 165, 190),
        "panel": (17, 45, 68),
        "border": (45, 86, 110),
        "accent": (45, 190, 235),
        "selection": (22, 84, 110),
    },
    Palette.COBALT: {
        "background": (10, 18, 45),
        "foreground": (235, 240, 255),
        "muted": (130, 145, 185),
        "panel": (22, 34, 75),
        "border": (48, 70, 130),
        "accent": (80, 125, 255),
        "selection": (46, 70, 145),
    },
    Palette.TERMINAL_GREEN: {
        "background": (3, 12, 5),
        "foreground": (190, 255, 196),
        "muted": (82, 165, 90),
        "panel": (8, 32, 12),
        "border": (24, 86, 31),
        "accent": (60, 255, 90),
        "selection": (15, 80, 25),
    },
    Palette.LIME: {
        "background": (18, 27, 8),
        "foreground": (242, 255, 220),
        "muted": (165, 195, 95),
        "panel": (42, 58, 18),
        "border": (83, 105, 38),
        "accent": (160, 255, 40),
        "selection": (76, 110, 20),
    },
    Palette.AMBER: {
        "background": (24, 12, 3),
        "foreground": (255, 222, 155),
        "muted": (190, 135, 64),
        "panel": (52, 28, 6),
        "border": (112, 69, 18),
        "accent": (255, 170, 35),
        "selection": (105, 56, 12),
    },
    Palette.SUNSET: {
        "background": (35, 10, 20),
        "foreground": (255, 225, 232),
        "muted": (195, 125, 145),
        "panel": (68, 22, 40),
        "border": (115, 45, 70),
        "accent": (255, 95, 125),
        "selection": (120, 42, 68),
    },
    Palette.PURPLE: {
        "background": (17, 9, 30),
        "foreground": (242, 230, 255),
        "muted": (165, 130, 195),
        "panel": (43, 22, 65),
        "border": (84, 48, 115),
        "accent": (190, 95, 255),
        "selection": (94, 48, 130),
    },
    Palette.PINK: {
        "background": (30, 7, 24),
        "foreground": (255, 230, 250),
        "muted": (195, 120, 180),
        "panel": (62, 20, 52),
        "border": (112, 43, 95),
        "accent": (255, 90, 210),
        "selection": (118, 42, 100),
    },
    Palette.MONO: {
        "background": (10, 10, 10),
        "foreground": (240, 240, 240),
        "muted": (145, 145, 145),
        "panel": (32, 32, 32),
        "border": (78, 78, 78),
        "accent": (255, 255, 255),
        "selection": (80, 80, 80),
    },
    Palette.SLATE: {
        "background": (20, 24, 30),
        "foreground": (230, 235, 242),
        "muted": (135, 145, 158),
        "panel": (38, 45, 55),
        "border": (78, 88, 102),
        "accent": (115, 180, 255),
        "selection": (62, 88, 118),
    },
    Palette.SOLAR: {
        "background": (0, 28, 35),
        "foreground": (238, 232, 213),
        "muted": (147, 161, 146),
        "panel": (7, 48, 58),
        "border": (42, 76, 82),
        "accent": (38, 190, 150),
        "selection": (28, 93, 88),
    },
    Palette.PAPER: {
        "background": (250, 247, 238),
        "foreground": (45, 44, 39),
        "muted": (122, 116, 101),
        "panel": (235, 230, 215),
        "border": (205, 198, 181),
        "accent": (180, 92, 45),
        "selection": (85, 63, 42),
    },
}


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

    def apply_palette(self, palette: Palette) -> None:
        colors = PALETTE_COLORS[palette]
        self.background = colors["background"]
        self.foreground = colors["foreground"]
        self.muted = colors["muted"]
        self.panel = colors["panel"]
        self.border = colors["border"]
        self.accent = colors["accent"]
        self.selection = colors["selection"]

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
