from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Callable

from PIL import Image

from .config import AppConfig, ColorDepth, DisplayMode, Language, Palette, Quality
from .i18n import tr
from .loader import LoadedImage
from .terminal import (
    ERASE_LINE,
    RESET,
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
        self.truecolor = (
            config.color_depth is ColorDepth.TRUECOLOR
            or (
                config.color_depth is ColorDepth.AUTO
                and supports_truecolor()
            )
        )

    def _fg(self, rgb: tuple[int, int, int]) -> str:
        return rgb_fg(rgb) if self.truecolor else rgb_fg_256(rgb)

    def _bg(self, rgb: tuple[int, int, int]) -> str:
        return rgb_bg(rgb) if self.truecolor else rgb_bg_256(rgb)

    def _style(
        self,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] | None = None,
        *,
        bold: bool = False,
    ) -> str:
        parts = [self._fg(fg)]
        if bg is not None:
            parts.append(self._bg(bg))
        if bold:
            parts.append("\x1b[1m")
        return "".join(parts)

    def _clean_frame(self, out: StringIO) -> None:
        out.write("\x1b[2J\x1b[H")
        out.write(self._bg(self.config.background))
        out.write(self._fg(self.config.foreground))

    def main_menu(
        self,
        cols: int,
        rows: int,
        selected: int,
        image_count: int = 0,
        language: Language = Language.ENGLISH,
        palette: Palette = Palette.LIGHT,
    ) -> str:
        out = StringIO()
        self._clean_frame(out)

        title = tr(language, "app_title")
        subtitle = tr(language, "subtitle")
        items = [
            tr(language, "view_images"),
            tr(language, "options"),
            tr(language, "quit"),
        ]

        center = max(1, cols // 2)
        title_row = max(3, rows // 2 - 9)

        logo = f"◆ {title} ◆"
        out.write(
            move(title_row, max(1, center - len(logo) // 2))
            + self._style(
                self.config.foreground,
                self.config.background,
                bold=True,
            )
            + logo
        )
        out.write(
            move(title_row + 1, max(1, center - len(subtitle) // 2))
            + self._style(self.config.muted, self.config.background)
            + subtitle.upper()
        )

        count_text = tr(language, "image_count", count=image_count)
        palette_text = f"{palette.label} · {self._color_depth_short(language)}"
        meta = f"{count_text}   •   {palette_text}"
        out.write(
            move(title_row + 3, max(1, center - len(meta) // 2))
            + self._style(self.config.muted, self.config.background)
            + meta[: max(1, cols - 2)]
        )

        button_w = min(56, max(30, cols - 10))
        button_h = 3
        gap = 1
        first_row = max(title_row + 5, rows // 2 - 4)
        left = max(2, center - button_w // 2)

        for i, item in enumerate(items):
            row = first_row + i * (button_h + gap)
            active = i == selected
            bg = self.config.selection if active else self.config.panel
            fg = (255, 255, 255) if active else self.config.foreground
            border = self.config.accent if active else self.config.border

            out.write(
                move(row, left)
                + self._style(border, bg)
                + "╭" + "─" * (button_w - 2) + "╮"
            )
            out.write(
                move(row + 1, left)
                + self._style(fg, bg, bold=active)
                + "│"
                + (
                    ("  ▸ " if active else "    ")
                    + item
                ).ljust(button_w - 1)
                + "│"
            )
            out.write(
                move(row + 2, left)
                + self._style(border, bg)
                + "╰" + "─" * (button_w - 2) + "╯"
            )

        hint = f"↑ ↓ {tr(language, 'navigate')}    Enter {tr(language, 'select')}    Q {tr(language, 'quit')}"
        out.write(
            move(rows - 2, max(1, center - len(hint) // 2))
            + self._style(self.config.muted, self.config.background)
            + hint[: max(1, cols - 2)]
        )
        out.write(RESET)
        return out.getvalue()

    def options_menu(
        self,
        cols: int,
        rows: int,
        selected: int,
        *,
        quality: Quality,
        display_mode: DisplayMode,
        palette: Palette,
        recursive_scan: bool,
        touch_controls: bool,
        language: Language,
        color_depth: ColorDepth,
        terminal_font: str,
        image_count: int,
    ) -> str:
        out = StringIO()
        self._clean_frame(out)

        center = cols // 2
        title = tr(language, "options")
        title_row = max(2, rows // 2 - 11)
        out.write(
            move(title_row, max(1, center - len(title) // 2))
            + self._style(self.config.foreground, self.config.background, bold=True)
            + title
        )

        items = [
            (tr(language, "image_quality"), quality.label),
            (tr(language, "display_mode"), display_mode.label),
            (tr(language, "color_palette"), palette.label),
            (tr(language, "color_depth"), color_depth.label),
            (tr(language, "recursive_scan"), tr(language, "on") if recursive_scan else tr(language, "off")),
            (tr(language, "touch_controls"), tr(language, "on") if touch_controls else tr(language, "off")),
            (tr(language, "language"), language.label),
            (tr(language, "font"), terminal_font or "Terminal default"),
            (tr(language, "back"), ""),
        ]

        panel_w = min(76, max(38, cols - 8))
        left = max(2, center - panel_w // 2)
        first_row = max(title_row + 3, 4)

        visible_height = max(5, rows - first_row - 5)
        max_items = max(4, visible_height // 2)
        window_start = max(
            0,
            min(
                selected - max_items // 2,
                len(items) - max_items,
            ),
        )

        for display_i in range(max_items):
            i = window_start + display_i
            if i >= len(items):
                break

            row = first_row + display_i * 2
            name, value = items[i]
            active = i == selected
            bg = self.config.selection if active else self.config.panel
            fg = (255, 255, 255) if active else self.config.foreground
            marker = "▸ " if active else "  "
            value_text = f"  {value}" if value else ""

            label = f"{marker}{name}{value_text}"
            if len(label) > panel_w - 2:
                label = label[: panel_w - 3] + "…"
            label = label.ljust(panel_w - 1)

            out.write(
                move(row, left)
                + self._style(
                    self.config.accent if active else self.config.border,
                    bg,
                )
                + "│"
                + self._style(fg, bg, bold=active)
                + label
                + "│"
            )
            out.write(
                move(row + 1, left)
                + self._style(
                    self.config.accent if active else self.config.border,
                    self.config.background,
                )
                + "╰" + "─" * (panel_w - 2) + "╯"
            )

        preview_row = min(rows - 5, first_row + max_items * 2 + 1)
        preview_title = tr(language, "palette_preview")
        out.write(
            move(preview_row, left)
            + self._style(self.config.foreground, self.config.background, bold=True)
            + preview_title
        )
        self._palette_demo(out, preview_row + 1, left, panel_w)

        term_text = tr(language, "terminal", cols=cols, rows=rows)
        count_text = tr(language, "image_count", count=image_count)
        depth_text = self._color_depth_short(language)
        meta = f"{term_text}   •   {count_text}   •   {depth_text}"
        out.write(
            move(min(rows - 3, preview_row + 4), left)
            + self._style(self.config.muted, self.config.background)
            + meta[:panel_w]
        )

        hint = f"↑ ↓ {tr(language, 'navigate')}   ← → {tr(language, 'select')}   Esc {tr(language, 'back_hint')}"
        out.write(
            move(rows - 1, max(1, center - len(hint) // 2))
            + self._style(self.config.muted, self.config.background)
            + hint[: max(1, cols - 2)]
        )
        out.write(RESET)
        return out.getvalue()

    def browser(
        self,
        cols: int,
        rows: int,
        entries: list[Path],
        selected: int,
        language: Language = Language.ENGLISH,
    ) -> str:
        out = StringIO()
        self._clean_frame(out)

        title = tr(language, "view_images")
        out.write(
            move(2, 3)
            + self._style(self.config.foreground, self.config.background, bold=True)
            + title
        )

        count = tr(language, "image_count", count=len(entries))
        out.write(
            move(3, 3)
            + self._style(self.config.muted, self.config.background)
            + count
        )

        body_top = 5
        body_bottom = rows - 5
        panel_w = min(cols - 6, 96)
        left = max(2, (cols - panel_w) // 2)
        visible = max(1, body_bottom - body_top + 1)

        start = max(
            0,
            min(
                selected - visible // 2,
                max(0, len(entries) - visible),
            ),
        )

        for i in range(visible):
            idx = start + i
            row = body_top + i

            if idx >= len(entries):
                out.write(move(row, left) + ERASE_LINE)
                continue

            entry = entries[idx]
            relative = entry.name
            active = idx == selected
            bg = self.config.selection if active else self.config.panel
            fg = (255, 255, 255) if active else self.config.foreground
            marker = "▸" if active else "·"
            text = f" {marker}  {relative}"

            if len(text) > panel_w:
                text = text[: panel_w - 1] + "…"
            text = text.ljust(panel_w)

            out.write(
                move(row, left)
                + self._style(fg, bg, bold=active)
                + text
            )

        if not entries:
            message = tr(language, "no_images")
            out.write(
                move((body_top + body_bottom) // 2, max(1, (cols - len(message)) // 2))
                + self._style(self.config.muted, self.config.background)
                + message
            )

        hint = f"↑ ↓ {tr(language, 'navigate')}   Enter {tr(language, 'open')}   Esc {tr(language, 'back_hint')}"
        out.write(
            move(rows - 2, max(1, (cols - len(hint)) // 2))
            + self._style(self.config.muted, self.config.background)
            + hint[: max(1, cols - 2)]
        )
        out.write(RESET)
        return out.getvalue()

    def frame(
        self,
        image: LoadedImage | None,
        quality: Quality,
        status: str,
        *,
        display_mode: DisplayMode = DisplayMode.FULL_BLOCK,
        language: Language = Language.ENGLISH,
        browser_entries: list[Path] | None = None,
        browser_index: int = 0,
        zoom: float = 1.0,
        pan_x: float = 0.0,
        pan_y: float = 0.0,
        info_overlay: bool = False,
        help_overlay: bool = False,
    ) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)

        if browser_entries is not None:
            return self.browser(cols, rows, browser_entries, browser_index, language)

        out = StringIO()
        self._clean_frame(out)

        filename = image.path.name if image else "IMAGE.RPI"
        if image:
            index_text = f"{browser_index + 1}/{max(1, browser_index + 1)}"
            zoom_text = tr(language, "zoom", value=f"{zoom:g}")
            top = (
                f" {tr(language, 'app_title')}  │  {filename}"
                f"  │  {quality.label}  │  {display_mode.label}"
                f"  │  {zoom_text}"
            )
        else:
            top = f" {tr(language, 'app_title')}  │  {tr(language, 'ready')}"

        out.write(
            move(1)
            + self._style(self.config.foreground, self.config.background, bold=True)
            + top[:cols].ljust(cols)
        )

        if image:
            dims = f"{image.original_size[0]}×{image.original_size[1]}"
            detail = f" {dims}  •  {self._size_text(image.file_bytes)}"
        else:
            detail = ""

        out.write(
            move(2)
            + self._style(self.config.muted, self.config.background)
            + detail[:cols].ljust(cols)
        )

        body_top = 4
        toolbar_h = 3
        body_bottom = rows - toolbar_h - 1

        if image:
            self._image(
                out,
                image.image,
                cols,
                body_top,
                body_bottom,
                display_mode,
                zoom,
                pan_x,
                pan_y,
            )
        else:
            self._empty(out, cols, body_top, body_bottom, language)

        if status:
            out.write(
                move(body_bottom + 1, 2)
                + self._style(
                    self.config.accent,
                    self.config.background,
                    bold=True,
                )
                + status[: max(1, cols - 4)]
            )

        self._toolbar(out, cols, rows, language, zoom, body_bottom)
        if help_overlay:
            self._help_overlay(out, cols, rows, language)
        elif info_overlay and image:
            self._info_overlay(out, cols, rows, image, quality, display_mode, zoom, language)

        out.write(RESET)
        return out.getvalue()

    def progress(
        self,
        stage: str,
        progress: float,
        message: str,
        *,
        language: Language = Language.ENGLISH,
    ) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)
        out = StringIO()
        self._clean_frame(out)

        title = tr(language, "app_title")
        subtitle = tr(language, "subtitle").upper()
        center = cols // 2

        out.write(
            move(max(3, rows // 2 - 6), max(1, center - len(title) // 2))
            + self._style(self.config.foreground, self.config.background, bold=True)
            + title
        )
        out.write(
            move(max(4, rows // 2 - 5), max(1, center - len(subtitle) // 2))
            + self._style(self.config.muted, self.config.background)
            + subtitle
        )

        box_w = min(68, max(32, cols - 8))
        left = max(2, center - box_w // 2)
        row = max(7, rows // 2 - 2)

        out.write(
            move(row, left)
            + self._style(self.config.border, self.config.panel)
            + "╭" + "─" * (box_w - 2) + "╮"
        )
        text = message[: box_w - 4].center(box_w - 4)
        out.write(
            move(row + 1, left)
            + self._style(self.config.foreground, self.config.panel)
            + "│ " + text + " │"
        )

        bar_w = box_w - 4
        filled = int(bar_w * max(0.0, min(1.0, progress)))
        bar = "█" * filled + "░" * (bar_w - filled)
        pct = f"{progress * 100:5.1f}%"
        out.write(
            move(row + 2, left)
            + self._style(self.config.accent, self.config.panel)
            + "│ " + bar[:bar_w] + " │"
        )
        out.write(
            move(row + 3, left)
            + self._style(self.config.border, self.config.panel)
            + "╰" + "─" * (box_w - len(pct) - 4) + f" {pct}╯"
        )
        out.write(
            move(row + 5, max(1, center - len(stage) // 2))
            + self._style(self.config.muted, self.config.background)
            + stage.upper()
        )
        out.write(RESET)
        return out.getvalue()

    def _image(
        self,
        out: StringIO,
        image: Image.Image,
        cols: int,
        top: int,
        bottom: int,
        display_mode: DisplayMode,
        zoom: float,
        pan_x: float,
        pan_y: float,
    ) -> None:
        view_w = max(8, cols - 2)
        view_h = max(2, bottom - top + 1)

        if display_mode is DisplayMode.HALF_BLOCK:
            source = self._view_source(image, view_w, view_h * 2, zoom, pan_x, pan_y)
            self._render_half_block(out, source, cols, top, bottom)
            return

        if display_mode is DisplayMode.BRAILLE:
            source = self._view_source(image, view_w * 2, view_h * 4, zoom, pan_x, pan_y)
            self._render_braille(out, source, cols, top, bottom)
            return

        if display_mode is DisplayMode.QUADRANT:
            source = self._view_source(image, view_w * 2, view_h * 2, zoom, pan_x, pan_y)
            self._render_quadrant(out, source, cols, top, bottom)
            return

        source = self._view_source(image, view_w, view_h, zoom, pan_x, pan_y)
        self._render_character_cells(out, source, cols, top, bottom, display_mode)

    def _view_source(
        self,
        image: Image.Image,
        target_w: int,
        target_h: int,
        zoom: float,
        pan_x: float,
        pan_y: float,
    ) -> Image.Image:
        target_w = max(1, target_w)
        target_h = max(1, target_h)
        zoom = max(1.0, min(8.0, zoom))

        scale = min(target_w / image.width, target_h / image.height)
        scaled_w = max(1, int(image.width * scale * zoom))
        scaled_h = max(1, int(image.height * scale * zoom))

        resized = image.resize(
            (scaled_w, scaled_h),
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new("RGB", (target_w, target_h), self.config.background)
        if zoom <= 1.0001:
            x = (target_w - scaled_w) // 2
            y = (target_h - scaled_h) // 2
            canvas.paste(resized, (x, y))
            return canvas

        left_space = max(0, scaled_w - target_w)
        top_space = max(0, scaled_h - target_h)
        cx = left_space * (0.5 + max(-1.0, min(1.0, pan_x)) * 0.5)
        cy = top_space * (0.5 + max(-1.0, min(1.0, pan_y)) * 0.5)
        crop = resized.crop(
            (
                int(cx),
                int(cy),
                int(cx) + target_w,
                int(cy) + target_h,
            )
        )
        canvas.paste(crop, (0, 0))
        return canvas

    @staticmethod
    def _rgb(pixel: tuple[int, ...]) -> tuple[int, int, int]:
        return tuple(int(c) for c in pixel[:3])

    @staticmethod
    def _luma(rgb: tuple[int, int, int]) -> int:
        r, g, b = rgb
        return max(0, min(255, int(0.2126 * r + 0.7152 * g + 0.0722 * b)))

    def _render_half_block(
        self,
        out: StringIO,
        source: Image.Image,
        cols: int,
        top: int,
        bottom: int,
    ) -> None:
        px = source.load()
        width, height = source.size
        xoff = max(1, (cols - width) // 2)

        for y in range(0, height, 2):
            row = top + y // 2
            if row > bottom:
                break

            out.write(move(row, xoff))
            current_fg = None
            current_bg = None

            for x in range(width):
                fg = self._rgb(px[x, y])
                bg = self._rgb(px[x, y + 1]) if y + 1 < height else self.config.background
                if fg != current_fg:
                    out.write(self._fg(fg))
                    current_fg = fg
                if bg != current_bg:
                    out.write(self._bg(bg))
                    current_bg = bg
                out.write("▀")

            out.write(RESET + self._bg(self.config.background) + self._fg(self.config.foreground))

    def _render_character_cells(
        self,
        out: StringIO,
        source: Image.Image,
        cols: int,
        top: int,
        bottom: int,
        display_mode: DisplayMode,
    ) -> None:
        px = source.load()
        width, height = source.size
        xoff = max(1, (cols - width) // 2)
        yoff = top + max(0, ((bottom - top + 1) - height) // 2)

        chars: dict[DisplayMode, str] = {
            DisplayMode.FULL_BLOCK: "█",
            DisplayMode.LOWER_BLOCK: "▄",
            DisplayMode.LEFT_BLOCK: "▌",
            DisplayMode.RIGHT_BLOCK: "▐",
            DisplayMode.DARK_SHADE: "▓",
            DisplayMode.MEDIUM_SHADE: "▒",
            DisplayMode.LIGHT_SHADE: "░",
            DisplayMode.DOT: "●",
            DisplayMode.SMALL_DOT: "·",
        }
        ascii_ramp = "@$#*+=-:. "
        block_ramp = "█▉▊▋▌▍▎▏ "

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
                    out.write(self._fg(rgb))
                    current_fg = rgb

                if display_mode is DisplayMode.ASCII:
                    char = ascii_ramp[min(len(ascii_ramp) - 1, lum * len(ascii_ramp) // 256)]
                elif display_mode is DisplayMode.BLOCK_GRADIENT:
                    char = block_ramp[min(len(block_ramp) - 1, lum * len(block_ramp) // 256)]
                else:
                    char = chars.get(display_mode, "█")

                out.write(char)

            out.write(RESET + self._bg(self.config.background) + self._fg(self.config.foreground))

    def _render_quadrant(
        self,
        out: StringIO,
        source: Image.Image,
        cols: int,
        top: int,
        bottom: int,
    ) -> None:
        px = source.load()
        width, height = source.size
        cells_w = max(1, (width + 1) // 2)
        cells_h = max(1, (height + 1) // 2)
        xoff = max(1, (cols - cells_w) // 2)
        yoff = top + max(0, ((bottom - top + 1) - cells_h) // 2)

        glyphs = (
            " ", "▘", "▝", "▀",
            "▖", "▌", "▞", "▛",
            "▗", "▚", "▐", "▜",
            "▄", "▙", "▟", "█",
        )

        points = (
            (0, 0, 1),
            (1, 0, 2),
            (0, 1, 4),
            (1, 1, 8),
        )

        for cy in range(cells_h):
            row = yoff + cy
            if row > bottom:
                break
            out.write(move(row, xoff))

            for cx in range(cells_w):
                colors: list[tuple[int, int, int]] = []
                mask = 0
                for dx, dy, bit in points:
                    x = cx * 2 + dx
                    y = cy * 2 + dy
                    if x >= width or y >= height:
                        continue
                    rgb = self._rgb(px[x, y])
                    colors.append(rgb)
                    if self._luma(rgb) < 170:
                        mask |= bit

                avg = self._average(colors)
                out.write(self._fg(avg) + glyphs[mask])

            out.write(RESET + self._bg(self.config.background) + self._fg(self.config.foreground))

    def _render_braille(
        self,
        out: StringIO,
        source: Image.Image,
        cols: int,
        top: int,
        bottom: int,
    ) -> None:
        px = source.load()
        width, height = source.size
        cells_w = max(1, (width + 1) // 2)
        cells_h = max(1, (height + 3) // 4)
        xoff = max(1, (cols - cells_w) // 2)
        yoff = top + max(0, ((bottom - top + 1) - cells_h) // 2)

        points = (
            (0, 0, 1), (0, 1, 2), (0, 2, 4),
            (1, 0, 8), (1, 1, 16), (1, 2, 32),
            (0, 3, 64), (1, 3, 128),
        )

        for cy in range(cells_h):
            row = yoff + cy
            if row > bottom:
                break
            out.write(move(row, xoff))

            for cx in range(cells_w):
                mask = 0
                colors: list[tuple[int, int, int]] = []
                for dx, dy, bit in points:
                    x = cx * 2 + dx
                    y = cy * 4 + dy
                    if x >= width or y >= height:
                        continue
                    rgb = self._rgb(px[x, y])
                    colors.append(rgb)
                    if self._luma(rgb) < 170:
                        mask |= bit

                out.write(self._fg(self._average(colors)) + chr(0x2800 + mask))

            out.write(RESET + self._bg(self.config.background) + self._fg(self.config.foreground))

    @staticmethod
    def _average(colors: list[tuple[int, int, int]]) -> tuple[int, int, int]:
        if not colors:
            return (255, 255, 255)
        return tuple(
            sum(c[i] for c in colors) // len(colors)
            for i in range(3)
        )

    def _toolbar(
        self,
        out: StringIO,
        cols: int,
        rows: int,
        language: Language,
        zoom: float,
        row: int,
    ) -> None:
        buttons = [
            tr(language, "previous"),
            tr(language, "browse"),
            tr(language, "fit"),
            tr(language, "info"),
            tr(language, "next"),
        ]
        gap = 1
        total = sum(len(v) + 4 for v in buttons) + gap * (len(buttons) - 1)
        left = max(1, (cols - total) // 2)
        x = left

        out.write(
            move(row + 1)
            + self._style(self.config.border, self.config.background)
            + "─" * cols
        )

        for i, button in enumerate(buttons):
            w = len(button) + 4
            bg = self.config.panel
            fg = self.config.foreground
            out.write(
                move(row + 2, x)
                + self._style(self.config.border, bg)
                + "╭" + "─" * (w - 2) + "╮"
            )
            out.write(
                move(row + 3, x)
                + self._style(fg, bg, bold=True)
                + "│ " + button.center(w - 4) + " │"
            )
            out.write(
                move(row + 4, x)
                + self._style(self.config.border, bg)
                + "╰" + "─" * (w - 2) + "╯"
            )
            x += w + gap

        zoom_text = f"{zoom:g}x"
        if cols > total + len(zoom_text) + 4:
            out.write(
                move(row + 4, 2)
                + self._style(self.config.muted, self.config.background)
                + zoom_text
            )

    def _palette_demo(self, out: StringIO, row: int, left: int, width: int) -> None:
        colors = [
            self.config.background,
            self.config.foreground,
            self.config.muted,
            self.config.panel,
            self.config.border,
            self.config.accent,
            self.config.selection,
        ]
        swatch_w = max(3, width // len(colors))
        for i, color in enumerate(colors):
            x = left + i * swatch_w
            w = min(swatch_w, max(1, left + width - x))
            out.write(
                move(row, x)
                + self._bg(color)
                + " " * w
                + RESET
            )

        gradient_w = max(1, width // 24)
        start = self.config.background
        end = self.config.accent
        for i in range(24):
            t = i / 23
            color = tuple(
                int(start[c] + (end[c] - start[c]) * t)
                for c in range(3)
            )
            out.write(
                move(row + 1, left + i * gradient_w)
                + self._bg(color)
                + " " * min(gradient_w, width - i * gradient_w)
                + RESET
            )

    def _color_depth_short(self, language: Language) -> str:
        return tr(language, "truecolor") if self.truecolor else tr(language, "ansi256")

    @staticmethod
    def _size_text(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KiB"
        return f"{size / 1024 / 1024:.1f} MiB"

    def _empty(self, out: StringIO, cols: int, top: int, bottom: int, language: Language) -> None:
        message = tr(language, "no_images")
        row = (top + bottom) // 2
        out.write(
            move(row, max(1, (cols - len(message)) // 2))
            + self._style(self.config.muted, self.config.background)
            + message
        )

    def _help_overlay(self, out: StringIO, cols: int, rows: int, language: Language) -> None:
        lines = [
            tr(language, "app_title"),
            "",
            "A  Display mode",
            "P  Color palette",
            "+/-  Zoom",
            "0  Fit to screen",
            "I  Image information",
            "H  Help",
            "O  Browse",
            "Esc  Main menu",
            "Q  Quit",
        ]
        self._overlay(out, cols, rows, lines)

    def _info_overlay(
        self,
        out: StringIO,
        cols: int,
        rows: int,
        image: LoadedImage,
        quality: Quality,
        display_mode: DisplayMode,
        zoom: float,
        language: Language,
    ) -> None:
        lines = [
            tr(language, "info").upper(),
            "",
            f"File: {image.path.name}",
            f"Original: {image.original_size[0]} × {image.original_size[1]}",
            f"Preview: {image.source_size[0]} × {image.source_size[1]}",
            f"Mode: {display_mode.label}",
            f"Quality: {quality.label}",
            f"Zoom: {zoom:g}x",
            f"File size: {self._size_text(image.file_bytes)}",
        ]
        self._overlay(out, cols, rows, lines)

    def _overlay(self, out: StringIO, cols: int, rows: int, lines: list[str]) -> None:
        width = min(72, max(34, cols - 6))
        height = min(len(lines) + 2, rows - 4)
        left = max(2, (cols - width) // 2)
        top = max(2, (rows - height) // 2)

        for i in range(height):
            out.write(
                move(top + i, left)
                + self._style(self.config.foreground, self.config.panel)
                + " " * width
            )

        for i, line in enumerate(lines[: height - 2]):
            out.write(
                move(top + 1 + i, left + 2)
                + self._style(
                    self.config.foreground,
                    self.config.panel,
                    bold=(i == 0),
                )
                + line[: width - 4]
            )
