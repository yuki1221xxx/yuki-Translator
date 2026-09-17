# Build with: .venv\Scripts\python.exe -m PyInstaller --noconfirm YukiTranslator.spec
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata
from pathlib import Path
import sys

datas = []
for fixture in ('ko_hello_f', 'ko_hello_m', 'ja_hello'):
    datas.append((f'tests/fixtures/{fixture}.mp3', 'test-fixtures'))
binaries = []
for package in ('faster_whisper', 'edge_tts'):
    datas += collect_data_files(package)
for package in ('ctranslate2', 'onnxruntime', 'pyaudiowpatch', 'sherpa_onnx'):
    binaries += collect_dynamic_libs(package)
for distribution in ('faster-whisper', 'sherpa-onnx', 'sherpa-onnx-core', 'langid', 'edge-tts', 'huggingface-hub', 'tqdm', 'regex', 'requests', 'packaging', 'filelock', 'numpy', 'tokenizers', 'safetensors'):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        # Some are optional dependencies. Imports used by the app are still
        # validated by PyInstaller's analysis and the packaged self-test.
        pass

a = Analysis(['launcher.py'], pathex=[], binaries=binaries, datas=datas,
             hiddenimports=['win32com.client', 'pythoncom', 'pywintypes', 'scipy.special._special_ufuncs'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['torch', 'torchaudio', 'transformers', 'argostranslate', 'stanza', 'minisbd',
                       'nvidia', 'spacy', 'matplotlib', 'IPython', 'pytest', 'notebook', 'tensorboard'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='YukiTranslator',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='YukiTranslator')
