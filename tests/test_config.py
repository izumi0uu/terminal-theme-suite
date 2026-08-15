import hashlib
import copy
import json
from importlib import resources
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

from terminal_theme_suite import config


class ConfigTests(unittest.TestCase):
    EXPECTED_WALLPAPERS = {
        "hero-amber": "cf063dbb469cf21307cd084f179062e10613d96ad7f74f64ab71d82cf243a73f",
        "catppuccin": "8cd8b7695ebb8b593e940ee499ee2344e8f50f25ba71dc9d6e6d30b36b593030",
        "tokyo-night": "7b960551280751a0fed60414bf4c88f38228b2ec2c930184ccd2f63cd4a0ec10",
        "dracula": "f537b5267b186e29fbbe173f3c0877dd3f1523023ed7a1f3b7b0ca5748799934",
    }
    EXPECTED_WALLPAPER_PRESETS = {
        "android18-neon",
        "android18-redline",
        "apex-cloudline",
        "blonde-charcoal",
        "blonde-peek-gold",
        "bluehair-night-city",
        "capsule-city",
        "dragon-ball-lineart",
        "duckegg-fashion",
        "fern-lilac",
        "graffiti-bubble",
        "hazel-tangerine",
        "lavender-elf-dawn",
        "lucy-night-balcony",
        "maid-raspberry",
        "orbital-heroine",
        "pink-braids-noir",
        "rooftop-blue-hour",
        "rooftop-golden-hour",
        "ruri-dragon",
        "sailor-saturn-lavender",
        "sailor-saturn-violet",
        "saturn-girl-purple",
        "showa-street",
        "summer-cloud",
        "toga-signal-yellow",
        "trunks-solar-yellow",
        "vinyl-bed-chill",
        "wake-up-editorial",
        "warrior-sky-cliff",
        "whitecap-blue",
        "whitehair-redline",
        "yellow-circuit",
    }

    def test_builtin_order_starts_with_hero_amber(self):
        self.assertEqual(list(config.builtin_theme_documents())[0], "hero-amber")

    def test_presets_are_self_contained_and_use_curated_local_wallpapers(self):
        documents = config.builtin_theme_documents()
        self.assertEqual(
            set(documents),
            set(self.EXPECTED_WALLPAPERS) | self.EXPECTED_WALLPAPER_PRESETS,
        )
        for preset_id, document in documents.items():
            directory = Path(document["_preset_directory"])
            wallpaper = directory / document["wallpaper"]["file"]
            data = wallpaper.read_bytes()
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual(directory.name, preset_id)
            self.assertEqual(document["schema_version"], 1)
            self.assertIn("claude", document["targets"])
            self.assertIn("codex", document["targets"])
            self.assertIn("hermes", document["targets"])
            self.assertEqual(document["wallpaper"]["file"], "wallpaper.png")
            if preset_id in self.EXPECTED_WALLPAPERS:
                self.assertEqual((width, height), (1586, 992))
                self.assertEqual(
                    hashlib.sha256(data).hexdigest(),
                    self.EXPECTED_WALLPAPERS[preset_id],
                )
            else:
                self.assertEqual((width, height), (2880, 1800))

    @staticmethod
    def _luminance(value):
        raw = value.removeprefix("#")
        channels = []
        for index in (0, 2, 4):
            channel = int(raw[index : index + 2], 16) / 255
            channels.append(
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
            )
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    @classmethod
    def _contrast(cls, left, right):
        low, high = sorted((cls._luminance(left), cls._luminance(right)))
        return (high + 0.05) / (low + 0.05)

    def test_wallpaper_presets_meet_flat_contrast_contract(self):
        documents = config.builtin_theme_documents()
        text_roles = {
            "foreground",
            "muted",
            "dim",
            "accent",
            "accent_alt",
            "red",
            "green",
            "yellow",
            "blue",
            "cyan",
            "teal",
            "orange",
            "pink",
        }
        for preset_id in self.EXPECTED_WALLPAPER_PRESETS:
            document = documents[preset_id]
            colors = document["colors"]
            surfaces = [
                colors["background"],
                colors["background_alt"],
                colors["surface"],
                colors["surface_alt"],
            ]
            for role in text_roles:
                for surface in surfaces:
                    self.assertGreaterEqual(
                        self._contrast(colors[role], surface),
                        4.5,
                        f"{preset_id}: {role} on {surface}",
                    )
            self.assertGreaterEqual(
                self._contrast(colors["foreground"], colors["selection"]),
                4.5,
                f"{preset_id}: selected text",
            )
            for index, ansi in enumerate(document["ansi"]):
                self.assertGreaterEqual(
                    self._contrast(ansi, colors["background"]),
                    4.5,
                    f"{preset_id}: ANSI {index}",
                )

    def test_preset_schema_is_bundled(self):
        schema = resources.files("terminal_theme_suite").joinpath(
            "data", "schemas", "preset.schema.json"
        )
        document = json.loads(schema.read_text(encoding="utf-8"))
        self.assertEqual(document["properties"]["schema_version"]["const"], 1)
        self.assertEqual(document["properties"]["ansi"]["minItems"], 16)
        self.assertIn("claude", document["properties"]["targets"]["properties"])
        self.assertIn("codex", document["properties"]["targets"]["properties"])
        self.assertIn("hermes", document["properties"]["targets"]["properties"])
        self.assertNotIn("iterm2", document["properties"]["targets"]["properties"])
        hermes_roles = document["properties"]["targets"]["properties"]["hermes"][
            "properties"
        ]["overrides"]["propertyNames"]["enum"]
        self.assertEqual(set(hermes_roles), config.HERMES_COLOR_ROLES)
        codex_style_roles = document["properties"]["targets"]["properties"]["codex"][
            "properties"
        ]["styles"]["propertyNames"]["enum"]
        self.assertEqual(set(codex_style_roles), config.CODEX_STYLE_ROLES)

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

    def test_preset_validation_rejects_unsupported_iterm2_target(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = copy.deepcopy(
            {key: value for key, value in source.items() if not key.startswith("_")}
        )
        document["targets"]["iterm2"] = {"Blend": 0.5}
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "unsupported integrations"):
            config._validate_preset_document(document, directory)

    def test_zip_resource_wallpaper_is_materialized_to_stable_cache(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = {
            key: value for key, value in source.items() if not key.startswith("_")
        }
        wallpaper = Path(source["_preset_directory"]) / document["wallpaper"]["file"]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "presets.zip"
            cache_dir = root / "backgrounds"
            config_path = root / "config.json"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "terminal_theme_suite/data/presets/hero-amber/preset.json",
                    json.dumps(document),
                )
                archive.writestr(
                    "terminal_theme_suite/data/presets/hero-amber/wallpaper.png",
                    wallpaper.read_bytes(),
                )

            with zipfile.ZipFile(archive_path) as archive:
                resource_root = zipfile.Path(archive, at="terminal_theme_suite/")
                with (
                    patch.object(config.resources, "files", return_value=resource_root),
                    patch.object(config, "BACKGROUND_DIR", cache_dir),
                    patch.object(config, "CONFIG_FILE", config_path),
                    patch.object(config, "ensure_user_dirs", lambda: None),
                ):
                    config.builtin_theme_documents.cache_clear()
                    loaded = config.load_config()
                    config.builtin_theme_documents.cache_clear()

            self.assertEqual(len(loaded.themes), 1)
            background = loaded.themes[0].background
            self.assertEqual(
                background,
                (cache_dir / "bundled" / "hero-amber" / "wallpaper.png").resolve(),
            )
            self.assertEqual(background.read_bytes(), wallpaper.read_bytes())

    def test_package_data_includes_all_preset_text_assets(self):
        project = Path(__file__).resolve().parents[1]
        pyproject = (project / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"data/presets/*/*.txt"', pyproject)

    def test_preset_validation_rejects_unknown_claude_token(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = copy.deepcopy(
            {key: value for key, value in source.items() if not key.startswith("_")}
        )
        document["targets"]["claude"]["overrides"]["typoColor"] = "#ffffff"
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "unsupported token"):
            config._validate_preset_document(document, directory)

    def test_preset_validation_rejects_unknown_codex_role(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = copy.deepcopy(
            {key: value for key, value in source.items() if not key.startswith("_")}
        )
        document["targets"]["codex"]["overrides"]["typo_role"] = "#ffffff"
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "unsupported role"):
            config._validate_preset_document(document, directory)

    def test_preset_validation_rejects_unknown_codex_style_role(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = copy.deepcopy(
            {key: value for key, value in source.items() if not key.startswith("_")}
        )
        document["targets"]["codex"]["styles"]["typo_role"] = ["bold"]
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "unsupported role"):
            config._validate_preset_document(document, directory)

    def test_preset_validation_rejects_invalid_codex_font_style(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = copy.deepcopy(
            {key: value for key, value in source.items() if not key.startswith("_")}
        )
        document["targets"]["codex"]["styles"]["comment"] = ["blink"]
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "bold, italic, or underline"):
            config._validate_preset_document(document, directory)

    def test_preset_validation_rejects_unknown_hermes_role(self):
        source = config.builtin_theme_documents()["hero-amber"]
        document = copy.deepcopy(
            {key: value for key, value in source.items() if not key.startswith("_")}
        )
        document["targets"]["hermes"]["overrides"]["typo_role"] = "#ffffff"
        directory = Path(source["_preset_directory"])
        with self.assertRaisesRegex(ValueError, "unsupported role"):
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

    def test_terminal_typography_defaults_to_inherit(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(json.dumps({"themes": {}}), encoding="utf-8")
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(loaded.terminal_typography.mode, "inherit")
        self.assertIsNone(loaded.terminal_typography.font_family)

    def test_managed_terminal_typography_is_validated_and_loaded(self):
        typography = {
            "mode": "managed",
            "font_family": "MesloLGSNF-Regular",
            "non_ascii_font_family": "MesloLGSNF-Regular",
            "font_size": 14,
            "horizontal_spacing": 1,
            "vertical_spacing": 1.05,
            "ligatures": True,
            "use_bold_font": True,
            "use_italic_font": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps({"terminal_typography": typography, "themes": {}}),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(loaded.terminal_typography.mode, "managed")
        self.assertEqual(loaded.terminal_typography.font_family, "MesloLGSNF-Regular")
        self.assertEqual(loaded.terminal_typography.font_size, 14)
        self.assertEqual(loaded.terminal_typography.vertical_spacing, 1.05)
        self.assertTrue(loaded.terminal_typography.ligatures)

    def test_managed_terminal_typography_requires_font_and_size(self):
        with self.assertRaisesRegex(ValueError, "requires font_family and font_size"):
            config._terminal_typography({"mode": "managed"})

    def test_omp_symbol_preset_defaults_to_nerd(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(json.dumps({"themes": {}}), encoding="utf-8")
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(loaded.omp_symbol_preset, "nerd")

    def test_omp_symbol_preset_is_loaded_from_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(
                json.dumps({"omp_symbol_preset": "emoji", "themes": {}}),
                encoding="utf-8",
            )
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(loaded.omp_symbol_preset, "emoji")

    def test_omp_symbol_preset_rejects_blank_and_non_string(self):
        with self.assertRaisesRegex(ValueError, "omp_symbol_preset"):
            config._omp_symbol_preset("")
        with self.assertRaisesRegex(ValueError, "omp_symbol_preset"):
            config._omp_symbol_preset(7)

    def test_fresh_config_uses_bundled_backgrounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "config.json"
            with (
                patch.object(config, "CONFIG_FILE", config_path),
                patch.object(config, "ensure_user_dirs", lambda: None),
            ):
                loaded = config.load_config()

        self.assertEqual(len(loaded.themes), 37)
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
