import queue
import threading
import unittest
from unittest.mock import Mock, patch
import numpy as np

from accuracy import ASR_MODELS, DEFAULT_MODEL, HEAVY_MODEL, recognition_location
from i18n import TEXT, UI_LANGUAGES, message, render
from speech import Speaker, scaled_pcm
from subtitles import placement


class ModelAndLocaleTests(unittest.TestCase):
    def test_model_selection_uses_different_files(self):
        self.assertNotEqual(recognition_location(DEFAULT_MODEL), recognition_location(HEAVY_MODEL))
        self.assertIn('1.7b', str(recognition_location(HEAVY_MODEL)))

    def test_all_locales_cover_the_same_placeholders(self):
        import string
        for key, variants in TEXT.items():
            self.assertEqual(len(variants), len(UI_LANGUAGES), key)
            fields = [{name for _, name, _, _ in string.Formatter().parse(t) if name} for t in variants]
            self.assertEqual(fields[0], fields[1], key)
            self.assertEqual(fields[0], fields[2], key)

    def test_nested_worker_messages_change_language(self):
        msg = message('language_info', reason=message('same_language', language=message('ja')))
        self.assertIn('Japanese', render(msg, 'en'))
        self.assertIn('일본어', render(msg, 'ko'))


class SubtitlePositionTests(unittest.TestCase):
    def test_position_on_negative_coordinate_monitor(self):
        self.assertEqual(placement((-1920, 0, 0, 1080), 900, 100, 'bottom_center')[:2], (-1410, 932))

    def test_custom_position_is_kept_on_selected_monitor(self):
        self.assertEqual(placement((0, 0, 1920, 1080), 900, 100, 'custom', custom=(9999, -9999))[:2], (1020, 0))

    def test_custom_offsets_are_applied(self):
        self.assertEqual(placement((0, 0, 1920, 1080), 900, 100, 'custom', 50, 20, (100, 200))[:2], (150, 220))

    def test_offsets_apply_to_selected_anchor(self):
        self.assertEqual(placement((0, 0, 1920, 1080), 900, 100, 'top_left', 50, 20)[:2], (74, 44))


class SpeechTests(unittest.TestCase):
    def test_volume_zero_and_half_are_applied_to_pcm(self):
        samples = np.array([-.8, .2, .8], np.float32)
        self.assertFalse(np.frombuffer(scaled_pcm(samples, 0), np.float32).any())
        np.testing.assert_allclose(np.frombuffer(scaled_pcm(samples, 50), np.float32), samples * .5)

    def test_cancelled_generation_is_never_played(self):
        speaker = Speaker.__new__(Speaker)
        speaker.generation = 2
        speaker.enabled = True
        speaker.shutdown = threading.Event()
        self.assertTrue(speaker.cancelled(1))
        self.assertFalse(speaker.cancelled(2))
        speaker.enabled = False
        self.assertTrue(speaker.cancelled(2))

    def test_local_korean_uses_local_model_without_windows_voice(self):
        speaker = Speaker.__new__(Speaker)
        speaker.events = queue.Queue()
        speaker.queue = queue.Queue()
        speaker.shutdown = threading.Event()
        speaker.playing = threading.Event()
        speaker.generation, speaker.enabled, speaker.voice = 0, True, None
        speaker.queue.put((0, '안녕하세요', 'ko', {'index': 1, 'name': 'test'}, 'local'))
        def played(*args):
            speaker.shutdown.set()
        speaker.play_audio = Mock(side_effect=played)
        with patch('speech.LocalVoice') as voice:
            voice.return_value.generate.return_value = (np.ones(100, np.float32), 24000)
            speaker.run()
            voice.return_value.generate.assert_called_once_with('안녕하세요', 'ko')
        speaker.play_audio.assert_called_once()


if __name__ == '__main__':
    unittest.main()
