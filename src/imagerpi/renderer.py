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
    rgb_bg_16,
    rgb_bg_256,
    rgb_fg,
    rgb_fg_16,
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
        if self.truecolor:
            return rgb_fg(rgb, True)
        if self.config.color_depth is ColorDepth.ANSI16:
            return rgb_fg_16(rgb)
        return rgb_fg_256(rgb)

    def _bg(self, rgb: tuple[int, int, int]) -> str:
        if self.truecolor:
            return rgb_bg(rgb, True)
        if self.config.color_depth is ColorDepth.ANSI16:
            return rgb_bg_16(rgb)
        return rgb_bg_256(rgb)

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
        # Set the background before clearing so blank cells are painted with
        # the selected application palette instead of the terminal's default.
        out.write(self._bg(self.config.background))
        out.write(self._fg(self.config.foreground))
        out.write("\x1b[2J\x1b[H")

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

        center = max(1, cols // 2)
        left, title_row, first_row, button_w, button_h, gap = self._main_menu_geometry(cols, rows)

        title = tr(language, "app_title")
        subtitle = tr(language, "subtitle")
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

        spaced = " ".join(title)
        out.write(
            move(title_row + 1, max(1, center - len(spaced) // 2))
            + self._style(self.config.accent, self.config.background, bold=True)
            + spaced
        )

        out.write(
            move(title_row + 2, max(1, center - len(subtitle) // 2))
            + self._style(self.config.muted, self.config.background)
            + subtitle
        )

        count_text = tr(language, "image_count", count=image_count)
        palette_text = f"{palette.label} · {self._color_depth_short(language)}"
        meta = f"{count_text}   •   {palette_text}"
        out.write(
            move(title_row + 3, max(1, center - len(meta) // 2))
            + self._style(self.config.muted, self.config.background)
            + meta[: max(1, cols - 2)]
        )

        items = [
            (
                "1",
                tr(language, "view_images"),
                tr(language, "view_images_desc"),
                "▣",
            ),
            (
                "2",
                tr(language, "options"),
                tr(language, "options_desc"),
                "⚙",
            ),
            (
                "3",
                tr(language, "quit"),
                tr(language, "quit_desc"),
                "×",
            ),
        ]

        for i, (number, label, description, icon) in enumerate(items):
            row = first_row + i * (button_h + gap)
            active = i == selected
            bg = self.config.selection if active else self.config.panel
            fg = (255, 255, 255) if active else self.config.foreground
            border = self.config.accent if active else self.config.border

            if button_h >= 4:
                top = "╭" + "─" * (button_w - 2) + "╮"
                middle = f"│  {icon}  {number}  {label}"
                detail = f"│      {description}"
                bottom = "╰" + "─" * (button_w - 2) + "╯"

                out.write(move(row, left) + self._style(border, bg) + top)
                out.write(
                    move(row + 1, left)
                    + self._style(fg, bg, bold=active)
                    + middle.ljust(button_w - 1)[: button_w - 1]
                    + "│"
                )
                out.write(
                    move(row + 2, left)
                    + self._style(
                        self.config.muted if not active else (225, 235, 255),
                        bg,
                    )
                    + detail.ljust(button_w - 1)[: button_w - 1]
                    + "│"
                )
                out.write(move(row + 3, left) + self._style(border, bg) + bottom)
            elif button_h == 3:
                top = "╭" + "─" * (button_w - 2) + "╮"
                middle = f"│  {icon}  {number}  {label}"
                bottom = "╰" + "─" * (button_w - 2) + "╯"
                out.write(move(row, left) + self._style(border, bg) + top)
                out.write(
                    move(row + 1, left)
                    + self._style(fg, bg, bold=active)
                    + middle.ljust(button_w - 1)[: button_w - 1]
                    + "│"
                )
                out.write(move(row + 2, left) + self._style(border, bg) + bottom)
            else:
                out.write(
                    move(row, left)
                    + self._style(border, bg)
                    + "┌" + "─" * (button_w - 2) + "┐"
                )
                label_line = f"│  {icon}  {number}  {label}"
                out.write(
                    move(row + 1, left)
                    + self._style(fg, bg, bold=active)
                    + label_line.ljust(button_w - 1)[: button_w - 1]
                    + "│"
                )

        hint = (
            f"↑ ↓ {tr(language, 'navigate')}   "
            f"Enter {tr(language, 'select')}   "
            f"1/2/3 {tr(language, 'select')}   "
            f"Q {tr(language, 'quit')}"
        )
        footer_row = max(1, rows - 1)
        out.write(
            move(footer_row, max(1, center - len(hint) // 2))
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

        title = tr(language, "options")
        center = max(1, cols // 2)
        out.write(
            move(2, max(1, center - len(title) // 2))
            + self._style(
                self.config.foreground,
                self.config.background,
                bold=True,
            )
            + title.upper()
        )

        items = [
            (tr(language, "image_quality"), quality.label),
            (tr(language, "display_mode"), display_mode.label),
            (tr(language, "color_palette"), palette.label),
            (tr(language, "color_depth"), color_depth.label),
            (
                tr(language, "recursive_scan"),
                tr(language, "on") if recursive_scan else tr(language, "off"),
            ),
            (
                tr(language, "touch_controls"),
                tr(language, "on") if touch_controls else tr(language, "off"),
            ),
            (tr(language, "language"), language.label),
            (tr(language, "font"), terminal_font or "Terminal default"),
            (tr(language, "reset_settings"), ""),
            (tr(language, "back"), ""),
        ]

        wide = cols >= 86 and rows >= 18
        top = 4

        if wide:
            list_w = min(48, max(42, cols // 2))
            preview_w = min(30, max(26, cols - list_w - 8))
            total_w = list_w + 3 + preview_w
            left = max(2, center - total_w // 2)
            preview_left = left + list_w + 3
        else:
            list_w = min(78, max(38, cols - 8))
            left = max(2, center - list_w // 2)
            preview_left = left
            preview_w = list_w

        # Medium terminals stack the preview below the list; tiny terminals
        # skip it entirely to keep the controls readable.
        reserve_preview = 6 if (not wide and rows >= 16) else 0
        bottom = max(top, rows - 3 - reserve_preview)
        visible_rows = max(1, bottom - top + 1)
        max_items = min(len(items), visible_rows)
        window_start = max(
            0,
            min(selected - max_items // 2, len(items) - max_items),
        )

        for display_i in range(max_items):
            i = window_start + display_i
            row = top + display_i
            name, value = items[i]
            active = i == selected

            if wide:
                bg = self.config.selection if active else self.config.panel
                fg = (255, 255, 255) if active else self.config.foreground
                border = self.config.accent if active else self.config.border

                out.write(
                    move(row, left)
                    + self._style(border, bg)
                    + ("▌" if active else "│")
                    + self._style(fg, bg, bold=active)
                )
                value_text = f"  {value}" if value else ""
                label = f" {name}{value_text}"
                if len(label) > list_w - 3:
                    label = label[: list_w - 4] + "…"
                out.write(label.ljust(list_w - 2) + "│")
            else:
                bg = self.config.selection if active else self.config.panel
                fg = (255, 255, 255) if active else self.config.foreground
                border = self.config.accent if active else self.config.border
                marker = "▸ " if active else "  "
                value_text = f"  {value}" if value else ""
                label = f"{marker}{name}{value_text}"
                if len(label) > list_w - 2:
                    label = label[: list_w - 3] + "…"
                label = label.ljust(list_w - 2)

                out.write(
                    move(row, left)
                    + self._style(border, bg)
                    + "│"
                    + self._style(fg, bg, bold=active)
                    + label
                    + "│"
                )

        if window_start > 0:
            out.write(
                move(top, left + list_w - 3)
                + self._style(self.config.accent, self.config.panel, bold=True)
                + "↑"
            )
        if window_start + max_items < len(items):
            out.write(
                move(top + max_items - 1, left + list_w - 3)
                + self._style(self.config.accent, self.config.panel, bold=True)
                + "↓"
            )

        # Dedicated preview card. It shows the selected theme and actual color depth.
        preview_top = 4 if wide else top + max_items + 1
        available_preview_rows = max(0, rows - preview_top - 2)
        draw_preview = wide or available_preview_rows >= 5
        preview_h = min(10, available_preview_rows) if draw_preview else 0
        bottom_row = 0

        if draw_preview and preview_h >= 5:
            out.write(
                move(preview_top, preview_left)
                + self._style(self.config.border, self.config.panel)
                + "╭" + "─" * (preview_w - 2) + "╮"
            )

            preview_title = tr(language, "palette_preview")
            out.write(
                move(preview_top + 1, preview_left)
                + self._style(
                    self.config.foreground,
                    self.config.panel,
                    bold=True,
                )
                + "│"
                + preview_title.center(preview_w - 2)
                + "│"
            )

            palette_line = f"  {palette.label}  "
            out.write(
                move(preview_top + 2, preview_left)
                + self._style(
                    self.config.accent,
                    self.config.panel,
                    bold=True,
                )
                + "│"
                + palette_line.center(preview_w - 2)
                + "│"
            )

            self._palette_demo(
                out,
                preview_top + 3,
                preview_left + 2,
                preview_w - 4,
            )

            color_count = tr(
                language,
                "image_colors",
                count=self._color_count_short(),
            )
            out.write(
                move(preview_top + 5, preview_left + 2)
                + self._style(self.config.muted, self.config.panel)
                + color_count[: preview_w - 4]
            )

            if preview_h >= 7:
                depth_line = (
                    f"{tr(language, 'color_depth')}: "
                    f"{self._color_depth_short(language)}"
                )
                out.write(
                    move(preview_top + 6, preview_left + 2)
                    + self._style(self.config.muted, self.config.panel)
                    + depth_line[: preview_w - 4]
                )

            if preview_h >= 8:
                mode_line = (
                    f"{tr(language, 'display_mode')}: "
                    f"{display_mode.label}"
                )
                out.write(
                    move(preview_top + 7, preview_left + 2)
                    + self._style(self.config.muted, self.config.panel)
                    + mode_line[: preview_w - 4]
                )

            bottom_row = preview_top + preview_h
            if bottom_row < rows - 2:
                out.write(
                    move(bottom_row, preview_left)
                    + self._style(self.config.border, self.config.panel)
                    + "╰" + "─" * (preview_w - 2) + "╯"
                )

        term_text = tr(language, "terminal", cols=cols, rows=rows)
        count_text = tr(language, "image_count", count=image_count)
        meta = f"{term_text}   •   {count_text}"
        out.write(
            move(3, max(1, center - len(meta) // 2))
            + self._style(self.config.muted, self.config.background)
            + meta[: max(1, cols - 2)]
        )

        hint = (
            f"↑ ↓ {tr(language, 'navigate')}   "
            f"← → {tr(language, 'select')}   "
            f"Enter {tr(language, 'select')}   "
            f"Esc {tr(language, 'back_hint')}"
        )
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
        root: Path | None = None,
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
            try:
                relative = str(entry.relative_to(root)) if root else entry.name
            except ValueError:
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

        if entries and len(entries) > visible:
            track_h = max(1, body_bottom - body_top + 1)
            thumb_h = max(1, track_h * visible // len(entries))
            thumb_y = body_top + (track_h - thumb_h) * start // max(1, len(entries) - visible)
            out.write(
                move(body_top, min(cols - 2, left + panel_w + 1))
                + self._style(self.config.border, self.config.background)
                + "│"
            )
            for bar_row in range(body_top, body_bottom + 1):
                if thumb_y <= bar_row < thumb_y + thumb_h:
                    out.write(
                        move(bar_row, min(cols - 2, left + panel_w + 1))
                        + self._style(self.config.accent, self.config.background)
                        + "█"
                    )

        if not entries:
            message = tr(language, "no_images")
            out.write(
                move((body_top + body_bottom) // 2, max(1, (cols - len(message)) // 2))
                + self._style(self.config.muted, self.config.background)
                + message
            )

        # A real back button makes the browser comfortable on touchscreens.
        back_w = min(30, max(18, cols - 12))
        back_left = max(1, (cols - back_w) // 2)
        back_row = rows - 3
        out.write(
            move(back_row, back_left)
            + self._style(self.config.border, self.config.panel)
            + "╭" + "─" * (back_w - 2) + "╮"
        )
        back_label = tr(language, "back")
        out.write(
            move(back_row + 1, back_left)
            + self._style(self.config.foreground, self.config.panel, bold=True)
            + "│  " + back_label.center(back_w - 6) + "  │"
        )

        hint = f"↑ ↓ {tr(language, 'navigate')}   Enter {tr(language, 'open')}   Esc {tr(language, 'back_hint')}"
        out.write(
            move(rows - 1, max(1, (cols - len(hint)) // 2))
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
        image_count: int = 0,
        zoom: float = 1.0,
        pan_x: float = 0.0,
        pan_y: float = 0.0,
        info_overlay: bool = False,
        help_overlay: bool = False,
    ) -> str:
        size = terminal_size()
        cols, rows = max(size.columns, 40), max(size.lines, 12)

        if browser_entries is not None:
            return self.browser(
                cols,
                rows,
                browser_entries,
                browser_index,
                language,
            )

        out = StringIO()
        self._clean_frame(out)

        filename = image.path.name if image else "IMAGE.RPI"
        if image:
                index_text = f"{browser_index + 1}/{max(1, image_count)}"
            zoom_text = tr(language, "zoom", value=f"{zoom:g}")
            top = (
                f" {tr(language, 'app_title')}  │  {filename}"
                f"  │  {index_text}"
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
        body_bottom = max(body_top, rows - 7)
        toolbar_row = rows - 4

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

        self._toolbar(out, cols, rows, language, zoom, toolbar_row)
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

        if display_mode is DisplayMode.FULL_BLOCK:
            source = self._view_source(image, view_w, view_h * 2, zoom, pan_x, pan_y)
            self._render_rectangles(out, source, cols, top, bottom)
            return

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

        crop_w = min(target_w, scaled_w)
        crop_h = min(target_h, scaled_h)
        src_x = int(min(max(cx, 0), max(0, scaled_w - crop_w)))
        src_y = int(min(max(cy, 0), max(0, scaled_h - crop_h)))

        crop = resized.crop(
            (
                src_x,
                src_y,
                src_x + crop_w,
                src_y + crop_h,
            )
        )
        dst_x = (target_w - crop_w) // 2
        dst_y = (target_h - crop_h) // 2
        canvas.paste(crop, (dst_x, dst_y))
        return canvas

    @staticmethod
    def _rgb(pixel: tuple[int, ...]) -> tuple[int, int, int]:
        return tuple(int(c) for c in pixel[:3])

    @staticmethod
    def _luma(rgb: tuple[int, int, int]) -> int:
        r, g, b = rgb
        return max(0, min(255, int(0.2126 * r + 0.7152 * g + 0.0722 * b)))

    def _render_rectangles(
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

            for x in range(width):
                a = self._rgb(px[x, y])
                b = self._rgb(px[x, y + 1]) if y + 1 < height else a
                rgb = tuple((a[i] + b[i]) // 2 for i in range(3))
                if rgb != current_fg:
                    out.write(self._fg(rgb))
                    current_fg = rgb
                out.write("█")

            out.write(
                RESET
                + self._bg(self.config.background)
                + self._fg(self.config.foreground)
            )

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
        compact = cols < 72
        if compact:
            buttons = [
                ("menu", "M"),
                ("prev", "<"),
                ("zoom_out", "-"),
                ("fit", "F"),
                ("info", "I"),
                ("zoom_in", "+"),
                ("next", ">"),
            ]
        else:
            buttons = [
                ("menu", tr(language, "menu")),
                ("prev", "‹"),
                ("zoom_out", "−"),
                ("browse", tr(language, "browse")),
                ("fit", tr(language, "fit")),
                ("info", tr(language, "info")),
                ("zoom_in", "+"),
                ("next", "›"),
            ]

        gap = 1
        widths = [max(5, len(label) + 4) for _, label in buttons]
        total = sum(widths) + gap * (len(buttons) - 1)

        if total > cols - 2:
            buttons = [
                ("menu", "M"),
                ("prev", "<"),
                ("zoom_out", "-"),
                ("browse", "B"),
                ("fit", "F"),
                ("info", "I"),
                ("zoom_in", "+"),
                ("next", ">"),
            ]
            widths = [5] * len(buttons)
            total = sum(widths) + gap * (len(buttons) - 1)

        left = max(1, (cols - total) // 2)

        out.write(
            move(row)
            + self._style(self.config.border, self.config.background)
            + "─" * cols
        )

        x = left
        for (action, label), width in zip(buttons, widths):
            active = (
                (action == "fit" and abs(zoom - 1.0) < 0.001)
                or (action == "zoom_in" and zoom > 1.0)
            )
            bg = self.config.selection if active else self.config.panel
            fg = (255, 255, 255) if active else self.config.foreground
            border = self.config.accent if active else self.config.border

            out.write(
                move(row + 1, x)
                + self._style(border, bg)
                + "╭" + "─" * (width - 2) + "╮"
            )
            out.write(
                move(row + 2, x)
                + self._style(fg, bg, bold=True)
                + "│"
                + label.center(width - 2)
                + "│"
            )
            out.write(
                move(row + 3, x)
                + self._style(border, bg)
                + "╰" + "─" * (width - 2) + "╯"
            )
            x += width + gap

        zoom_text = tr(language, "zoom", value=f"{zoom:g}")
        out.write(
            move(row + 4, max(1, (cols - len(zoom_text)) // 2))
            + self._style(self.config.muted, self.config.background)
            + zoom_text[: max(1, cols - 2)]
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
        width = max(7, width)
        swatch_w = max(1, width // len(colors))
        for i, color in enumerate(colors):
            x = left + (i * width) // len(colors)
            x2 = left + ((i + 1) * width) // len(colors)
            w = max(1, x2 - x)
            out.write(
                move(row, x)
                + self._bg(color)
                + " " * w
                + RESET
            )

        # Use proportional boundaries so all 24 segments fit exactly, even in
        # narrow Options panels.
        steps = 24
        for i in range(steps):
            x = left + (i * width) // steps
            x2 = left + ((i + 1) * width) // steps
            w = max(1, x2 - x)
            t = i / (steps - 1)
            start = self.config.background
            end = self.config.accent
            color = tuple(
                int(start[c] + (end[c] - start[c]) * t)
                for c in range(3)
            )
            out.write(
                move(row + 1, x)
                + self._bg(color)
                + " " * w
                + RESET
            )



    def _color_depth_short(self, language: Language) -> str:
        if self.truecolor:
            return tr(language, "truecolor")
        if self.config.color_depth is ColorDepth.ANSI16:
            return tr(language, "ansi16")
        return tr(language, "ansi256")

    def _color_count_short(self) -> str:
        if self.truecolor:
            return "16,777,216"
        if self.config.color_depth is ColorDepth.ANSI16:
            return "16"
        return "256"

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

    @staticmethod
    @staticmethod
    def _main_menu_geometry(
        cols: int,
        rows: int,
    ) -> tuple[int, int, int, int, int, int]:
        center = max(1, cols // 2)
        very_compact = rows < 14
        compact = rows < 22

        title_row = 1 if very_compact else 2
        if very_compact:
            button_w, button_h, gap = min(52, max(28, cols - 8)), 2, 0
        elif compact:
            button_w, button_h, gap = min(54, max(30, cols - 10)), 3, 0
        else:
            button_w, button_h, gap = min(58, max(32, cols - 12)), 4, 1

        total_height = 3 * button_h + 2 * gap

        # Keep a real footer row below the final button, even on tiny terminals.
        footer_row = max(1, rows - 1)
        desired = max(title_row + 4, (rows - total_height) // 2)
        max_first = max(title_row + 4, footer_row - total_height - 1)
        first_row = min(desired, max_first)

        # In the tightest terminals, sacrifice vertical centering rather than
        # letting the cards collide with the footer or title.
        first_row = max(title_row + 4, min(first_row, rows - total_height - 2))
        left = max(2, center - button_w // 2)
        return left, title_row, first_row, button_w, button_h, gap

    @staticmethod
    def main_menu_hit(x: int, y: int, cols: int, rows: int) -> int | None:
        left, _, first_row, button_w, button_h, gap = Renderer._main_menu_geometry(cols, rows)
        if not (left <= x < left + button_w):
            return None
        for i in range(3):
            row = first_row + i * (button_h + gap)
            if row <= y <= row + button_h - 1:
                return i
        return None

    @staticmethod
    def options_menu_hit(
        x: int,
        y: int,
        cols: int,
        rows: int,
        selected: int,
        item_count: int = 10,
    ) -> int | None:
        center = max(1, cols // 2)
        wide = cols >= 86 and rows >= 18
        if wide:
            list_w = min(48, max(42, cols // 2))
            preview_w = min(30, max(26, cols - list_w - 8))
            total_w = list_w + 3 + preview_w
            left = max(2, center - total_w // 2)
        else:
            list_w = min(78, max(38, cols - 8))
            left = max(2, center - list_w // 2)

        top = 4
        bottom = max(top, rows - 3)
        reserve_preview = 6 if (not wide and rows >= 16) else 0
        bottom = max(top, rows - 3 - reserve_preview)
        visible_rows = max(1, bottom - top + 1)
        max_items = min(item_count, visible_rows)
        window_start = max(
            0,
            min(selected - max_items // 2, item_count - max_items),
        )

        if not (left <= x < left + list_w):
            return None
        if y < top or y >= top + max_items:
            return None

        index = window_start + (y - top)
        return index if index < item_count else None



    @staticmethod
    def browser_hit(
        x: int,
        y: int,
        cols: int,
        rows: int,
        count: int,
        selected: int,
    ) -> int | None:
        body_top = 5
        body_bottom = rows - 5
        if y in {rows - 3, rows - 2}:
            return -1
        if y < body_top or y > body_bottom:
            return None
        visible = max(1, body_bottom - body_top + 1)
        start = max(0, min(selected - visible // 2, max(0, count - visible)))
        index = start + (y - body_top)
        return index if 0 <= index < count else None

    @staticmethod
    def viewer_hit(
        self,
        x: int,
        y: int,
        cols: int,
        rows: int,
        language: Language = Language.ENGLISH,
    ) -> str | None:
        toolbar_row = rows - 4
        if y < toolbar_row + 1 or y > toolbar_row + 3:
            return None

        compact = cols < 72
        if compact:
            labels = [
                ("menu", "M"),
                ("prev", "<"),
                ("zoom_out", "-"),
                ("fit", "F"),
                ("info", "I"),
                ("zoom_in", "+"),
                ("next", ">"),
            ]
        else:
            labels = [
                ("menu", tr(language, "menu")),
                ("prev", "‹"),
                ("zoom_out", "−"),
                ("browse", tr(language, "browse")),
                ("fit", tr(language, "fit")),
                ("info", tr(language, "info")),
                ("zoom_in", "+"),
                ("next", "›"),
            ]

        gap = 1
        widths = [max(5, len(label) + 4) for _, label in labels]
        total = sum(widths) + gap * (len(labels) - 1)
        if total > cols - 2:
            labels = [
                ("menu", "M"),
                ("prev", "<"),
                ("zoom_out", "-"),
                ("browse", "B"),
                ("fit", "F"),
                ("info", "I"),
                ("zoom_in", "+"),
                ("next", ">"),
            ]
            widths = [5] * len(labels)
            total = sum(widths) + gap * (len(labels) - 1)

        left = max(1, (cols - total) // 2)
        current_x = left
        for (action, _), width in zip(labels, widths):
            if current_x <= x < current_x + width:
                return action
            current_x += width + gap

        return None

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
