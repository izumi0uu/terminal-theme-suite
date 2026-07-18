import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tomlkit

from terminal_theme_suite.adapters import herdr, omp
from terminal_theme_suite.config import load_config


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_omp_theme_has_coordinated_required_tokens(self):
        hero = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        document = omp.build_theme(hero)
        colors = document["colors"]
        self.assertEqual(document["$schema"], omp.OMP_THEME_SCHEMA)
        self.assertEqual(colors["text"], "#120f0d")
        self.assertEqual(colors["toolOutput"], "#211b17")
        self.assertEqual(colors["statusLinePath"], "#0f355c")
        self.assertNotIn("link", colors)
        self.assertNotIn("toolText", colors)

    def test_herdr_update_preserves_unrelated_sections(self):
        hero = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "config.toml"
            target.write_text('[terminal]\nnew_cwd = "follow"\n', encoding="utf-8")
            with patch.object(herdr, "HERDR_CONFIG", target):
                updated = herdr._updated_document(hero)
        document = tomlkit.parse(updated)
        self.assertEqual(document["terminal"]["new_cwd"], "follow")
        self.assertEqual(document["theme"]["name"], "catppuccin-latte")
        self.assertEqual(document["theme"]["custom"]["panel_bg"], "reset")

    def test_herdr_update_replaces_existing_theme_only(self):
        hero = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "config.toml"
            target.write_text(
                '[theme]\nname = "nord"\nauto_switch = true\n\n[keys]\nprefix = "ctrl+a"\n',
                encoding="utf-8",
            )
            with patch.object(herdr, "HERDR_CONFIG", target):
                updated = herdr._updated_document(hero)
        document = tomlkit.parse(updated)
        self.assertEqual(document["theme"]["name"], "catppuccin-latte")
        self.assertFalse(document["theme"]["auto_switch"])
        self.assertEqual(document["keys"]["prefix"], "ctrl+a")


if __name__ == "__main__":
    unittest.main()
