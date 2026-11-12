import os
import tempfile
import unittest

from core.rules import PasswordRules
from core.store import domain_from_url, safe_name, save_password


class StoreTest(unittest.TestCase):
    def test_domain(self):
        self.assertEqual(
            domain_from_url("https://www.example.com/register"), "www.example.com"
        )
        self.assertEqual(domain_from_url("http://a.b:8443/x"), "a.b")

    def test_safe_name(self):
        self.assertEqual(safe_name("a/b:c*?.com"), "a_b_c__.com")

    def test_save_writes_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = save_password(
                "https://example.com/signup",
                "Abc123!@#xyz",
                PasswordRules(min_length=12),
                username="u",
                directory=directory,
            )
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("Abc123!@#xyz", content)
            self.assertIn("example.com", content)
            self.assertTrue(os.path.basename(path).startswith("example.com_"))


if __name__ == "__main__":
    unittest.main()
