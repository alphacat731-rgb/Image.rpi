from __future__ import annotations

import os
import shutil
import sys
import termios
import tty
from contextlib import contextmanager
from dataclasses import dataclass

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


def supports_truecolor() -> bool:
    if os.getenv("COLORTERM", "").lower() in {"truecolor", "24bit"}:
        return True
    term = os.getenv("TERM", "")
    return (
        "direct" in term
        or "truecolor" in term
        or "kitty" in term
        or "foot" in term
    )


def rgb_fg(rgb: tuple[int, int, int]) -> str:
    if supports_truecolor():
        r, g, b = rgb
        return f"{ESC}38;2;{r};{g};{b}m"
    return f"{ESC}38;5;{_ansi256_index(rgb)}m"


def rgb_bg(rgb: tuple[int, int, int]) -> str:
    if supports_truecolor():
        r, g, b = rgb
        return f"{ESC}48;2;{r};{g};{b}m"
    return f"{ESC}48;5;{_ansi256_index(rgb)}m"


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


def terminal_size() -> shutil.os.terminal_size:
    return shutil.get_terminal_size((80, 24))


@dataclass(slots=True)
class RawTerminal:
    enabled: bool = False
    fd: int = sys.stdin.fileno()
    _old: list | None = None

    def enter(self) -> None:
        if not os.isatty(self.fd):
            return
        self._old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.enabled = True
        sys.stdout.write(ALT_SCREEN_ON + HIDE_CURSOR + MOUSE_ON + CLEAR + RESET)
        sys.stdout.flush()

    def leave(self) -> None:
        if self.enabled:
            sys.stdout.write(RESET + MOUSE_OFF + SHOW_CURSOR + ALT_SCREEN_OFF)
            sys.stdout.flush()
            if self._old is not None:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self._old)
        self.enabled = False

    def read_key(self) -> str:
        if not self.enabled:
            return sys.stdin.read(1)

        ch = os.read(self.fd, 1).decode("utf-8", "ignore")
        if ch != "\x1b":
            return ch

        seq = ch
        import select
        while select.select([self.fd], [], [], 0.01)[0]:
            seq += os.read(self.fd, 1).decode("utf-8", "ignore")

        if seq.startswith("\x1b[<") and seq.endswith(("M", "m")):
            payload = seq[3:-1]
            try:
                button, x, y = (int(part) for part in payload.split(";"))
                action = "PRESS" if seq.endswith("M") else "RELEASE"
                return f"MOUSE:{action}:{button}:{x}:{y}"
            except (TypeError, ValueError):
                pass

        return {
            "\x1b[A": "UP",
            "\x1b[B": "DOWN",
            "\x1b[C": "RIGHT",
            "\x1b[D": "LEFT",
            "\x1b[H": "HOME",
            "\x1b[F": "END",
        }.get(seq, "ESC")

    def write(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()


@contextmanager
def terminal_session():
    terminal = RawTerminal()
    terminal.enter()
    try:
        yield terminal
    finally:
        terminal.leave()
