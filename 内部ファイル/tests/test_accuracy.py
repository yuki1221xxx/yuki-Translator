import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
import numpy as np
from accuracy import prepare_audio, recognize, text_language, clean_recognition
from engine import Segmenter


class AccuracyTests(unittest.TestCase):
    def test_model_scaffold_is_not_shown_or_translated(self):
        self.assertEqual(clean_recognition('language Korean<asr_text>지금 어디에 있어요?'), '지금 어디에 있어요?')
        self.assertEqual(clean_recognition('**language Japanese**<asr_text>こんにちは。'), 'こんにちは。')
        self.assertEqual(clean_recognition('language learning is useful'), 'language learning is useful')

    def test_silence_is_not_amplified_into_noise(self):
        self.assertTrue(np.all(prepare_audio(np.zeros(16000)) == 0))

    def test_quiet_gain_is_bounded_and_padding_retains_signal(self):
        audio = np.full(16000, .003, np.float32)
        prepared = prepare_audio(audio)
        self.assertEqual(len(prepared), 24000)
        np.testing.assert_allclose(prepared[3200:19200], audio*4)

    @patch('faster_whisper.vad.get_speech_timestamps', return_value=[{'start': 0, 'end': 16000}])
    def test_recognition_never_forces_language_or_invents_confidence(self, vad):
        model = Mock()
        model.create_stream.return_value.result = SimpleNamespace(text='こんにちは', tokens=['こんにちは'])
        text, info = recognize(model, np.ones(16000)*.02)
        self.assertEqual(text, 'こんにちは')
        self.assertEqual(info.language, 'ja')
        self.assertIsNone(info.language_probability)
        model.create_stream.return_value.set_option.assert_not_called()

    @patch('faster_whisper.vad.get_speech_timestamps', return_value=[])
    def test_no_speech_never_reaches_decoder(self, vad):
        model = Mock()
        self.assertEqual(recognize(model, np.zeros(16000))[0], '')
        model.decode_stream.assert_not_called()

    @patch('faster_whisper.vad.get_speech_timestamps', return_value=[{'start': 0, 'end': 16000}])
    def test_truncated_sentence_is_not_translated(self, vad):
        model = Mock()
        model.create_stream.return_value.result = SimpleNamespace(text='こんにちは', tokens=['x']*128)
        self.assertEqual(recognize(model, np.ones(16000)*.02)[0], '')

    def test_text_language_handles_ambiguity_without_forcing_japanese(self):
        self.assertEqual(text_language('안녕하세요.'), 'ko')
        self.assertEqual(text_language('よろしくお願いします。'), 'ja')
        self.assertIsNone(text_language('提纲'))
        self.assertIsNone(text_language('안녕こんにちは'))
        self.assertIsNone(text_language('12345'))

    def test_idle_flush_keeps_actual_audio_contiguous(self):
        segmenter = Segmenter(16000)
        for _ in range(30):
            segmenter.feed(np.full(320, .04, np.float32))
        utterance = segmenter.finish_idle()
        np.testing.assert_allclose(utterance[:9600], .04)
        self.assertFalse(segmenter.frames)
        self.assertIsNone(segmenter.finish_idle())
