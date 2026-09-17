import unittest
from engine import language_decision


class LanguageTests(unittest.TestCase):
    def test_text_language_does_not_require_a_fabricated_probability(self):
        self.assertEqual(language_decision('ko', None, 'auto', 'ja')[0], 'translate')
        self.assertEqual(language_decision(None, None, 'auto', 'ja')[0], 'skip')

    def test_japanese_is_not_translated_as_korean(self):
        self.assertEqual(language_decision('ja', .98, 'auto', 'ja')[0], 'original')

    def test_japanese_to_korean(self):
        self.assertEqual(language_decision('ja', .98, 'auto', 'ko')[0], 'translate')

    def test_korean_to_japanese(self):
        self.assertEqual(language_decision('ko', .98, 'auto', 'ja')[0], 'translate')

    def test_fixed_korean_rejects_japanese(self):
        self.assertEqual(language_decision('ja', .98, 'ko', 'ja')[0], 'skip')

    def test_uncertain_language_is_not_forced(self):
        self.assertEqual(language_decision('ko', .35, 'auto', 'ja')[0], 'skip')

    def test_unsupported_language_is_not_forced(self):
        self.assertEqual(language_decision('de', .98, 'auto', 'ja')[0], 'skip')
