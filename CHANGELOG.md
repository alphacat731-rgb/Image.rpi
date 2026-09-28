# Changelog

## 0.2.0

### Added
- Fullscreen, centered main menu with View Images, Options and Quit.
- Responsive Options screen with image quality, display mode, palette, color depth, scan, touch, language and font settings.
- 24 built-in interface palettes plus editable RGB overrides in `~/.config/imagerpi/config.json`.
- Palette swatches and color-depth preview.
- Rectangle-first image rendering with terminal-cell aspect compensation.
- Additional display modes: half block, lower/side blocks, gradient blocks, quadrants, shades, dots, Braille and ASCII.
- Zoom controls from 1× to 8× with keyboard and touchscreen toolbar support.
- Library startup scan, recursive indexing, relative paths and scrollbar.
- Page navigation in the image browser.
- Persistent user settings and safe font presets.
- Synchronized terminal writes and buffered escape-sequence input.
- JPEG draft decoding for more memory-friendly large-image loading.

### Fixed
- Continuous full-screen redraw that caused severe blinking.
- Touch hitboxes missing from menus.
- Viewer toolbar overlapping the lower terminal rows.
- Lost/reordered escape sequences during fast input.
- Explicit ANSI256/Truecolor setting being ignored.
- EXIF-rotated images being sized against the wrong orientation.
- Extreme zoom on panoramic/portrait images producing black padding.
- CLI image paths not opening automatically after startup indexing.
- Font option accidentally triggering Reset Settings.
- Reset Settings unable to clear saved palette overrides.

### Validation
- GitHub Actions tests on Python 3.11 and 3.13.
