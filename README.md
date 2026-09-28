# IMAGE.RPI

A terminal-native image viewer for small Linux systems, especially Raspberry Pi 3B-class hardware running Debian 13 "Trixie" in a terminal-only environment.

## Features

- Rectangle-first rendering (█) that automatically scales to the terminal resolution.
- Half-block, gradient-block, quadrant, shade, dot, Braille and ASCII display modes.
- White canvas with ANSI Truecolor/256-color output.
- Automatic aspect-ratio fitting to the current terminal size.
- Six quality presets: Very Low, Low, Medium, High, Very High, Ultra.
- 24 built-in interface color presets with editable RGB overrides.
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

## Main menu

IMAGE.RPI starts in a fullscreen, centered application menu:

- View Images
- Options
- Quit

The Options screen contains image quality, display mode and color palette settings plus a small palette/color-depth preview.

## Controls

| Key | Action |
|---|---|
| Up / Down | Navigate menus |
| Enter | Select |
| Esc | Back to the main menu |
| A | Cycle display mode in the viewer |
| P | Cycle interface palette |
| R | Cycle image quality |
| I | Image information |
| H | Help |
| O | Open image browser |
| Left / Right | Previous / next image |
| Q | Quit |

The touchscreen can also be used where the terminal forwards touch as SGR mouse events.

## Display modes

The default is Rectangles (█). IMAGE.RPI fits the image to the current terminal cell area, so a larger terminal provides more cells and therefore smaller visual rectangles.

ASCII rendering is still available as an optional compatibility mode; it is not the default.

## Color palettes

IMAGE.RPI includes 24 built-in interface themes. The theme itself does not reduce the number of image colors. When the terminal reports Truecolor support, image pixels can use 24-bit RGB (16,777,216 possible RGB values); otherwise the renderer falls back to 256-color ANSI output.

On first run, the app creates:

    ~/.config/imagerpi/config.json

You can edit this file to change the default palette/display mode and override any preset's interface RGB values with hex colors. A repository example is provided as config.example.json.

Example:

    "palettes": {
      "light": {
        "accent": "#FF00AA",
        "selection": "#101820"
      }
    }

## Text font

A terminal application normally does not control the terminal emulator's font. IMAGE.RPI therefore supports an optional best-effort terminal_font setting for terminals that implement xterm-style font control; otherwise the terminal's own font settings remain in control.

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