import os
import tempfile
import unittest

from core.settings import AppSettings, BackendConfig, load_settings, save_settings


class SettingsTest(unittest.TestCase):
    def test_defaults(self):
        settings = AppSettings()
        self.assertEqual(settings.backend.kind, "fcc")
        self.assertIn("glm-5.3-flash", settings.backend.model)

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            original = AppSettings(
                backend=BackendConfig(
                    kind="custom",
                    name="My API",
                    base_url="https://api.example.com/v1",
                    model="my-model",
                    api_key="secret",
                )
            )
            save_settings(original, path)
            loaded = load_settings(path)
            self.assertEqual(loaded.backend.kind, "custom")
            self.assertEqual(loaded.backend.base_url, "https://api.example.com/v1")
            self.assertEqual(loaded.backend.model, "my-model")
            self.assertEqual(loaded.backend.api_key, "secret")

    def test_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded = load_settings(os.path.join(directory, "nope.json"))
            self.assertEqual(loaded.backend.kind, "fcc")


if __name__ == "__main__":
    unittest.main()
