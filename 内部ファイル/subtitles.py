"""Borderless, color-keyed Windows movie subtitles with persistent positioning."""
import tkinter as tk

TRANSPARENT = '#010203'
POSITIONS = ('top_left', 'top_center', 'top_right', 'center_left', 'center_center',
             'center_right', 'bottom_left', 'bottom_center', 'bottom_right', 'custom')


def monitors(root):
    import win32api
    displays = []
    for handle, _, _ in win32api.EnumDisplayMonitors():
        info = win32api.GetMonitorInfo(handle)
        rect = info['Work']
        displays.append({'id': info['Device'], 'rect': rect, 'primary': bool(info['Flags'] & 1)})
    displays.sort(key=lambda m: not m['primary'])
    return displays or [{'id': 'primary', 'rect': (0, 0, root.winfo_screenwidth(), root.winfo_screenheight()), 'primary': True}]


def placement(rect, width, height, position, dx=0, dy=0, custom=None):
    left, top, right, bottom = rect
    width, height = min(width, right-left), min(height, bottom-top)
    if position == 'custom' and custom is not None:
        x, y = custom[0] + dx, custom[1] + dy
    else:
        vertical, horizontal = (position if position in POSITIONS and position != 'custom' else 'bottom_center').split('_')
        x = {'left': left+24, 'center': left+(right-left-width)//2, 'right': right-width-24}[horizontal] + dx
        y = {'top': top+24, 'center': top+(bottom-top-height)//2, 'bottom': bottom-height-48}[vertical] + dy
    return max(left, min(x, right-width)), max(top, min(y, bottom-height)), width, height


class SubtitleOverlay:
    def __init__(self, root, on_move):
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT)
        self.window.attributes('-transparentcolor', TRANSPARENT)
        self.window.attributes('-topmost', True)
        self.canvas = tk.Canvas(self.window, bg=TRANSPARENT, highlightthickness=0, bd=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag_move)
        self.canvas.bind('<ButtonRelease-1>', self.drag_end)
        self.on_move = on_move
        self.movable = False
        self.text = ''
        self.original = ''
        self.custom = None
        self.rect = (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
        self.font_size = 30
        self.position = 'bottom_center'
        self.dx = self.dy = 0
        self.show_original = False
        self.alpha = 1.0
        self._drag = None
        self.style_job = None
        self.window.bind('<Destroy>', self.on_destroy)

    def configure(self, *, rect, font_size, position, dx, dy, custom, show_original, alpha, movable):
        self.rect, self.font_size, self.position = rect, font_size, position
        self.dx, self.dy, self.custom = dx, dy, custom
        self.show_original, self.alpha, self.movable = show_original, alpha, movable
        self.window.attributes('-alpha', alpha)
        self.redraw()
        if self.style_job:
            self.window.after_cancel(self.style_job)
        self.style_job = self.window.after_idle(self.apply_style)

    def on_destroy(self, event):
        if event.widget == self.window and self.style_job:
            self.window.after_cancel(self.style_job)
            self.style_job = None

    def apply_style(self):
        if self.style_job:
            self.window.after_cancel(self.style_job)
            self.style_job = None
        import win32gui, win32con
        if not self.window.winfo_exists():
            return
        hwnd = win32gui.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
        if self.movable:
            style &= ~win32con.WS_EX_TRANSPARENT
        else:
            style |= win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

    def set_text(self, text, original=''):
        self.text, self.original = text, original
        self.redraw()

    def redraw(self):
        self.canvas.delete('all')
        width = min(1100, max(300, int((self.rect[2]-self.rect[0]) * .80)))
        horizontal = self.position.split('_')[-1]
        anchor = 'nw' if horizontal == 'left' else 'ne' if horizontal == 'right' else 'n'
        justify = 'left' if anchor == 'nw' else 'right' if anchor == 'ne' else 'center'
        x = 8 if anchor == 'nw' else width-8 if anchor == 'ne' else width//2
        font = ('Yu Gothic UI', self.font_size, 'bold')

        def outlined(text, y, font, color, tag):
            options = dict(text=text, font=font, anchor=anchor, justify=justify, width=width-24)
            stroke = max(1, round(self.font_size / 16))
            for ox, oy in ((-stroke,-stroke),(0,-stroke),(stroke,-stroke),(-stroke,0),(stroke,0),(-stroke,stroke),(0,stroke),(stroke,stroke)):
                self.canvas.create_text(x+ox, y+oy, fill='#000000', **options)
            return self.canvas.create_text(x, y, fill=color, tags=tag, **options)

        main = outlined(self.text, 5, font, '#ffffff', 'translation')
        height = self.canvas.bbox(main)[3] + 10
        if self.show_original and self.original:
            source = outlined(self.original, height, ('Yu Gothic UI', max(12, self.font_size//2)), '#dddddd', 'original')
            height = self.canvas.bbox(source)[3] + 10
        height = min(max(48, height), self.rect[3]-self.rect[1])
        if self.movable:
            frame = self.canvas.create_rectangle(1, 1, width-2, height-2,
                                                  fill='#162537', outline='#73ebc4', width=2)
            self.canvas.tag_lower(frame)
        x, y, width, height = placement(self.rect, width, height, self.position, self.dx, self.dy, self.custom)
        self.window.geometry(f'{width}x{height}')
        self.window.update_idletasks()
        # Native positioning supports displays to the left/above the primary display.
        import win32gui, win32con
        hwnd = win32gui.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, x, y, width, height, win32con.SWP_NOACTIVATE)

    def show(self):
        self.window.deiconify()
        self.redraw()
        self.apply_style()

    def hide(self):
        self.window.withdraw()

    def drag_start(self, event):
        if self.movable:
            self._drag = (event.x_root-self.window.winfo_x(), event.y_root-self.window.winfo_y())

    def drag_move(self, event):
        if self.movable and self._drag:
            self.position = 'custom'
            self.custom = (event.x_root-self._drag[0], event.y_root-self._drag[1])
            self.redraw()

    def drag_end(self, _):
        if self._drag:
            self._drag = None
            self.custom = (self.window.winfo_x(), self.window.winfo_y())
            self.on_move(self.custom)
