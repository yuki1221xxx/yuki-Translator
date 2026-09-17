"""First-launch model download UI for the installer build."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from i18n import message, render, tr
from models_setup import bootstrap_ready, install_bootstrap_models
from runtime import FROZEN


BG, PANEL, FG, MUTED, ACCENT = '#0d131e', '#17202e', '#eef3fa', '#93a5bd', '#73ebc4'


def run_first_launch_setup(language: str = 'ja') -> bool:
    if not FROZEN or bootstrap_ready():
        return True

    root = tk.Tk()
    root.title('yuki Translator')
    root.configure(bg=BG)
    root.geometry('640x320')
    root.resizable(False, False)
    root.protocol('WM_DELETE_WINDOW', root.destroy)

    events: queue.Queue = queue.Queue()
    result = {'ok': False}

    frame = ttk.Frame(root, padding=28)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text=tr('setup_title', language), font=('Yu Gothic UI', 18, 'bold'), foreground=ACCENT).pack(anchor='w')
    ttk.Label(frame, text=tr('setup_intro', language), wraplength=560, foreground=MUTED).pack(anchor='w', pady=(12, 18))
    status = tk.StringVar(value=tr('setup_progress', language))
    ttk.Label(frame, textvariable=status, foreground=FG, wraplength=560).pack(anchor='w', pady=(0, 12))
    progress = ttk.Progressbar(frame, mode='indeterminate', length=560)
    progress.pack(fill='x')
    progress.start(12)

    def poll():
        try:
            while True:
                kind, data = events.get_nowait()
                if kind == 'status':
                    status.set(render(data, language))
                elif kind == 'done':
                    result['ok'] = True
                    progress.stop()
                    root.after(100, root.destroy)
                    return
                elif kind == 'error':
                    progress.stop()
                    messagebox.showerror(tr('error', language), render(data, language), parent=root)
                    root.after(100, root.destroy)
                    return
        except queue.Empty:
            pass
        root.after(120, poll)

    def work():
        try:
            install_bootstrap_models(lambda msg: events.put(('status', msg)))
            events.put(('done', None))
        except Exception as exc:
            events.put(('error', message('setup_failed', detail=exc)))

    threading.Thread(target=work, daemon=True).start()
    poll()
    root.mainloop()
    return result['ok']
