"""Stable paths for source runs and the Windows application bundle."""
import os
from pathlib import Path
import sys

FROZEN = getattr(sys, 'frozen', False)
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
DATA_DIR = (Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'yuki-Translator') if FROZEN else APP_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE = DATA_DIR / 'models'
