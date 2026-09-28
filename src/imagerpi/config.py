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


class Language(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"

    @property
    def label(self) -> str:
        return "English" if self is Language.ENGLISH else "Español"

    @classmethod
    def next(cls, current: "Language") -> "Language":
        values = list(cls)
        return values[(values.index(current) + 1) % len(values)]


class ColorDepth(str, Enum):
    AUTO = "auto"
    TRUECOLOR = "truecolor"
    ANSI256 = "ansi256"

    @property
    def label(self) -> str:
        return {
            ColorDepth.AUTO: "Auto",
            ColorDepth.TRUECOLOR: "Truecolor",
            ColorDepth.ANSI256: "256 colors",
        }[self]

    @classmethod
    def next(cls, current: "ColorDepth") -> "ColorDepth":
        values = list(cls)
        return values[(values.index(current) + 1) % len(values)]


class DisplayMode(str, Enum):
    HALF_BLOCK = "half"
    FULL_BLOCK = "full"
    LOWER_BLOCK = "lower"
    LEFT_BLOCK = "left"
    BLOCK_GRADIENT = "gradient"
    QUADRANT = "quadrant"
    RIGHT_BLOCK = "right"
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
            DisplayMode.FULL_BLOCK: "Rectangles (█)",
            DisplayMode.LOWER_BLOCK: "Lower Block (▄)",
            DisplayMode.LEFT_BLOCK: "Left Block (▌)",
            DisplayMode.RIGHT_BLOCK: "Right Block (▐)",
            DisplayMode.BLOCK_GRADIENT: "Block Gradient (▏▎▍▌▋▊▉█)",
            DisplayMode.QUADRANT: "Quadrants (◩)",
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
    MATRIX = "matrix"
    LIME = "lime"
    AMBER = "amber"
    SUNSET = "sunset"
    RED = "red"
    PURPLE = "purple"
    VIOLET = "violet"
    PINK = "pink"
    MAGENTA = "magenta"
    BLUE = "blue"
    CYAN = "cyan"
    MONO = "mono"
    SLATE = "slate"
    SOLAR = "solar"
    PAPER = "paper"
    HIGH_CONTRAST = "high_contrast"
    NORDIC = "nordic"
    FOREST = "forest"
    ROSE = "rose"

    @property
    def label(self) -> str:
        return {
            Palette.LIGHT: "Light",
            Palette.ARCTIC: "Arctic",
            Palette.OCEAN: "Ocean",
            Palette.COBALT: "Cobalt",
            Palette.TERMINAL_GREEN: "Terminal Green",
            Palette.MATRIX: "Matrix",
            Palette.LIME: "Lime",
            Palette.AMBER: "Amber CRT",
            Palette.SUNSET: "Sunset",
            Palette.RED: "Red",
            Palette.PURPLE: "Purple",
            Palette.VIOLET: "Violet",
            Palette.PINK: "Pink",
            Palette.MAGENTA: "Magenta",
            Palette.BLUE: "Blue",
            Palette.CYAN: "Cyan",
            Palette.MONO: "Mono",
            Palette.SLATE: "Slate",
            Palette.SOLAR: "Solar",
            Palette.PAPER: "Paper",
            Palette.HIGH_CONTRAST: "High Contrast",
            Palette.NORDIC: "Nordic",
            Palette.FOREST: "Forest",
            Palette.ROSE: "Rose",
        }[self]

    @classmethod
    def next(cls, current: "Palette") -> "Palette":
        values = list(cls)
        return values[(values.index(current) + 1) % len(values)]


FONT_PRESETS = (
    "",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Noto Sans Mono",
    "Monospace",
)


PALETTE_COLORS: dict[Palette, dict[str, tuple[int, int, int]]] = {
    Palette.LIGHT: {"background": (255, 255, 255), "foreground": (20, 20, 24), "muted": (105, 105, 112), "panel": (244, 245, 247), "border": (215, 217, 222), "accent": (42, 90, 255), "selection": (25, 30, 45)},
    Palette.ARCTIC: {"background": (238, 248, 255), "foreground": (15, 35, 48), "muted": (75, 110, 125), "panel": (218, 238, 249), "border": (170, 210, 225), "accent": (0, 145, 190), "selection": (24, 82, 105)},
    Palette.OCEAN: {"background": (8, 23, 38), "foreground": (225, 245, 255), "muted": (120, 165, 190), "panel": (17, 45, 68), "border": (45, 86, 110), "accent": (45, 190, 235), "selection": (22, 84, 110)},
    Palette.COBALT: {"background": (10, 18, 45), "foreground": (235, 240, 255), "muted": (130, 145, 185), "panel": (22, 34, 75), "border": (48, 70, 130), "accent": (80, 125, 255), "selection": (46, 70, 145)},
    Palette.TERMINAL_GREEN: {"background": (3, 12, 5), "foreground": (190, 255, 196), "muted": (82, 165, 90), "panel": (8, 32, 12), "border": (24, 86, 31), "accent": (60, 255, 90), "selection": (15, 80, 25)},
    Palette.MATRIX: {"background": (0, 5, 1), "foreground": (190, 255, 190), "muted": (50, 155, 55), "panel": (2, 22, 5), "border": (8, 85, 18), "accent": (20, 255, 55), "selection": (10, 75, 20)},
    Palette.LIME: {"background": (18, 27, 8), "foreground": (242, 255, 220), "muted": (165, 195, 95), "panel": (42, 58, 18), "border": (83, 105, 38), "accent": (160, 255, 40), "selection": (76, 110, 20)},
    Palette.AMBER: {"background": (24, 12, 3), "foreground": (255, 222, 155), "muted": (190, 135, 64), "panel": (52, 28, 6), "border": (112, 69, 18), "accent": (255, 170, 35), "selection": (105, 56, 12)},
    Palette.SUNSET: {"background": (35, 10, 20), "foreground": (255, 225, 232), "muted": (195, 125, 145), "panel": (68, 22, 40), "border": (115, 45, 70), "accent": (255, 95, 125), "selection": (120, 42, 68)},
    Palette.RED: {"background": (32, 6, 8), "foreground": (255, 225, 225), "muted": (190, 105, 110), "panel": (62, 16, 20), "border": (116, 35, 42), "accent": (255, 70, 70), "selection": (120, 35, 40)},
    Palette.PURPLE: {"background": (17, 9, 30), "foreground": (242, 230, 255), "muted": (165, 130, 195), "panel": (43, 22, 65), "border": (84, 48, 115), "accent": (190, 95, 255), "selection": (94, 48, 130)},
    Palette.VIOLET: {"background": (13, 5, 28), "foreground": (238, 225, 255), "muted": (145, 105, 190), "panel": (34, 14, 70), "border": (72, 35, 125), "accent": (130, 80, 255), "selection": (85, 45, 145)},
    Palette.PINK: {"background": (30, 7, 24), "foreground": (255, 230, 250), "muted": (195, 120, 180), "panel": (62, 20, 52), "border": (112, 43, 95), "accent": (255, 90, 210), "selection": (118, 42, 100)},
    Palette.MAGENTA: {"background": (29, 4, 25), "foreground": (255, 220, 248), "muted": (190, 100, 175), "panel": (62, 13, 56), "border": (115, 30, 100), "accent": (255, 45, 215), "selection": (120, 28, 105)},
    Palette.BLUE: {"background": (5, 12, 35), "foreground": (224, 238, 255), "muted": (105, 135, 190), "panel": (12, 28, 74), "border": (30, 60, 135), "accent": (45, 120, 255), "selection": (32, 68, 145)},
    Palette.CYAN: {"background": (3, 24, 28), "foreground": (220, 255, 255), "muted": (90, 170, 175), "panel": (8, 52, 58), "border": (26, 100, 108), "accent": (35, 235, 220), "selection": (25, 105, 105)},
    Palette.MONO: {"background": (10, 10, 10), "foreground": (240, 240, 240), "muted": (145, 145, 145), "panel": (32, 32, 32), "border": (78, 78, 78), "accent": (255, 255, 255), "selection": (80, 80, 80)},
    Palette.SLATE: {"background": (20, 24, 30), "foreground": (230, 235, 242), "muted": (135, 145, 158), "panel": (38, 45, 55), "border": (78, 88, 102), "accent": (115, 180, 255), "selection": (62, 88, 118)},
    Palette.SOLAR: {"background": (0, 28, 35), "foreground": (238, 232, 213), "muted": (147, 161, 146), "panel": (7, 48, 58), "border": (42, 76, 82), "accent": (38, 190, 150), "selection": (28, 93, 88)},
    Palette.PAPER: {"background": (250, 247, 238), "foreground": (45, 44, 39), "muted": (122, 116, 101), "panel": (235, 230, 215), "border": (205, 198, 181), "accent": (180, 92, 45), "selection": (85, 63, 42)},
    Palette.HIGH_CONTRAST: {"background": (0, 0, 0), "foreground": (255, 255, 255), "muted": (190, 190, 190), "panel": (25, 25, 25), "border": (255, 255, 255), "accent": (255, 215, 0), "selection": (0, 110, 255)},
    Palette.NORDIC: {"background": (15, 23, 33), "foreground": (225, 235, 242), "muted": (125, 145, 160), "panel": (28, 42, 55), "border": (65, 90, 108), "accent": (130, 205, 210), "selection": (50, 95, 115)},
    Palette.FOREST: {"background": (6, 20, 12), "foreground": (220, 245, 225), "muted": (105, 155, 115), "panel": (15, 45, 24), "border": (38, 92, 52), "accent": (80, 205, 100), "selection": (35, 100, 48)},
    Palette.ROSE: {"background": (28, 10, 17), "foreground": (255, 232, 238), "muted": (185, 125, 145), "panel": (58, 24, 35), "border": (110, 52, 70), "accent": (245, 105, 135), "selection": (115, 48, 68)},
}


DEFAULT_USER_CONFIG = {
    "default_palette": "light",
    "default_display_mode": "rectangles",
    "terminal_font": "",
    "palettes": {},
}


def _config_path() -> Path:
    return Path.home() / ".config" / "imagerpi" / "config.json"


def load_user_config() -> dict:
    import json
    path = _config_path()

    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(DEFAULT_USER_CONFIG, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(DEFAULT_USER_CONFIG)
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_USER_CONFIG)


def _hex_rgb(value: object, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not isinstance(value, str):
        return fallback
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return fallback


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
    default_palette: Palette = Palette.LIGHT
    default_display_mode: DisplayMode = DisplayMode.FULL_BLOCK
    terminal_font: str = ""
    color_depth: ColorDepth = ColorDepth.AUTO
    recursive_scan: bool = True
    touch_controls: bool = True
    language: Language = Language.ENGLISH
    palette_overrides: dict[str, dict[str, tuple[int, int, int]]] | None = None

    def apply_palette(self, palette: Palette) -> None:
        colors = dict(PALETTE_COLORS[palette])
        overrides = (self.palette_overrides or {}).get(palette.value, {})
        for key, fallback in colors.items():
            colors[key] = overrides.get(key, fallback)

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
        user = load_user_config()
        quality_name = os.getenv("IMAGERPI_QUALITY", str(user.get("quality", "ULTRA"))).upper()
        quality = getattr(Quality, quality_name, Quality.ULTRA)
        palette_name = str(user.get("default_palette", "light")).lower()
        palette = next((p for p in Palette if p.value == palette_name), Palette.LIGHT)

        mode_name = str(user.get("default_display_mode", "rectangles")).lower()
        mode_aliases = {
            "rectangles": DisplayMode.FULL_BLOCK,
            "full": DisplayMode.FULL_BLOCK,
            "half": DisplayMode.HALF_BLOCK,
        }
        display_mode = mode_aliases.get(mode_name, DisplayMode.FULL_BLOCK)
        for mode in DisplayMode:
            if mode.value == mode_name:
                display_mode = mode
                break

        overrides: dict[str, dict[str, tuple[int, int, int]]] = {}
        raw_palettes = user.get("palettes", {})
        if isinstance(raw_palettes, dict):
            for palette_key, raw_colors in raw_palettes.items():
                if not isinstance(raw_colors, dict):
                    continue

                enum_palette = next(
                    (p for p in Palette if p.value == str(palette_key).lower()),
                    None,
                )
                if enum_palette is None:
                    continue

                base = PALETTE_COLORS[enum_palette]
                parsed: dict[str, tuple[int, int, int]] = {}
                for color_key, fallback in base.items():
                    parsed[color_key] = _hex_rgb(
                        raw_colors.get(color_key),
                        fallback,
                    )
                overrides[enum_palette.value] = parsed

        depth_name = str(user.get("color_depth", "auto")).lower()
        depth = next((d for d in ColorDepth if d.value == depth_name), ColorDepth.AUTO)

        language_name = str(user.get("language", "en")).lower()
        language = next((lang for lang in Language if lang.value == language_name), Language.ENGLISH)

        return cls(
            max_pixels=max_pixels,
            large_file_bytes=large_file,
            render_fps=fps,
            default_quality=quality,
            default_palette=palette,
            default_display_mode=display_mode,
            terminal_font=str(user.get("terminal_font", "") or "").strip(),
            color_depth=depth,
            recursive_scan=bool(user.get("recursive_scan", True)),
            touch_controls=bool(user.get("touch_controls", True)),
            language=language,
            palette_overrides=overrides,
        )


def save_user_config(
    *,
    palette: Palette,
    display_mode: DisplayMode,
    quality: Quality,
    language: Language,
    color_depth: ColorDepth,
    recursive_scan: bool,
    touch_controls: bool,
    terminal_font: str,
    palette_overrides: dict | None = None,
) -> None:
    import json

    path = _config_path()
    current = load_user_config()
    current.update(
        {
            "default_palette": palette.value,
            "default_display_mode": "rectangles" if display_mode is DisplayMode.FULL_BLOCK else display_mode.value,
            "quality": quality.name,
            "language": language.value,
            "color_depth": color_depth.value,
            "recursive_scan": recursive_scan,
            "touch_controls": touch_controls,
            "terminal_font": terminal_font,
            "palettes": palette_overrides or current.get("palettes", {}),
        }
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value or "")
        return parsed if parsed > 0 else default
    except ValueError:
        return default
