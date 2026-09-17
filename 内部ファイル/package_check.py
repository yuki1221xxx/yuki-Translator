"""Explicit --self-test checks real bundled DLLs, UI and local inference."""
import json
from pathlib import Path


def run(report_path):
    import os
    import threading
    os.environ['HF_HUB_OFFLINE'] = '1'
    from runtime import FROZEN, DATA_DIR, APP_DIR
    import engine
    import numpy as np
    from faster_whisper.audio import decode_audio
    from accuracy import DirectTranslator, load_recognizer, recognize, DEFAULT_MODEL, HEAVY_MODEL
    import sys
    import edge_tts
    import av
    import tkinter as tk
    from app import App
    model, device = load_recognizer()
    silence, _ = recognize(model, np.zeros(16000, dtype=np.float32))
    assert not silence, 'Silence must not produce words'
    translate = DirectTranslator()
    translations = {
        'ja_ko': translate.translate('今日は良い天気です。', 'ja', 'ko'),
        'ko_ja': translate.translate('안녕하세요.', 'ko', 'ja'),
    }
    assert all(translations.values()), 'Translation result was empty'
    assert 'こんにちは' in translations['ko_ja'], translations
    fixtures = Path(sys._MEIPASS) / 'test-fixtures' if FROZEN else APP_DIR / 'tests' / 'fixtures'
    recognition = []
    for name, expected in [('ko_hello_f', 'ko'), ('ko_hello_m', 'ko'), ('ja_hello', 'ja')]:
        text, info = recognize(model, decode_audio(str(fixtures / f'{name}.mp3'), sampling_rate=16000))
        assert info.language == expected, (text, info.language)
        translated = translate.translate(text, expected, 'ja')
        assert 'こんにちは' in translated, (text, translated)
        recognition.append(dict(name=name, text=text, translated=translated))
    from process_audio import ProcessCapture
    native_capture = {}
    def check_native():
        try:
            with ProcessCapture(os.getpid()) as stream:
                stream.read()
                native_capture['ok'] = True
        except Exception as exc:
            native_capture['error'] = repr(exc)
    worker = threading.Thread(target=check_native)
    worker.start()
    worker.join(15)
    assert native_capture.get('ok'), native_capture
    assert engine.language_decision('ja', .98, 'auto', 'ja')[0] == 'original'
    assert engine.language_decision('ja', .98, 'ko', 'ja')[0] == 'skip'
    import gc
    del model
    gc.collect()
    heavy, _ = load_recognizer(HEAVY_MODEL)
    heavy_text, heavy_info = recognize(heavy, decode_audio(str(fixtures / 'ko_hello_m.mp3'), sampling_rate=16000))
    assert heavy_info.language == 'ko' and '안녕' in heavy_text, heavy_text
    from speech import LocalVoice
    from scipy.signal import resample_poly
    import math
    local_voice = LocalVoice()
    translated_ko = translate.translate('こんにちは。よろしくお願いします。', 'ja', 'ko')
    speech, speech_rate = local_voice.generate(translated_ko, 'ko')
    assert len(speech) > speech_rate * .2 and np.max(np.abs(speech)) > .001
    divisor = math.gcd(speech_rate, 16000)
    spoken, spoken_info = recognize(heavy, resample_poly(speech, 16000 // divisor, speech_rate // divisor))
    assert spoken_info.language == 'ko', spoken
    del heavy, local_voice
    gc.collect()
    root = tk.Tk()
    app = App(root, persist=False)
    root.update()
    app.subtitle_enabled.set(True)
    app.show_overlay()
    app.events.put(('result', ('테스트', '字幕テスト')))
    app.poll()
    root.update()
    assert app.subtitles.text == '字幕テスト'
    app.speak.set(False)
    app.update_speech()
    assert not app.speaker.enabled
    app.subtitle_enabled.set(False)
    app.update_subtitle_output()
    root.update()
    assert app.overlay.state() == 'withdrawn'
    app.subtitle_enabled.set(True)
    app.update_subtitle_output()
    root.update()
    assert app.overlay.attributes('-topmost')
    assert app.overlay.overrideredirect()
    assert app.overlay.attributes('-transparentcolor') == '#010203'
    import win32gui, win32con
    hwnd = win32gui.GetParent(app.overlay.winfo_id()) or app.overlay.winfo_id()
    assert win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TRANSPARENT
    directions = app.source.get(), app.target.get()
    localized = {}
    for language in ('ja', 'ko', 'en'):
        app.ui_language.set(language)
        app.change_language()
        root.update()
        localized[language] = app.start_button.cget('text')
        assert (app.source.get(), app.target.get()) == directions
    assert len(set(localized.values())) == 3
    app.movable.set(True)
    app.update_overlay()
    root.update()
    assert not (win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TRANSPARENT)
    app.position.set('top_left')
    app.offset_x.set(50)
    app.update_overlay()
    root.update()
    assert app.overlay.winfo_x() >= app.subtitles.rect[0]
    app.model.set(HEAVY_MODEL)
    app.refresh_choices()
    assert '1.7B' in app.model_box.get()
    from process_audio import application_processes
    applications = application_processes()
    assert all(p['pid'] != os.getpid() for p in applications)
    app.tabs.select(1)
    root.update()
    from types import SimpleNamespace
    app.preview_move(SimpleNamespace(x=app.preview.winfo_width()/2, y=app.preview.winfo_height()/2))
    assert app.position.get() == 'custom'
    assert app.input_box.current() >= 0, app.notice.get()
    assert app.output_box.current() >= 0, app.notice.get()
    report = dict(ok=True, frozen=FROZEN, data_dir=str(DATA_DIR),
                  inputs=len(app.devices), outputs=len(app.outputs),
                  voices=[v[1] for v in app.voices], translations=translations,
                  recognizer=f'{DEFAULT_MODEL} / {device}', recognition=recognition, overlay=True, process_capture=native_capture,
                  source=app.source.get(), model=app.model.get(), localized=localized,
                  heavy_recognition=heavy_text, local_korean_speech=dict(text=translated_ko, seconds=len(speech)/speech_rate, recognized=spoken),
                  transparent_background=True, click_through=True, subtitle_position=True,
                  independent_outputs=True, visual_position_preview=True, capture_apps=len(applications))
    # Avoid changing a user's saved settings from the diagnostic.
    app.speaker.shutdown.set()
    app.speaker.thread.join(timeout=3)
    root.destroy()
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
