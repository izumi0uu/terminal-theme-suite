from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from terminal_theme_suite import service
from terminal_theme_suite.config import load_config


class ServiceTests(unittest.TestCase):
    def test_adjacent_theme_wraps(self):
        config = load_config()
        with tempfile.TemporaryDirectory() as temporary:
            missing_state = Path(temporary) / "state.json"
            with patch.object(service, "STATE_FILE", missing_state):
                first = service.current_theme_id(config)
                previous = service.adjacent_theme(-1, config)
        self.assertEqual(first, "hero-amber")
        self.assertEqual(previous.id, config.themes[-1].id)

    def test_apply_reuses_existing_dynamic_profiles(self):
        config = load_config()
        with tempfile.TemporaryDirectory() as temporary:
            profile_file = Path(temporary) / "profiles.plist"
            profile_file.touch()
            with (
                patch.object(service, "load_config", return_value=config),
                patch.object(service, "ITERM_PROFILE_FILE", profile_file),
                patch.object(
                    service, "SWITCH_LOCK", Path(temporary) / "switch.lock"
                ),
                patch.object(service, "_backup_once", return_value=[]),
                patch.object(service.iterm2, "sync_profiles") as sync_profiles,
                patch.object(
                    service.iterm2,
                    "apply_profile",
                    return_value="iTerm2 switched",
                ),
                patch.object(
                    service.omp,
                    "apply_theme",
                    return_value=("OMP switched", None),
                ),
                patch.object(
                    service.herdr,
                    "apply_theme",
                    return_value=("Herdr switched", None),
                ),
                patch.object(service, "atomic_write_json"),
            ):
                result = service.apply("hero-amber")
        sync_profiles.assert_not_called()
        self.assertEqual(result.theme.id, "hero-amber")

    def test_apply_runs_integrations_in_parallel(self):
        config = load_config()
        barrier = threading.Barrier(3, timeout=2)

        def iterm_apply(*_args):
            barrier.wait()
            return "iTerm2 switched"

        def omp_apply(_theme):
            barrier.wait()
            return "OMP switched", None

        def herdr_apply(_theme):
            barrier.wait()
            return "Herdr switched", None

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile_file = root / "profiles.plist"
            profile_file.touch()
            with (
                patch.object(service, "load_config", return_value=config),
                patch.object(service, "ITERM_PROFILE_FILE", profile_file),
                patch.object(service, "SWITCH_LOCK", root / "switch.lock"),
                patch.object(service, "_backup_once", return_value=[]),
                patch.object(service.iterm2, "apply_profile", side_effect=iterm_apply),
                patch.object(service.omp, "apply_theme", side_effect=omp_apply),
                patch.object(service.herdr, "apply_theme", side_effect=herdr_apply),
                patch.object(service, "atomic_write_json"),
            ):
                result = service.apply("hero-amber")

        self.assertIn("integrations", result.timings)
        self.assertIn("iterm2", result.timings)
        self.assertIn("omp", result.timings)
        self.assertIn("herdr", result.timings)
        self.assertIn("total", result.timings)
        self.assertEqual(
            result.messages,
            [
                "Profiles -> " + str(profile_file),
                "iTerm2 switched",
                "OMP switched",
                "Herdr switched",
            ],
        )

    def test_apply_does_not_write_state_when_an_integration_fails(self):
        config = load_config()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile_file = root / "profiles.plist"
            profile_file.touch()
            with (
                patch.object(service, "load_config", return_value=config),
                patch.object(service, "ITERM_PROFILE_FILE", profile_file),
                patch.object(service, "SWITCH_LOCK", root / "switch.lock"),
                patch.object(service, "_backup_once", return_value=[]),
                patch.object(
                    service.iterm2, "apply_profile", return_value="iTerm2 switched"
                ),
                patch.object(
                    service.omp,
                    "apply_theme",
                    side_effect=RuntimeError("theme write failed"),
                ),
                patch.object(
                    service.herdr,
                    "apply_theme",
                    return_value=("Herdr switched", None),
                ),
                patch.object(service, "atomic_write_json") as write_state,
            ):
                with self.assertRaisesRegex(RuntimeError, "state was not updated"):
                    service.apply("hero-amber")

        write_state.assert_not_called()

    def test_concurrent_next_commands_advance_twice(self):
        config = load_config()
        start = threading.Barrier(2, timeout=2)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile_file = root / "profiles.plist"
            profile_file.touch()

            def switch_next():
                start.wait()
                return service.apply_adjacent(1).theme.id

            with (
                patch.object(service, "load_config", return_value=config),
                patch.object(service, "STATE_FILE", root / "state.json"),
                patch.object(service, "ITERM_PROFILE_FILE", profile_file),
                patch.object(service, "SWITCH_LOCK", root / "switch.lock"),
                patch.object(service, "_backup_once", return_value=[]),
                patch.object(
                    service.iterm2, "apply_profile", return_value="iTerm2 switched"
                ),
                patch.object(
                    service.omp,
                    "apply_theme",
                    return_value=("OMP switched", None),
                ),
                patch.object(
                    service.herdr,
                    "apply_theme",
                    return_value=("Herdr switched", None),
                ),
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    themes = list(executor.map(lambda _index: switch_next(), range(2)))

        self.assertEqual(set(themes), {"catppuccin", "tokyo-night"})


if __name__ == "__main__":
    unittest.main()
