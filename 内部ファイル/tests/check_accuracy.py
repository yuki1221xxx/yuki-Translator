"""Explicit model evaluation on synthetic Japanese/Korean speech, including noise."""
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from faster_whisper.audio import decode_audio
from accuracy import load_recognizer, recognize, DirectTranslator, DEFAULT_MODEL

EXPECTED = {'ko_hello_f': '안녕하세요', 'ko_hello_m': '안녕하세요', 'ko_thanks': '감사합니다',
            'ko_wait': '잠깐만 기다려 주세요', 'ko_where': '지금 어디에 있어요',
            'ja_hello': 'こんにちはよろしくお願いします'}


def normalized(text):
    return re.sub(r'[\W_]+', '', text)


def main(model_name):
    model, device = load_recognizer(model_name, report=print)
    translator = DirectTranslator()
    results = []
    for name, expected in EXPECTED.items():
        original = decode_audio(str(Path(__file__).parent / 'fixtures' / f'{name}.mp3'), sampling_rate=16000)
        for variant in ('clean', 'quiet_noise'):
            audio = original.copy()
            if variant == 'quiet_noise':
                rng = np.random.default_rng(13)
                rms = np.sqrt(np.mean(audio**2))
                audio = (audio + rng.normal(0, rms * .18, len(audio))) * .2
            started = time.perf_counter()
            text, info = recognize(model, audio)
            elapsed = time.perf_counter() - started
            translated = translator.translate(text, info.language, 'ja') if text and info.language in {'ja', 'ko', 'en'} else ''
            row = dict(name=name, variant=variant, expected=expected, text=text, language=info.language,
                       probability=None if info.language_probability is None else round(info.language_probability, 3), translated=translated,
                       seconds=round(elapsed, 2), exact=normalized(text)==normalized(expected))
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    report = dict(model=model_name, device=device, exact=sum(r['exact'] for r in results), total=len(results), results=results)
    out = Path(__file__).parent / ('accuracy-qwen3-asr-1.7b.json' if '1.7B' in model_name else 'accuracy-qwen3-asr.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert all('こんにちは' in r['translated'] for r in results if r['name'].startswith('ko_hello')), 'Greeting regression'
    assert all(r['language']==('ja' if r['name'].startswith('ja') else 'ko') for r in results), 'Language regression'


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv)>1 else DEFAULT_MODEL)
