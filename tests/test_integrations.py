import tempfile
import unittest
from datetime import datetime, timezone
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

    def test_omp_switch_hot_path_does_not_spawn_omp(self):
        theme = next(theme for theme in self.config.themes if theme.id == "hero-amber")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "terminal-theme-suite.json"
            generation = Path(temporary) / "omp-generation.json"
            with (
                patch.object(omp, "OMP_ACTIVE_THEME", target),
                patch.object(omp, "OMP_GENERATION_FILE", generation),
                patch.object(omp, "OMP_RUNTIME_DIR", Path(temporary) / "runtime"),
                patch.object(omp, "_run") as run,
                patch.object(omp, "_running_omp_processes", return_value={}),
            ):
                message, warning = omp.apply_theme(theme)

            self.assertTrue(target.is_file())
            request = json.loads(generation.read_text(encoding="utf-8"))
            self.assertEqual(len(request["generation"]), 36)
            self.assertEqual(len(request["theme_sha256"]), 64)

        run.assert_not_called()
        self.assertEqual(message, "OMP theme file updated")
        self.assertIn("theme will apply on next OMP start", warning)

    def test_omp_runtime_status_requires_loaded_extension_presence(self):
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(omp, "OMP_RUNTIME_DIR", Path(temporary)),
                patch.object(
                    omp, "OMP_GENERATION_FILE", Path(temporary) / "generation"
                ),
                patch.object(
                    omp, "_running_omp_processes", return_value={12345: 1000.0}
                ),
            ):
                ready, detail = omp.runtime_reload_status()

        self.assertFalse(ready)
        self.assertIn("not loaded by OMP PID(s): 12345", detail)

    def test_omp_runtime_status_accepts_matching_presence(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            generation = runtime / "generation.json"
            generation.write_text(
                json.dumps({"generation": "generation-1", "theme_sha256": "abc123"}),
                encoding="utf-8",
            )
            (runtime / "12345.json").write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "theme": "terminal-theme-suite",
                        "process_started_at": "1970-01-01T00:16:40+00:00",
                        "token": "runtime-token",
                        "ready": True,
                        "applied_generation": "generation-1",
                        "applied_theme_sha256": "abc123",
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(omp, "OMP_RUNTIME_DIR", runtime),
                patch.object(omp, "OMP_GENERATION_FILE", generation),
                patch.object(omp, "_pid_running", return_value=True),
                patch.object(
                    omp, "_running_omp_processes", return_value={12345: 1000.0}
                ),
            ):
                ready, detail = omp.runtime_reload_status()

        self.assertTrue(ready)
        self.assertIn("watcher active in OMP PID(s): 12345", detail)
        self.assertIn("generation generation-1 acknowledged", detail)

    def test_omp_runtime_rejects_reused_pid_with_different_start_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            (runtime / "12345.json").write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "theme": "terminal-theme-suite",
                        "process_started_at": "1970-01-01T00:16:40+00:00",
                        "token": "old-process-token",
                        "ready": True,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(omp, "OMP_RUNTIME_DIR", runtime),
                patch.object(omp, "_pid_running", return_value=True),
            ):
                states = omp._runtime_states({12345: 2000.0})

        self.assertEqual(states, {})

    def test_omp_wait_accepts_matching_generation_ack(self):
        generation = {"generation": "generation-1", "theme_sha256": "abc123"}
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            (runtime / "12345.json").write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "theme": "terminal-theme-suite",
                        "process_started_at": "1970-01-01T00:16:40+00:00",
                        "token": "runtime-token",
                        "ready": True,
                        "applied_generation": "generation-1",
                        "applied_theme_sha256": "abc123",
                        "applied_at": datetime.now(timezone.utc).isoformat(),
                        "error": None,
                        "error_generation": None,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(omp, "OMP_RUNTIME_DIR", runtime),
                patch.object(omp, "_pid_running", return_value=True),
                patch.object(
                    omp, "_running_omp_processes", return_value={12345: 1000.0}
                ),
            ):
                ready, detail = omp._wait_for_generation(generation, timeout=0)

        self.assertTrue(ready)
        self.assertIn("generation-1 acknowledged by OMP PID(s): 12345", detail)

    def test_omp_wait_reports_ack_timeout(self):
        generation = {"generation": "generation-2", "theme_sha256": "def456"}
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            (runtime / "12345.json").write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "theme": "terminal-theme-suite",
                        "process_started_at": "1970-01-01T00:16:40+00:00",
                        "token": "runtime-token",
                        "ready": True,
                        "applied_generation": "generation-1",
                        "applied_theme_sha256": "abc123",
                        "error": None,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(omp, "OMP_RUNTIME_DIR", runtime),
                patch.object(omp, "_pid_running", return_value=True),
                patch.object(
                    omp, "_running_omp_processes", return_value={12345: 1000.0}
                ),
            ):
                ready, detail = omp._wait_for_generation(generation, timeout=0)

        self.assertFalse(ready)
        self.assertIn("did not acknowledge generation generation-2", detail)

    def test_omp_wait_reports_extension_error(self):
        generation = {"generation": "generation-3", "theme_sha256": "789abc"}
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)
            (runtime / "12345.json").write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "theme": "terminal-theme-suite",
                        "process_started_at": "1970-01-01T00:16:40+00:00",
                        "token": "runtime-token",
                        "ready": False,
                        "error": "theme schema rejected",
                        "error_generation": "generation-3",
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(omp, "OMP_RUNTIME_DIR", runtime),
                patch.object(omp, "_pid_running", return_value=True),
                patch.object(
                    omp, "_running_omp_processes", return_value={12345: 1000.0}
                ),
            ):
                ready, detail = omp._wait_for_generation(generation, timeout=0)

        self.assertFalse(ready)
        self.assertIn("theme schema rejected", detail)

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
        self.assertIn("ctx.ui.setTheme(THEME_NAME)", source)
        self.assertIn('const THEME_NAME = "terminal-theme-suite"', source)
        self.assertIn('pi.on("session_shutdown"', source)
        self.assertIn("fs.watch(configRoot", source)
        self.assertIn("generationKey === observedGenerationKey", source)
        self.assertIn("randomUUID()", source)
        self.assertIn("applied_generation", source)
        self.assertIn("process.pid", source)
        self.assertNotIn("setInterval", source)

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
        self.assertEqual(
            arguments[:4], ("/usr/local/bin/omp", "config", "set", "extensions")
        )
        self.assertEqual(json.loads(arguments[4]), ["/tmp/existing.ts", str(target)])

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
