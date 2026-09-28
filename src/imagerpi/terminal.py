from __future__ import annotations

import os
import shutil
import sys
import termios
import tty
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache

ESC = "\x1b["
RESET = ESC + "0m"
HIDE_CURSOR = ESC + "?25l"
SHOW_CURSOR = ESC + "?25h"
ALT_SCREEN_ON = ESC + "?1049h"
ALT_SCREEN_OFF = ESC + "?1049l"
MOUSE_ON = ESC + "?1000h" + ESC + "?1006h"
MOUSE_OFF = ESC + "?1000l" + ESC + "?1006l"
CLEAR = ESC + "2J" + ESC + "H"
ERASE_LINE = ESC + "2K"
SYNC_BEGIN = ESC + "?2026h"
SYNC_END = ESC + "?2026l"


def _ansi256_index(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + round((r - 8) / 247 * 24)
    return (
        16
        + 36 * round(r / 255 * 5)
        + 6 * round(g / 255 * 5)
        + round(b / 255 * 5)
    )


@lru_cache(maxsize=1)
def supports_truecolor() -> bool:
    if os.getenv("IMAGERPI_COLOR_DEPTH", "").lower() == "truecolor":
        return True
    if os.getenv("IMAGERPI_COLOR_DEPTH", "").lower() == "ansi256":
        return False
    if os.getenv("COLORTERM", "").lower() in {"truecolor", "24bit"}:
        return True
    term = os.getenv("TERM", "").lower()
    return "direct" in term or "truecolor" in term or "kitty" in term or "foot" in term


def rgb_fg(
    rgb: tuple[int, int, int],
    truecolor: bool | None = None,
) -> str:
    use_truecolor = supports_truecolor() if truecolor is None else truecolor
    if use_truecolor:
        r, g, b = rgb
        return f"{ESC}38;2;{r};{g};{b}m"
    return rgb_fg_256(rgb)


def rgb_bg(
    rgb: tuple[int, int, int],
    truecolor: bool | None = None,
) -> str:
    use_truecolor = supports_truecolor() if truecolor is None else truecolor
    if use_truecolor:
        r, g, b = rgb
        return f"{ESC}48;2;{r};{g};{b}m"
    return rgb_bg_256(rgb)


ANSI16_RGB = (
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (128, 128, 0),
    (0, 0, 128),
    (128, 0, 128),
    (0, 128, 128),
    (192, 192, 192),
    (128, 128, 128),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
)


def _ansi16_index(rgb: tuple[int, int, int]) -> int:
    def distance(c):
        return sum((int(rgb[i]) - c[i]) ** 2 for i in range(3))
    return min(range(len(ANSI16_RGB)), key=lambda i: distance(ANSI16_RGB[i]))


def rgb_fg_16(rgb: tuple[int, int, int]) -> str:
    index = _ansi16_index(rgb)
    return f"{ESC}{30 + index if index < 8 else 90 + index - 8}m"


def rgb_bg_16(rgb: tuple[int, int, int]) -> str:
    index = _ansi16_index(rgb)
    return f"{ESC}{40 + index if index < 8 else 100 + index - 8}m"


def rgb_fg_256(rgb: tuple[int, int, int]) -> str:
    return f"{ESC}38;5;{_ansi256_index(rgb)}m"


def rgb_bg_256(rgb: tuple[int, int, int]) -> str:
    return f"{ESC}48;5;{_ansi256_index(rgb)}m"


def move(row: int, col: int = 1) -> str:
    return f"{ESC}{row};{col}H"


def style(
    fg: tuple[int, int, int],
    bg: tuple[int, int, int] | None = None,
    *,
    bold: bool = False,
) -> str:
    parts = [rgb_fg(fg)]
    if bg is not None:
        parts.append(rgb_bg(bg))
    if bold:
        parts.append(ESC + "1m")
    return "".join(parts)


def set_terminal_font(font: str) -> str:
    safe = font.replace("\x1b", "").replace("\x07", "").replace("\n", "")
    return f"\x1b]50;{safe}\x07"


def reset_terminal_font() -> str:
    return "\x1b]50;#0\x07"


def terminal_size() -> shutil.os.terminal_size:
    return shutil.get_terminal_size((80, 24))


@dataclass(slots=True)
class RawTerminal:
    enabled: bool = False
    fd: int = sys.stdin.fileno()
    _old: list | None = None
    _font_was_set: bool = False
    _input_buffer: str = ""

    def enter(self, font: str = "", mouse: bool = True) -> None:
        if not os.isatty(self.fd):
            return
        self._old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.enabled = True

        font_sequence = set_terminal_font(font) if font else ""
        self._font_was_set = bool(font_sequence)
        mouse_sequence = MOUSE_ON if mouse else ""
        sys.stdout.write(
            ALT_SCREEN_ON
            + HIDE_CURSOR
            + mouse_sequence
            + CLEAR
            + RESET
            + font_sequence
        )
        sys.stdout.flush()

    def leave(self) -> None:
        if self.enabled:
            font_reset = reset_terminal_font() if self._font_was_set else ""
            sys.stdout.write(
                SYNC_END
                + RESET
                + font_reset
                + MOUSE_OFF
                + SHOW_CURSOR
                + ALT_SCREEN_OFF
            )
            sys.stdout.flush()
            if self._old is not None:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self._old)
        self.enabled = False
        self._font_was_set = False
        self._input_buffer = ""

    def _read_available(self) -> str:
        import select

        chunks: list[str] = []
        while select.select([self.fd], [], [], 0.01)[0]:
            data = os.read(self.fd, 64)
            if not data:
                break
            chunks.append(data.decode("utf-8", "ignore"))
        return "".join(chunks)

    def read_key(self) -> str:
        if not self.enabled:
            return sys.stdin.read(1)

        if self._input_buffer:
            data = self._input_buffer
            self._input_buffer = ""
        else:
            data = os.read(self.fd, 1).decode("utf-8", "ignore")

        if not data:
            return ""

        if data[0] != "\x1b":
            self._input_buffer = data[1:]
            return data[0]

        data += self._read_available()

        if data.startswith("\x1b[<"):
            end = None
            for i, ch in enumerate(data[3:], start=3):
                if ch in "Mm":
                    end = i + 1
                    break

            if end is not None:
                sequence = data[:end]
                self._input_buffer = data[end:]
                payload = sequence[3:-1]
                try:
                    button, x, y = (int(part) for part in payload.split(";"))
                    action = "PRESS" if sequence.endswith("M") else "RELEASE"
                    return f"MOUSE:{action}:{button}:{x}:{y}"
                except (TypeError, ValueError):
                    return "ESC"

        key_sequences = (
            ("\x1b[A", "UP"),
            ("\x1b[B", "DOWN"),
            ("\x1b[C", "RIGHT"),
            ("\x1b[D", "LEFT"),
            ("\x1b[H", "HOME"),
            ("\x1b[F", "END"),
            ("\x1b[1~", "HOME"),
            ("\x1b[4~", "END"),
            ("\x1b[5~", "PAGEUP"),
            ("\x1b[6~", "PAGEDOWN"),
        )
        for sequence, key in key_sequences:
            if data.startswith(sequence):
                self._input_buffer = data[len(sequence):]
                return key

        self._input_buffer = data[1:]
        return "ESC"

    def write(self, text: str, *, synchronized: bool = True) -> None:
        if synchronized:
            sys.stdout.write(SYNC_BEGIN)
        sys.stdout.write(text)
        if synchronized:
            sys.stdout.write(SYNC_END)
        sys.stdout.flush()


@contextmanager
def terminal_session(font: str = "", mouse: bool = True):
    terminal = RawTerminal()
    terminal.enter(font, mouse=mouse)
    try:
        yield terminal
    finally:
        terminal.leave()
