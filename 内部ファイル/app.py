import json
import logging
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from engine import Session, Speaker, audio_devices, speech_devices
from process_audio import application_processes
from widgets import Toggle
from runtime import DATA_DIR
from accuracy import DEFAULT_MODEL, ASR_MODELS
from speech import TEST_PHRASES
from i18n import UI_LANGUAGES, message, render, tr
from subtitles import SubtitleOverlay, POSITIONS, monitors

BG, PANEL, FG, MUTED, ACCENT = '#0d131e', '#17202e', '#eef3fa', '#93a5bd', '#73ebc4'
LEGACY_LANGS = {'自動判定（日・韓・英）': 'auto', '日本語': 'ja', '한국어 / 韓国語': 'ko', 'English / 英語': 'en'}


class App:
    def __init__(self, root, persist=True):
        self.persist = persist
        self.root = root
        self.settings_path = DATA_DIR / 'settings.json'
        try:
            saved = json.loads(self.settings_path.read_text('utf-8'))
        except (OSError, ValueError):
            saved = {}
        self.saved = saved
        self.ui_language = tk.StringVar(value=saved.get('ui_language', 'ja') if saved.get('ui_language', 'ja') in UI_LANGUAGES else 'ja')
        source = LEGACY_LANGS.get(saved.get('source'), saved.get('source', 'auto'))
        target = LEGACY_LANGS.get(saved.get('target'), saved.get('target', 'ja'))
        self.source = tk.StringVar(value=source if source in ('auto', 'ja', 'ko', 'en') else 'auto')
        self.target = tk.StringVar(value=target if target in ('ja', 'ko', 'en') else 'ja')
        self.model = tk.StringVar(value=saved.get('model') if saved.get('model') in ASR_MODELS else DEFAULT_MODEL)
        self.hardware = tk.StringVar(value='CPU')
        self.backend = tk.StringVar(value='online' if saved.get('backend') in ('online', 'オンライン（翻訳文を送信）') else 'local')
        self.volume = tk.IntVar(value=max(0, min(100, saved.get('volume', 70))))
        self.speak = tk.BooleanVar(value=saved.get('speak', True))
        self.subtitle_enabled = tk.BooleanVar(value=saved.get('subtitle_enabled', True))
        self.background_apps = tk.BooleanVar(value=saved.get('background_apps', False))
        self.guard = tk.BooleanVar(value=saved.get('guard', True))
        self.font_size = tk.IntVar(value=max(16, min(64, saved.get('font_size', 30))))
        self.opacity = tk.DoubleVar(value=max(.3, min(1, saved.get('opacity', 1))))
        self.threshold = tk.DoubleVar(value=max(.002, min(.04, saved.get('threshold', .008))))
        self.position = tk.StringVar(value=saved.get('position', 'bottom_center') if saved.get('position', 'bottom_center') in POSITIONS else 'bottom_center')
        self.monitor = tk.StringVar(value=saved.get('monitor', ''))
        self.offset_x = tk.IntVar(value=saved.get('offset_x', 0))
        self.offset_y = tk.IntVar(value=saved.get('offset_y', 0))
        self.show_original = tk.BooleanVar(value=saved.get('show_original', False))
        self.movable = tk.BooleanVar(value=False)
        self.custom_position = saved.get('custom_position')
        self.events = queue.Queue()
        self.session = None
        self.installing = False
        self.closed = False
        self.save_timer = None
        self.speaker = Speaker(self.events)
        self.devices, self.outputs, self.voices = [], [], []
        self.text_widgets, self.choices, self.controls = [], [], []
        self.status, self.notice, self.detected, self.backend_status = [tk.StringVar() for _ in range(4)]
        self.last_messages = {'status': message('idle'), 'notice': '', 'detected': message('waiting'), 'backend_status': message('backend_pending')}
        self.level = tk.DoubleVar(value=0)
        self.has_caption = False
        root.title('yuki Translator')
        root.geometry('1080x880')
        root.minsize(960, 800)
        root.configure(bg=BG)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', font=('Yu Gothic UI', 10), background=BG, foreground=FG, borderwidth=0)
        style.configure('TButton', padding=(14, 9), background=PANEL, borderwidth=0, relief='flat')
        style.map('TButton', background=[('active', '#283951')], foreground=[('disabled', '#56677e')])
        style.configure('Primary.TButton', background=ACCENT, foreground='#0b2423', font=('Yu Gothic UI', 11, 'bold'), padding=(24, 13))
        style.map('Primary.TButton', background=[('active', '#a0f6d9'), ('disabled', '#243d3b')], foreground=[('disabled', '#7d9297')])
        style.configure('TCombobox', fieldbackground=PANEL, background=PANEL, foreground=FG, bordercolor='#2b3b50', lightcolor=PANEL, darkcolor=PANEL, arrowcolor=MUTED, padding=9)
        style.map('TCombobox', fieldbackground=[('readonly', PANEL), ('disabled', BG)], foreground=[('readonly', FG), ('disabled', MUTED)], selectbackground=[('readonly', PANEL)], selectforeground=[('readonly', FG)])
        root.option_add('*TCombobox*Listbox.background', PANEL)
        root.option_add('*TCombobox*Listbox.foreground', FG)
        root.option_add('*TCombobox*Listbox.selectBackground', '#304763')
        style.configure('TCheckbutton', background=BG, padding=(0, 5))
        style.configure('TScale', background=ACCENT, troughcolor=PANEL, borderwidth=0, bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL)
        style.configure('TNotebook', background=BG, borderwidth=0, bordercolor=BG, lightcolor=BG, darkcolor=BG)
        style.configure('TNotebook.Tab', padding=(24, 11), borderwidth=0, bordercolor=BG, lightcolor=BG, darkcolor=BG)
        style.map('TNotebook.Tab', background=[('selected', '#24354c'), ('!selected', BG)], foreground=[('selected', FG), ('!selected', MUTED)])
        style.layout('TNotebook.Tab', [])
        style.configure('Nav.TButton', background=BG, foreground=MUTED, padding=(22, 12), font=('Yu Gothic UI', 11))
        style.configure('ActiveNav.TButton', background='#203149', foreground=ACCENT, padding=(22, 12), font=('Yu Gothic UI', 11, 'bold'))
        style.configure('TSpinbox', fieldbackground=PANEL, foreground=FG, background=PANEL, insertcolor=FG)
        style.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor=PANEL, borderwidth=0)
        container = ttk.Frame(root, padding=(28, 20))
        container.pack(fill='both', expand=True)
        header = ttk.Frame(container)
        header.pack(fill='x', pady=(0, 20))
        brand = ttk.Frame(header)
        brand.pack(side='left')
        ttk.Label(brand, text='yuki', font=('Segoe UI', 29, 'bold'), foreground=ACCENT).pack(side='left')
        ttk.Label(brand, text=' / Translator', font=('Segoe UI', 23), foreground=FG).pack(side='left', padx=(3, 0))
        self.language_box = self.choice(header, self.ui_language, list(UI_LANGUAGES), lambda k: UI_LANGUAGES[k], self.change_language, locked=False)
        self.language_box.configure(width=11)
        self.language_box.pack(side='right')
        self.label(header, 'ui_language', foreground=MUTED).pack(side='right', padx=12)
        navigation = ttk.Frame(container)
        navigation.pack(fill='x', pady=(0, 6))
        self.nav_buttons = []
        for index, key in enumerate(('tab_voice', 'tab_subtitles', 'tab_settings')):
            button = self.button(navigation, key, lambda i=index: self.tabs.select(i))
            button.configure(style='Nav.TButton')
            button.pack(side='left', padx=(0, 8))
            self.nav_buttons.append(button)
        self.tabs = ttk.Notebook(container)
        self.tabs.bind('<<NotebookTabChanged>>', self.update_navigation)
        self.tabs.pack(fill='x')
        voice_tab, caption_tab, settings_tab = [ttk.Frame(self.tabs, padding=(18, 20)) for _ in range(3)]
        for tab in (voice_tab, caption_tab, settings_tab):
            self.tabs.add(tab)
        self.label(voice_tab, 'input', foreground=MUTED).pack(anchor='w')
        inputs = ttk.Frame(voice_tab)
        inputs.pack(fill='x', pady=(7, 4))
        self.refresh_button = self.button(inputs, 'refresh', self.refresh)
        self.refresh_button.pack(side='right', padx=(10, 0))
        self.input_box = ttk.Combobox(inputs, state='readonly')
        self.input_box.pack(side='left', fill='x', expand=True)
        self.label(voice_tab, 'capture_hint', foreground=MUTED).pack(anchor='w', pady=(2, 15))
        route = ttk.Frame(voice_tab)
        route.pack(fill='x')
        route.columnconfigure(0, weight=1); route.columnconfigure(2, weight=1)
        self.label(route, 'source', foreground=MUTED).grid(row=0, column=0, sticky='w', pady=(0, 6))
        self.label(route, 'target', foreground=MUTED).grid(row=0, column=2, sticky='w', pady=(0, 6))
        self.source_box = self.choice(route, self.source, ['auto', 'ja', 'ko', 'en'])
        self.source_box.grid(row=1, column=0, sticky='ew')
        ttk.Label(route, text='→', foreground=ACCENT, font=('Segoe UI', 20)).grid(row=1, column=1, padx=22)
        self.target_box = self.choice(route, self.target, ['ja', 'ko', 'en'])
        self.target_box.grid(row=1, column=2, sticky='ew')
        outputs = ttk.Frame(voice_tab)
        outputs.pack(fill='x', pady=(20, 18))
        outputs.columnconfigure((0, 1), weight=1, uniform='output')
        for column, key, hint, variable, command in ((0, 'speak', 'speech_hint', self.speak, self.update_speech), (1, 'subtitles_on', 'subtitle_output_hint', self.subtitle_enabled, self.update_subtitle_output)):
            card = tk.Frame(outputs, bg=PANEL, padx=16, pady=13)
            card.grid(row=0, column=column, sticky='ew', padx=(0, 6) if column==0 else (6, 0))
            Toggle(card, variable, command).pack(side='right', padx=(12, 0))
            self.label(card, key, background=PANEL, font=('Yu Gothic UI', 12, 'bold')).pack(anchor='w')
            self.label(card, hint, background=PANEL, foreground=MUTED, font=('Yu Gothic UI', 9)).pack(anchor='w', pady=(3, 0))
        audio = ttk.Frame(voice_tab)
        audio.pack(fill='x')
        self.label(audio, 'volume', foreground=MUTED).pack(side='left')
        ttk.Scale(audio, from_=0, to=100, variable=self.volume, command=self.update_speech).pack(side='left', fill='x', expand=True, padx=12)
        self.volume_label = ttk.Label(audio, width=5)
        self.volume_label.pack(side='left')
        self.test_button = self.button(audio, 'test_speech', self.test_speech)
        self.test_button.pack(side='right', padx=(12, 0))
        self.controls.append(self.input_box)
        self.input_box.bind('<<ComboboxSelected>>', self.save_soon)

        settings_tab.columnconfigure(1, weight=1)
        def setting(row, key, widget):
            self.label(settings_tab, key, foreground=MUTED).grid(row=row, column=0, sticky='w', padx=(0, 22), pady=7)
            widget.grid(row=row, column=1, sticky='ew', pady=7)
            return widget
        self.model_box = setting(0, 'model', self.choice(settings_tab, self.model, list(ASR_MODELS), lambda k: self.t(ASR_MODELS[k]['label'])))
        self.label(settings_tab, 'model_hint', foreground=MUTED).grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))
        self.backend_box = setting(2, 'backend', self.choice(settings_tab, self.backend, ['local', 'online'], callback=self.update_speech))
        self.output_box = setting(3, 'output', ttk.Combobox(settings_tab, state='readonly'))
        self.controls.append(self.output_box)
        self.output_box.bind('<<ComboboxSelected>>', self.save_soon)
        self.guard_check = self.check(settings_tab, 'guard', self.guard, self.save_soon)
        self.guard_check.grid(row=4, column=0, columnspan=2, sticky='w')
        self.background_check = self.check(settings_tab, 'background_apps', self.background_apps, self.refresh)
        self.background_check.grid(row=5, column=0, columnspan=2, sticky='w')
        self.threshold_scale = setting(6, 'threshold', ttk.Scale(settings_tab, from_=.002, to=.04, variable=self.threshold, command=self.save_soon))
        tools = ttk.Frame(settings_tab)
        tools.grid(row=7, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        self.install_button = self.button(tools, 'install', self.install)
        self.install_button.pack(side='left')
        self.button(tools, 'guide', self.guide).pack(side='left', padx=10)

        self.displays = monitors(root)
        if self.monitor.get() not in [m['id'] for m in self.displays]:
            self.monitor.set(self.displays[0]['id'])
        def display_label(key):
            index, display = next((i, m) for i, m in enumerate(self.displays) if m['id']==key)
            left, top, right, bottom = display['rect']
            return self.t('display_name', number=index+1, width=right-left, height=bottom-top)
        screen_row = ttk.Frame(caption_tab)
        screen_row.pack(fill='x', pady=(0, 10))
        self.label(screen_row, 'monitor', foreground=MUTED).pack(side='left', padx=(0, 12))
        self.choice(screen_row, self.monitor, [m['id'] for m in self.displays], display_label, self.update_overlay, locked=False).pack(side='left', fill='x', expand=True)
        body = ttk.Frame(caption_tab)
        body.pack(fill='x')
        preview_area = ttk.Frame(body)
        preview_area.pack(side='left', fill='both', expand=True, padx=(0, 18))
        self.preview = tk.Canvas(preview_area, height=220, background=BG, highlightthickness=0, cursor='fleur')
        self.preview.pack(fill='both', expand=True)
        self.preview.bind('<Configure>', lambda _: self.draw_preview())
        self.preview.bind('<Button-1>', self.preview_move)
        self.preview.bind('<B1-Motion>', self.preview_move)
        self.label(preview_area, 'preview_hint', foreground=MUTED, font=('Yu Gothic UI', 9)).pack(anchor='w', pady=(7, 0))
        right = ttk.Frame(body, width=275)
        right.pack(side='right', fill='y')
        grid = ttk.Frame(right)
        grid.pack(fill='x', pady=(0, 10))
        for i, (pos, arrow) in enumerate(zip(POSITIONS[:9], ('↖','↑','↗','←','•','→','↙','↓','↘'))):
            button = ttk.Button(grid, text=arrow, width=5, command=lambda p=pos: self.select_position(p))
            button.grid(row=i//3, column=i%3, padx=3, pady=3, sticky='ew')
        self.position_box = self.choice(right, self.position, list(POSITIONS), callback=self.update_overlay, locked=False)
        self.position_box.pack(fill='x')
        self.label(right, 'font_size', foreground=MUTED).pack(anchor='w', pady=(10, 0))
        ttk.Scale(right, from_=16, to=64, variable=self.font_size, command=self.update_overlay).pack(fill='x')
        display_options = ttk.Frame(caption_tab)
        display_options.pack(fill='x', pady=(10, 5))
        self.check(display_options, 'move_subtitles', self.movable, self.update_overlay).pack(side='left')
        self.check(display_options, 'show_original', self.show_original, self.update_overlay).pack(side='left', padx=14)
        ttk.Scale(display_options, from_=.3, to=1, variable=self.opacity, command=self.update_overlay, length=100).pack(side='right')
        self.label(display_options, 'opacity', foreground=MUTED).pack(side='right', padx=8)
        self.label(caption_tab, 'subtitle_hint', foreground=MUTED, wraplength=900, font=('Yu Gothic UI', 9)).pack(anchor='w')

        actions = ttk.Frame(container)
        actions.pack(fill='x', pady=(18, 10))
        self.start_button = self.button(actions, 'start', self.start)
        self.start_button.configure(style='Primary.TButton')
        self.start_button.pack(side='left')
        self.stop_button = self.button(actions, 'stop', self.stop)
        self.stop_button.configure(state='disabled')
        self.stop_button.pack(side='left', padx=10)
        ttk.Progressbar(actions, variable=self.level, maximum=100, length=120).pack(side='right', padx=(10, 0))
        self.label(actions, 'level', foreground=MUTED).pack(side='right')
        ttk.Label(container, textvariable=self.status, foreground=ACCENT).pack(anchor='w', pady=(0, 3))
        ttk.Label(container, textvariable=self.detected, foreground=MUTED).pack(anchor='w')
        ttk.Label(settings_tab, textvariable=self.backend_status, foreground=MUTED, wraplength=840).grid(row=8, column=0, columnspan=2, sticky='w', pady=8)
        ttk.Label(container, textvariable=self.notice, foreground='#f5c78d', wraplength=1000).pack(anchor='w')
        self.label(container, 'recent', foreground=MUTED, font=('Yu Gothic UI', 10, 'bold')).pack(anchor='w', pady=(12, 7))
        self.history = tk.Text(container, bg=PANEL, fg=FG, relief='flat', bd=0, font=('Yu Gothic UI', 12), wrap='word', height=5, padx=18, pady=14, state='disabled', insertbackground=FG)
        self.history.pack(fill='both', expand=True)
        self.history.tag_configure('original', foreground=MUTED, font=('Yu Gothic UI', 10))
        self.history.tag_configure('translated', foreground=FG, font=('Yu Gothic UI', 13))
        self.subtitles = SubtitleOverlay(root, self.overlay_moved)
        self.overlay = self.subtitles.window
        self.change_language()
        self.update_overlay()
        self.update_speech()
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_timer = root.after(100, self.poll)

    def t(self, key, **params):
        return tr(key, self.ui_language.get(), **params)

    def update_navigation(self, *_):
        selected = self.tabs.index(self.tabs.select())
        for index, button in enumerate(self.nav_buttons):
            button.configure(style='ActiveNav.TButton' if index==selected else 'Nav.TButton')

    def label(self, parent, key, **kwargs):
        widget = ttk.Label(parent, **kwargs)
        self.text_widgets.append((widget, key))
        return widget

    def button(self, parent, key, command):
        widget = ttk.Button(parent, command=command)
        self.text_widgets.append((widget, key))
        return widget

    def check(self, parent, key, variable, command):
        widget = ttk.Checkbutton(parent, variable=variable, command=command)
        self.text_widgets.append((widget, key))
        return widget

    def choice(self, parent, variable, keys, label=None, callback=None, locked=True):
        widget = ttk.Combobox(parent, state='readonly')
        formatter = label or self.t
        self.choices.append((widget, variable, keys, formatter))
        if locked:
            self.controls.append(widget)
        def selected(_):
            variable.set(keys[widget.current()])
            if callback:
                callback()
            self.save_soon()
        widget.bind('<<ComboboxSelected>>', selected)
        return widget

    def refresh_choices(self):
        for widget, variable, keys, formatter in self.choices:
            widget['values'] = [formatter(k) for k in keys]
            widget.current(keys.index(variable.get()))

    def change_language(self, *_):
        for widget, key in self.text_widgets:
            widget.configure(text=self.t(key))
        self.tabs.tab(0, text=self.t('tab_voice'))
        self.tabs.tab(1, text=self.t('tab_subtitles'))
        self.tabs.tab(2, text=self.t('tab_settings'))
        self.refresh_choices()
        for key, value in self.last_messages.items():
            getattr(self, key).set(render(value, self.ui_language.get()))
        self.refresh_device_labels()
        if not self.has_caption:
            self.subtitles.set_text(self.t('subtitle_preview'))
        self.draw_preview()
        self.save_soon()

    def set_message(self, key, value):
        self.last_messages[key] = value
        getattr(self, key).set(render(value, self.ui_language.get()))

    def refresh_device_labels(self):
        input_index, output_index = self.input_box.current(), self.output_box.current()
        counts = {}
        for d in self.devices:
            if d.get('kind')=='process':
                counts[d['name']] = counts.get(d['name'], 0)+1
        friendly = {'chrome.exe':'Chrome', 'msedge.exe':'Microsoft Edge', 'firefox.exe':'Firefox', 'discord.exe':'Discord', 'brave.exe':'Brave', 'opera.exe':'Opera'}
        labels = []
        for d in self.devices:
            if d.get('kind')=='process':
                name = friendly.get(d['name'].lower(), d['name'])
                labels.append(self.t('app_missing', name=name) if not d.get('pid') else name + (f" · PID {d['pid']}" if counts[d['name']]>1 else ''))
            else:
                labels.append(f"{self.t('loopback' if d.get('isLoopbackDevice') else 'mic')} | {d['name']}")
        self.input_box['values'] = labels
        self.output_box['values'] = [d[1] for d in self.outputs]
        if input_index >= 0 and input_index < len(self.devices):
            self.input_box.current(input_index)
        if output_index >= 0 and output_index < len(self.outputs):
            self.output_box.current(output_index)

    def refresh(self):
        try:
            self.set_message('notice', '')
            old_input = self.devices[self.input_box.current()]['name'] if self.input_box.current() >= 0 else self.saved.get('input_name')
            old_output = self.outputs[self.output_box.current()][1] if self.output_box.current() >= 0 else self.saved.get('output_name')
            old_pid = self.devices[self.input_box.current()].get('pid') if self.input_box.current() >= 0 else self.saved.get('input_pid')
            processes = application_processes(self.background_apps.get())
            applications = [dict(kind='process', index=None, name=p['name'], pid=p['pid'], created=p['create_time']) for p in processes]
            self.devices = applications + audio_devices()
            matches = [i for i,d in enumerate(self.devices) if d['name']==old_input]
            if old_input and not matches:
                self.devices.insert(0, dict(kind='process', index=None, name=old_input, pid=None, created=None))
            if not self.devices:
                self.devices = [dict(kind='process', index=None, name='App', pid=None, created=None)]
            self.voices, self.outputs = speech_devices()
            self.refresh_device_labels()
            if self.devices:
                self.input_box.current(next((i for i,d in enumerate(self.devices) if d['name']==old_input and d.get('pid')==old_pid), next((i for i,d in enumerate(self.devices) if d['name']==old_input), 0)))
            if self.outputs:
                self.output_box.current(next((i for i,d in enumerate(self.outputs) if d[1] == old_output), 0))
        except Exception as exc:
            self.set_message('notice', message('device_error', detail=exc))

    def update_speech(self, *_):
        previous = self.speaker.backend
        self.speaker.volume = int(float(self.volume.get()))
        self.speaker.enabled = self.speak.get()
        self.speaker.backend = self.backend.get()
        self.volume_label.configure(text=f'{self.speaker.volume}%')
        if not self.speak.get() or previous != self.speaker.backend:
            self.speaker.cancel()
        self.save_soon()

    def test_speech(self):
        if self.output_box.current() < 0:
            self.set_message('notice', message('output_missing'))
            return
        if not self.speak.get() or self.volume.get() <= 0:
            self.set_message('notice', message('speech_disabled'))
            return
        self.speaker.cancel()
        self.set_message('notice', message('speech_test'))
        language = self.target.get()
        self.speaker.say(TEST_PHRASES[language], language, self.outputs[self.output_box.current()][0])

    def update_overlay(self, *_):
        if not hasattr(self, 'subtitles'):
            return
        try:
            dx, dy = self.offset_x.get(), self.offset_y.get()
        except tk.TclError:
            return
        display = next((m for m in self.displays if m['id'] == self.monitor.get()), self.displays[0])
        self.subtitles.configure(rect=display['rect'], font_size=int(self.font_size.get()), position=self.position.get(), dx=dx, dy=dy, custom=self.custom_position, show_original=self.show_original.get(), alpha=self.opacity.get(), movable=self.movable.get())
        if not self.subtitle_enabled.get():
            self.subtitles.hide()
        elif self.movable.get():
            self.subtitles.show()
        self.draw_preview()
        self.save_soon()

    def select_position(self, position):
        self.position.set(position)
        self.offset_x.set(0)
        self.offset_y.set(0)
        self.refresh_choices()
        self.update_overlay()

    def draw_preview(self):
        if not hasattr(self, 'preview') or not hasattr(self, 'subtitles'):
            return
        c = self.preview
        c.delete('all')
        width, height = max(200, c.winfo_width()), max(140, c.winfo_height())
        left, top, right, bottom = self.subtitles.rect
        scale = min((width-24)/(right-left), (height-24)/(bottom-top))
        w, h = (right-left)*scale, (bottom-top)*scale
        x0, y0 = (width-w)/2, (height-h)/2
        self.preview_mapping = (x0, y0, scale, left, top)
        c.create_rectangle(x0,y0,x0+w,y0+h, fill='#121e2c', outline='#354962', width=2)
        for fraction in (1/3, 2/3):
            c.create_line(x0+w*fraction,y0,x0+w*fraction,y0+h, fill='#26374d', dash=(3,5))
            c.create_line(x0,y0+h*fraction,x0+w,y0+h*fraction, fill='#26374d', dash=(3,5))
        from subtitles import placement
        actual_w, actual_h = self.subtitles.window.winfo_width(), self.subtitles.window.winfo_height()
        x,y,_,_ = placement(self.subtitles.rect,actual_w,actual_h,self.position.get(),self.offset_x.get(),self.offset_y.get(),self.custom_position)
        px, py = x0+(x-left)*scale, y0+(y-top)*scale
        pw, ph = actual_w*scale, max(26,actual_h*scale)
        py = max(y0+2, min(py + actual_h*scale/2 - ph/2, y0+h-ph-2))
        c.create_rectangle(px,py,px+pw,py+ph, fill='#203e42', outline=ACCENT, width=2)
        c.create_text(px+pw/2,py+ph/2,text=self.t('preview_sample'),fill=FG,font=('Yu Gothic UI',10,'bold'),width=max(60,pw-12))
        for offset in (0, 4):
            c.create_line(px+7+offset,py+ph/2-4,px+7+offset,py+ph/2+4,fill=ACCENT)
        if not self.subtitle_enabled.get():
            c.create_text(x0+8,y0+8,anchor='nw',text=self.t('subtitle_disabled'),fill=MUTED,font=('Yu Gothic UI',9))

    def preview_move(self, event):
        if not hasattr(self, 'preview_mapping'):
            return
        x0,y0,scale,left,top = self.preview_mapping
        x = left+(event.x-x0)/scale-self.subtitles.window.winfo_width()/2
        y = top+(event.y-y0)/scale-self.subtitles.window.winfo_height()/2
        from subtitles import placement
        x,y,_,_ = placement(self.subtitles.rect,self.subtitles.window.winfo_width(),self.subtitles.window.winfo_height(),'custom',custom=(round(x),round(y)))
        self.custom_position = [x,y]
        self.position.set('custom')
        self.offset_x.set(0)
        self.offset_y.set(0)
        self.refresh_choices()
        self.update_overlay()

    def overlay_moved(self, position):
        self.custom_position = list(position)
        self.position.set('custom')
        self.offset_x.set(0)
        self.offset_y.set(0)
        self.refresh_choices()
        self.draw_preview()
        self.save_soon()

    def show_overlay(self):
        self.update_overlay()
        if self.subtitle_enabled.get():
            self.subtitles.show()

    def update_subtitle_output(self):
        if not self.subtitle_enabled.get():
            self.movable.set(False)
            self.subtitles.hide()
        else:
            self.show_overlay()
        self.draw_preview()
        self.save_soon()

    def lock(self, locked):
        for widget in self.controls:
            widget.configure(state='disabled' if locked else 'readonly')
        for widget in (self.start_button, self.install_button, self.refresh_button, self.threshold_scale, self.guard_check, self.background_check):
            widget.configure(state='disabled' if locked else 'normal')

    def start(self):
        if self.session or self.installing:
            return
        if self.input_box.current() < 0 or (self.speak.get() and self.output_box.current() < 0):
            messagebox.showerror(self.t('error'), self.t('device_required'))
            return
        self.set_message('notice', '')
        selected = self.devices[self.input_box.current()]
        if selected.get('kind')=='process' and not selected.get('pid'):
            self.set_message('notice', message('app_select'))
            return
        config = dict(source=self.source.get(), target=self.target.get(), model=self.model.get(), hardware='cpu', input=selected['index'], input_kind=selected.get('kind', 'device'), process_pid=selected.get('pid'), process_created=selected.get('created'), output=self.outputs[self.output_box.current()][0] if self.output_box.current() >= 0 else None, guard=self.guard.get(), threshold=self.threshold.get())
        self.session = Session(config, self.events, self.speaker)
        self.lock(True)
        self.stop_button.configure(state='normal')
        self.movable.set(False)
        self.show_overlay()
        self.save_settings()
        self.session.thread.start()

    def stop(self):
        if self.session:
            self.session.stop.set()
            self.set_message('status', message('stopping'))
        self.speaker.cancel()
        self.stop_button.configure(state='disabled')

    def install(self):
        self.installing = True
        self.lock(True)
        model = self.model.get()
        def work():
            try:
                from models_setup import install_models
                install_models(lambda msg: self.events.put(('status', msg)), model)
            except Exception as exc:
                self.events.put(('error', message('install_failed', detail=exc)))
            finally:
                self.events.put(('installed', None))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        if self.closed:
            return
        if getattr(self, 'poll_timer', None):
            self.root.after_cancel(self.poll_timer)
            self.poll_timer = None
        for _ in range(100):
            try:
                kind, data = self.events.get_nowait()
            except queue.Empty:
                break
            if kind in ('status', 'language', 'backend'):
                self.set_message({'status':'status', 'language':'detected', 'backend':'backend_status'}[kind], data)
            elif kind == 'level':
                self.level.set(min(100, data * 500))
            elif kind in ('notice', 'error'):
                self.set_message('notice', data)
                if kind == 'error':
                    logging.error(str(data))
            elif kind == 'result':
                original, translated = data
                self.has_caption = True
                self.subtitles.set_text(translated, original)
                self.draw_preview()
                self.history.configure(state='normal')
                self.history.insert('end', f'{datetime.now():%H:%M:%S}  {self.t("original")}: {original}\n', 'original')
                self.history.insert('end', translated + '\n\n', 'translated')
                if int(self.history.index('end-1c').split('.')[0]) > 400:
                    self.history.delete('1.0', '100.0')
                self.history.see('end')
                self.history.configure(state='disabled')
            elif kind == 'stopped':
                self.session = None
                self.speaker.cancel()
                self.lock(False)
                self.stop_button.configure(state='disabled')
                self.set_message('status', message('stopped'))
                self.level.set(0)
            elif kind == 'installed':
                self.installing = False
                self.lock(False)
        self.poll_timer = self.root.after(100, self.poll)

    def guide(self):
        messagebox.showinfo(self.t('guide'), self.t('guide_text'))

    def save_soon(self, *_):
        if not self.persist or self.closed:
            return
        if self.save_timer:
            self.root.after_cancel(self.save_timer)
        self.save_timer = self.root.after(400, self.save_settings)

    def save_settings(self):
        if not self.persist:
            return
        if self.save_timer:
            self.root.after_cancel(self.save_timer)
        self.save_timer = None
        try:
            saved = {key: getattr(self, key).get() for key in ('ui_language', 'source', 'target', 'model', 'hardware', 'backend', 'volume', 'speak', 'guard', 'font_size', 'opacity', 'threshold', 'position', 'monitor', 'offset_x', 'offset_y', 'show_original', 'subtitle_enabled', 'background_apps')}
            saved['custom_position'] = self.custom_position
            saved['schema_version'] = 6
            if self.input_box.current() >= 0:
                saved['input_name'] = self.devices[self.input_box.current()]['name']
                saved['input_pid'] = self.devices[self.input_box.current()].get('pid')
            if self.output_box.current() >= 0:
                saved['output_name'] = self.outputs[self.output_box.current()][1]
            self.settings_path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
        except (OSError, tk.TclError):
            logging.exception('Settings save failed')

    def close(self):
        self.save_settings()
        self.closed = True
        self.stop()
        self.speaker.shutdown.set()
        if self.save_timer:
            self.root.after_cancel(self.save_timer)
        self.root.after_cancel(self.poll_timer)
        self.root.destroy()


def main():
    logging.basicConfig(filename=DATA_DIR / 'app.log', level=logging.WARNING, encoding='utf-8')
    root = tk.Tk()
    app = App(root)
    root.report_callback_exception = lambda t, v, tb: (logging.error('UI error', exc_info=(t, v, tb)), messagebox.showerror(app.t('error'), render(v, app.ui_language.get())))
    root.mainloop()


if __name__ == '__main__':
    main()
