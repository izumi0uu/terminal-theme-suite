import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from terminal_theme_suite.adapters import hermes
from terminal_theme_suite.config import HERMES_COLOR_ROLES, load_config


class HermesAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_skin_maps_every_supported_color_role(self):
        hero = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        document = yaml.safe_load(hermes.serialize_skin(hero))

        self.assertEqual(document["name"], "terminal-theme-suite")
        self.assertEqual(document["description"], "Terminal Theme Suite - Hero Amber")
        self.assertEqual(document["colors"]["banner_text"], "#120f0d")
        self.assertEqual(document["colors"]["status_bar_bg"], "#e1aa72")
        self.assertEqual(document["colors"]["selection_bg"], "#f1c28f")
        self.assertEqual(set(document["colors"]), HERMES_COLOR_ROLES)

    def test_preset_override_replaces_generated_role(self):
        source_theme = next(
            theme for theme in self.config.themes if theme.id == "catppuccin"
        )
        source = copy.deepcopy(source_theme.extra["source"])
        source["targets"]["hermes"]["overrides"]["ui_accent"] = "#123456"
        theme = replace(source_theme, extra={**source_theme.extra, "source": source})

        self.assertEqual(hermes.build_skin(theme)["colors"]["ui_accent"], "#123456")

    def test_apply_preserves_config_values_and_selects_stable_skin(self):
        tokyo = next(theme for theme in self.config.themes if theme.id == "tokyo-night")
        original = """model:
  provider: test-provider
display:
  interface: tui
toolsets:
  - web
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.yaml"
            active_skin = root / "skins" / "terminal-theme-suite.yaml"
            config_path.write_text(original, encoding="utf-8")
            config_path.chmod(0o600)
            with (
                patch.object(hermes, "HERMES_CONFIG", config_path),
                patch.object(hermes, "HERMES_ACTIVE_SKIN", active_skin),
                patch.object(hermes.shutil, "which", return_value="/bin/hermes"),
            ):
                message, warning = hermes.apply_theme(tokyo)
                ready, detail = hermes.configuration_status()

            saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            skin = yaml.safe_load(active_skin.read_text(encoding="utf-8"))
            config_mode = config_path.stat().st_mode & 0o777

        self.assertEqual(saved["model"]["provider"], "test-provider")
        self.assertEqual(saved["display"]["interface"], "tui")
        self.assertEqual(saved["display"]["skin"], "terminal-theme-suite")
        self.assertEqual(saved["toolsets"], ["web"])
        self.assertEqual(skin["description"], "Terminal Theme Suite - Tokyo Night")
        self.assertEqual(config_mode, 0o600)
        self.assertEqual(message, "Hermes CLI -> Tokyo Night")
        self.assertIn("run /skin terminal-theme-suite", warning)
        self.assertTrue(ready)
        self.assertIn("terminal-theme-suite.yaml", detail)

    def test_existing_selection_warns_about_runtime_reload(self):
        dracula = next(theme for theme in self.config.themes if theme.id == "dracula")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.yaml"
            active_skin = root / "skins" / "terminal-theme-suite.yaml"
            config_path.write_text(
                "display:\n  skin: terminal-theme-suite\n", encoding="utf-8"
            )
            with (
                patch.object(hermes, "HERMES_CONFIG", config_path),
                patch.object(hermes, "HERMES_ACTIVE_SKIN", active_skin),
                patch.object(hermes.shutil, "which", return_value="/bin/hermes"),
            ):
                _message, warning = hermes.apply_theme(dracula)

            saved_config = config_path.read_text(encoding="utf-8")

        self.assertIn("do not watch skin files", warning)
        self.assertEqual(saved_config, "display:\n  skin: terminal-theme-suite\n")

    def test_invalid_config_is_not_overwritten(self):
        theme = self.config.themes[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.yaml"
            active_skin = root / "skins" / "terminal-theme-suite.yaml"
            config_path.write_text("display: [broken", encoding="utf-8")
            with (
                patch.object(hermes, "HERMES_CONFIG", config_path),
                patch.object(hermes, "HERMES_ACTIVE_SKIN", active_skin),
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid YAML"):
                    hermes.apply_theme(theme)

            self.assertEqual(
                config_path.read_text(encoding="utf-8"), "display: [broken"
            )
            self.assertFalse(active_skin.exists())

    def test_skin_rolls_back_when_config_write_fails(self):
        theme = self.config.themes[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "config.yaml"
            active_skin = root / "skins" / "terminal-theme-suite.yaml"
            active_skin.parent.mkdir()
            active_skin.write_bytes(b"previous-skin")
            config_path.write_text("display:\n  interface: cli\n", encoding="utf-8")
            with (
                patch.object(hermes, "HERMES_CONFIG", config_path),
                patch.object(hermes, "HERMES_ACTIVE_SKIN", active_skin),
                patch.object(
                    hermes,
                    "atomic_write_text",
                    side_effect=[None, OSError("config is read-only")],
                ),
            ):
                with self.assertRaisesRegex(OSError, "read-only"):
                    hermes.apply_theme(theme)

            self.assertEqual(active_skin.read_bytes(), b"previous-skin")
            self.assertEqual(
                config_path.read_text(encoding="utf-8"),
                "display:\n  interface: cli\n",
            )


if __name__ == "__main__":
    unittest.main()
