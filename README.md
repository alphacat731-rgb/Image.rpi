# IMAGE.RPI

A terminal-native image viewer for small Linux systems, especially Raspberry Pi 3B-class hardware running Debian 13 "Trixie" in a terminal-only environment.

## Features

- Unicode half-block (▀) image rendering directly in the terminal.
- White canvas with ANSI RGB/256-color output.
- Automatic aspect-ratio fitting to the current terminal size.
- Six quality presets: Very Low, Low, Medium, High, Very High, Ultra.
- Background image loading with progress UI for large files.
- Keyboard-driven image browser and previous/next navigation.
- Image information and help overlays.
- EXIF orientation handling.
- Transparent images composited over white.
- JPEG, PNG, WebP, BMP, GIF, TIFF and common Netpbm formats via Pillow.
- Conservative decoded-pixel safety limit for Raspberry Pi memory constraints.
- No GTK, Qt, X11 or Wayland dependency.

## Install on Debian Trixie

Run:

    chmod +x install.sh
    ./install.sh

The installer uses Debian packages and places a launcher at /usr/local/bin/imagerpi.

## Run

    imagerpi /home/pi/Pictures/photo.jpg
    imagerpi /home/pi/Pictures
    imagerpi

## Controls

| Key | Action |
|---|---|
| O | Open browser |
| R | Cycle quality |
| I | Image information |
| H | Help |
| Left / Right | Previous / next |
| Up / Down | Browser selection |
| Enter | Open selected image |
| Q / Esc | Quit |

## Quality

Quality controls the number of source samples generated before terminal rendering. Lower levels trade detail for less resize work; Ultra uses the maximum useful terminal sample size. The renderer then fits the preview to the available terminal area.

## Environment variables

- IMAGERPI_MAX_PIXELS — decoded pixel safety limit, default 60,000,000.
- IMAGERPI_LARGE_FILE_MB — large-file threshold, default 24.
- IMAGERPI_FPS — UI cadence, clamped to 8–30, default 20.
- IMAGERPI_QUALITY — default preset such as HIGH or ULTRA.

Example:

    IMAGERPI_MAX_PIXELS=100000000 imagerpi huge.png

## Project layout

    src/imagerpi/
    ├── app.py
    ├── config.py
    ├── loader.py
    ├── renderer.py
    ├── terminal.py
    └── __main__.py

IMAGE.RPI stays GUI-free on purpose: the terminal is the display surface.