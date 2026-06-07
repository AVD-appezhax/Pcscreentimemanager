import json
import tempfile
import unittest
from pathlib import Path

import studylock


class StudyLockTests(unittest.TestCase):
    def test_default_sites_exclude_youtube_and_include_expanded_pack(self) -> None:
        self.assertNotIn("youtube.com", studylock.DEFAULT_BLOCKED_SITES)
        self.assertNotIn("youtu.be", studylock.DEFAULT_BLOCKED_SITES)
        for site in [
            "tiktok.com",
            "instagram.com",
            "crazygames.com",
            "peacocktv.com",
            "aliexpress.com",
            "tinder.com",
        ]:
            self.assertIn(site, studylock.DEFAULT_BLOCKED_SITES)

    def test_config_migration_adds_site_pack_and_strips_youtube(self) -> None:
        original_config_path = studylock.CONFIG_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            studylock.CONFIG_PATH = Path(temp_dir) / "studylock_config.json"
            studylock.CONFIG_PATH.write_text(
                json.dumps(
                    {
                        "duration_minutes": 45,
                        "max_break_minutes": 10,
                        "blocked_apps": ["discord.exe"],
                        "blocked_sites": ["youtube.com", "example.com"],
                        "site_pack_version": 1,
                    }
                ),
                encoding="utf-8",
            )

            try:
                config = studylock.StudyConfig.load()
                self.assertEqual(config.duration_minutes, 45)
                self.assertIn("example.com", config.blocked_sites)
                self.assertIn("tiktok.com", config.blocked_sites)
                self.assertNotIn("youtube.com", config.blocked_sites)
                self.assertEqual(config.site_pack_version, studylock.SITE_PACK_VERSION)

                config.save()
                saved = json.loads(studylock.CONFIG_PATH.read_text(encoding="utf-8"))
                self.assertEqual(saved["site_pack_version"], studylock.SITE_PACK_VERSION)
                self.assertNotIn("youtube.com", saved["blocked_sites"])
            finally:
                studylock.CONFIG_PATH = original_config_path

    def test_wallpaper_exes_are_ignored_but_games_are_kept(self) -> None:
        matches: set[str] = set()
        studylock.add_exe_candidate(matches, "wallpaper64.exe")
        studylock.add_exe_candidate(matches, "minecraft.exe")
        self.assertNotIn("wallpaper64.exe", matches)
        self.assertIn("minecraft.exe", matches)

    def test_break_activation_delay_is_30_seconds(self) -> None:
        self.assertEqual(studylock.BREAK_ACTIVATION_DELAY_SECONDS, 30)

    def test_quoted_value_unescapes_steam_paths(self) -> None:
        text = '"path" "D:\\\\SteamLibrary"'
        self.assertEqual(studylock.quoted_value(text, "path"), r"D:\SteamLibrary")


if __name__ == "__main__":
    unittest.main()
