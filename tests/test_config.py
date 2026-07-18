import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terminal_theme_suite import config


class ConfigTests(unittest.TestCase):
    def test_builtin_order_starts_with_hero_amber(self):
        self.assertEqual(list(config.builtin_theme_documents())[0], "hero-amber")

    def test_load_config_merges_private_background(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "themes": {
                            "hero-amber": {
                                "background": "~/Pictures/private.png",
                                "blend": 0.4,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()
        hero = next(theme for theme in loaded.themes if theme.id == "hero-amber")
        self.assertEqual(
            hero.background, Path("~/Pictures/private.png").expanduser().resolve()
        )
        self.assertEqual(hero.blend, 0.4)
        self.assertEqual(hero.herdr_panel_bg, "reset")
        self.assertEqual(hero.extra["background_source"], "custom")

    def test_fresh_config_uses_bundled_backgrounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(len(loaded.themes), 4)
        for theme in loaded.themes:
            self.assertEqual(theme.extra["background_source"], "bundled")
            self.assertIsNotNone(theme.background)
            self.assertTrue(theme.background.is_file())
            self.assertEqual(theme.background.suffix, ".png")

    def test_legacy_null_background_uses_bundled_preset(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps({"themes": {"hero-amber": {"background": None}}}),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        hero = next(theme for theme in loaded.themes if theme.id == "hero-amber")
        self.assertEqual(hero.extra["background_source"], "bundled")
        self.assertEqual(hero.background.name, "hero-amber.png")

    def test_false_background_disables_bundled_preset(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps({"themes": {"dracula": {"background": False}}}),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        dracula = next(theme for theme in loaded.themes if theme.id == "dracula")
        self.assertIsNone(dracula.background)
        self.assertEqual(dracula.extra["background_source"], "disabled")

    def test_background_reset_removes_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps(
                    {"themes": {"hero-amber": {"background": "/tmp/custom.png"}}}
                ),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                config.update_theme_background("hero-amber", False)
                disabled = json.loads(config_path.read_text(encoding="utf-8"))
                config.update_theme_background("hero-amber", None)
                reset = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertIs(disabled["themes"]["hero-amber"]["background"], False)
        self.assertNotIn("background", reset["themes"]["hero-amber"])


if __name__ == "__main__":
    unittest.main()
