"""Higher quality local recognition and direct multilingual translation."""
import re
from types import SimpleNamespace

import numpy as np
from runtime import APP_DIR, MODEL_CACHE
from i18n import UserMessageError

DEFAULT_MODEL = 'Qwen3-ASR 0.6B int8'
ASR_FOLDER = 'qwen3-asr-0.6b-int8'
ASR_REPO = 'csukuangfj2/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25'
HEAVY_MODEL = 'Qwen3-ASR 1.7B int8'
ASR_MODELS = {
    DEFAULT_MODEL: {'folder': ASR_FOLDER, 'repo': ASR_REPO, 'label': 'model_light'},
    HEAVY_MODEL: {'folder': 'qwen3-asr-1.7b-int8',
                  'repo': 'thieunv-asilla/sherpa-onnx-qwen3-asr-1.7B-int8', 'label': 'model_heavy'},
}
TRANSLATION_REPO = 'luigi000/nllb-200-distilled-600M-ct2-int8'
LANG_CODES = {'ja': 'jpn_Jpan', 'ko': 'kor_Hang', 'en': 'eng_Latn'}


def recognition_location(model_name=DEFAULT_MODEL):
    folder = ASR_MODELS[model_name]['folder']
    bundled = APP_DIR / 'models' / folder
    return bundled if (bundled / 'decoder.int8.onnx').is_file() else MODEL_CACHE / folder


def load_recognizer(model_name=DEFAULT_MODEL, hardware='auto', report=lambda msg: None):
    import sherpa_onnx
    folder = recognition_location(model_name)
    if not (folder / 'decoder.int8.onnx').is_file():
        raise UserMessageError('asr_missing')
    model = sherpa_onnx.OfflineRecognizer.from_qwen3_asr(
        conv_frontend=str(folder / 'conv_frontend.onnx'),
        encoder=str(folder / 'encoder.int8.onnx'), decoder=str(folder / 'decoder.int8.onnx'),
        tokenizer=str(folder / 'tokenizer'), num_threads=6, provider='cpu',
        max_total_len=512, max_new_tokens=128, temperature=1e-6)
    from i18n import message
    report(message('backend_status', model=model_name))
    return model, 'cpu'


def prepare_audio(audio):
    """Preserve quiet word onsets and bound gain; never turn silence into speech."""
    audio = np.asarray(audio, dtype=np.float32)
    if not len(audio):
        return audio
    rms = float(np.sqrt(np.mean(audio ** 2)))
    peak = float(np.max(np.abs(audio)))
    gain = min(4.0, 0.08 / max(rms, 1e-6), 0.95 / max(peak, 1e-6)) if rms > .001 else 1.0
    audio = audio * max(1.0, gain)
    return np.pad(audio, (3200, 4800))


def text_language(text):
    """sherpa 1.13.8 discards Qwen's language header; do not invent ASR confidence.

    Kana/Hangul distinguish the requested languages. Mixed scripts and Han-only
    phrases remain unknown rather than forcing Chinese text into Japanese.
    """
    kana = bool(re.search(r'[\u3041-\u3096\u30a1-\u30fa]', text))
    hangul = bool(re.search(r'[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]', text))
    if kana and hangul:
        return None
    if kana:
        return 'ja'
    if hangul:
        return 'ko'
    if re.search(r'[\u3400-\u9fff]', text) or not re.search('[a-zA-Z]', text):
        return None
    import langid
    detected, _ = langid.classify(text)
    return 'en' if detected == 'en' else None


def clean_recognition(text):
    # Some 1.7B exports emit the language scaffold as ordinary tokens, which
    # sherpa's special-token cleanup cannot strip. Require the explicit marker.
    text = re.sub(r'^\s*(?:\*\*)?language\s+[A-Za-z][A-Za-z -]{0,40}?(?:\*\*)?\s*<asr_text>\s*', '', text)
    return re.sub(r'\s*<\|im_end\|>\s*$', '', text).strip()


def recognize(model, audio):
    from faster_whisper.vad import get_speech_timestamps, VadOptions
    audio = prepare_audio(audio)
    info = SimpleNamespace(language=None, language_probability=None)
    if not len(audio) or not np.isfinite(audio).all():
        return '', info
    # Gate non-speech, but retain the complete waveform to preserve short words.
    speech = get_speech_timestamps(audio, VadOptions(min_speech_duration_ms=120,
                                                    min_silence_duration_ms=500, speech_pad_ms=300))
    if not speech:
        return '', info
    stream = model.create_stream()
    stream.accept_waveform(16000, audio)
    # Never set stream language: a Korean-only prompt also mangles Japanese speech.
    model.decode_stream(stream)
    text = clean_recognition(stream.result.text)
    # At the generation limit the sentence may be incomplete (e.g. lost negation).
    if len(stream.result.tokens) >= 120:
        return '', info
    info.language = text_language(text)
    return text, info


def translation_location():
    bundled = APP_DIR / 'models' / 'translation-nllb'
    return bundled if bundled.is_dir() else MODEL_CACHE / 'translation-nllb'


class DirectTranslator:
    def __init__(self):
        import ctranslate2
        import sentencepiece
        folder = translation_location()
        if not (folder / 'model.bin').exists():
            raise UserMessageError('translation_missing')
        # SentencePiece's native fopen cannot handle some Japanese Windows paths.
        self.tokenizer = sentencepiece.SentencePieceProcessor(model_proto=(folder / 'sentencepiece.bpe.model').read_bytes())
        self.model = ctranslate2.Translator(str(folder), device='cpu', compute_type='int8', intra_threads=6)

    def translate(self, text, source, target):
        if source == target:
            return text
        tokens = [LANG_CODES[source], *self.tokenizer.encode(text, out_type=str), '</s>']
        prefix = LANG_CODES[target]
        result = self.model.translate_batch([tokens], target_prefix=[[prefix]], beam_size=4,
                                            max_decoding_length=256, repetition_penalty=1.1,
                                            no_repeat_ngram_size=3)[0]
        return self.tokenizer.decode([t for t in result.hypotheses[0] if t not in {prefix, '</s>', '<s>', '<pad>'}]).strip()
