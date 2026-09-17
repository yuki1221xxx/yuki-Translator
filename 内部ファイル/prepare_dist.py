"""Copy docs and license metadata into the app bundle without model files."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'dist' / 'YukiTranslator'
DEST.mkdir(parents=True, exist_ok=True)

for name in ('README.md', 'MODEL_NOTES.md'):
    shutil.copy2(ROOT / name, DEST / name)

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
(DEST / 'VERSION.txt').write_text(
    (ROOT / 'version.py').read_text(encoding='utf-8').split('APP_VERSION = ', 1)[1].split('\n', 1)[0].strip("'\"\n "),
    encoding='utf-8',
)
print('Application bundle prepared')
