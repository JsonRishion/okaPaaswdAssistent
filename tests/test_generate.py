import re
import unittest

from core.generate import generate_password
from core.rules import PasswordRules


class GenerateTest(unittest.TestCase):
    def test_meets_all_classes(self):
        rules = PasswordRules(
            min_length=16,
            max_length=16,
            require_upper=True,
            require_lower=True,
            require_digit=True,
            require_symbol=True,
        )
        pwd = generate_password(rules)
        self.assertEqual(len(pwd), 16)
        self.assertTrue(any(ch.isupper() for ch in pwd))
        self.assertTrue(any(ch.islower() for ch in pwd))
        self.assertTrue(any(ch.isdigit() for ch in pwd))
        self.assertTrue(any(not ch.isalnum() for ch in pwd))

    def test_length_bounds(self):
        rules = PasswordRules(min_length=8, max_length=10, require_digit=True)
        for _ in range(50):
            pwd = generate_password(rules)
            self.assertTrue(8 <= len(pwd) <= 10)

    def test_forbidden_chars(self):
        rules = PasswordRules(
            min_length=20, max_length=20, require_lower=True, forbidden_chars="abcxyz"
        )
        for _ in range(50):
            pwd = generate_password(rules)
            self.assertFalse(set(pwd) & set("abcxyz"))

    def test_regex_respected(self):
        rules = PasswordRules(
            min_length=12,
            max_length=12,
            require_digit=True,
            regex="^[A-Za-z0-9]+$",
        )
        for _ in range(50):
            pwd = generate_password(rules)
            self.assertIsNotNone(re.match(rules.regex, pwd))

    def test_no_spaces_by_default(self):
        rules = PasswordRules(min_length=30, max_length=30, allow_spaces=False)
        pwd = generate_password(rules)
        self.assertNotIn(" ", pwd)


if __name__ == "__main__":
    unittest.main()
