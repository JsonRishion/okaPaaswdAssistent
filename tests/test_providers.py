import unittest

from core.providers import detect_assistants, detect_backends


class ProvidersTest(unittest.TestCase):
    def test_detect_backends_returns_list(self):
        result = detect_backends(timeout=1)
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("kind", item)
            self.assertIn("base_url", item)

    def test_detect_assistants_returns_list(self):
        result = detect_assistants()
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("name", item)
            self.assertIn("path", item)


if __name__ == "__main__":
    unittest.main()
