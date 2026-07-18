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


if __name__ == "__main__":
    unittest.main()
