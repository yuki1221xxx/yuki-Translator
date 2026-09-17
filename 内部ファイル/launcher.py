"""Windows executable entry point, including an opt-in packaging diagnostic."""
import multiprocessing
import sys


def main():
    multiprocessing.freeze_support()
    from runtime import DATA_DIR
    # Some ML dependencies print progress even in a windowed application.
    if sys.stdout is None:
        sys.stdout = open(DATA_DIR / 'runtime.log', 'a', encoding='utf-8', buffering=1)
    if sys.stderr is None:
        sys.stderr = sys.stdout
    try:
        if '--self-test' in sys.argv:
            from package_check import run
            run(sys.argv[sys.argv.index('--self-test') + 1])
        else:
            from app import main as start
            start()
    except Exception:
        import traceback
        from pathlib import Path
        details = traceback.format_exc()
        (DATA_DIR / 'startup-error.log').write_text(details, encoding='utf-8')
        if '--self-test' in sys.argv:
            import json
            Path(sys.argv[sys.argv.index('--self-test') + 1]).write_text(
                json.dumps({'ok': False, 'error': details}, ensure_ascii=False), encoding='utf-8')
        else:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror('yuki Translator', f'起動できませんでした。\n{details}\nログ: {DATA_DIR}')
            root.destroy()
        raise SystemExit(1)


if __name__ == '__main__':
    main()
