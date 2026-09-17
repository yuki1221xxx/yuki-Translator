"""Small native Tk controls styled for the translator dashboard."""
import tkinter as tk


class Toggle(tk.Frame):
    def __init__(self, parent, variable, command, bg='#17202e'):
        super().__init__(parent, bg=bg)
        self.variable, self.command, self.bg = variable, command, bg
        self.canvas = tk.Canvas(self, width=54, height=30, bg=bg, bd=0, highlightthickness=0, cursor='hand2', takefocus=True)
        self.canvas.pack()
        self.canvas.bind('<Button-1>', self.toggle)
        self.canvas.bind('<space>', self.toggle)
        self.canvas.bind('<Return>', self.toggle)
        self.canvas.bind('<FocusIn>', lambda _: self.draw())
        self.canvas.bind('<FocusOut>', lambda _: self.draw())
        self.variable.trace_add('write', lambda *_: self.draw())
        self.draw()

    def toggle(self, _=None):
        self.variable.set(not self.variable.get())
        self.command()

    def draw(self):
        c = self.canvas
        c.delete('all')
        enabled = self.variable.get()
        color = '#73ebc4' if enabled else '#435169'
        c.create_oval(3, 4, 25, 26, fill=color, outline='')
        c.create_rectangle(14, 4, 39, 26, fill=color, outline='')
        c.create_oval(28, 4, 50, 26, fill=color, outline='')
        x = 31 if enabled else 6
        c.create_oval(x, 7, x+16, 23, fill='#10202a' if enabled else '#e2e8f2', outline='')
        if c.focus_get() == c:
            c.create_rectangle(1, 1, 52, 28, outline='#e2e8f2', dash=(2, 2))
