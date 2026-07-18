import tempfile
import unittest
import json
from pathlib import Path
import subprocess
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

    def test_omp_extension_enables_theme_watcher_on_session_start(self):
        source = omp._extension_source()
        self.assertIn('pi.on("session_start"', source)
        self.assertIn('ctx.ui.setTheme(THEME_NAME)', source)
        self.assertIn('const THEME_NAME = "terminal-theme-suite"', source)

    def test_omp_extension_install_preserves_existing_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "omp-live-reload.ts"
            responses = [
                subprocess.CompletedProcess(
                    [], 0, stdout='["/tmp/existing.ts"]\n', stderr=""
                ),
                subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            ]
            with (
                patch.object(omp, "OMP_LIVE_RELOAD_EXTENSION", target),
                patch.object(omp, "_run", side_effect=responses) as run,
            ):
                added = omp.install_live_reload_extension("/usr/local/bin/omp")
            self.assertTrue(target.is_file())

        self.assertTrue(added)
        arguments = run.call_args_list[1].args
        self.assertEqual(arguments[:4], ("/usr/local/bin/omp", "config", "set", "extensions"))
        self.assertEqual(
            json.loads(arguments[4]), ["/tmp/existing.ts", str(target)]
        )

    def test_omp_extension_remove_preserves_other_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "omp-live-reload.ts"
            target.write_text("extension", encoding="utf-8")
            responses = [
                subprocess.CompletedProcess(
                    [],
                    0,
                    stdout=json.dumps([str(target), "/tmp/existing.ts"]),
                    stderr="",
                ),
                subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            ]
            with (
                patch.object(omp, "OMP_LIVE_RELOAD_EXTENSION", target),
                patch.object(omp, "_run", side_effect=responses) as run,
            ):
                removed = omp.remove_live_reload_extension("/usr/local/bin/omp")

            self.assertFalse(target.exists())

        self.assertTrue(removed)
        arguments = run.call_args_list[1].args
        self.assertEqual(json.loads(arguments[4]), ["/tmp/existing.ts"])


if __name__ == "__main__":
    unittest.main()
