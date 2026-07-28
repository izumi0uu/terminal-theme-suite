import copy
from dataclasses import replace
import plistlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tomlkit

from terminal_theme_suite.adapters import codex
from terminal_theme_suite.config import CODEX_COLOR_ROLES, load_config


class CodexAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_theme_is_valid_plist_with_syntax_and_diff_scopes(self):
        hero = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        document = plistlib.loads(codex.serialize_theme(hero))
        scopes = {
            item.get("scope"): item.get("settings", {})
            for item in document["settings"]
            if item.get("scope")
        }

        self.assertEqual(document["name"], "Terminal Theme Suite - Hero Amber")
        self.assertEqual(document["settings"][0]["settings"]["foreground"], "#120f0d")
        self.assertIn("comment, punctuation.definition.comment", scopes)
        self.assertIn("markup.inserted, diff.inserted", scopes)
        self.assertIn("markup.deleted, diff.deleted", scopes)
        self.assertEqual(
            scopes["comment, punctuation.definition.comment"]["fontStyle"], "italic"
        )
        self.assertEqual(
            scopes["keyword, keyword.control, keyword.other"]["fontStyle"], "bold"
        )
        self.assertEqual(
            scopes["markup.underline.link, string.other.link"]["fontStyle"],
            "underline",
        )
        self.assertNotEqual(
            scopes["markup.inserted, diff.inserted"]["background"],
            hero.colors["green"],
        )
        self.assertEqual(set(codex._roles(hero)), CODEX_COLOR_ROLES)

    def test_preset_styles_can_override_or_clear_defaults(self):
        source_theme = next(
            theme for theme in self.config.themes if theme.id == "catppuccin"
        )
        source = copy.deepcopy(source_theme.extra["source"])
        source["targets"]["codex"]["styles"]["comment"] = []
        source["targets"]["codex"]["styles"]["string"] = ["bold", "italic"]
        theme = replace(source_theme, extra={**source_theme.extra, "source": source})
        document = codex.build_theme(theme)
        scopes = {
            item.get("scope"): item.get("settings", {})
            for item in document["settings"]
            if item.get("scope")
        }

        self.assertNotIn("fontStyle", scopes["comment, punctuation.definition.comment"])
        self.assertEqual(
            scopes["string, punctuation.definition.string"]["fontStyle"],
            "bold italic",
        )

    def test_apply_preserves_toml_and_selects_stable_theme(self):
        tokyo = next(theme for theme in self.config.themes if theme.id == "tokyo-night")
        original = """# keep this comment
model = "gpt-test"

[tui.model_availability_nux]
"gpt-test" = 1

[mcp_servers.docs]
url = "https://example.test/mcp"
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.toml"
            active_theme = root / "themes" / "terminal-theme-suite.tmTheme"
            config_path.write_text(original, encoding="utf-8")
            with (
                patch.object(codex, "CODEX_CONFIG", config_path),
                patch.object(codex, "CODEX_ACTIVE_THEME", active_theme),
                patch.object(codex.shutil, "which", return_value="/bin/codex"),
            ):
                message, warning = codex.apply_theme(tokyo)
                ready, detail = codex.configuration_status()

            saved_text = config_path.read_text(encoding="utf-8")
            saved = tomlkit.parse(saved_text)
            theme = plistlib.loads(active_theme.read_bytes())

        self.assertIn("# keep this comment", saved_text)
        self.assertEqual(saved["model"], "gpt-test")
        self.assertEqual(
            saved["mcp_servers"]["docs"]["url"], "https://example.test/mcp"
        )
        self.assertEqual(saved["tui"]["model_availability_nux"]["gpt-test"], 1)
        self.assertEqual(saved["tui"]["theme"], "terminal-theme-suite")
        self.assertEqual(theme["name"], "Terminal Theme Suite - Tokyo Night")
        self.assertEqual(message, "Codex CLI -> Tokyo Night (syntax/diff)")
        self.assertIn("select terminal-theme-suite once with /theme", warning)
        self.assertTrue(ready)
        self.assertIn("terminal-theme-suite.tmTheme", detail)

    def test_existing_selection_still_warns_about_runtime_reload(self):
        dracula = next(theme for theme in self.config.themes if theme.id == "dracula")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.toml"
            active_theme = root / "themes" / "terminal-theme-suite.tmTheme"
            config_path.write_text(
                '[tui]\ntheme = "terminal-theme-suite"\n', encoding="utf-8"
            )
            with (
                patch.object(codex, "CODEX_CONFIG", config_path),
                patch.object(codex, "CODEX_ACTIVE_THEME", active_theme),
                patch.object(codex.shutil, "which", return_value="/bin/codex"),
            ):
                _message, warning = codex.apply_theme(dracula)

        self.assertIn("do not watch .tmTheme files", warning)

    def test_invalid_config_is_not_overwritten(self):
        theme = self.config.themes[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.toml"
            active_theme = root / "themes" / "terminal-theme-suite.tmTheme"
            config_path.write_text("[broken", encoding="utf-8")
            with (
                patch.object(codex, "CODEX_CONFIG", config_path),
                patch.object(codex, "CODEX_ACTIVE_THEME", active_theme),
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid TOML"):
                    codex.apply_theme(theme)

            self.assertEqual(config_path.read_text(encoding="utf-8"), "[broken")
            self.assertFalse(active_theme.exists())

    def test_theme_rolls_back_when_config_write_fails(self):
        theme = self.config.themes[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.toml"
            active_theme = root / "themes" / "terminal-theme-suite.tmTheme"
            active_theme.parent.mkdir()
            active_theme.write_bytes(b"previous-theme")
            config_path.write_text('model = "gpt-test"\n', encoding="utf-8")
            with (
                patch.object(codex, "CODEX_CONFIG", config_path),
                patch.object(codex, "CODEX_ACTIVE_THEME", active_theme),
                patch.object(
                    codex,
                    "atomic_write_text",
                    side_effect=OSError("config is read-only"),
                ),
            ):
                with self.assertRaisesRegex(OSError, "read-only"):
                    codex.apply_theme(theme)

            self.assertEqual(active_theme.read_bytes(), b"previous-theme")
            self.assertEqual(
                config_path.read_text(encoding="utf-8"), 'model = "gpt-test"\n'
            )


if __name__ == "__main__":
    unittest.main()
