import queue
import unittest
import numpy as np
from engine import Segmenter, put_latest


class AudioTests(unittest.TestCase):
    def test_silence_never_becomes_utterance(self):
        segmenter = Segmenter(16000)
        for _ in range(500):
            self.assertIsNone(segmenter.feed(np.zeros(320, dtype=np.float32)))

    def test_utterance_keeps_onset_and_ends_after_silence(self):
        segmenter = Segmenter(16000)
        silence = np.zeros(320, dtype=np.float32)
        voice = np.full(320, 0.05, dtype=np.float32)
        for _ in range(10):
            segmenter.feed(silence)
        for _ in range(25):
            self.assertIsNone(segmenter.feed(voice))
        results = [segmenter.feed(silence) for _ in range(40)]
        utterances = [r for r in results if r is not None]
        self.assertEqual(len(utterances), 1)
        self.assertEqual(np.count_nonzero(utterances[0]), 25 * 320)
        self.assertTrue(np.all(utterances[0][:3200] == 0))

    def test_long_speech_is_bounded(self):
        segmenter = Segmenter(16000, maximum=1)
        outputs = [segmenter.feed(np.full(320, 0.05, dtype=np.float32)) for _ in range(110)]
        self.assertEqual(sum(x is not None for x in outputs), 2)

    def test_backlog_drops_oldest(self):
        pending = queue.Queue(maxsize=2)
        self.assertFalse(put_latest(pending, 'old'))
        put_latest(pending, 'recent')
        self.assertTrue(put_latest(pending, 'new'))
        self.assertEqual([pending.get(), pending.get()], ['recent', 'new'])

    def test_reset_discards_audio_during_playback(self):
        segmenter = Segmenter(16000)
        for _ in range(20):
            segmenter.feed(np.full(320, 0.05, dtype=np.float32))
        segmenter.reset()
        for _ in range(40):
            self.assertIsNone(segmenter.feed(np.zeros(320, dtype=np.float32)))


if __name__ == '__main__':
    unittest.main()
