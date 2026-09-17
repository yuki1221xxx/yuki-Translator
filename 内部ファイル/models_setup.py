"""Download only the models required by the lightweight local application."""
from runtime import MODEL_CACHE
from accuracy import DEFAULT_MODEL, ASR_MODELS, TRANSLATION_REPO, recognition_location, translation_location
from speech import TTS_FOLDER, TTS_REPO, TTS_FILES, tts_location
from i18n import message

ASR_REQUIRED = [
    'conv_frontend.onnx', 'encoder.int8.onnx', 'decoder.int8.onnx',
    'tokenizer/merges.txt', 'tokenizer/vocab.json', 'tokenizer/tokenizer_config.json',
]
TRANSLATION_REQUIRED = ['model.bin', 'config.json', 'sentencepiece.bpe.model']


def asr_ready(model=DEFAULT_MODEL) -> bool:
    return all((recognition_location(model) / name).is_file() for name in ASR_REQUIRED)


def translation_ready() -> bool:
    return all((translation_location() / name).is_file() for name in TRANSLATION_REQUIRED)


def tts_ready() -> bool:
    return all((tts_location() / name).is_file() for name in TTS_FILES)


def bootstrap_ready(model=DEFAULT_MODEL) -> bool:
    return asr_ready(model) and translation_ready() and tts_ready()


def install_models(report=print, model=DEFAULT_MODEL):
    from huggingface_hub import snapshot_download
    report(message('install_asr', model=model))
    selected = ASR_MODELS[model]
    required = ['conv_frontend.onnx', 'encoder.int8.onnx', 'decoder.int8.onnx',
                'tokenizer/merges.txt', 'tokenizer/vocab.json', 'tokenizer/tokenizer_config.json']
    if not all((recognition_location(model) / f).is_file() for f in required):
        snapshot_download(selected['repo'], local_dir=str(MODEL_CACHE / selected['folder']),
                          allow_patterns=['*.onnx', 'tokenizer/*', 'README.md', 'LICENSE*'])
    report(message('install_translation'))
    if not all((translation_location() / f).is_file() for f in ['model.bin', 'config.json', 'sentencepiece.bpe.model']):
        snapshot_download(TRANSLATION_REPO, local_dir=str(MODEL_CACHE / 'translation-nllb'),
                          allow_patterns=['*.json', '*.bin', '*.model', 'README.md', 'LICENSE*'])
    report(message('install_tts'))
    if not all((tts_location() / f).is_file() for f in TTS_FILES):
        snapshot_download(TTS_REPO, local_dir=str(MODEL_CACHE / TTS_FOLDER),
                          allow_patterns=['*.onnx', '*.json', '*.bin', 'README.md', '*LICENSE*'])
    report(message('installed'))


def install_bootstrap_models(report=print, model=DEFAULT_MODEL):
    install_models(report, model)


if __name__ == '__main__':
    install_models()
