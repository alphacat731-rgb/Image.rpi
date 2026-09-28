from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from imagerpi.config import AppConfig, DisplayMode, Palette, Quality
from imagerpi.loader import ImageLoader, list_images


class CoreTests(unittest.TestCase):
    def test_quality_cycles(self) -> None:
        self.assertIs(Quality.next(Quality.ULTRA), Quality.VERY_LOW)
        self.assertIs(Quality.next(Quality.HIGH), Quality.VERY_HIGH)

    def test_rectangle_mode_is_default_and_palettes_are_expanded(self) -> None:
        config = AppConfig()
        self.assertIs(config.default_display_mode, DisplayMode.FULL_BLOCK)
        self.assertEqual(len(list(Palette)), 24)
        config.apply_palette(Palette.MATRIX)
        self.assertEqual(config.accent, (20, 255, 55))

    def test_quality_changes_target_pixels(self) -> None:
        loader = ImageLoader(AppConfig())
        sizes = [
            loader._target_pixels((1600, 1200), q, (100, 30))
            for q in Quality
        ]
        self.assertEqual(sizes[0], (30, 23))
        self.assertTrue(
            all(
                a[0] <= b[0] and a[1] <= b[1]
                for a, b in zip(sizes, sizes[1:])
            )
        )

    def test_image_loading_and_white_composite(self) -> None:
        loader = ImageLoader(AppConfig())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transparent.png"
            image = Image.new("RGBA", (40, 20), (255, 0, 0, 0))
            image.putpixel((0, 0), (255, 0, 0, 255))
            image.save(path)

            loaded = loader.load(path, Quality.ULTRA, (80, 24))
            self.assertEqual(loaded.image.mode, "RGB")
            self.assertEqual(loaded.original_size, (40, 20))
            self.assertEqual(loaded.image.getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(
                loaded.image.getpixel((1, 1)),
                (255, 255, 255),
            )

    def test_renderer_touch_hit_regions_exist(self) -> None:
        from imagerpi.config import ColorDepth
        from imagerpi.renderer import Renderer

        config = AppConfig()
        config.color_depth = ColorDepth.ANSI256
        renderer = Renderer(config)
        self.assertEqual(renderer.main_menu_hit(40, 7, 80, 24), 0)
        self.assertEqual(renderer.main_menu_hit(40, 8, 80, 24), 0)
        self.assertEqual(renderer.main_menu_hit(40, 10, 80, 24), 1)
        self.assertEqual(renderer.viewer_hit(20, 20, 80, 24), None)
        self.assertEqual(renderer.viewer_hit(30, 21, 80, 24), "browse")
        self.assertEqual(renderer.viewer_hit(21, 21, 80, 24), "prev")
        self.assertEqual(renderer.viewer_hit(40, 21, 80, 24), "browse")

    def test_small_terminal_menu_geometry(self) -> None:
        from imagerpi.renderer import Renderer

        left, title_row, first_row, width, height, gap = Renderer._main_menu_geometry(80, 12)
        self.assertEqual((title_row, first_row, height, gap), (1, 5, 2, 0))
        self.assertLessEqual(first_row + 2 * (height + gap) + height - 1, 10)

    def test_touch_hit_regions_follow_visible_rows(self) -> None:
        from imagerpi.config import ColorDepth
        from imagerpi.renderer import Renderer

        config = AppConfig()
        config.color_depth = ColorDepth.ANSI256
        renderer = Renderer(config)

        self.assertEqual(renderer.options_menu_hit(40, 4, 80, 24, 0), 0)
        self.assertEqual(renderer.options_menu_hit(40, 5, 80, 24, 0), 1)
        self.assertEqual(renderer.browser_hit(40, 5, 80, 24, 5, 0), 0)
        self.assertEqual(renderer.browser_hit(40, 22, 80, 24, 5, 0), -1)

    def test_all_display_modes_render(self) -> None:
        from io import StringIO
        from imagerpi.renderer import Renderer

        config = AppConfig()
        renderer = Renderer(config)
        sample = Image.new("RGB", (32, 20), (120, 180, 240))

        for mode in DisplayMode:
            with self.subTest(mode=mode.value):
                out = StringIO()
                renderer._image(
                    out,
                    sample,
                    40,
                    1,
                    14,
                    mode,
                    1.0,
                    0.0,
                    0.0,
                )
                self.assertTrue(out.getvalue())

    def test_extreme_zoom_keeps_background_padding(self) -> None:
        from imagerpi.renderer import Renderer

        config = AppConfig()
        renderer = Renderer(config)
        sample = Image.new("RGB", (40, 2), (255, 0, 0))
        view = renderer._view_source(
            sample,
            20,
            10,
            8.0,
            0.0,
            0.0,
        )
        self.assertEqual(view.size, (20, 10))
        self.assertIn(
            view.getpixel((0, 9)),
            {config.background, (255, 0, 0)},
        )

    def test_list_images_recursive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "nested"
            nested.mkdir()
            (root / "root.png").write_bytes(b"placeholder")
            (nested / "nested.jpg").write_bytes(b"placeholder")
            found = list_images(root, recursive=True)
            self.assertEqual(
                [p.name for p in found],
                ["nested.jpg", "root.png"],
            )
            shallow = list_images(root, recursive=False)
            self.assertEqual([p.name for p in shallow], ["root.png"])

    def test_list_images_filters_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.txt").write_text("not an image")
            (root / "a.png").write_bytes(b"placeholder")
            (root / "C.JPG").write_bytes(b"placeholder")
            self.assertEqual(
                [p.name for p in list_images(root)],
                ["a.png", "C.JPG"],
            )


if __name__ == "__main__":
    unittest.main()
