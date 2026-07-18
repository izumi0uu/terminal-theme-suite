import hashlib
import json
from importlib import resources
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terminal_theme_suite import config


class ConfigTests(unittest.TestCase):
    EXPECTED_WALLPAPERS = {
        "hero-amber": "cf063dbb469cf21307cd084f179062e10613d96ad7f74f64ab71d82cf243a73f",
        "catppuccin": "8cd8b7695ebb8b593e940ee499ee2344e8f50f25ba71dc9d6e6d30b36b593030",
        "tokyo-night": "7b960551280751a0fed60414bf4c88f38228b2ec2c930184ccd2f63cd4a0ec10",
        "dracula": "f537b5267b186e29fbbe173f3c0877dd3f1523023ed7a1f3b7b0ca5748799934",
    }

    def test_builtin_order_starts_with_hero_amber(self):
        self.assertEqual(list(config.builtin_theme_documents())[0], "hero-amber")

    def test_presets_are_self_contained_and_use_curated_local_wallpapers(self):
        documents = config.builtin_theme_documents()
        self.assertEqual(set(documents), set(self.EXPECTED_WALLPAPERS))
        for preset_id, expected_hash in self.EXPECTED_WALLPAPERS.items():
            document = documents[preset_id]
            directory = Path(document["_preset_directory"])
            wallpaper = directory / document["wallpaper"]["file"]
            data = wallpaper.read_bytes()
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual(directory.name, preset_id)
            self.assertEqual(document["schema_version"], 1)
            self.assertEqual((width, height), (1586, 992))
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)

    def test_preset_schema_is_bundled(self):
        schema = resources.files("terminal_theme_suite").joinpath(
            "data", "schemas", "preset.schema.json"
        )
        document = json.loads(schema.read_text(encoding="utf-8"))
        self.assertEqual(document["properties"]["schema_version"]["const"], 1)
        self.assertEqual(document["properties"]["ansi"]["minItems"], 16)

    def test_preset_validation_rejects_incomplete_ansi_palette(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = {
            key: value for key, value in source.items() if not key.startswith("_")
        }
        document["ansi"] = document["ansi"][:-1]
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "exactly 16 colors"):
            config._validate_preset_document(document, directory)

    def test_preset_validation_rejects_wallpaper_path_traversal(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = {
            key: value for key, value in source.items() if not key.startswith("_")
        }
        document["wallpaper"] = dict(document["wallpaper"])
        document["wallpaper"]["file"] = "../wallpaper.png"
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "local asset filename"):
            config._validate_preset_document(document, directory)

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
        self.assertEqual(hero.extra["background_source"], "custom")

    def test_fresh_config_uses_bundled_backgrounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(len(loaded.themes), 4)
        for theme in loaded.themes:
            self.assertEqual(theme.extra["background_source"], "bundled")
            self.assertIsNotNone(theme.background)
            self.assertTrue(theme.background.is_file())
            self.assertEqual(theme.background.suffix, ".png")
        hero = next(theme for theme in loaded.themes if theme.id == "hero-amber")
        self.assertEqual(hero.blend, 0.8)

    def test_legacy_null_background_uses_bundled_preset(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps({"themes": {"hero-amber": {"background": None}}}),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        hero = next(theme for theme in loaded.themes if theme.id == "hero-amber")
        self.assertEqual(hero.extra["background_source"], "bundled")
        self.assertEqual(hero.background.name, "wallpaper.png")

    def test_false_background_disables_bundled_preset(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps({"themes": {"dracula": {"background": False}}}),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        dracula = next(theme for theme in loaded.themes if theme.id == "dracula")
        self.assertIsNone(dracula.background)
        self.assertEqual(dracula.extra["background_source"], "disabled")

    def test_background_reset_removes_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps(
                    {"themes": {"hero-amber": {"background": "/tmp/custom.png"}}}
                ),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                config.update_theme_background("hero-amber", False)
                disabled = json.loads(config_path.read_text(encoding="utf-8"))
                config.update_theme_background("hero-amber", None)
                reset = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertIs(disabled["themes"]["hero-amber"]["background"], False)
        self.assertNotIn("background", reset["themes"]["hero-amber"])


if __name__ == "__main__":
    unittest.main()
