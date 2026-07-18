import tempfile
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


if __name__ == "__main__":
    unittest.main()
