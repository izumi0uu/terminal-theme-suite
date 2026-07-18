import plistlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from terminal_theme_suite.adapters import iterm2
from terminal_theme_suite.config import load_config


class ItermProfileTests(unittest.TestCase):
    def test_sync_profiles_generates_shortcuts_and_active_default(self):
        config = load_config()
        config.base_profile_guid = "BASE-GUID"
        config.command_path = "/Users/test/.local/bin/term-theme"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "profiles.plist"
            with patch.object(iterm2, "ITERM_PROFILE_FILE", output):
                iterm2.sync_profiles(config, "hero-amber")
            with output.open("rb") as handle:
                document = plistlib.load(handle)

        profiles = document["Profiles"]
        hero = next(
            profile for profile in profiles if profile["Name"] == "TTS - Hero Amber"
        )
        self.assertEqual(hero["Dynamic Profile Parent GUID"], "BASE-GUID")
        self.assertEqual(hero["Foreground Color"]["Red Component"], 0x12 / 255)
        self.assertEqual(hero["Keyboard Map"][iterm2.NEXT_SHORTCUT]["Action"], 35)
        self.assertIn(
            "next --quiet", hero["Keyboard Map"][iterm2.NEXT_SHORTCUT]["Text"]
        )
        self.assertNotIn(iterm2.NEW_TAB_SHORTCUT, hero["Keyboard Map"])
        self.assertNotIn(iterm2.NEW_WINDOW_SHORTCUT, hero["Keyboard Map"])
        self.assertTrue(
            hero["Background Image Location"].endswith(
                "presets/hero-amber/wallpaper.png"
            )
        )
        self.assertEqual(hero["Background Image Mode"], 2)
        self.assertTrue(
            all(profile["Name"].startswith("TTS - ") for profile in profiles)
        )

    def test_profile_without_wallpaper_explicitly_clears_parent_image(self):
        config = load_config()
        config.base_profile_guid = "BASE-GUID"
        theme = replace(
            next(theme for theme in config.themes if theme.id == "dracula"),
            background=None,
        )
        profile = iterm2._profile(theme, config, None)
        self.assertEqual(profile["Background Image Location"], "")

    def test_shortcuts_merge_with_base_profile_keymap(self):
        config = load_config()
        config.base_profile_guid = "BASE-GUID"
        preferences = {
            "New Bookmarks": [
                {
                    "Guid": "BASE-GUID",
                    "Keyboard Map": {
                        "0x61-0x100000": {"Action": 12, "Text": "existing"}
                    },
                }
            ]
        }
        with patch.object(iterm2, "_load_preferences", return_value=preferences):
            mappings = iterm2._keyboard_map(config, "BASE-GUID")
        self.assertIn("0x61-0x100000", mappings)
        self.assertIn(iterm2.NEXT_SHORTCUT, mappings)

    def test_shortcuts_run_cli_without_writing_to_terminal(self):
        config = load_config()
        config.command_path = "/Users/test/.local/bin/term-theme"
        mappings = iterm2._keyboard_map(config, None)
        command = mappings[iterm2.NEXT_SHORTCUT]["Text"]
        self.assertEqual(command, "/Users/test/.local/bin/term-theme next --quiet")
        self.assertEqual(
            mappings[iterm2.NEXT_SHORTCUT]["Action"], iterm2.RUN_COPROCESS_ACTION
        )

    def test_source_profile_uses_top_level_default_guid(self):
        preferences = {
            "Default Bookmark Guid": "TTS-GUID",
            "New Bookmarks": [
                {"Name": "Default", "Guid": "BASE-GUID"},
                {
                    "Name": "TTS - Hero Amber",
                    "Guid": "TTS-GUID",
                    "Dynamic Profile Parent GUID": "BASE-GUID",
                    "Normal Font": "MesloLGSNF-Regular 14",
                },
            ],
        }
        with patch.object(iterm2, "_load_preferences", return_value=preferences):
            source = iterm2._source_profile()
            base_guid = iterm2.discover_base_profile_guid()
        self.assertEqual(source["Guid"], "TTS-GUID")
        self.assertEqual(base_guid, "BASE-GUID")

    def test_profile_carries_non_theme_source_overrides(self):
        config = load_config()
        preferences = {
            "New Bookmarks": [
                {
                    "Name": "Existing Theme",
                    "Guid": "SOURCE-GUID",
                    "Dynamic Profile Parent GUID": "BASE-GUID",
                    "Default Bookmark": "Yes",
                    "Normal Font": "MesloLGSNF-Regular 14",
                    "Unlimited Scrollback": True,
                    "Background Color": {"Red Component": 1},
                }
            ]
        }
        theme = next(theme for theme in config.themes if theme.id == "tokyo-night")
        with patch.object(iterm2, "_load_preferences", return_value=preferences):
            profile = iterm2._profile(theme, config, theme.id)
        self.assertEqual(profile["Normal Font"], "MesloLGSNF-Regular 14")
        self.assertTrue(profile["Unlimited Scrollback"])
        self.assertEqual(profile["Dynamic Profile Parent GUID"], "BASE-GUID")
        self.assertNotEqual(
            profile["Background Color"],
            preferences["New Bookmarks"][0]["Background Color"],
        )

    def test_running_iterm_switches_through_daemon(self):
        with (
            patch.object(iterm2.sys, "platform", "darwin"),
            patch.object(iterm2, "_iterm_is_running", return_value=True),
            patch.object(iterm2, "_invoke_daemon") as invoke_daemon,
            patch.object(iterm2, "_set_persistent_default") as set_default,
        ):
            message = iterm2.apply_profile("TTS - Test", "TEST-GUID")
        invoke_daemon.assert_called_once_with("TEST-GUID", "all")
        set_default.assert_called_once_with("TEST-GUID")
        self.assertIn("TTS - Test", message)


if __name__ == "__main__":
    unittest.main()
