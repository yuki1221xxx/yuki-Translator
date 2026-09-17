"""Local multilingual speech and cancellable WASAPI playback with live volume."""
import math
import queue
import threading

import numpy as np
from runtime import APP_DIR, MODEL_CACHE
from i18n import message, UserMessageError

TTS_FOLDER = 'tts-supertonic-3'
TTS_REPO = 'csukuangfj2/sherpa-onnx-supertonic-3-tts-int8-2026-05-11'
TTS_FILES = ['duration_predictor.int8.onnx', 'text_encoder.int8.onnx',
             'vector_estimator.int8.onnx', 'vocoder.int8.onnx',
             'tts.json', 'unicode_indexer.bin', 'voice.bin']
TEST_PHRASES = {'ja': 'こんにちは。日本語の読み上げテストです。',
                'ko': '안녕하세요. 한국어 음성 출력 테스트입니다.',
                'en': 'Hello. This is a speech output test.'}


def tts_location():
    bundled = APP_DIR / 'models' / TTS_FOLDER
    return bundled if all((bundled / f).is_file() for f in TTS_FILES) else MODEL_CACHE / TTS_FOLDER


class LocalVoice:
    def __init__(self):
        import sherpa_onnx as so
        folder = tts_location()
        if not all((folder / f).is_file() for f in TTS_FILES):
            raise UserMessageError('tts_missing')
        config = so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(
            supertonic=so.OfflineTtsSupertonicModelConfig(
                duration_predictor=str(folder / TTS_FILES[0]), text_encoder=str(folder / TTS_FILES[1]),
                vector_estimator=str(folder / TTS_FILES[2]), vocoder=str(folder / TTS_FILES[3]),
                tts_json=str(folder / TTS_FILES[4]), unicode_indexer=str(folder / TTS_FILES[5]),
                voice_style=str(folder / TTS_FILES[6])), num_threads=2, provider='cpu'))
        if not config.validate():
            raise UserMessageError('tts_missing')
        self.model = so.OfflineTts(config)

    def generate(self, text, language):
        import sherpa_onnx as so
        config = so.GenerationConfig()
        config.sid = 6
        config.num_steps = 5
        config.extra = {'lang': language}
        result = self.model.generate(text, config)
        samples = np.asarray(result.samples, dtype=np.float32)
        if not len(samples) or not np.isfinite(samples).all() or not np.any(samples):
            raise UserMessageError('tts_empty')
        return samples, result.sample_rate


def output_devices():
    import pyaudiowpatch as pa
    with pa.PyAudio() as p:
        host = p.get_host_api_info_by_type(pa.paWASAPI)
        devices = [dict(p.get_device_info_by_index(i)) for i in range(p.get_device_count())
                   if p.get_device_info_by_index(i)['hostApi'] == host['index']
                   and p.get_device_info_by_index(i)['maxOutputChannels'] > 0]
        devices.sort(key=lambda d: d['index'] != host['defaultOutputDevice'])
        # Carry the name as well so an unplugged device cannot silently become another output.
        return [({'index': int(d['index']), 'name': d['name']}, d['name']) for d in devices]


def scaled_pcm(samples, volume):
    return (np.clip(samples, -1, 1) * (max(0, min(100, float(volume))) / 100)).astype(np.float32).tobytes()


class Speaker:
    def __init__(self, events):
        self.events = events
        self.queue = queue.Queue(maxsize=2)
        self.volume = 70
        self.enabled = True
        self.backend = 'local'
        self.playing = threading.Event()
        self.shutdown = threading.Event()
        self.generation = 0
        self.voice = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def say(self, text, lang, output):
        item = (self.generation, text, lang, dict(output), self.backend)
        try:
            self.queue.put_nowait(item)
        except queue.Full:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                pass
            self.queue.put_nowait(item)

    def cancel(self):
        self.generation += 1

    def cancelled(self, generation):
        return generation != self.generation or not self.enabled or self.shutdown.is_set()

    def run(self):
        while not self.shutdown.is_set():
            try:
                generation, text, lang, output, backend = self.queue.get(timeout=.1)
            except queue.Empty:
                continue
            if self.cancelled(generation):
                continue
            try:
                if backend == 'online':
                    audio, rate = self.online_audio(text, lang, generation)
                else:
                    if self.voice is None:
                        self.events.put(('notice', message('speech_loading')))
                        self.voice = LocalVoice()
                    audio, rate = self.voice.generate(text, lang)
                if self.cancelled(generation):
                    continue
                self.events.put(('notice', ''))
                self.play_audio(audio, rate, output, generation)
            except Exception as exc:
                self.events.put(('notice', message('speech_failed', detail=exc)))
            finally:
                self.playing.clear()

    def play_audio(self, samples, rate, output, generation):
        import pyaudiowpatch as pa
        from scipy.signal import resample_poly
        with pa.PyAudio() as p:
            try:
                device = p.get_device_info_by_index(output['index'])
            except (OSError, ValueError):
                raise UserMessageError('output_missing')
            if (device['name'] != output['name'] or device['maxOutputChannels'] <= 0
                    or device['hostApi'] != p.get_host_api_info_by_type(pa.paWASAPI)['index']):
                raise UserMessageError('output_missing')
            output_rate = int(device['defaultSampleRate'])
            divisor = math.gcd(rate, output_rate)
            samples = resample_poly(samples, output_rate // divisor, rate // divisor).astype(np.float32)
            channels = min(2, int(device['maxOutputChannels']))
            if self.cancelled(generation):
                return
            stream = p.open(format=pa.paFloat32, channels=channels, rate=output_rate,
                            output=True, output_device_index=device['index'], frames_per_buffer=512)
            try:
                self.playing.set()
                for offset in range(0, len(samples), 512):
                    if self.cancelled(generation):
                        break
                    block = np.repeat(samples[offset:offset + 512, None], channels, axis=1)
                    stream.write(scaled_pcm(block, self.volume))
            finally:
                stream.stop_stream()
                stream.close()

    def online_audio(self, text, lang, generation):
        import asyncio
        import io
        import edge_tts
        from faster_whisper.audio import decode_audio

        async def synthesize():
            name = {'ja': 'ja-JP-NanamiNeural', 'ko': 'ko-KR-SunHiNeural', 'en': 'en-US-JennyNeural'}[lang]
            data = bytearray()
            async for chunk in edge_tts.Communicate(text, name).stream():
                if self.cancelled(generation):
                    return b''
                if chunk['type'] == 'audio':
                    data.extend(chunk['data'])
            return bytes(data)

        data = asyncio.run(asyncio.wait_for(synthesize(), timeout=30))
        if not data:
            return np.empty(0, np.float32), 24000
        return decode_audio(io.BytesIO(data), sampling_rate=24000), 24000
