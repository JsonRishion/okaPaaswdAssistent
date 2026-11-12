import unittest

from core.rules import PasswordRules, from_attributes, infer_from_field, parse_hints


class RulesTest(unittest.TestCase):
    def test_length_range(self):
        out = parse_hints("密码长度 8-20 位")
        self.assertEqual(out.get("min_length"), 8)
        self.assertEqual(out.get("max_length"), 20)

    def test_english_hints(self):
        out = parse_hints("At least 10 characters, must contain uppercase and a digit")
        self.assertEqual(out.get("min_length"), 10)
        self.assertTrue(out.get("require_upper"))
        self.assertTrue(out.get("require_digit"))

    def test_attribute_pattern(self):
        out = from_attributes(
            {"minlength": "12", "maxlength": "24", "pattern": "^[A-Za-z0-9]+$"}
        )
        self.assertEqual(out.get("min_length"), 12)
        self.assertEqual(out.get("max_length"), 24)
        self.assertEqual(out.get("regex"), "^[A-Za-z0-9]+$")

    def test_infer_prefers_attributes(self):
        rules = infer_from_field({"attrs": {"minlength": "14"}, "text": "至少 6 位"})
        self.assertEqual(rules.min_length, 14)

    def test_from_dict_ignores_unknown(self):
        rules = PasswordRules.from_dict({"min_length": 9, "bogus": 1})
        self.assertEqual(rules.min_length, 9)


if __name__ == "__main__":
    unittest.main()
