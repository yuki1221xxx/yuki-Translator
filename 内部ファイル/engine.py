"""Audio segmentation, local inference and Windows speech output."""
import math
import os
import queue
import threading
import time
from collections import deque
from pathlib import Path
from process_audio import ProcessCapture, discord_processes
from accuracy import DirectTranslator, load_recognizer, recognize
from speech import Speaker, output_devices
from i18n import message, UserMessageError

import numpy as np

ROOT = Path(__file__).resolve().parent
LANGUAGE_NAMES = {'ja': '日本語', 'ko': '韓国語', 'en': '英語'}


def language_decision(language, probability, source, target):
    """Never force an utterance into a language chosen in the UI."""
    if language not in LANGUAGE_NAMES or (probability is not None and probability < 0.60):
        return 'skip', message('unknown_language')
    if source != 'auto' and language != source:
        return 'skip', message('filtered_language', language=message(language))
    if language == target:
        return 'original', message('same_language', language=message(language))
    return 'translate', message('translation_direction', language=message(language), target=message(target))


def put_latest(q, item):
    try:
        q.put_nowait(item)
        return False
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        q.put_nowait(item)
        return True


class Segmenter:
    """20 ms PCM frames; pre-roll prevents clipping word onsets."""
    def __init__(self, rate, threshold=0.008, silence=0.8, maximum=7):
        self.rate, self.threshold = rate, threshold
        self.silence, self.maximum = silence, maximum
        self.pre = deque(maxlen=20)
        self.frames = []
        self.quiet = self.length = self.voiced = 0

    def feed(self, frame):
        duration = len(frame) / self.rate
        active = float(np.sqrt(np.mean(frame ** 2))) >= self.threshold
        if not self.frames:
            if not active:
                self.pre.append(frame)
                return None
            self.frames = list(self.pre)
            self.pre.clear()
        self.frames.append(frame)
        self.length += duration
        self.voiced += duration if active else 0
        self.quiet = 0 if active else self.quiet + duration
        if self.quiet >= self.silence or self.length >= self.maximum:
            result = np.concatenate(self.frames) if self.voiced >= 0.20 else None
            self.reset()
            return result
        return None

    def reset(self):
        self.frames = []
        self.pre.clear()
        self.quiet = self.length = self.voiced = 0

    def finish_idle(self):
        """Flush only after real inactivity, without inserting gaps between packets."""
        result = None
        if self.frames and self.voiced >= 0.20:
            result = np.concatenate(self.frames + [np.zeros(int(self.rate * self.silence), np.float32)])
        self.reset()
        return result


def audio_devices():
    import pyaudiowpatch as pa
    with pa.PyAudio() as p:
        host = p.get_host_api_info_by_type(pa.paWASAPI)['index']
        return [dict(p.get_device_info_by_index(i)) for i in range(p.get_device_count())
                if p.get_device_info_by_index(i)['hostApi'] == host
                and p.get_device_info_by_index(i)['maxInputChannels'] > 0]


def speech_devices():
    return [], output_devices()


class Session:
    def __init__(self, config, events, speaker):
        self.config, self.events, self.speaker = config, events, speaker
        self.stop = threading.Event()
        self.audio = queue.Queue(maxsize=2)
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        capture = None
        try:
            from scipy.signal import resample_poly
            c = self.config
            self.events.put(('status', message('loading')))
            model, device = load_recognizer(c['model'], c.get('hardware', 'auto'),
                                            lambda msg: self.events.put(('backend', msg)))
            translator = DirectTranslator()
            if self.stop.is_set():
                return
            capture = threading.Thread(target=self.capture, daemon=True)
            capture.start()
            while not self.stop.is_set():
                try:
                    audio, rate = self.audio.get(timeout=0.1)
                except queue.Empty:
                    continue
                divisor = math.gcd(rate, 16000)
                audio = resample_poly(audio, 16000 // divisor, rate // divisor).astype(np.float32)
                original, info = recognize(model, audio)
                if not original or self.stop.is_set():
                    self.events.put(('language', message('unclear')))
                    continue
                action, reason = language_decision(info.language, info.language_probability, c['source'], c['target'])
                self.events.put(('language', message('language_info', reason=reason)))
                if action == 'skip':
                    continue
                translated = original if action == 'original' else translator.translate(original, info.language, c['target'])
                if self.stop.is_set():
                    break
                self.events.put(('result', (original, translated)))
                if action == 'translate' and self.speaker.enabled and c.get('output') is not None:
                    self.speaker.say(translated, c['target'], c['output'])
        except Exception as exc:
            self.events.put(('error', message('session_error', detail=exc)))
        finally:
            self.stop.set()
            if capture:
                capture.join(timeout=3)
            self.events.put(('stopped', None))

    def capture(self):
        if self.config.get('input_kind') in ('process', 'discord'):
            self.capture_process()
            return
        import pyaudiowpatch as pa
        try:
            with pa.PyAudio() as p:
                device = p.get_device_info_by_index(self.config['input'])
                rate = int(device['defaultSampleRate'])
                channels = min(2, int(device['maxInputChannels']))
                frames = int(rate * 0.02)
                segmenter = Segmenter(rate, threshold=self.config['threshold'])
                stream = p.open(format=pa.paFloat32, channels=channels, rate=rate,
                                input=True, input_device_index=device['index'], frames_per_buffer=frames)
                self.events.put(('status', message('input_active', name=device['name'])))
                meter_at = 0
                try:
                    while not self.stop.is_set():
                        if stream.get_read_available() < frames:
                            self.stop.wait(0.02)
                            continue
                        raw = stream.read(frames, exception_on_overflow=False)
                        audio = np.frombuffer(raw, np.float32).reshape(-1, channels).mean(axis=1)
                        if time.monotonic() - meter_at >= 0.1:
                            self.events.put(('level', float(np.sqrt(np.mean(audio ** 2)))))
                            meter_at = time.monotonic()
                        if self.config['guard'] and self.speaker.playing.is_set():
                            segmenter.reset()
                            continue
                        result = segmenter.feed(audio)
                        if result is not None and put_latest(self.audio, (result, rate)):
                            self.events.put(('notice', message('backlog')))
                finally:
                    stream.stop_stream()
                    stream.close()
        except Exception as exc:
            self.events.put(('error', message('capture_error', detail=exc)))
            self.stop.set()

    def capture_process(self):
        import psutil
        try:
            selected = self.config.get('process_pid', self.config.get('discord_pid'))
            if not selected:
                raise UserMessageError('app_select')
            try:
                owner = psutil.Process(selected)
                expected_creation = self.config.get('process_created', self.config.get('discord_created'))
                if expected_creation is None or owner.create_time() != expected_creation:
                    raise UserMessageError('app_restarted')
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                raise UserMessageError('app_restarted')
            name = owner.name()
            with ProcessCapture(owner.pid) as stream:
                self.events.put(('status', message('app_connected', name=name)))
                segmenter = Segmenter(stream.rate, threshold=self.config['threshold'])
                pending = np.empty(0, np.float32)
                meter_at = last_audio = check_at = time.monotonic()
                frame_size = int(stream.rate * 0.02)
                while not self.stop.is_set():
                    now = time.monotonic()
                    if now - check_at >= 1:
                        if not owner.is_running():
                            raise UserMessageError('app_closed')
                        check_at = now
                    block = stream.read()
                    now = time.monotonic()
                    if len(block):
                        last_audio = now
                        pending = np.concatenate((pending, block))
                    elif now - last_audio >= segmenter.silence and segmenter.frames:
                        if len(pending):
                            segmenter.feed(pending)
                            pending = np.empty(0, np.float32)
                        result = segmenter.finish_idle()
                        if result is not None:
                            put_latest(self.audio, (result, stream.rate))
                    if now - meter_at >= 0.1:
                        level = float(np.sqrt(np.mean(block ** 2))) if len(block) else 0
                        self.events.put(('level', level))
                        meter_at = now
                    while len(pending) >= frame_size:
                        frame, pending = pending[:frame_size], pending[frame_size:]
                        result = segmenter.feed(frame)
                        if result is not None and put_latest(self.audio, (result, stream.rate)):
                            self.events.put(('notice', message('backlog')))
        except Exception as exc:
            self.events.put(('error', message('capture_error', detail=exc)))
            self.stop.set()
