from __future__ import annotations

from io import StringIO
from pathlib import Path

from PIL import Image

from .config import AppConfig, DisplayMode, Quality
from .loader import LoadedImage
from .terminal import (
    RESET,
    ERASE_LINE,
    move,
    rgb_bg,
    rgb_bg_256,
    rgb_fg,
    rgb_fg_256,
    style,
    supports_truecolor,
    terminal_size,
)


class Renderer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.truecolor = supports_truecolor()

    def frame(
        self,
        image: LoadedImage | None,
        quality: Quality,
        status: str,
        *,
        display_mode: DisplayMode = DisplayMode.HALF_BLOCK,
        browser: bool = False,
        browser_entries: list[Path] | None = None,
        browser_index: int = 0,
        help_overlay: bool = False,
        info_overlay: bool = False,
    ) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)
        out = StringIO()
        out.write("\x1b[2J\x1b[H")
        out.write(rgb_bg(self.config.background) + rgb_fg(self.config.foreground))

        self._header(out, cols, image, quality, display_mode)
        body_top = 4
        body_bottom = rows - 3

        if browser:
            self._browser(
                out,
                cols,
                body_top,
                body_bottom,
                browser_entries or [],
                browser_index,
            )
        elif image is not None:
            self._image(
                out,
                image.image,
                cols,
                body_top,
                body_bottom,
                display_mode,
            )
        else:
            self._empty(out, cols, body_top, body_bottom, status)

        self._footer(out, cols, rows, status, display_mode)

        if help_overlay:
            self._help_overlay(out, cols, rows)
        elif info_overlay and image is not None:
            self._info_overlay(out, cols, rows, image, quality)

        out.write(RESET)
        return out.getvalue()

    def progress(self, stage: str, progress: float, message: str) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)
        out = StringIO()
        out.write(rgb_bg(self.config.background) + rgb_fg(self.config.foreground))
        self._header(out, cols, None, None, None)

        box_w = min(cols - 8, 72)
        box_left = max(2, (cols - box_w) // 2)
        row = max(7, rows // 2 - 2)

        out.write(move(row, box_left))
        out.write(
            style(self.config.foreground, self.config.panel, bold=True)
            + " " * box_w
        )
        out.write(move(row + 1, box_left))
        out.write(
            style(self.config.foreground, self.config.panel)
            + "  "
            + message[: box_w - 4].ljust(box_w - 4)
            + "  "
        )
        out.write(move(row + 2, box_left))

        filled = int((box_w - 4) * max(0.0, min(1.0, progress)))
        bar = "=" * filled + ">" + " " * max(0, (box_w - 5) - filled)
        out.write(
            rgb_bg(self.config.panel)
            + rgb_fg(self.config.accent)
            + "  "
            + bar[: box_w - 4]
            + "  "
        )

        out.write(move(row + 3, box_left))
        out.write(
            style(self.config.foreground, self.config.background)
            + f"  {stage.upper():<10} {progress * 100:5.1f}%".ljust(box_w)
        )
        out.write(RESET)
        return out.getvalue()

    def _header(
        self,
        out: StringIO,
        cols: int,
        image: LoadedImage | None,
        quality: Quality | None,
        display_mode: DisplayMode | None,
    ) -> None:
        left = " IMAGE.RPI "
        middle = " terminal image viewer "
        details = []
        if quality is not None:
            details.append(quality.label)
        if display_mode is not None:
            details.append(display_mode.label)
        right = (" " + " | ".join(details) + " ") if details else " "
        line = (left + middle).ljust(max(0, cols - len(right)), "-") + right
        out.write(
            move(1)
            + style(self.config.foreground, self.config.background, bold=True)
            + line[:cols]
        )

        if image:
            name = image.path.name
            dims = f"{image.original_size[0]}x{image.original_size[1]}"
            detail = (
                f" {name}  |  {dims}  |  "
                f"{image.file_bytes / 1024 / 1024:.1f} MiB"
            )
        else:
            detail = " Ready for images"

        out.write(
            move(2)
            + style(self.config.muted, self.config.background)
            + detail[:cols].ljust(cols)
        )
        out.write(
            move(3)
            + style(self.config.border, self.config.background)
            + "─" * cols
        )

    def _prepare_image(
        self,
        image: Image.Image,
        width: int,
        height: int,
        pixel_height_multiplier: int,
        pixel_width_multiplier: int = 1,
    ) -> Image.Image:
        target_w = max(1, width * pixel_width_multiplier)
        target_h = max(1, height * pixel_height_multiplier)
        src = image.copy()

        scale = min(target_w / src.width, target_h / src.height)
        if abs(scale - 1.0) > 0.001:
            src = src.resize(
                (
                    max(1, int(src.width * scale)),
                    max(1, int(src.height * scale)),
                ),
                Image.Resampling.LANCZOS,
            )
        return src

    @staticmethod
    def _rgb(pixel: tuple[int, ...]) -> tuple[int, int, int]:
        return tuple(int(c) for c in pixel[:3])

    @staticmethod
    def _luma(rgb: tuple[int, int, int]) -> int:
        r, g, b = rgb
        return max(0, min(255, int(0.2126 * r + 0.7152 * g + 0.0722 * b)))

    def _image(
        self,
        out: StringIO,
        image: Image.Image,
        cols: int,
        top: int,
        bottom: int,
        display_mode: DisplayMode,
    ) -> None:
        view_w = max(8, cols - 2)
        view_h = max(2, bottom - top + 1)

        if display_mode == DisplayMode.BRAILLE:
            self._braille(out, image, cols, top, bottom, view_w, view_h)
            return

        if display_mode == DisplayMode.HALF_BLOCK:
            src = self._prepare_image(image, view_w, view_h, 2)
            self._render_half_block(out, src, cols, top, bottom)
            return

        src = self._prepare_image(image, view_w, view_h, 1)
        self._render_character_cells(
            out,
            src,
            cols,
            top,
            bottom,
            display_mode,
        )

    def _render_half_block(
        self,
        out: StringIO,
        src: Image.Image,
        cols: int,
        top: int,
        bottom: int,
    ) -> None:
        px = src.load()
        width, height = src.size
        xoff = max(1, (cols - width) // 2)
        view_h = bottom - top + 1
        yoff = top + max(0, (view_h * 2 - height) // 4)

        fg_encoder = rgb_fg if self.truecolor else rgb_fg_256
        bg_encoder = rgb_bg if self.truecolor else rgb_bg_256

        for y in range(0, height, 2):
            row = yoff + y // 2
            if row > bottom:
                break

            out.write(move(row, xoff))
            current_fg = current_bg = None

            for x in range(width):
                fg = self._rgb(px[x, y])
                bg = self._rgb(px[x, y + 1]) if y + 1 < height else (255, 255, 255)

                if fg != current_fg:
                    out.write(fg_encoder(fg))
                    current_fg = fg
                if bg != current_bg:
                    out.write(bg_encoder(bg))
                    current_bg = bg

                out.write("▀")

            out.write(" " + RESET)

    def _render_character_cells(
        self,
        out: StringIO,
        src: Image.Image,
        cols: int,
        top: int,
        bottom: int,
        display_mode: DisplayMode,
    ) -> None:
        px = src.load()
        width, height = src.size
        xoff = max(1, (cols - width) // 2)
        yoff = top + max(0, ((bottom - top + 1) - height) // 2)

        fg_encoder = rgb_fg if self.truecolor else rgb_fg_256
        chars = {
            DisplayMode.FULL_BLOCK: lambda l: "█",
            DisplayMode.LOWER_BLOCK: lambda l: "▄",
            DisplayMode.DARK_SHADE: lambda l: "▓",
            DisplayMode.MEDIUM_SHADE: lambda l: "▒",
            DisplayMode.LIGHT_SHADE: lambda l: "░",
            DisplayMode.DOT: lambda l: "●",
            DisplayMode.SMALL_DOT: lambda l: "·",
        }
        ascii_ramp = "@%#*+=-:. "

        for y in range(height):
            row = yoff + y
            if row > bottom:
                break

            out.write(move(row, xoff))
            current_fg = None

            for x in range(width):
                rgb = self._rgb(px[x, y])
                lum = self._luma(rgb)

                if rgb != current_fg:
                    out.write(fg_encoder(rgb))
                    current_fg = rgb

                if display_mode == DisplayMode.ASCII:
                    char = ascii_ramp[
                        min(
                            len(ascii_ramp) - 1,
                            lum * len(ascii_ramp) // 256,
                        )
                    ]
                else:
                    char = chars[display_mode](lum)

                out.write(char)

            out.write(" " + RESET)

    def _braille(
        self,
        out: StringIO,
        image: Image.Image,
        cols: int,
        top: int,
        bottom: int,
        view_w: int,
        view_h: int,
    ) -> None:
        src = self._prepare_image(image, view_w, view_h, 4, 2)
        px = src.load()
        width, height = src.size
        xoff = max(1, (cols - ((width + 1) // 2)) // 2)
        rows_needed = (height + 3) // 4
        yoff = top + max(0, ((bottom - top + 1) - rows_needed) // 2)

        # Braille dot layout:
        # 1 4
        # 2 5
        # 3 6
        # 7 8
        bits = (
            (0, 0, 1),
            (0, 1, 2),
            (0, 2, 4),
            (1, 0, 8),
            (1, 1, 16),
            (1, 2, 32),
            (0, 3, 64),
            (1, 3, 128),
        )

        fg_encoder = rgb_fg if self.truecolor else rgb_fg_256

        for by in range(0, height, 4):
            row = yoff + by // 4
            if row > bottom:
                break

            out.write(move(row, xoff))
            current_fg = None

            for bx in range(0, width, 2):
                mask = 0
                colors: list[tuple[int, int, int]] = []

                for dx, dy, bit in bits:
                    x = bx + dx
                    y = by + dy
                    if x >= width or y >= height:
                        continue
                    rgb = self._rgb(px[x, y])
                    colors.append(rgb)

                    # Darker pixels become braille dots.
                    if self._luma(rgb) < 170:
                        mask |= bit

                if colors:
                    avg = tuple(
                        sum(color[i] for color in colors) // len(colors)
                        for i in range(3)
                    )
                else:
                    avg = (255, 255, 255)

                if avg != current_fg:
                    out.write(fg_encoder(avg))
                    current_fg = avg

                out.write(chr(0x2800 + mask))

            out.write(" " + RESET)

    def _empty(
        self,
        out: StringIO,
        cols: int,
        top: int,
        bottom: int,
        status: str,
    ) -> None:
        text = "Press O to browse or pass an image path on the command line."
        row = (top + bottom) // 2
        out.write(
            move(row, max(2, (cols - len(text)) // 2))
            + style(self.config.muted)
            + text
        )
        if status:
            row += 2
            out.write(
                move(row, max(2, (cols - len(status)) // 2))
                + style(
                    self.config.foreground,
                    self.config.background,
                    bold=True,
                )
                + status
            )

    def _browser(
        self,
        out: StringIO,
        cols: int,
        top: int,
        bottom: int,
        entries: list[Path],
        selected: int,
    ) -> None:
        title = "OPEN IMAGE"
        out.write(
            move(top, 2)
            + style(self.config.foreground, self.config.background, bold=True)
            + title
        )

        visible = max(1, bottom - top - 2)
        start = max(
            0,
            min(
                selected - visible // 2,
                max(0, len(entries) - visible),
            ),
        )
        panel_w = min(cols - 4, 84)

        for i in range(visible):
            idx = start + i
            row = top + 2 + i

            if idx >= len(entries):
                out.write(move(row, 2) + ERASE_LINE)
                continue

            name = entries[idx].name
            marker = ">" if idx == selected else " "
            text = f" {marker} {name}"
            text = text[:panel_w].ljust(panel_w)

            if idx == selected:
                out.write(
                    move(row, 2)
                    + style(
                        (255, 255, 255),
                        self.config.selection,
                        bold=True,
                    )
                    + text
                )
            else:
                out.write(
                    move(row, 2)
                    + style(self.config.foreground, self.config.background)
                    + text
                )

        if not entries:
            msg = "No supported images in this directory."
            out.write(move(top + 4, 2) + style(self.config.muted) + msg)

    def _footer(
        self,
        out: StringIO,
        cols: int,
        rows: int,
        status: str,
        display_mode: DisplayMode,
    ) -> None:
        out.write(
            move(rows - 2)
            + style(self.config.border)
            + "─" * cols
        )
        hints = (
            f" A Display: {display_mode.label}"
            "   P Palette   O Browse   R Quality   I Info"
            "   ←/→ Previous/Next   Q Quit "
        )
        out.write(
            move(rows - 1)
            + style(self.config.muted, self.config.background)
            + hints[:cols].ljust(cols)
        )
        if status:
            out.write(
                move(rows - 2)
                + style(
                    self.config.accent,
                    self.config.background,
                    bold=True,
                )
                + (" " + status)[:cols]
            )

    def _overlay_box(
        self,
        out: StringIO,
        cols: int,
        rows: int,
        width: int,
        height: int,
    ) -> tuple[int, int]:
        width = min(width, cols - 4)
        height = min(height, rows - 4)
        left = max(2, (cols - width) // 2)
        top = max(2, (rows - height) // 2)

        for r in range(top, top + height):
            out.write(
                move(r, left)
                + style(self.config.foreground, self.config.panel)
                + " " * width
            )

        return left, top

    def _help_overlay(self, out: StringIO, cols: int, rows: int) -> None:
        lines = [
            "IMAGE.RPI",
            "",
            "O  Browse images",
            "A  Cycle display mode",
            "P  Cycle color palette",
            "R  Cycle Very Low -> Ultra",
            "I  Image information",
            "H  This help",
            "LEFT/RIGHT  Previous / Next",
            "UP/DOWN  Browse selection",
            "ENTER  Open selected image",
            "Q  Quit",
            "",
            "Display modes: blocks, shades, dots, braille and ASCII.",
        ]
        left, top = self._overlay_box(
            out,
            cols,
            rows,
            68,
            len(lines) + 2,
        )

        for i, line in enumerate(lines):
            out.write(
                move(top + 1 + i, left + 2)
                + style(
                    self.config.foreground,
                    self.config.panel,
                    bold=(i == 0),
                )
                + line[:64]
            )

    def _info_overlay(
        self,
        out: StringIO,
        cols: int,
        rows: int,
        image: LoadedImage,
        quality: Quality,
    ) -> None:
        lines = [
            "IMAGE INFORMATION",
            "",
            f"File:     {image.path.name}",
            f"Original: {image.original_size[0]} x {image.original_size[1]}",
            f"Rendered: {image.image.width} x {image.image.height}",
            f"Mode:     {image.mode}",
            f"Size:     {image.file_bytes / 1024 / 1024:.2f} MiB",
            f"Quality:  {quality.label}",
        ]
        left, top = self._overlay_box(
            out,
            cols,
            rows,
            58,
            len(lines) + 2,
        )

        for i, line in enumerate(lines):
            out.write(
                move(top + 1 + i, left + 2)
                + style(
                    self.config.foreground,
                    self.config.panel,
                    bold=(i == 0),
                )
                + line[:54]
            )
