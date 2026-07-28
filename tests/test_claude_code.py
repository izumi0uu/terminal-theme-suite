import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from terminal_theme_suite.adapters import claude_code
from terminal_theme_suite.config import CLAUDE_COLOR_TOKENS, load_config


class ClaudeCodeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_theme_maps_full_semantic_palette(self):
        hero = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        document = claude_code.build_theme(hero)
        overrides = document["overrides"]

        self.assertEqual(document["base"], "light")
        self.assertEqual(overrides["text"], hero.colors["foreground"])
        self.assertEqual(overrides["promptBorder"], hero.colors["accent"])
        self.assertEqual(overrides["selectionBg"], hero.colors["selection"])
        self.assertNotEqual(overrides["diffAdded"], hero.colors["green"])
        self.assertNotEqual(overrides["diffRemoved"], hero.colors["red"])
        self.assertIn("blue_FOR_SUBAGENTS_ONLY", overrides)
        self.assertIn("rainbow_violet_shimmer", overrides)
        self.assertEqual(set(overrides), CLAUDE_COLOR_TOKENS)

    def test_apply_preserves_settings_and_uses_stable_slug(self):
        tokyo = next(theme for theme in self.config.themes if theme.id == "tokyo-night")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = root / "settings.json"
            theme_dir = root / "themes"
            active_theme = theme_dir / "terminal-theme-suite.json"
            settings.write_text(
                json.dumps({"editorMode": "vim", "theme": "dark"}),
                encoding="utf-8",
            )
            with (
                patch.object(claude_code, "CLAUDE_SETTINGS", settings),
                patch.object(claude_code, "CLAUDE_THEME_DIR", theme_dir),
                patch.object(claude_code, "CLAUDE_ACTIVE_THEME", active_theme),
                patch.object(claude_code.shutil, "which", return_value="/bin/claude"),
            ):
                message, warning = claude_code.apply_theme(tokyo)

            saved_settings = json.loads(settings.read_text(encoding="utf-8"))
            saved_theme = json.loads(active_theme.read_text(encoding="utf-8"))

        self.assertEqual(saved_settings["editorMode"], "vim")
        self.assertEqual(saved_settings["theme"], "custom:terminal-theme-suite")
        self.assertEqual(saved_theme["name"], "Terminal Theme Suite - Tokyo Night")
        self.assertEqual(message, "Claude Code -> Tokyo Night")
        self.assertIn("restart any running Claude Code session once", warning)

    def test_apply_hot_reloads_after_initial_activation(self):
        dracula = next(theme for theme in self.config.themes if theme.id == "dracula")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            theme_dir = root / "themes"
            theme_dir.mkdir()
            settings = root / "settings.json"
            active_theme = theme_dir / "terminal-theme-suite.json"
            settings.write_text(
                json.dumps({"theme": "custom:terminal-theme-suite"}),
                encoding="utf-8",
            )
            with (
                patch.object(claude_code, "CLAUDE_SETTINGS", settings),
                patch.object(claude_code, "CLAUDE_THEME_DIR", theme_dir),
                patch.object(claude_code, "CLAUDE_ACTIVE_THEME", active_theme),
                patch.object(claude_code.shutil, "which", return_value="/bin/claude"),
            ):
                _message, warning = claude_code.apply_theme(dracula)

        self.assertIsNone(warning)

    def test_invalid_settings_are_not_overwritten(self):
        theme = self.config.themes[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = root / "settings.json"
            theme_dir = root / "themes"
            active_theme = theme_dir / "terminal-theme-suite.json"
            settings.write_text("{broken", encoding="utf-8")
            with (
                patch.object(claude_code, "CLAUDE_SETTINGS", settings),
                patch.object(claude_code, "CLAUDE_THEME_DIR", theme_dir),
                patch.object(claude_code, "CLAUDE_ACTIVE_THEME", active_theme),
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
                    claude_code.apply_theme(theme)

            self.assertEqual(settings.read_text(encoding="utf-8"), "{broken")
            self.assertFalse(active_theme.exists())


if __name__ == "__main__":
    unittest.main()
