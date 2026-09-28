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
        self.assertEqual(sizes[0], (20, 10))
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
        self.assertEqual(renderer.main_menu_hit(40, 10, 80, 24), 0)
        self.assertEqual(renderer.viewer_hit(20, 20, 80, 24), None)

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
