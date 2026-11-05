"""Styled building blocks for the UMBRΛLE overlay: colours, labels, buttons, switches,
sliders, popovers, tooltips, the scrolling list area, and the window tricks an overlay
needs (fades, click-through)."""
import ctypes
import ctypes.wintypes
import tkinter as tk

# UMBRΛLE palette: obsidian base, dark glass panels, arcane violet accents, thin rims.
# Tk can only make a whole window see-through (not single surfaces), so these are the solid
# colours of each surface and the window's opacity setting supplies the glass. The old key
# names stay so every screen keeps its meaning: "gold" is now the light violet highlight
# (quest titles, the chosen tab or sort, a quest ready to turn in).
C = {
    "base": "#09090F", "bg": "#111019", "card": "#18151F", "card_hi": "#201B2D",
    "border": "#322B4B", "border_hi": "#4C4175",
    "header": "#14121E", "header_dark": "#111019",
    "accent": "#8B5CF6", "accent_hi": "#A78BFA", "press": "#3A2D66",
    "text": "#F4F1FA", "muted": "#AAA5BA", "disabled": "#5F5A72",
    "gold": "#CDBDFF", "link": "#B9A2FF", "green": "#86DDAA", "red": "#FF8FA0",
    "button": "#231E33", "button_hi": "#2F2845",
    # text on the title row: all pass 4.5:1 there, also when the window is see-through
    "bar_muted": "#C4BFD2", "bar_green": "#8FE3B3",
}
FONT = "Segoe UI"
# one set of plain, single-colour symbols (colour emoji clashed with the palette)
ICON = {"gps": "➜", "search": "⌕", "here": "◎", "best": "✦", "idea": "✧", "npc": "◦", "shop": "◇"}
BRAND_FONT = "Bahnschrift SemiBold"   # geometric, for the UMBRΛLE wordmark (falls back to Segoe UI)


TEXT_SCALES = (1.0, 1.15, 1.3)   # the text size setting cycles through these
text_scale = 1.0                 # current one; applies to widgets created after it changes

# hover / pressed colours for each background a button can sit on
HOVER = {"button": "button_hi", "header": "button", "header_dark": "button", "bg": "card_hi",
         "card": "card_hi", "card_hi": "button_hi", "base": "card_hi"}


def font_size(size):
    return max(6, round(size * text_scale))


def px(widget, n):
    """`n` screen pixels at 96 dpi. The app pins Tk to 96 dpi (it ignores Windows scaling), so
    this is n, but sizes still follow Tk's scaling if that ever changes."""
    return round(n * widget.winfo_fpixels("1i") / 96)


def label(parent, text="", fg="text", bg="bg", size=9, bold=False, **kw):
    return tk.Label(parent, text=text, fg=C.get(fg, fg), bg=C.get(bg, bg),
                    font=(FONT, font_size(size), "bold" if bold else "normal"), **kw)


def work_area(x, y):
    """(left, top, right, bottom) of the screen area (minus the taskbar) of the monitor nearest
    to the screen point (x, y). Other monitors can be at negative positions."""
    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.wintypes.DWORD), ("rcMonitor", ctypes.wintypes.RECT),
                    ("rcWork", ctypes.wintypes.RECT), ("dwFlags", ctypes.wintypes.DWORD)]
    user32 = ctypes.windll.user32
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    monitor = user32.MonitorFromPoint(ctypes.wintypes.POINT(int(x), int(y)), 2)  # 2 = nearest
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    r = info.rcWork
    return r.left, r.top, r.right, r.bottom


def on_a_screen(x, y):
    """Whether the screen point (x, y) is on any monitor."""
    return ctypes.windll.user32.MonitorFromPoint(ctypes.wintypes.POINT(int(x), int(y)), 0) != 0


def on_monitor_of(widget, x, y, width, height):
    """(x, y) moved just enough that a width x height window fits on the monitor `widget` is on."""
    left, top, right, bottom = work_area(widget.winfo_rootx() + widget.winfo_width() // 2, widget.winfo_rooty())
    return max(left, min(x, right - width)), max(top, min(y, bottom - height))


def reduced_motion():
    """Windows' "Show animations in Windows" setting is off: no fades."""
    on = ctypes.c_bool(True)
    try:
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0)  # SPI_GETCLIENTAREAANIMATION
    except (AttributeError, OSError):
        return False
    return not on.value


def hwnd_of(win):
    return ctypes.windll.user32.GetAncestor(win.winfo_id(), 2)  # GA_ROOT: the real top-level window


def fade(win, target, ms=150, done=None):
    """Change a window's opacity to `target` over `ms` (at once with reduced motion on)."""
    job = getattr(win, "_fade_job", None)
    if job:
        win.after_cancel(job)
        win._fade_job = None
    start = float(win.attributes("-alpha"))
    steps = 1 if reduced_motion() or abs(start - target) < 0.02 else 5

    def step(i):
        win.attributes("-alpha", start + (target - start) * i / steps)
        if i < steps:
            win._fade_job = win.after(ms // steps, step, i + 1)
        else:
            win._fade_job = None
            if done:
                done()
    step(1)


class Tooltip:
    """Readable hints shared by new controls and original engine widgets."""
    def __init__(self, widget, text):
        self.widget, self.text, self.win, self.job = widget, text, None, None
        widget._companion_tooltip = self
        for event in ('<Enter>', '<FocusIn>'):
            widget.bind(event, self._schedule, add='+')
        for event in ('<Leave>', '<FocusOut>', '<Button-1>'):
            widget.bind(event, self._hide, add='+')
        widget.bind('<Destroy>', self._destroyed, add='+')

    def _destroyed(self, event):
        if event.widget == self.widget:
            self._hide()

    def _schedule(self, event=None):
        self._hide()
        self.job = self.widget.after(350, self._show)

    def _show(self):
        self.job = None
        if not self.widget.winfo_exists() or self.win:
            return
        self.win = tk.Toplevel(self.widget)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        tk.Label(self.win, text=self.text, bg=C['tip_bg'], fg=C['tip_text'],
                 font=(FONT, font_size(10)), padx=10, pady=6, wraplength=320,
                 justify='left', highlightthickness=1,
                 highlightbackground='#596579').pack()
        self.win.update_idletasks()
        width, height = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        left, top, right, bottom = work_area(self.widget.winfo_rootx(), self.widget.winfo_rooty())
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2 - width // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        if y + height > bottom - 6:
            y = self.widget.winfo_rooty() - height - 6
        x, y = max(left+6, min(x, right-width-6)), max(top+6, y)
        self.win.geometry(f'{x:+d}{y:+d}')
        self.win.deiconify()

    def _hide(self, event=None):
        if self.job:
            try:
                self.widget.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        win, self.win = self.win, None
        if win:
            try:
                win.destroy()
            except tk.TclError:
                pass


def button(parent, text, command, bg="button", fg="text", size=9, padx=6, tip=None, **kw):
    """A flat text button: lighter while hovered, darker violet while pressed, a violet ring
    while it has the keyboard focus (Tab), and Enter or Space press it."""
    b = label(parent, text, fg=fg, bg=bg, size=size, padx=padx, pady=0, cursor="hand2", takefocus=1,
              highlightthickness=1, highlightbackground=C.get(bg, bg), highlightcolor=C["accent_hi"], **kw)
    b.fg, b.bg, b.disabled = C.get(fg, fg), C.get(bg, bg), False
    hover = C[HOVER[bg]] if bg in HOVER else b.bg

    def press(_=None):
        if not b.disabled:
            b.config(bg=C["press"])
            command()
        return "break"
    b.bind("<Button-1>", press)
    b.bind("<ButtonRelease-1>", lambda e: b.winfo_exists() and b.config(bg=hover if not b.disabled else b.bg))
    b.bind("<Return>", press)
    b.bind("<space>", press)
    b.bind("<Enter>", lambda e: b.disabled or b.config(bg=hover), add="+")
    b.bind("<Leave>", lambda e: b.config(bg=b.bg), add="+")
    if tip:
        Tooltip(b, tip)
    return b


def set_enabled(b, enabled):
    """Grey a button() or menu_item() out (it ignores clicks), or bring it back."""
    b.disabled = not enabled
    for part in getattr(b, "parts", [b]):
        if isinstance(part, tk.Label):
            part.config(fg=getattr(part, "fg", C["text"]) if enabled else C["disabled"],
                        cursor="hand2" if enabled else "")
    b.config(takefocus=1 if enabled else 0)


def menu_item(parent, text, command, hint="", bg="header"):
    """A full-width menu row: the action on the left, its shortcut (muted) on the right; the
    whole row lights up on hover and can be focused with Tab and pressed with Enter or Space."""
    row = tk.Frame(parent, bg=C[bg], cursor="hand2", takefocus=1, highlightthickness=1,
                   highlightbackground=C[bg], highlightcolor=C["accent_hi"])
    main = label(row, text, bg=bg, size=9, anchor="w", padx=px(row, 9), pady=px(row, 3), cursor="hand2")
    main.pack(side="left", fill="x", expand=True)
    tip = label(row, hint, fg="muted", bg=bg, size=7, padx=px(row, 10), cursor="hand2")
    tip.pack(side="right")
    main.fg, tip.fg = C["text"], C["muted"]
    row.parts, row.disabled = (row, main, tip), False

    def paint(colour):
        for part in row.parts:
            part.config(bg=colour)

    def press(_=None):
        if not row.disabled:
            paint(C["press"])
            command()
        return "break"
    for part in row.parts:
        part.bind("<Button-1>", press)
        part.bind("<Enter>", lambda e: row.disabled or paint(C["card_hi"]))
        part.bind("<Leave>", lambda e: row.winfo_exists() and paint(C[bg]))
    row.bind("<Return>", press)
    row.bind("<space>", press)
    return row


def entry(parent, textvariable, width=None, size=9, **kw):
    """A text box: elevated surface, thin rim that turns violet while you type in it."""
    return tk.Entry(parent, textvariable=textvariable, width=width, bg=C["card_hi"], fg=C["text"],
                    insertbackground=C["text"], relief="flat", font=(FONT, font_size(size)), highlightthickness=1,
                    highlightbackground=C["border"], highlightcolor=C["accent_hi"],
                    selectbackground=C["accent"], selectforeground=C["text"], **kw)


def link(parent, text, command, bg="card", fg="link", size=9, **kw):
    """Clickable text: plain colour, underlined only while hovered (less visual noise)."""
    l = label(parent, text, fg=fg, bg=bg, size=size, cursor="hand2", **kw)
    l.bind("<Button-1>", lambda e: command())
    l.bind("<Enter>", lambda e: l.config(font=(FONT, font_size(size), "underline")))
    l.bind("<Leave>", lambda e: l.config(font=(FONT, font_size(size), "normal")))
    return l


class Switch(tk.Canvas):
    """A small on/off switch: violet track when on. Click it, or focus it (Tab) and press Space."""

    def __init__(self, parent, value, command, bg="bg", enabled=True):
        self.w, self.h = px(parent, 26), px(parent, 14)
        super().__init__(parent, width=self.w, height=self.h, bg=C.get(bg, bg), highlightthickness=1,
                         highlightbackground=C.get(bg, bg), highlightcolor=C["accent_hi"], bd=0,
                         cursor="hand2" if enabled else "", takefocus=int(enabled))
        self.value, self.command, self.hover, self.enabled = bool(value), command, False, enabled
        self.bind("<Button-1>", self.toggle)
        self.bind("<space>", self.toggle)
        self.bind("<Return>", self.toggle)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._draw()

    def _set_hover(self, on):
        self.hover = on and self.enabled
        self._draw()

    def set(self, value):
        self.value = bool(value)
        self._draw()

    def toggle(self, _=None):
        if self.enabled:
            self.value = not self.value
            self._draw()
            self.command(self.value)
        return "break"

    def _draw(self):
        self.delete("all")
        w, h, r = self.w, self.h, self.h / 2
        track = (C["card_hi"] if not self.enabled else C["accent"] if self.value
                 else C["border_hi"] if self.hover else C["border"])
        self.create_oval(0, 0, h, h, fill=track, outline="")
        self.create_oval(w - h, 0, w, h, fill=track, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=track, outline="")
        k = 2
        x = w - h + k if self.value else k
        self.create_oval(x, k, x + h - 2 * k, h - k, fill=C["text"] if self.enabled else C["disabled"], outline="")


class Bar(tk.Canvas):
    """A thin progress bar (0..1): violet on a dim track, green once done."""

    def __init__(self, parent, share=0.0, bg="bg", done=False, height=3):
        super().__init__(parent, width=1, height=px(parent, height), bg=C.get(bg, bg), highlightthickness=0, bd=0)
        self.share, self.done = share, done
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, share, done=False):
        if (share, done) != (self.share, self.done):
            self.share, self.done = share, done
            self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_rectangle(0, 0, w, h, fill=C["border"], outline="")
        if self.share > 0:
            self.create_rectangle(0, 0, round(w * min(1.0, self.share)), h, outline="",
                                  fill=C["green"] if self.done else C["accent"])


class Slider(tk.Canvas):
    """A thin horizontal slider (low..high): drag or click it, the mouse wheel and the arrow
    keys move it in `step`s. `command(value)` runs as it moves."""

    def __init__(self, parent, low, high, value, command, step=0.05, width=140, bg="bg"):
        self.w, self.h = px(parent, width), px(parent, 16)
        super().__init__(parent, width=self.w, height=self.h, bg=C.get(bg, bg), highlightthickness=1,
                         highlightbackground=C.get(bg, bg), highlightcolor=C["accent_hi"], bd=0,
                         cursor="hand2", takefocus=1)
        self.low, self.high, self.step, self.command = low, high, step, command
        self.value = value
        self.bind("<Button-1>", self._at)
        self.bind("<B1-Motion>", self._at)
        self.bind("<MouseWheel>", lambda e: self._nudge(1 if e.delta > 0 else -1))
        self.bind("<Right>", lambda e: self._nudge(1))
        self.bind("<Left>", lambda e: self._nudge(-1))
        self._draw()

    def _set(self, value):
        value = round(min(self.high, max(self.low, value)) / self.step) * self.step
        if abs(value - self.value) > 1e-9:
            self.value = value
            self._draw()
            self.command(value)

    def _at(self, e):
        k = self.h / 2
        self._set(self.low + (e.x - k) / max(1, self.w - 2 * k) * (self.high - self.low))

    def _nudge(self, direction):
        self._set(self.value + direction * self.step)
        return "break"

    def _draw(self):
        self.delete("all")
        k, mid = self.h / 2, self.h / 2
        x = k + (self.value - self.low) / (self.high - self.low) * (self.w - 2 * k)
        t = max(2, self.h // 6)
        self.create_rectangle(k, mid - t / 2, self.w - k, mid + t / 2, fill=C["border"], outline="")
        self.create_rectangle(k, mid - t / 2, x, mid + t / 2, fill=C["accent"], outline="")
        r = self.h * 0.32
        self.create_oval(x - r, mid - r, x + r, mid + r, fill=C["text"], outline=C["accent_hi"])


class Popover(tk.Toplevel):
    """A small floating panel (settings, search) in the overlay's style: a thin rim, opens next
    to `anchor`, closes on Esc or when you click somewhere else."""

    def __init__(self, anchor, on_close=None):
        super().__init__(anchor, bg=C["border"])
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.withdraw()  # placed once its size is known, so it never shows up somewhere else first
        self.anchor, self.on_close = anchor, on_close
        self.body = tk.Frame(self, bg=C["header"])
        self.body.pack(fill="both", expand=True, padx=1, pady=1)
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<FocusOut>", lambda e: self.after(80, self._closed_elsewhere))

    def show(self):
        """Place it under the anchor (right edges lined up), kept on the anchor's monitor."""
        self.update_idletasks()
        a, w, h = self.anchor, self.winfo_reqwidth(), self.winfo_reqheight()
        x, y = a.winfo_rootx() + a.winfo_width() - w, a.winfo_rooty() + a.winfo_height() + 4
        left, top, right, bottom = work_area(a.winfo_rootx(), a.winfo_rooty())
        if y + h > bottom:  # no room below: open above the anchor instead
            y = a.winfo_rooty() - h - 4
        self.geometry(f"+{max(left, min(x, right - w))}+{max(top, min(y, bottom - h))}")
        self.deiconify()
        self.after(30, self.focus_force)

    def _closed_elsewhere(self):
        if not self.winfo_exists():
            return
        try:
            focus = self.focus_get()
        except (KeyError, tk.TclError):
            focus = None
        if focus is None or not str(focus).startswith(str(self)):
            self.close()

    def close(self):
        if self.winfo_exists():
            self.destroy()
            if self.on_close:
                self.on_close()


class frozen:
    """`with frozen(area): ...` holds back painting of one inner area (not the whole window:
    on the see-through top window that left it stale) while its content changes, lays the
    result out, then paints it all at once. Without it Windows paints every piece as it
    changes, which shows up as several half-updated frames: the flicker."""
    WM_SETREDRAW = 0x000B
    RDW_FLAGS = 0x0001 | 0x0004 | 0x0080 | 0x0100  # invalidate, erase, all children, update now

    def __init__(self, area):
        self.area = area

    def __enter__(self):
        self.user32 = ctypes.windll.user32
        self.hwnd = self.area.winfo_id()
        self.user32.SendMessageW(self.hwnd, self.WM_SETREDRAW, 0, 0)
        return self

    def __exit__(self, *exc):
        try:
            self.area.update_idletasks()  # finish the layout while nothing is painted
        finally:
            self.user32.SendMessageW(self.hwnd, self.WM_SETREDRAW, 1, 0)
            self.user32.RedrawWindow(self.hwnd, None, None, self.RDW_FLAGS)
            # Tk answers Windows' paint requests at its next idle moment, not right away;
            # run that drawing now so nothing old is left on screen in between
            self.area.update_idletasks()
        return False


class SlimScrollbar(tk.Canvas):
    """A thin scrollbar in the window's colours (the Windows one is a white and grey slab):
    a rounded thumb that can be dragged, clicking the track pages, and it hides itself
    when everything fits."""
    WIDTH = 8

    def __init__(self, parent, command):
        super().__init__(parent, width=self.WIDTH, bg=C["bg"], highlightthickness=0, bd=0)
        self.command, self.first, self.last = command, 0.0, 1.0
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Enter>", lambda e: self._draw(hover=True))
        self.bind("<Leave>", lambda e: self._draw())

    def set(self, first, last):  # called by the canvas as it scrolls
        self.first, self.last = float(first), float(last)
        self._draw()

    def _draw(self, hover=False):
        self.delete("all")
        if self.first <= 0 and self.last >= 1:
            return  # nothing to scroll: no bar at all
        h = self.winfo_height()
        top, bottom = self.first * h, max(self.first * h + 18, self.last * h)
        x0, x1 = 2, self.WIDTH - 1
        colour = C["accent"] if hover else C["border_hi"]
        r = (x1 - x0) / 2
        self.create_oval(x0, top, x1, top + 2 * r, fill=colour, outline="")
        self.create_oval(x0, bottom - 2 * r, x1, bottom, fill=colour, outline="")
        self.create_rectangle(x0, top + r, x1, bottom - r, fill=colour, outline="")

    def _press(self, e):
        h = max(1, self.winfo_height())
        if self.first * h <= e.y <= self.last * h:
            self._grab = e.y / h - self.first  # grabbed the thumb: drag it
        else:
            self._grab = None
            self.command("scroll", -1 if e.y < self.first * h else 1, "pages")

    def _drag(self, e):
        if getattr(self, "_grab", None) is not None:
            self.command("moveto", e.y / max(1, self.winfo_height()) - self._grab)


class ScrollArea(tk.Frame):
    """Vertical scrolling frame with mouse-wheel support."""

    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        self.canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0, bd=0)
        self.bar = SlimScrollbar(self, command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=C["bg"])
        self._restore_y, self._restore_job, self._old = None, None, None
        self.inner.bind("<Configure>", self._on_inner_resize)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y")  # packed first so the list can't squeeze it to nothing
        self.canvas.pack(side="left", fill="both", expand=True)
        self._wheel_registration=self.bind_all("<MouseWheel>", self._wheel, add="+")
        self.bind("<Destroy>",self._cleanup_scroll,add="+")

    def _cleanup_scroll(self,event):
        if event.widget != self:return
        if self._restore_job:
            try:self.after_cancel(self._restore_job)
            except tk.TclError:pass
        try:self._root()._unbind(('bind','all','<MouseWheel>'),self._wheel_registration)
        except tk.TclError:pass

    def _wheel(self, event):
        if str(event.widget).startswith(str(self)):
            self.canvas.yview_scroll(int(-event.delta / 120) * 2, "units")

    def clear(self, keep_position=True):
        """Start a redraw: new content goes into a fresh frame, built off-screen, which
        `commit()` swaps in at once, so frequent updates don't flicker. By default the view
        stays where it was scrolled to."""
        # remember the scroll position in pixels: as a fraction it would jump whenever the new
        # content is taller or shorter than the old
        height = max(1, self.inner.winfo_height())
        self._restore_y = self.canvas.yview()[0] * height if keep_position else 0
        self._old = self.inner
        self.inner = tk.Frame(self.canvas, bg=C["bg"])
        self.inner.bind("<Configure>", self._on_inner_resize)

    def commit(self):
        self.inner.update_idletasks()  # lay the new content out before it becomes visible
        self.canvas.itemconfigure(self._win, window=self.inner)
        if self._old is not None:
            self._old.destroy()
            self._old = None
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._apply_restore()
        # the new content may still change size for a moment; keep re-applying the old
        # position as its size changes, then stop so the user can scroll freely again
        if self._restore_job:
            self.after_cancel(self._restore_job)
        self._restore_job = self.after(600, self._stop_restoring)

    def _stop_restoring(self):
        self._restore_y, self._restore_job = None, None

    def _on_inner_resize(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._apply_restore()

    def _apply_restore(self):
        if self._restore_y is None:
            return
        target = self._restore_y / max(1, self.inner.winfo_reqheight())
        if abs(self.canvas.yview()[0] - target) > 0.001:  # only move when actually off
            self.canvas.yview_moveto(target)
