# Changelog

## 0.2.1

### Improved
- Friendlier responsive main menu with larger cards, descriptions and touch-safe geometry.
- Responsive Options layout with a dedicated palette preview on wide terminals.
- Better viewer toolbar with a real Menu control and cleaner button framing.
- 16-color ANSI output is now available alongside ANSI256 and Truecolor.
- Palette preview now shows UI swatches, a color-range strip and the actual image color count.
- Higher-resolution decoded image sources preserve substantially more detail for 1×–8× zoom.

### Fixed
- Global Q quit key now works from Options as well as other screens.
- Viewer Menu touch target was missing despite being handled by the app.
- Browser now has a real touchscreen Back button.
- Main-menu compact geometry no longer collides with the footer.
- Options preview can no longer overlap the settings list on small terminals.
- Options metadata no longer collides with the preview in medium terminals.
- Small-terminal main menu cards stay clear of the footer.
- Application background is applied before clearing, keeping blank cells consistent with the selected palette.
- Touch hitboxes no longer include the first cell outside their visible cards.
- Overlay Esc now closes the overlay before leaving the viewer.
- Browser Home/End navigation is wired up.
- Recursive library-scan progress is kept monotonic.
- Zoom and pan are preserved when the current image is reloaded for a terminal resize or quality change.
- Scaled viewer images are cached so zoom/pan movement avoids repeating expensive resizes.
- The viewer cache is deliberately bounded for Raspberry Pi memory usage.
- Palette preview gradients are constrained to their panel width.
- ANSI16 conversion is included for terminals without ANSI256/Truecolor support.

## 0.2.0

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
