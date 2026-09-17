"""Stable paths for source runs and the Windows application bundle."""
import os
from pathlib import Path
import sys

FROZEN = getattr(sys, 'frozen', False)
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
_data_override = os.environ.get('YUKI_TRANSLATOR_DATA_DIR')
DATA_DIR = (Path(_data_override).expanduser().resolve() if _data_override else
            (Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'yuki-Translator') if FROZEN else APP_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE = DATA_DIR / 'models'
MODEL_CACHE.mkdir(parents=True, exist_ok=True)
