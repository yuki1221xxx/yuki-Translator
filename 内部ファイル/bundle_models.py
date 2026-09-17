"""Populate the distributable with model files and license information."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

from accuracy import ASR_MODELS
from speech import TTS_FOLDER

ROOT = Path(__file__).resolve().parent
DEST = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'dist' / 'YukiTranslator'
DEST.mkdir(parents=True, exist_ok=True)
for folder in [m['folder'] for m in ASR_MODELS.values()] + [TTS_FOLDER]:
    shutil.copytree(ROOT / 'models' / folder, DEST / 'models' / folder,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('.cache'))
shutil.copytree(ROOT / 'models' / 'translation-nllb', DEST / 'models' / 'translation-nllb',
                dirs_exist_ok=True, ignore=shutil.ignore_patterns('.cache'))
shutil.copy2(ROOT / 'README.md', DEST / 'README.md')
shutil.copy2(ROOT / 'MODEL_NOTES.md', DEST / 'MODEL_NOTES.md')
licenses = DEST / 'licenses'
licenses.mkdir(exist_ok=True)
versions = []
for dist in importlib.metadata.distributions():
    name = dist.metadata.get('Name', 'unknown')
    versions.append(f'{name}=={dist.version}')
    for file in dist.files or []:
        if any(word in file.name.lower() for word in ('license', 'copying', 'notice')):
            source = Path(dist.locate_file(file))
            if source.is_file() and source.suffix.lower() not in {'.py', '.pyc', '.pyd'}:
                target = licenses / name / str(file).replace('..', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
(DEST / 'DEPENDENCIES.txt').write_text('\n'.join(sorted(versions)), encoding='utf-8')
print(f'Application ready: {DEST / "YukiTranslator.exe"}')
