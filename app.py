"""UMBRΛLE: a compact always-on-top overlay that floats above
MapleStory Classic and guides you through your quests, monsters, items, training maps and
party quests. It collapses to a small title row and expands into a floating panel.

Game integration is read-only screen capture + OCR (like a screenshot tool): it never
reads the game's memory and never sends the game any input."""
import ctypes
import ctypes.wintypes
import json
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from difflib import SequenceMatcher
from tkinter import messagebox

from PIL import Image, ImageTk

import gps_image
import leveling
import party_quests
import quest_rank
import trainer
import widgets
import item_sources
from companion_portraits import portrait
from game_sync import MINIMAP_CORNER, HotkeyThread, capture_and_read, find_game_window, window_rect
from minimap import portal_direction, portal_side, render_minimap
from widgets import BRAND_FONT, C, FONT, ICON, TEXT_SCALES, ScrollArea, Tooltip, button, entry, frozen, label, link
from meowdb import APP_DIR, BASE, CACHE_DIR, MeowDB, write_atomic

VERSION = "2.0.0"
# bundled files (the icon) sit in PyInstaller's unpack folder when packaged
BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(APP_DIR, "state.json")
SHOW_REQUEST = os.path.join(APP_DIR, "show.request")  # left by a second launch: "show yourself"
GUIDES_FILE = os.path.join(CACHE_DIR, "guides.json")
GUIDES_VERSION = 4     # includes shops and breakable acquisition sources per objective
MAX_MAPS = 3          # map suggestions shown per objective
KEEP_MAPS = 8         # maps saved per objective, so enough stay after unreachable ones are left out
MAX_DROPPERS = 2      # monsters shown per item
TRAINING_MAPS = 15    # maps listed on the Training tab
EXP_BAR_EVERY = 3         # auto syncs per EXP bar read (each ~0.5 s of OCR in the background)
GPS_STRIP = (300, 50)     # the GPS strip's picture, at 100% screen scaling (it scales with it)
GPS_DETAILS_HEIGHT = 230  # px for the opened GPS's map (the tallest minimap is 200)
GPS_SIZES = (0.72, 1.0, 1.3)  # the GPS size setting (⤢): small, the default, then medium and large
SUGGESTIONS = 5       # quests offered under "Quests you could take now"
GONE_AFTER = 5        # syncs in a row a LIVE quest must be missing before we act (~10 s)
AUTOSAVE_MS = 30000     # save the list this often when it changed
STARTUP_SOLID_MS = 4000  # stay solid this long after opening, so the window is easy to see
RESET_SCAN_MS = 1500   # how often Reset looks at the Quest window
RESET_TIMEOUT_S = 60   # give up if the Quest window never shows up
AUTO_SYNC_MS = 2000    # auto sync re-reads only the quest helper + map name areas, so it stays light
TOPMOST_MS = 3000     # re-assert always-on-top this often (games like to steal it)
HOTKEY_TEXT = "Ctrl+Shift+S"
EDGE = 4              # px of the expanded panel's edge you can drag to resize it
MIN_W, MIN_H = 300, 160
PANEL_SIZE = (320, 0.55)  # expanded panel: width at 100% scaling, most height as a share of the screen
MIN_PANEL_H = 320         # px (at 100%): the panel shrinks to its content, but not below this
AUTO_COLLAPSE_S = 1.5     # back in the game for this long (mouse off the panel): it folds up
PILL_STATUS_CHARS = 26    # the title row's status line; its width sets the collapsed overlay's width
FLASH_MS = 4000           # how long a message replaces the status line while collapsed
TABS = (("quests", "Quests"), ("mobs", "Mobs"), ("items", "Items"), ("train", "Training"), ("pq", "PQ"))
DEFAULT_STATE = {"level": 1, "active": [], "tracked": [], "done": {}, "progress": {}, "completed": [],
                 "map": None, "auto_sync": True, "geometry": "372x560+60+60",
                 "expanded": None, "tab": "quests", "idle_alpha": 0.88, "auto_collapse": False}
OPACITY_STEPS = (0.45, 0.55, 0.65, 0.75, 0.85, 1.0)  # see-through levels while not hovered
GPS_ALPHA = 0.96      # the GPS window's default see-through level (its ◐ changes it)
HOVER_ALPHA = 0.97    # nearly solid while the mouse is over the window, so it's easy to read


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def npc_map(db, name):
    npc = db.npc(name)
    return npc["maps"][0] if npc and npc.get("maps") else None


def sigil_image(size):
    """The UMBRΛLE sigil, `size` px square on a transparent background (made by make_icon.py)."""
    try:
        img = Image.open(os.path.join(BUNDLE_DIR, "assets", "sigil.png")).resize((size, size), Image.LANCZOS)
    except OSError:
        img = Image.new("RGBA", (size, size))
    return ImageTk.PhotoImage(img)


class App:
    def __init__(self, root):
        self.root = root
        self.db = MeowDB()
        self.state = {**DEFAULT_STATE, **load_json(STATE_FILE, {})}
        if not self.state.get("auto_on_v2"):
            # AUTO used to start off, so location, routes and counts silently stopped updating;
            # switch it on once for existing users (they can still turn it off)
            self.state["auto_sync"] = self.state["auto_on_v2"] = True
        saved = load_json(GUIDES_FILE, {})
        self.guides = saved.get("guides", {}) if saved.get("v") == GUIDES_VERSION else {}
        self.pending = set()      # quest ids being resolved right now
        self.previews = {}        # card key -> (map_id, mob_id, npc_name, exit_portal) on its minimap
        self.routes = {}          # card key -> (goal map, mob_id, npc_name) being navigated to
        self._dist = (None, {})   # (from map, portals-away for every map)
        self._dist_from = {}      # (map, taxis) -> portals-away from that map, for quest estimates
        self._rank_tried = set()  # suggested quests whose guide was already looked up for ranking
        self._done_cache = (None, set())  # (list + completed, quests known to be done)
        self.mob_drops = {}       # monster id -> item names it drops
        self.hints = {}           # quest id -> what its NPC says on accepting (None: none / failed)
        self.all_maps = {}        # quest id -> showing every objective's map list
        self.full_routes = set()  # card keys whose route shows every step
        self.gps, self.gps_key = None, None  # the GPS window and which route it shows
        self.item_results = {}    # search text -> matching items (None while searching)
        self.item_drops = {}      # item page id -> monsters dropping it, with rates
        self.pq_tried = set()     # (pq, stage, combination) crossed off as tried, this run only
        self.images = {}          # keeps PhotoImages alive
        self.syncing = False
        self.focus = None         # screen areas to re-read on quick auto syncs
        self.resetting = None     # progress of a "Reset from Quest window" read, while it runs
        self._reads = {}          # last raw reading per quest/objective/map (see _confirmed)
        self._gone = {}           # LIVE quest id -> syncs in a row it was missing (see _check_gone)
        self.objective_labels = {}  # (quest id, objective index) -> its "have / need" label
        self.quest_bars = {}        # quest id -> its card's progress bar
        self._notice_low = {}       # (quest id, objective) -> a lower count read once (see _on_synced)
        self.trainer = trainer.Trainer()  # the next step when ▶ Trainer is on
        self._trainer_sig, self._trainer_busy = None, False
        self.collapsed = False    # just the title row showing
        self.menu = None          # the settings popover, while open
        self._pill_spot = None    # where the title row was before expanding, to collapse back there
        self._flash_job = None
        self._auto_job = None
        self.results = queue.Queue()

        root.overrideredirect(True)
        root.configure(bg=C["border"])   # the 1 px rim around the whole overlay
        root.attributes("-topmost", True)
        self._hovered = False
        # open solid for a few seconds so it's easy to spot, then go see-through as usual
        self._alpha(root, 1.0)
        self._preview_job = root.after(STARTUP_SOLID_MS, self._end_startup_preview)

        self._build()
        self._restore_place()
        self.root.after(300, self.snap_to_corner)  # docked: the game window may be somewhere else now
        widgets.text_scale = self.state.get("text_scale", 1.0)
        self.root.after(100, self._poll)
        self.root.after(TOPMOST_MS, self._keep_on_top)
        self.root.after(200, self._watch_hover)
        self._saved = json.dumps(self.state, sort_keys=True)
        self.root.after(AUTOSAVE_MS, self._autosave)
        self.root.bind_all("<Control-MouseWheel>", self._wheel_opacity)
        self.root.bind("<Key>", self._on_key)
        self.run_bg(self.db.load_indexes, self._on_loaded)
        self.state.pop("click_through", None)  # from a version that had it
        HotkeyThread({ord("S"): lambda: self.results.put((lambda _: self.sync_from_game(), None, None))}).start()

    # ---------- background work ----------

    def run_bg(self, fn, callback, on_error=None):
        def work():
            try:
                self.results.put((callback, fn(), None))
            except Exception as e:  # network / OCR errors are shown in the status bar
                self.results.put((on_error or (lambda _: None), None, e))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        # Yield to input/paint even when many network results arrive together.
        deadline = time.perf_counter() + .008
        processed = 0
        while processed < 12:
            try:
                callback, value, error = self.results.get_nowait()
            except queue.Empty:
                break
            if error:
                self.set_status(f"Error: {error}", "red")
            callback(value)
            processed += 1
            if time.perf_counter() >= deadline:
                break
        if os.path.exists(SHOW_REQUEST):
            try:
                os.remove(SHOW_REQUEST)
            except OSError:
                pass
            self.show_again()
        self.root.after(10 if not self.results.empty() else 100, self._poll)

    def show_again(self):
        """Opening UMBRΛLE while it already runs lands here: bring the open one forward, on a
        screen, instead of starting a second copy."""
        if not self._on_screen(self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width()):
            self.reset_position()
        self._last_front = None  # back on top at the next check
        self.set_status("UMBRΛLE was already open: here it is")

    def _keep_on_top(self):
        # SetWindowPos with NOACTIVATE keeps us above the game without taking its focus
        # (lift() activates the window, which made the game stutter)
        # Only when another window has just come to the front (e.g. the game): re-asserting
        # on every tick makes a see-through window repaint, which shows as a faint flicker.
        user32 = ctypes.windll.user32
        hwnd = user32.GetAncestor(self.root.winfo_id(), 2)  # GA_ROOT
        front = user32.GetForegroundWindow()
        if front != getattr(self, "_last_front", None):
            self._last_front = front
            HWND_TOPMOST, SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = -1, 0x1, 0x2, 0x10
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        # a monitor was unplugged or switched off with the overlay on it: bring it back
        if self.root.winfo_viewable() and not self._on_screen(self.root.winfo_x(), self.root.winfo_y(),
                                                              self.root.winfo_width()):
            self.reset_position()
        self.root.after(TOPMOST_MS, self._keep_on_top)

    # ---------- layout ----------

    def _build(self):
        # the root's colour shows as a 1 px rim; inside it, the expanded panel's outer few pixels
        # (left, right, bottom) resize it
        self.outer = outer = tk.Frame(self.root, bg=C["bg"])
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        self.root.bind("<Motion>", self._edge_cursor)
        self.root.bind("<Leave>", lambda e: e.widget is self.root and self.root.config(cursor=""))
        self.root.bind("<ButtonPress-1>", self._start_edge_resize)
        self.root.bind("<B1-Motion>", self._edge_resize)
        self.root.bind("<ButtonRelease-1>", self._end_resize, add="+")
        # text is wrapped to the width the window had when it was drawn: redraw when it changes
        self._render_width, self._refit_job = None, None
        self.root.bind("<Configure>", self._on_window_resize, add="+")
        self._build_title_row(outer)
        self.focus_card = tk.Frame(outer, bg=C["header"])  # the focused quest, while collapsed
        self._focus_shown = None

        self.body = tk.Frame(outer, bg=C["bg"])
        self.body.pack(fill="both", expand=True, padx=EDGE - 1, pady=(0, EDGE - 1))
        p = lambda n: widgets.px(self.root, n)
        tk.Frame(self.body, bg=C["border"], height=1).pack(fill="x")  # hairline under the title row

        bar = tk.Frame(self.body, bg=C["bg"])
        bar.pack(fill="x", pady=(p(4), 0), padx=p(2))
        self.tab_btns = {}
        for i, (key, text) in enumerate(TABS, start=1):
            cell = tk.Frame(bar, bg=C["bg"])
            cell.pack(side="left")
            b = button(cell, text, lambda k=key: self.set_tab(k), bg="bg", fg="muted", size=9, padx=p(6),
                       tip=f"{text} ({i})")
            b.pack()
            b.line = tk.Frame(cell, bg=C["bg"], height=2)  # violet underline on the open tab
            b.line.pack(fill="x", padx=p(6))
            self.tab_btns[key] = b

        # where you are, and the level + map search that most tabs use
        ctx = tk.Frame(self.body, bg=C["bg"])
        ctx.pack(fill="x", pady=(p(5), p(3)))
        self.level = tk.StringVar(value=str(self.state["level"]))
        level_box = entry(ctx, self.level, width=3, size=9, justify="center")
        level_box.pack(side="right", padx=(p(2), p(4)), ipady=1)
        label(ctx, "Lv", fg="muted", size=8).pack(side="right")
        self.find_btn = button(ctx, ICON["search"], lambda: self.open_map_search(self.find_btn), bg="bg",
                               size=12, padx=p(4), tip="GPS to a map, NPC or shop (/)")
        self.find_btn.pack(side="right", padx=(0, p(6)))
        level_box.bind("<Return>", lambda e: self.set_level())
        level_box.bind("<FocusOut>", lambda e: self.set_level())
        self.map_label = label(ctx, "", fg="muted", size=8, anchor="w", padx=p(6), cursor="hand2")
        self.map_label.pack(side="left", fill="x", expand=True)
        self.map_label.bind("<Button-1>", lambda e: self.open_map_search(self.map_label, correct=True))
        self.map_label.bind("<Enter>", lambda e: self.map_label.config(fg=C["text"]))
        self.map_label.bind("<Leave>", lambda e: self.map_label.config(fg=C["muted"]))
        Tooltip(self.map_label, "Wrong map? Click and pick the right one: it's remembered for next time")

        # kills left to level up on this map, on every tab (see render_levelup)
        self.lvl_strip = tk.Frame(self.body, bg=C["card"])
        self.lvl_strip.pack(fill="x", padx=p(4), pady=(0, p(3)))
        self._lvl_spec = None

        # search boxes live outside the scroll area so redraws don't steal their focus
        self.search_bars, self.search_entries = {}, {}
        self.mob_query, self.item_query = tk.StringVar(), tk.StringVar()
        for tab, var in (("mobs", self.mob_query), ("items", self.item_query)):
            frame = tk.Frame(self.body, bg=C["bg"])
            box = entry(frame, var)
            if tab == "mobs":
                self._build_level_filter(frame)  # "Lv [  ] - [  ]" to the right of the name box
            box.pack(fill="x", padx=6, pady=4, ipady=2)
            self.search_bars[tab], self.search_entries[tab] = frame, box
        self.mob_query.trace_add("write", lambda *_: self._debounce_mob_search())
        # item search asks the website, so wait until typing pauses
        self._item_search_job = None
        self.item_query.trace_add("write", lambda *_: self._debounce_item_search())

        self.scroll = ScrollArea(self.body)
        self.scroll.pack(fill="both", expand=True)

        foot = tk.Frame(self.body, bg=C["bg"])
        # packed at the bottom before the list, so a short window squeezes the list and
        # never pushes the status line and resize grip out of sight
        foot.pack(side="bottom", fill="x", before=self.scroll)
        self.status = label(foot, "Loading data from meowdb.com...", fg="muted", size=8, anchor="w", padx=6,
                            justify="left")
        self.status.pack(side="left", fill="x", expand=True)
        # long messages wrap onto a second line instead of being cut off at the window's edge
        foot.bind("<Configure>", lambda e: self.status.config(wraplength=max(120, e.width - 30)))
        grip = label(foot, "◢", fg="border_hi", size=8, cursor="size_nw_se")
        grip.pack(side="right")
        grip.bind("<ButtonPress-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._resize)

    def _build_title_row(self, outer):
        """The title row, which is all that shows when collapsed: drag handle, sigil, wordmark and
        one status line, then sync, expand / collapse and the settings menu."""
        p = lambda n: widgets.px(self.root, n)
        head = self.header = tk.Frame(outer, bg=C["header"])
        head.pack(fill="x")
        grip = label(head, "⠿", fg="border_hi", bg="header", size=10, cursor="fleur", padx=p(4))
        grip.pack(side="left", fill="y")
        Tooltip(grip, "Drag to move · double-click to expand or collapse")
        # quiet until you reach for it, then clearly a handle
        grip.bind("<Enter>", lambda e: grip.config(fg=C["muted"]), add="+")
        grip.bind("<Leave>", lambda e: grip.config(fg=C["border_hi"]), add="+")
        self._sigil = sigil_image(p(26))
        mark = tk.Label(head, image=self._sigil, bg=C["header"], cursor="fleur")
        mark.pack(side="left", padx=(0, p(8)), pady=p(9))
        self.menu_btn = button(head, "⋯", self.open_menu, bg="header", fg="bar_muted", size=11, padx=p(6),
                               tip="Settings")
        self.menu_btn.pack(side="right", padx=(0, p(4)))
        self.collapse_btn = button(head, "▴", self.toggle_collapse, bg="header", fg="bar_muted", size=12,
                                   padx=p(6), tip="Collapse (Esc)")
        self.collapse_btn.pack(side="right")
        button(head, "⟳", self.sync_from_game, bg="header", fg="bar_muted", size=10, padx=p(5),
               tip=f"Sync from the game now ({HOTKEY_TEXT})").pack(side="right")
        self.pin_btn = button(head, "⚲", self.toggle_pin, bg="header", fg="bar_muted", size=11, padx=p(5),
                              tip="Pin: lock where the overlay and the GPS are (click again to unpin)")
        self.pin_btn.pack(side="right")
        self._paint_pin()
        self.trainer_btn = button(head, "▶", self.toggle_trainer, bg="header", fg="bar_muted", size=10,
                                  padx=p(5), tip="Trainer: picks what to do next and steers the GPS (you play)")
        self.trainer_btn.pack(side="right")
        self._paint_trainer()
        self.corner_btn = button(head, "◥", self.toggle_corner_dock, bg="header", fg="bar_muted", size=9,
                                 padx=p(5), tip="Dock in the game's top-right corner (drag it to undock)")
        self.corner_btn.pack(side="right")
        self._paint_corner()
        words = self.words = tk.Frame(head, bg=C["header"])
        words.pack(side="left", fill="y", pady=(p(7), p(6)))
        top = tk.Frame(words, bg=C["header"])
        top.pack(anchor="w", fill="x")
        # the wordmark, spaced out with thin spaces (Tk has no letter spacing)
        self.title = tk.Label(top, text=" ".join("UMBRΛLE"), bg=C["header"], fg=C["text"],
                              font=(BRAND_FONT, 10), cursor="fleur", padx=0, pady=0)
        self.title.pack(side="left")
        self.auto_dot = label(top, "●", bg="header", size=7, cursor="hand2", padx=0, pady=0)
        self.auto_dot.pack(side="left", padx=(p(4), p(2)))
        self.auto_dot.bind("<Button-1>", lambda e: self.toggle_auto())
        Tooltip(self.auto_dot, "AUTO: following the game every 2 s (click to switch)")
        # the free space right of the wordmark: your EXP bar and kills left (see refresh_exp_pill)
        self.exp_pill = label(top, "", fg="bar_muted", bg="header", size=8, padx=0, pady=0, bd=0)
        self.exp_pill.pack(side="right")
        self.exp_pill.tip = Tooltip(self.exp_pill, "")
        words.bind("<Configure>", lambda e: self.refresh_exp_pill(), add="+")  # re-fit on expand / resize
        self.pill_status = label(words, "Loading...", fg="muted", bg="header", size=8, anchor="w",
                                 width=PILL_STATUS_CHARS, padx=0, pady=0)
        self.pill_status.pack(anchor="w", fill="x")
        self.pill_bar = widgets.Bar(words, bg="header", height=2)  # how far the next objective is

        for widget in (head, grip, mark, words, top, self.title, self.pill_status, self.exp_pill):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._move)
            widget.bind("<ButtonRelease-1>", self._end_move)
            widget.bind("<Double-Button-1>", lambda e: self.toggle_collapse())
        self._paint_auto()

    # ---------- position and size ----------

    def panel_width(self):
        """Width the lists are laid out for: the window's, or the panel's saved width while
        collapsed (so expanding doesn't need a redraw)."""
        return self.state["panel_size"][0] if self.collapsed else self.root.winfo_width()

    @staticmethod
    def _on_screen(x, y, w):
        """Whether a window at (x, y), w wide, has its title row on some monitor."""
        return widgets.on_a_screen(x + 20, y + 10) or widgets.on_a_screen(x + w - 20, y + 10)

    def _place(self, w, h, at=None):
        """Size the window w x h. At `at` (x, y), or else the title row stays where it is, and
        near the right edge of the screen the right edge stays put, so the panel grows toward
        the middle, not off the screen. Either way it's kept within its monitor (a tall panel
        near the bottom moves up). Returns the new (x, y)."""
        cx, cy, cw = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width()
        x, y = at if at else (cx, cy)
        left, top, right, bottom = widgets.work_area(x + min(w, cw) // 2, y + 10)
        if not at and cx + cw / 2 > (left + right) / 2:
            x = cx + cw - w
        w, h = min(w, right - left), min(h, bottom - top)
        x, y = max(left, min(x, right - w)), max(top, min(y, bottom - h))
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.state["pos"] = [x, y]
        return x, y

    def _pill_size(self):
        self.root.update_idletasks()
        return self.root.winfo_reqwidth(), self.root.winfo_reqheight()

    def _restore_place(self):
        """Open where it was last time, collapsed or not, on a screen that still exists."""
        s = self.state
        if "pos" not in s:  # first start of the overlay: keep the old window's spot
            m = re.fullmatch(r"(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)", s.get("geometry") or "")
            if m:
                s["pos"] = [int(m[3].replace("+", "", 1)), int(m[4].replace("+", "", 1))]
        if not s.get("compact_v3"):  # once: the compact panel size (older sizes were often near full
            # height; v3: sizes saved before the app ignored Windows scaling were too wide for 100%)
            left, top, right, bottom = widgets.work_area(*(s.get("pos") or (0, 0)))
            s["panel_size"] = [max(MIN_W, widgets.px(self.root, PANEL_SIZE[0])), round((bottom - top) * PANEL_SIZE[1])]
            s["compact_v3"] = True
        if s.get("collapsed"):
            self.collapsed = True
            self.body.pack_forget()
            self.collapse_btn.config(text="▾")
            w, h = self._pill_size()
        else:
            w, h = s["panel_size"]
        x, y = s.get("pos") or (None, None)
        if x is None or not (widgets.on_a_screen(x + 40, y + 10) and widgets.on_a_screen(x + w - 40, y + 10)):
            x, y = self._home_spot(w)
        self._place(w, h, at=(x, y))

    def _home_spot(self, w):
        """Top-right of the game window (or of the main screen): away from the minimap, which is
        top-left, and from the middle, where your character is."""
        box = find_game_window()
        left, top, right, _ = box if box else widgets.work_area(0, 0)  # (0, 0) is on the main screen
        return right - w - widgets.px(self.root, 16), top + widgets.px(self.root, 48)

    def _corner_spot(self, w):
        """(x, y) that puts a window w wide flush in the game window's top-right corner (or the
        main screen's, with no game window)."""
        box = find_game_window()
        _, top, right, _ = box if box else widgets.work_area(0, 0)
        return right - w, top

    def toggle_corner_dock(self):
        self.state["corner_docked"] = not self.state.get("corner_docked")
        self._paint_corner()
        if self.state["corner_docked"]:
            self._pill_spot = None
            self.snap_to_corner()
            self.set_status("Docked in the game's top-right corner: it stays there (drag it to undock)")
        else:
            self.set_status("Undocked: drag the title row to move it")

    def snap_to_corner(self):
        """While docked: back flush in the corner, e.g. after expanding, collapsing, a resize or
        the game window moving. Nothing happens when it's already there."""
        if not self.state.get("corner_docked") or getattr(self, "_drag", None):
            return
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x, y = self._corner_spot(w)
        if (self.root.winfo_x(), self.root.winfo_y()) != (x, y):
            self._place(w, h, at=(x, y))

    def _paint_corner(self):
        on = bool(self.state.get("corner_docked"))
        self.corner_btn.fg = C["accent_hi"] if on else C["bar_muted"]
        self.corner_btn.config(fg=self.corner_btn.fg)

    def reset_position(self):
        """The menu: back to the home spot, e.g. after dragging it off-screen."""
        w, h = self.root.winfo_width(), self.root.winfo_height()
        self._place(w, h, at=self._home_spot(w))
        self._pill_spot = None
        self.dock_gps()
        self.set_status("Back at its home spot: top-right of the game window")

    def _start_move(self, e):
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _move(self, e):
        if self.state.get("pinned") or not getattr(self, "_drag", None):
            return
        self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _end_move(self, e):
        """Remember where it was dropped; dropped off every screen, it comes back to the nearest."""
        if not getattr(self, "_drag", None):
            return
        self._drag = None
        x, y, w, h = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()
        if self.state.get("corner_docked") and (x, y) != self._corner_spot(w):
            self.toggle_corner_dock()  # dragged out of the corner: it stays where you dropped it
        if self._on_screen(x, y, w):
            self.state["pos"] = [x, y]
        else:
            self._place(w, h, at=(x, y))
        self._pill_spot = None  # moved by hand: collapse where it is now

    def _start_resize(self, e, edges="rb"):
        self._size = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y(),
                      self.root.winfo_width(), self.root.winfo_height(), edges)
        self._resizing = True

    def _resize(self, e):
        if self.state.get("pinned") or self.collapsed or not getattr(self, "_resizing", False):
            return
        x0, y0, left, top, w, h, edges = self._size
        dx, dy = e.x_root - x0, e.y_root - y0
        if "l" in edges:
            new_w = max(MIN_W, w - dx)
            left, w = left + (w - new_w), new_w
        elif "r" in edges:
            w = max(MIN_W, w + dx)
        if "b" in edges:
            h = max(MIN_H, h + dy)
        self.root.geometry(f"{w}x{h}+{left}+{top}")

    def _end_resize(self, _):
        if getattr(self, "_resizing", False):
            self._resizing = False
            if not self.collapsed:
                self.state["panel_size"] = [self.root.winfo_width(), self.root.winfo_height()]
                self.state["pos"] = [self.root.winfo_x(), self.root.winfo_y()]
            self.snap_to_corner()

    def _edges_at(self, e):
        """Which panel edges the pointer is on ('l', 'r', 'b'), only over the edge itself."""
        if e.widget is not self.outer or self.collapsed or self.state.get("pinned"):
            return ""
        x, y = e.x_root - self.root.winfo_rootx(), e.y_root - self.root.winfo_rooty()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        return (("l" if x <= EDGE else "r" if x >= w - EDGE - 1 else "")
                + ("b" if y >= h - EDGE - 1 else ""))

    def _edge_cursor(self, e):
        # Child widgets inherit the window's cursor, so it must be reset as soon as the
        # pointer is over anything but the edge, or the arrows "stick" inside the window.
        cursor = {"l": "sb_h_double_arrow", "r": "sb_h_double_arrow", "b": "sb_v_double_arrow",
                  "lb": "size_ne_sw", "rb": "size_nw_se"}.get(self._edges_at(e), "")
        if self.root.cget("cursor") != cursor:
            self.root.config(cursor=cursor)

    def _start_edge_resize(self, e):
        edges = self._edges_at(e)
        self._edge = edges
        if edges:
            self._start_resize(e, edges)

    def _edge_resize(self, e):
        if e.widget is self.outer and getattr(self, "_edge", ""):
            self._resize(e)

    def toggle_pin(self):
        """Locked: dragging and resizing the overlay are ignored until unlocked (the GPS window
        follows the game's minimap on its own)."""
        self.state["pinned"] = not self.state.get("pinned")
        self._paint_pin()
        self.set_status("Pinned: the overlay and the GPS stay where they are" if self.state["pinned"]
                        else "Unpinned: drag the title row to move, the edges to resize")

    def _paint_pin(self):
        """Pinned: a lit violet chip; unpinned: a plain icon like the buttons next to it."""
        b = self.pin_btn
        on = bool(self.state.get("pinned"))
        b.fg, b.bg = (C["accent_hi"], C["press"]) if on else (C["bar_muted"], C["header"])
        b.config(fg=b.fg, bg=b.bg, highlightbackground=b.bg)

    def toggle_collapse(self):
        """Collapsed: only the title row, as wide as its contents. Expanded: the panel at its saved
        size, growing away from the screen edge it's near. Collapsing again returns the title row
        to where it was, unless the panel was moved in between."""
        if self.collapsed:
            self.collapsed = False
            self._pill_spot = (self.root.winfo_x(), self.root.winfo_y())
            self.refresh_focus_card()  # the panel shows the quest now: no card
            if self._flash_job:  # the message is in the status line below now
                self.root.after_cancel(self._flash_job)
                self._flash_job = None
            self.body.pack(fill="both", expand=True, padx=EDGE - 1, pady=(0, EDGE - 1))
            self._expanded_at = self._place(*self.state["panel_size"])
            self._fit_height()
            self._expanded_at = tuple(self.state["pos"])
        else:
            if not (self.state.get("pos") and tuple(self.state["pos"]) == getattr(self, "_expanded_at", None)):
                self._pill_spot = None  # the panel was moved: collapse where it is
            self.collapsed = True
            self.body.pack_forget()
            self._focus_shown = None
            self.refresh_focus_card()
            self._place(*self._pill_size(), at=self._pill_spot)
        self.state["collapsed"] = self.collapsed
        self.collapse_btn.config(text="▾" if self.collapsed else "▴")
        self.refresh_pill()
        self.root.after_idle(self.snap_to_corner)

    # ---------- see-through ----------

    @staticmethod
    def _alpha(win, value, fade=False):
        if fade:
            widgets.fade(win, value)
        else:
            win.attributes("-alpha", value)

    def _watch_hover(self):
        """Solid while the mouse is over the window, see-through otherwise (blends with the game)."""
        self._watch_focus()
        if self._preview_job:  # showing a just-chosen level; don't flip back yet
            self.root.after(150, self._watch_hover)
            return
        x, y = self.root.winfo_pointerxy()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        inside = rx <= x < rx + self.root.winfo_width() and ry <= y < ry + self.root.winfo_height()
        if inside != self._hovered:
            self._hovered = inside
            self._alpha(self.root, HOVER_ALPHA if inside else self.state["idle_alpha"], fade=True)
        self._watch_gps_hover(x, y)
        self.root.after(150, self._watch_hover)

    def _watch_focus(self):
        """Auto-collapse: when you go from the overlay back to the game, the expanded panel folds
        up to its title row a moment later (not while the mouse is on it)."""
        if self.collapsed or not self.state.get("auto_collapse"):
            # forgotten while collapsed too: after "Reset from Quest window" (clicked here, then Q
            # pressed in the game) the panel opens again by itself and must stay open
            self._collapse_at, self._was_ours = None, False
            return
        user32 = ctypes.windll.user32
        front = user32.GetForegroundWindow()
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(front, ctypes.byref(pid))
        if pid.value == os.getpid():  # one of our windows has the keyboard
            self._was_ours, self._collapse_at = True, None
            return
        if getattr(self, "_was_ours", False):
            self._was_ours = False
            title = ctypes.create_unicode_buffer(64)
            user32.GetWindowTextW(front, title, 64)
            if title.value.startswith("MapleStory"):
                self._collapse_at = time.monotonic() + AUTO_COLLAPSE_S
        if getattr(self, "_collapse_at", None) and time.monotonic() >= self._collapse_at:
            if self._hovered:
                self._collapse_at = time.monotonic() + 0.5  # still reading it: wait
            else:
                self._collapse_at = None
                self.toggle_collapse()

    def toggle_auto_collapse(self):
        self.state["auto_collapse"] = not self.state.get("auto_collapse")
        self.set_status("Auto-collapse on: the panel folds up when you go back to the game"
                        if self.state["auto_collapse"] else "Auto-collapse off: the panel stays open")

    def _watch_gps_hover(self, x, y):
        """Same for the GPS window, with its own see-through level."""
        g = self.gps
        if not (g and g.winfo_exists()) or time.monotonic() < getattr(self, "_gps_preview_until", 0):
            return
        gx, gy = g.winfo_rootx(), g.winfo_rooty()
        inside = gx <= x < gx + g.winfo_width() and gy <= y < gy + g.winfo_height()
        if inside != self._gps_hovered:
            self._gps_hovered = inside
            self._alpha(g, HOVER_ALPHA if inside else self.state.get("gps_alpha", GPS_ALPHA), fade=True)
            self._show_gps_controls(inside)

    def set_opacity(self, alpha):
        self.state["idle_alpha"] = alpha
        self.set_status(f"Opacity {round(alpha * 100)}% (when the mouse is away)")
        # show the new level for a moment even though the mouse is over the window
        self._alpha(self.root, alpha)
        if self._preview_job:
            self.root.after_cancel(self._preview_job)

        def end_preview():
            self._preview_job, self._hovered = None, None  # re-check hover on the next tick
        self._preview_job = self.root.after(1200, end_preview)

    def set_text_size(self, scale):
        """Bigger text for the lists (the title row keeps its size, so its controls always fit)."""
        widgets.text_scale = self.state["text_scale"] = scale
        self.set_status(f"Text size {round(scale * 100)}%")
        self.render()

    def cycle_opacity(self):
        cur = self.state["idle_alpha"]
        nxt = next((a for a in OPACITY_STEPS if a > cur + 0.01), OPACITY_STEPS[0])
        self.set_opacity(nxt)

    def _wheel_opacity(self, e):
        self.set_opacity(round(min(1.0, max(0.3, self.state["idle_alpha"] + (0.05 if e.delta > 0 else -0.05))), 2))
        return "break"

    def _on_key(self, e):
        """Keys while the overlay has the keyboard: 1-5 tabs, / map search, Esc collapses (or
        leaves a search box). Typing in a box is left alone."""
        typing = isinstance(e.widget, tk.Entry)
        if e.keysym == "Escape":
            if typing:
                self.root.focus_set()
            elif not self.collapsed:
                self.toggle_collapse()
            return "break"
        if typing or self.collapsed:
            return None
        if e.char and e.char in "12345":
            self.set_tab(TABS[int(e.char) - 1][0])
            return "break"
        if e.char == "/":
            self.open_map_search(self.find_btn)
            return "break"
        return None

    # ---------- settings menu ----------

    def open_menu(self):
        """The ⋯ menu: opacity, text size, switches, actions and their shortcuts."""
        if self.menu and self.menu.winfo_exists():
            self.menu.close()
            return
        pop = self.menu = widgets.Popover(self.menu_btn)
        body, p = pop.body, (lambda n: widgets.px(self.root, n))

        def row(text, top=3):
            r = tk.Frame(body, bg=C["header"])
            r.pack(fill="x", padx=p(10), pady=(p(top), p(3)))
            label(r, text, bg="header", size=9).pack(side="left")
            return r

        def rule():
            tk.Frame(body, bg=C["border"], height=1).pack(fill="x", padx=p(10), pady=p(5))

        r = row("Opacity", top=10)
        pct = label(r, f"{round(self.state['idle_alpha'] * 100)}%", fg="muted", bg="header", size=8, width=4,
                    anchor="e")
        pct.pack(side="right")

        def opacity(v):
            self.set_opacity(round(v, 2))
            pct.config(text=f"{round(v * 100)}%")
        widgets.Slider(r, 0.3, 1.0, self.state["idle_alpha"], opacity, width=112, bg="header").pack(
            side="right", padx=(p(8), p(4)))

        r = row("Text size")
        sizes = {}

        def text_size(scale):
            self.set_text_size(scale)
            for s, b in sizes.items():
                b.bg, b.fg = (C["button"], C["gold"]) if s == scale else (C["header"], C["muted"])
                b.config(bg=b.bg, fg=b.fg, highlightbackground=b.bg)
        for scale in reversed(TEXT_SCALES):
            on = abs(scale - widgets.text_scale) < 0.01
            sizes[scale] = button(r, f"{round(scale * 100)}%", lambda s=scale: text_size(s),
                                  bg="button" if on else "header", fg="gold" if on else "muted", size=8, padx=p(4))
            sizes[scale].pack(side="right", padx=1)
        rule()

        for text, key, command, hint in (
                ("Auto sync", "auto_sync", self.toggle_auto, "every 2 s"),
                ("Auto-collapse", "auto_collapse", self.toggle_auto_collapse, "back in the game"),
                ("Lock position", "pinned", self.toggle_pin, "")):
            r = row(text)
            widgets.Switch(r, self.state.get(key), lambda _, c=command: c(), bg="header").pack(side="right")
            if hint:
                label(r, hint, fg="muted", bg="header", size=7).pack(side="right", padx=p(8))
        rule()

        def then_close(command):
            return lambda: (pop.close(), command())
        widgets.menu_item(body, "⟳   Sync now", then_close(self.sync_from_game)).pack(fill="x")
        widgets.menu_item(body, "NiaDB data / refresh", then_close(self.open_data_status)).pack(fill="x")
        widgets.menu_item(body, "⌂   Reset position", then_close(self.reset_position)).pack(fill="x")
        rule()
        widgets.menu_item(body, "✕   Quit UMBRΛLE", self.on_close, "saves your list").pack(fill="x")
        label(body, f"UMBRΛLE {VERSION}", fg="disabled", bg="header", size=7, anchor="e").pack(
            fill="x", padx=p(10), pady=(0, p(6)))
        pop.show()

    def set_status(self, text, color="muted"):
        if self.status.cget("text") != text or self.status.cget("fg") != C[color]:
            self.status.config(text=text, fg=C[color])
            if self.collapsed and not self.resetting:  # the status line isn't visible: show it on the title row
                self._pill(text, color)
                if self._flash_job:
                    self.root.after_cancel(self._flash_job)
                self._flash_job = self.root.after(FLASH_MS, self._end_flash)

    def _end_flash(self):
        self._flash_job = None
        self.refresh_pill()

    def _pill(self, text, color="muted"):
        """Put `text` on the title row's status line (shortened to fit)."""
        if len(text) > PILL_STATUS_CHARS:
            text = text[:PILL_STATUS_CHARS - 1].rstrip() + "…"
        if self.pill_status.cget("text") != text or self.pill_status.cget("fg") != C[color]:
            self.pill_status.config(text=text, fg=C[color])

    def next_objective(self):
        """What to do now, for the title row: the first unfinished objective of the open quest
        (or the first on the list), or its turn-in once everything is done. (text, share done,
        done) or None without quests."""
        active = self.state["active"]
        if not active:
            return None
        qid = self.focused() or (self.state["expanded"] if self.state["expanded"] in active else active[0])
        q, steps = self.db.quests[qid], self.guides.get(qid)
        done, progress = self.done_steps(qid), self.state["progress"].get(qid, {})
        for i, need in enumerate(q.get("need") or []):
            if i in done:
                continue
            name = (steps[i].get("name") if steps and i < len(steps) else None) or need["name"].replace("Defeat ", "")
            have, count = progress.get(str(i)), need.get("count", 1) or 1
            return f"{'–' if have is None else have}/{count} {name}", (have or 0) / count, False
        return f"Turn in: {q.get('completeNpc') or q.get('npc') or q['name']}", 1.0, True

    def refresh_pill(self):
        """The title row's status line: the next objective, with a thin bar for how far along it
        is (the location is on the game's own minimap). Without quests: where you are."""
        self.refresh_focus_card()  # also while a message is on the title row
        self.refresh_exp_pill()  # its room depends on the status line's width
        if self.resetting or self._flash_job:
            return
        if not self.db.quests:
            self._pill("Loading data...")
            self.pill_bar.pack_forget()
            return
        goal = self.next_objective()
        focus = self.focused()
        step = self.trainer.step if self.state.get("trainer_on") else None
        if step:
            self._pill(f"▶ {step['text']}", "gold")
            self.pill_bar.pack_forget()
        elif focus and self.collapsed:  # the card below lists every objective: here, which quest
            self._pill(self.db.quests[focus]["name"], "gold")
            self.pill_bar.pack_forget()
        elif goal:
            text, share, finished = goal
            self._pill(text, "green" if finished else "text")
            self.pill_bar.set(share, finished)
            if not self.pill_bar.winfo_ismapped():
                self.pill_bar.pack(fill="x", pady=(widgets.px(self.root, 3), 0))
        else:
            m = self.db.maps.get(self.state.get("map") or "")
            self._pill(f"{m['displayName'] if m else 'No quests yet'}")
            self.pill_bar.pack_forget()

    # ---------- focus on one quest ----------

    def focused(self):
        """The quest you focus on (◉ on its card), if it's still on the list."""
        qid = self.state.get("focus_quest")
        return qid if qid in self.state["active"] else None

    def toggle_focus(self, qid):
        """◉: work on just this quest. The panel then shows only it, and collapsed, every one of
        its objectives sits under the title row. ◉ again (or "All quests") shows them all."""
        if self.focused() == qid:
            self.state.pop("focus_quest", None)
            self.set_status("Showing all quests")
        else:
            self.state["focus_quest"] = qid
            self.state["expanded"] = qid
            self.set_status(f"Focus: {self.db.quests[qid]['name']}")
        self.render(keep_scroll=False)

    def objectives(self, qid):
        """[(have or None, count, name, done)] for each "have / need" objective of a quest."""
        q, steps = self.db.quests[qid], self.guides.get(qid)
        done, progress = self.done_steps(qid), self.state["progress"].get(qid, {})
        result = []
        for i, need in enumerate(q.get("need") or []):
            name = (steps[i].get("name") if steps and i < len(steps) else None) or need["name"].replace("Defeat ", "")
            count, have = need.get("count", 1) or 1, progress.get(str(i))
            if i in done and have is None:
                have = count
            result.append((have, count, name, i in done))
        return result

    def refresh_focus_card(self):
        """Collapsed with a focused quest: under the title row, each objective ("12 / 30 Dark
        Stump") with its own bar, then where to turn it in. Rebuilt only when what it shows
        changes, and the collapsed overlay grows or shrinks to fit it."""
        card = getattr(self, "focus_card", None)
        if card is None:
            return
        qid = self.focused()
        content = None
        if qid and self.collapsed and not self.resetting:
            q = self.db.quests[qid]
            content = (qid, tuple(self.objectives(qid)), q.get("completeNpc") or q.get("npc"),
                       qid in self.state["tracked"], widgets.text_scale)
        if content == self._focus_shown:
            return
        self._focus_shown = content
        for child in card.winfo_children():
            child.destroy()
        if not content:
            card.pack_forget()
        else:
            p = lambda n: widgets.px(self.root, n)
            q, objectives, turn_in, live = self.db.quests[qid], content[1], content[2], content[3]
            wrap = max(p(160), self.header.winfo_reqwidth() - p(40))
            tk.Frame(card, bg=C["border"], height=1).pack(fill="x")
            body = tk.Frame(card, bg=C["header"])
            body.pack(fill="x", padx=(p(14), p(10)), pady=(p(5), p(7)))
            for have, count, name, finished in objectives:
                row = tk.Frame(body, bg=C["header"])
                row.pack(fill="x", pady=(0, p(3)))
                line = tk.Frame(row, bg=C["header"])
                line.pack(fill="x")
                label(line, "✔" if finished else "☐", fg="green" if finished else "muted", bg="header",
                      size=8).pack(side="left")
                label(line, f"{'–' if have is None else have} / {count}", fg="green" if finished else "text",
                      bg="header", size=8, bold=True).pack(side="left", padx=(p(3), p(5)))
                label(line, name, fg="muted" if finished else "text", bg="header", size=8, anchor="w",
                      justify="left", wraplength=wrap - p(80)).pack(side="left", fill="x", expand=True)
                widgets.Bar(row, min(1.0, (have or 0) / count), bg="header", done=finished, height=2).pack(
                    fill="x", padx=(p(16), 0), pady=(p(1), 0))
            ready = all(o[3] for o in objectives)
            nm = npc_map(self.db, turn_in)
            where = f" · {nm.get('displayMapName') or nm['mapName']}" if nm else ""
            label(body, ("★ Turn in: " if ready else "➜ Turn in: ") + f"{turn_in or '?'}{where}",
                  fg="gold" if ready else "muted", bg="header", size=8, anchor="w", justify="left",
                  wraplength=wrap).pack(fill="x", pady=(p(2), 0))
            if objectives and not live:
                label(body, "Counts follow the game as you kill and loot", fg="disabled",
                      bg="header", size=7, anchor="w", justify="left", wraplength=wrap).pack(fill="x", pady=(p(2), 0))
            card.pack(fill="x", after=self.header)
        if self.collapsed:
            self._place(*self._pill_size(), at=(self.root.winfo_x(), self.root.winfo_y()))

    def set_tab(self, tab):
        self.state["tab"] = tab
        for key, b in self.tab_btns.items():
            b.fg = C["text"] if key == tab else C["muted"]
            b.config(fg=b.fg)
            b.line.config(bg=C["accent"] if key == tab else C["bg"])
        for key, frame in self.search_bars.items():
            if key == tab:
                frame.pack(fill="x", before=self.scroll)
                self.search_entries[key].focus_set()
            else:
                frame.pack_forget()
        self.render(keep_scroll=False)

    def set_level(self):
        try:
            level = max(1, min(200, int(self.level.get())))
        except ValueError:
            return
        if level != self.state["level"]:
            self.state["level"] = level
            self.render_levelup()
            self.trainer_tick()
            if self.state["tab"] == "train":
                self.render()

    def toggle_auto(self):
        self.state["auto_sync"] = not self.state["auto_sync"]
        self._paint_auto()
        self._schedule_auto_sync()
        self.set_status("AUTO on: following the game every 2 s" if self.state["auto_sync"] else
                        "AUTO is off: quests and counts update only when you press ⟳ (the GPS still follows you)",
                        "muted" if self.state["auto_sync"] else "gold")

    def _paint_auto(self):
        self.auto_dot.config(fg=C["bar_green"] if self.state["auto_sync"] else C["disabled"])
        self.refresh_pill()

    # ---------- kills to level up ----------

    def levelup_rows(self):
        """For each monster on this map, busiest first: (name, EXP you get per kill, % of your
        bar per kill, kills left to level up). Solo, or your share when your party kills it."""
        level, party = self.state["level"], self.state.get("party", 1)
        hits = self.state.get("party_hits", "all")
        exp, pct = self.state.get("exp_bar") or (None, None)
        now = leveling.exp_from_bar(exp, pct, level) if pct is not None else 0
        seen, rows = set(), []
        for mob in sorted((self.db.map_data.get(self.state.get("map") or "") or {}).get("monsters") or [],
                          key=lambda m: -(m.get("count") or 0)):
            info = self.db.monsters.get(int(mob["id"])) or {}
            if mob["id"] in seen or not info.get("exp"):
                continue
            seen.add(mob["id"])
            gain = leveling.party_exp(info["exp"], level, party, hits)
            rows.append((info.get("display") or mob["name"], gain, leveling.percent(gain, level),
                         leveling.kills_to_level(gain, level, now)))
        return rows

    def render_levelup(self):
        """The small "kills to level up" counter under the location row: where your EXP bar is,
        then each monster here with the % one kill gives and how many kills are left."""
        if not self.db.monsters:
            return
        self.refresh_exp_pill()
        level, party = self.state["level"], self.state.get("party", 1)
        hits, opened = self.state.get("party_hits", "all"), self.state.get("lvl_open", True)
        bar = self.state.get("exp_bar")
        rows = self.levelup_rows() if opened else []
        spec = (level, party, hits, opened, tuple(bar or ()), tuple(rows), widgets.text_scale)
        if spec == self._lvl_spec:
            return  # nothing changed: no redraw, so a sync every 2 s doesn't flicker
        self._lvl_spec = spec
        self.root.after_idle(self._fit_height)  # the strip's height counts in the panel's
        strip, p = self.lvl_strip, lambda n: widgets.px(self.root, n)
        for w in strip.winfo_children():
            w.destroy()

        head = tk.Frame(strip, bg=C["card"])
        head.pack(fill="x", padx=p(6), pady=(p(3), p(1)))
        for n in range(leveling.PARTY_MAX, 0, -1):  # packed right to left: 1 2 3 4 5 6
            chip = button(head, str(n), lambda n=n: self.set_party(n), size=8, padx=p(3),
                          bg="press" if n == party else "button", fg="text" if n == party else "muted",
                          tip="Solo" if n == 1 else f"Party of {n} on this map")
            chip.pack(side="right", padx=(p(1), 0))
        label(head, "👥", fg="muted", bg="card", size=8).pack(side="right", padx=(p(6), p(1)))
        need = leveling.exp_to_next(level)
        if bar:
            now = leveling.exp_from_bar(bar[0], bar[1], level)
            where = f"{bar[1]:.2f}% · {need - now:,} left"
        else:
            where = "from 0% (EXP bar not read yet)"
        title = label(head, f"{'▾' if opened else '▸'} Lv {level + 1} in", fg="text", bg="card", size=8,
                      cursor="hand2")
        title.pack(side="left")
        note = label(head, f" {where}", fg="muted", bg="card", size=8, anchor="w", cursor="hand2")
        note.pack(side="left", fill="x", expand=True)
        for w in (title, note):
            w.bind("<Button-1>", lambda e: self.toggle_levelup())
        Tooltip(note, "Your EXP is read from the game's EXP bar at the bottom of the screen on every "
                      "sync. Click to fold this counter.")
        if not opened:
            return

        if party > 1:
            line = tk.Frame(strip, bg=C["card"])
            line.pack(fill="x", padx=p(6), pady=(0, p(1)))
            for key, text, tip in (("all", "all hit", "Everyone damages each monster equally"),
                                   ("me", "I kill", "You do all the damage, the others are on the map"),
                                   ("leech", "I leech", "The others kill, you're on the map (no damage)")):
                button(line, text, lambda k=key: self.set_party_hits(k), size=8, padx=p(4),
                       bg="press" if key == hits else "button", fg="text" if key == hits else "muted",
                       tip=tip).pack(side="left", padx=(0, p(2)))
            label(line, " kills = the party's", fg="muted", bg="card", size=8).pack(side="left")
        if not rows:
            label(strip, "No monsters on this map", fg="muted", bg="card", size=8, anchor="w",
                  padx=p(6)).pack(fill="x", pady=(0, p(3)))
            return
        for name, gain, share, kills in rows[:4]:
            line = tk.Frame(strip, bg=C["card"])
            line.pack(fill="x", padx=p(6), pady=(0, p(1)))
            # numbers packed first, so a long name is cut instead of them
            label(line, " kills", fg="muted", bg="card", size=8).pack(side="right")
            label(line, f"{kills:,}", fg="gold", bg="card", size=9, bold=True).pack(side="right")
            label(line, f"+{leveling.fmt_percent(share)} · ", fg="green", bg="card", size=8).pack(side="right")
            label(line, f"{name} ", fg="text", bg="card", size=8, anchor="w").pack(side="left")
            label(line, f"{gain:,} EXP", fg="muted", bg="card", size=8, anchor="w").pack(side="left")
        tk.Frame(strip, bg=C["card"], height=p(2)).pack()

    def refresh_exp_pill(self):
        """The title row's top line, right of the wordmark (shown collapsed and expanded): your
        EXP bar's percent and the kills left to level up on this map. That space is only as wide
        as the status line under it, so the longest wording that fits is used."""
        bar, level = self.state.get("exp_bar"), self.state["level"]
        rows = self.levelup_rows() if bar else []
        if not bar:
            options, tip = [""], ""
        elif rows:
            name, gain, share, kills = rows[0]
            pct = bar[1]
            options = [f"{pct:.2f}% · {kills:,} kills", f"{pct:.2f}% · {kills:,}", f"{pct:.1f}% · {kills:,}",
                       f"{pct:.1f}%·{kills:,}", f"{pct:.1f}% {kills:,}", f"{pct:.0f}%·{kills:,}", f"{pct:.1f}%"]
            tip = (f"EXP {pct:.2f}% of Lv {level} · {kills:,} {name} to Lv {level + 1} "
                   f"(+{leveling.fmt_percent(share)} each)")
        else:
            options, tip = [f"{bar[1]:.2f}%", f"{bar[1]:.1f}%"], f"EXP {bar[1]:.2f}% of Lv {level} · no monsters here"
        self.root.update_idletasks()
        given = self.words.winfo_width() if self.words.winfo_ismapped() else 0  # less than asked, expanded
        room = min(self.pill_status.winfo_reqwidth(), given or 10 ** 4) - self.title.winfo_reqwidth()             - self.auto_dot.winfo_reqwidth() - widgets.px(self.root, 6)  # the dot's padding
        font = tkfont.Font(font=self.exp_pill.cget("font"))
        text = next((o for o in options if font.measure(o) <= room), options[-1])
        if self.exp_pill.cget("text") != text:
            self.exp_pill.config(text=text)
        self.exp_pill.tip.text = tip

    def toggle_levelup(self):
        self.state["lvl_open"] = not self.state.get("lvl_open", True)
        self.render_levelup()

    def set_party(self, n):
        self.state["party"] = n
        self.render_levelup()

    def set_party_hits(self, hits):
        self.state["party_hits"] = hits
        self.render_levelup()

    def on_exp_bar(self, texts, confirm):
        """A sync read the EXP bar (`texts`: OCR'd versions of it): keep it, and fix the level box
        when the bar says otherwise: the level whose EXP table fits the bar's number and percent
        ("28,474 [51.87%]" is only Lv 26), or one up when the bar drops from near 100% to near 0%."""
        level, before = self.state["level"], self.state.get("exp_bar")
        reading = leveling.read_bar(texts, level, before[1] if before else None)
        if not reading:
            return
        # the bar creeps up as you kill, so a reading never repeats while you hunt: a small rise
        # counts at once; a drop (death, level-up) or another level must come out twice in a row
        rising = reading[0] == level and before and 0 <= reading[2] - before[1] <= 20
        if not rising and not confirm(("exp_bar",), (reading[0], before and reading[2] < before[1])):
            return
        level, exp, pct = reading
        if exp is None and before and before[1] - pct > 50:
            level += 1  # leveled up (a death costs ~5-10%, never this much)
        if level != self.state["level"]:
            self.level.set(str(level))
            self.set_level()
        self.state["exp_bar"] = [exp, pct]
        self.render_levelup()

    # ---------- what to do, from meowdb's guides ----------

    def fetch_hint(self, qid):
        """Download what the quest's NPC says on accepting it (background, once per run), for
        quests no guide explains."""
        if qid in self.hints or qid in self.db.quest_guides:
            return
        self.hints[qid] = None  # asked: don't ask again

        def done(hint):
            self.hints[qid] = hint
            if hint and (self.state["tab"] == "items" or
                         self.state["tab"] == "quests" and self.state.get("expanded") == qid):
                self.render()
        self.run_bg(lambda: self.db.quest_hint(qid), done, on_error=lambda _: None)

    def map_named(self, name):
        """The map id whose name is `name` ("The Pig Beach"), or None."""
        name = (name or "").split(",")[0].strip().lower()
        return next((mid for mid, m in self.db.maps.items() if m["displayName"].lower() == name), None)

    def quest_goal(self, qid):
        """Where a quest sends you when it isn't about hunting: (map, npc or None, what), from its
        guide (the NPC that lets you in, the place a hint names) or its NPC's words. None if unknown."""
        q = self.db.quests[qid]
        own = {q.get("npc"), q.get("completeNpc")}
        for part in self.db.quest_guides.get(qid, []):
            for npc, map_id in part["npcs"]:
                if npc not in own:
                    return map_id, npc, f"{npc} ({part['section']})"
            for column, cell in part["facts"]:
                talk = re.match(r"Talk to (.+?) in (.+)$", cell) if column == "Where" else None
                spot = npc_map(self.db, talk[1]) if talk else None
                if spot:
                    return spot["mapId"], talk[1], cell
                if column == "Where" and self.map_named(cell):
                    return self.map_named(cell), None, cell
            for _, map_id in part["stages"][:1]:
                return map_id, None, part["section"]
        hint = self.hints.get(qid)
        for name, map_id in (hint or {}).get("maps") or []:
            return map_id, None, f"{name} (as {q.get('npc')} says)"
        return None

    def render_quest_guide(self, body, bg, qid, key=None):
        """Under the reward: meowdb's guide for this quest (where, what, who lets you in, its
        steps), or, without one, what its NPC says when you accept it. NPCs and places are GPS links
        (route `key`: the quest's own, or e.g. "item" on the Items tab)."""
        p, key = (lambda n: widgets.px(self.root, n)), key or qid
        entries = self.db.quest_guides.get(qid) or []
        for part in entries[:2]:
            box = tk.Frame(body, bg=C["card_hi"])
            box.pack(fill="x", pady=(0, 4))
            head = tk.Frame(box, bg=C["card_hi"])
            head.pack(fill="x", padx=p(6), pady=(p(3), 0))
            label(head, "📖", fg="accent_hi", bg="card_hi", size=8).pack(side="left")
            link(head, part["section"], lambda url=BASE + part["url"]: webbrowser.open(url), bg="card_hi",
                 fg="accent_hi", size=8).pack(side="left")
            for column, cell in part["facts"]:
                line = tk.Frame(box, bg=C["card_hi"])
                line.pack(fill="x", padx=p(6))
                label(line, f"{column}: ", fg="muted", bg="card_hi", size=8).pack(side="left", anchor="n")
                where = self.map_named(cell) if column == "Where" else None
                if where:
                    link(line, cell, lambda m=where: self.start_route(key, m), bg="card_hi", size=8).pack(side="left")
                else:
                    label(line, cell, fg="text", bg="card_hi", size=8, anchor="w", justify="left",
                          wraplength=self.wrap(80) - tkfont.Font(font=(FONT, widgets.font_size(8))).measure(
                              f"{column}: ")).pack(side="left", fill="x")
            for note in [n for n in part["notes"] if not self.map_named(n)][:6]:  # not a bare place name
                label(box, f"• {note}", fg="muted", bg="card_hi", size=8, anchor="w", justify="left",
                      wraplength=self.wrap(80)).pack(fill="x", padx=p(6))
            chips = tk.Frame(box, bg=C["card_hi"])
            chips.pack(fill="x", padx=p(6), pady=(p(2), p(4)))
            for npc, map_id in part["npcs"]:
                button(chips, f"{ICON['gps']} {npc}", lambda m=map_id, n=npc: self.start_route(key, m, None, n),
                       bg="button", fg="green", size=8, padx=p(4),
                       tip=f"GPS to {npc} in {self.db.maps.get(map_id, {}).get('displayName', map_id)}").pack(
                    side="left", padx=(0, p(3)))
            for name, map_id in part["stages"]:
                link(chips, name, lambda m=map_id: webbrowser.open(f"{BASE}/maps/{m}"), bg="card_hi", fg="link",
                     size=8).pack(side="left", padx=(p(2), 0))
        if entries:
            return
        hint = self.hints.get(qid)
        if qid not in self.hints:
            self.fetch_hint(qid)
        if not hint:
            return
        box = tk.Frame(body, bg=C["card_hi"])
        box.pack(fill="x", pady=(0, 4))
        said = hint["text"] if len(hint["text"]) <= 280 else hint["text"][:277].rsplit(" ", 1)[0] + "…"
        words = label(box, f"💬 {self.db.quests[qid].get('npc') or 'NPC'}: “{said}”", fg="muted", bg="card_hi", size=8,
                      anchor="w", justify="left", wraplength=self.wrap(70))
        words.pack(fill="x", padx=p(6), pady=(p(3), p(2)))
        if said != hint["text"]:
            Tooltip(words, hint["text"])
        if hint["maps"]:
            chips = tk.Frame(box, bg=C["card_hi"])
            chips.pack(fill="x", padx=p(6), pady=(0, p(4)))
            for name, map_id in dict(hint["maps"]).items():
                button(chips, f"{ICON['gps']} {name}", lambda m=map_id: self.start_route(key, m), bg="button",
                       fg="green", size=8, padx=p(4)).pack(side="left", padx=(0, p(3)))

    # ---------- trainer ----------

    def trainer_context(self):
        """What the trainer decides from, as plain values (see trainer.py)."""
        db, level = self.db, self.state["level"]
        scores = [v["score"] for v in (self.quest_value(db.quests[qid]) for qid in self.state["active"]) if v]
        return {"level": level, "map": self.state.get("map"), "active": list(self.state["active"]),
                "quests": db.quests, "done": {qid: self.done_steps(qid) for qid in self.state["active"]},
                "guides": self.guides, "dist": self.distances(), "map_data": db.map_data,
                "npc_map": lambda name: (npc_map(db, name) or {}).get("mapId"),
                "mob_name": lambda mid: (db.monsters.get(int(mid)) or {}).get("display") or str(mid),
                "suggestions": self.suggested_quests(limit=8, sort="value"),
                "active_score": max(scores, default=0),
                "goals": {qid: goal for qid in self.state["active"] for goal in [self.quest_goal(qid)] if goal},
                "training": db.training_maps(level, limit=None)}

    def trainer_tick(self, force=False):
        """With ▶ on: plan again when something changed and steer the GPS to the step. A quest
        taken, finished or turned in, a level-up or a new guide counts as an event (plan from
        scratch); a map change only switches to a step that's clearly closer from there."""
        if not self.state.get("trainer_on") or not self.db.quests or self._trainer_busy:
            return
        active = self.state["active"]
        events = (tuple(active), tuple(tuple(self.state["done"].get(q, [])) for q in active),
                  self.state["level"], tuple(q for q in active if q in self.guides))
        sig = (events, self.state.get("map"))
        if sig == self._trainer_sig and not force:
            return
        event = force or not self._trainer_sig or events != self._trainer_sig[0]
        self._trainer_sig = sig
        self._trainer_busy = True  # following the step redraws, which can come back here
        try:
            if self.trainer.update(self.trainer_context(), event) or (
                    self.trainer.step and "trainer" not in self.routes):
                self._follow_trainer(announce=True)
        finally:
            self._trainer_busy = False

    def _follow_trainer(self, announce=False):
        step = self.trainer.step
        if step and step["map"]:
            self.start_route("trainer", step["map"], step["mobs"] or None, step["npc"])
            if announce:
                self.set_status(f"▶ Next: {step['text']} · {step['reason']}", "gold")
        else:
            self._end_route("trainer")
            if self.gps_key == "trainer":
                self.close_gps()
            self.render()
        self.refresh_pill()

    def toggle_trainer(self):
        self.state["trainer_on"] = not self.state.get("trainer_on")
        self._paint_trainer()
        if self.state["trainer_on"]:
            self.trainer, self._trainer_sig = trainer.Trainer(), None
            self.trainer_tick(force=True)
            if not self.trainer.step:
                self.render()
                self.refresh_pill()
        else:
            self._end_route("trainer")
            if self.gps_key == "trainer":
                self.close_gps()
            self.set_status("Trainer paused: the GPS only goes where you send it")
            self.render()
            self.refresh_pill()

    def skip_trainer_step(self):
        self._trainer_busy = True
        try:
            self.trainer.skip(self.trainer_context())
            self._follow_trainer(announce=True)
        finally:
            self._trainer_busy = False

    def _paint_trainer(self):
        on = bool(self.state.get("trainer_on"))
        self.trainer_btn.fg = C["accent_hi"] if on else C["bar_muted"]
        self.trainer_btn.config(text="❚❚" if on else "▶", fg=self.trainer_btn.fg)

    def render_trainer_card(self):
        """Top of the Quests tab while the trainer is on: the step, why, Skip and Pause."""
        step, p = self.trainer.step, lambda n: widgets.px(self.root, n)
        card = tk.Frame(self.scroll.inner, bg=C["card_hi"])
        card.pack(fill="x", padx=6, pady=(4, 4))
        head = tk.Frame(card, bg=C["card_hi"])
        head.pack(fill="x", padx=p(8), pady=(p(6), 0))
        label(head, "▶ TRAINER", fg="accent_hi", bg="card_hi", size=8, bold=True).pack(side="left")
        button(head, "❚❚ Pause", self.toggle_trainer, bg="button", fg="muted", size=8, padx=p(4),
               tip="Stop leading the way").pack(side="right")
        if step:
            button(head, "Skip ›", self.skip_trainer_step, bg="button", fg="text", size=8, padx=p(4),
                   tip="Something else (this one is left out until you restart the app)").pack(
                side="right", padx=(0, p(4)))
        label(card, step["text"] if step else "Nothing worth doing from here right now",
              fg="gold" if step else "muted", bg="card_hi", size=10, bold=bool(step), anchor="w",
              justify="left", wraplength=self.wrap(40)).pack(fill="x", padx=p(8), pady=(p(2), 0))
        if step:
            label(card, step["reason"], fg="muted", bg="card_hi", size=8, anchor="w", justify="left",
                  wraplength=self.wrap(40)).pack(fill="x", padx=p(8))
        if step and step["kind"] in ("pickup", "turn_in") and step["quest"] in self.db.quests:
            label(card, f"🎁 {quest_rank.reward_text(self.db.quests[step['quest']], limit=3)}", fg="gold",
                  bg="card_hi", size=8, anchor="w", justify="left", wraplength=self.wrap(40)).pack(
                fill="x", padx=p(8), pady=(p(2), 0))
        self.render_reward_prefs(card, bg="card_hi")
        tk.Frame(card, bg=C["card_hi"], height=p(4)).pack()

    # ---------- data loaded ----------

    def _on_loaded(self, _):
        if not self.db.quests:
            return
        if getattr(self.db, 'access_paused', False):
            self.set_status('NiaDB updates paused: renewed site permission required; using saved data', 'gold')
        elif self.db.offline:
            self.set_status(f"Offline: meowdb.com unreachable, using saved data ({len(self.db.quests)} quests)")
        elif not self.state["auto_sync"]:
            self.set_status("AUTO is off: quests and counts update only when you press ⟳ (the GPS still follows you)",
                            "gold")
        else:
            self.set_status("Following the game (AUTO)")
        self.state["active"] = [q for q in self.state["active"] if q in self.db.quests]
        self.refresh_map_label()
        self.set_tab(self.state["tab"])
        self.prefetch()
        self._schedule_auto_sync()
        self.trainer_tick(force=True)

    def open_data_status(self):
        sources = getattr(self.db, 'data_sources', {})
        stamps = [row['fetched_at'] for row in sources.values() if row.get('fetched_at')]
        date = time.strftime('%Y-%m-%d', time.localtime(min(stamps))) if stamps else 'Unknown'
        paused = getattr(self.db, 'access_paused', False)
        text = (f'NiaDB data\n\n{len(self.db.quests)} quests · {len(self.db.maps)} maps · '
                f'{len(self.db.monsters)} monsters\nOldest loaded data: {date}\n\n')
        if paused:
            text += ('Live updates are paused: NiaDB withdrew this tool\'s old permission. '
                     'Saved data remains available. New content requires renewed permission from '
                     'contact@meowdb.com. Rules: https://meowdb.com/reuse\n\n'
                     'No repeated requests will be sent while access is paused.')
            messagebox.showinfo('NiaDB data', text, parent=self.root)
        elif messagebox.askyesno('NiaDB data', text + 'Download updated indexes now? This runs in the background.', parent=self.root):
            def loaded(value):
                self.guides.clear()
                self._on_loaded(value)
            self.run_bg(self.db.refresh_indexes, loaded)

    def refresh_map_label(self):
        m = self.db.maps.get(self.state.get("map") or "")
        text = (f"{ICON['here']} {m['displayName']} · {m.get('displayStreet', '')}" if m
                else f"{ICON['here']} Location unknown: keep the minimap visible")
        if self.map_label.cget("text") != text:
            self.map_label.config(text=text)
        self.refresh_pill()
        self.render_levelup()

    def prefetch(self):
        """Resolve guides for every active quest in the background, so opening one is instant."""
        for qid in self.state["active"]:
            self.fetch_hint(qid)
            if qid not in self.guides and qid not in self.pending:
                self.pending.add(qid)
                q = self.db.quests[qid]
                self.run_bg(lambda q=q: self.resolve_guide(q), lambda g, qid=qid: self._on_guide(qid, g))

    # ---------- rendering ----------

    def wrap(self, margin=70):
        """Pixels a line of text may use at the window's current width (minus `margin` for
        indents and buttons). Fixed widths cut text off in a narrow window."""
        return max(140, self.panel_width() - margin)

    def _on_window_resize(self, e):
        """Redraw to fit once the width has settled (not on every pixel while dragging)."""
        if (e.widget is not self.root or self.collapsed or self._render_width is None
                or abs(e.width - self._render_width) < 8):
            return
        if self._refit_job:
            self.root.after_cancel(self._refit_job)
        self._refit_job = self.root.after(250, self._refit)

    def _refit(self):
        self._refit_job = None
        if not self.collapsed:
            self.render()

    def render(self, keep_scroll=True):
        self._render_width = self.panel_width()
        n = len(self.state["active"])
        quests = self.tab_btns["quests"]
        if quests.cget("text") != (f"Quests {n}" if n else "Quests"):
            quests.config(text=f"Quests {n}" if n else "Quests")
        # the whole content area (location line, list and scrollbar) is painted once, when the
        # new content is complete
        with frozen(self.body):
            self.refresh_map_label()
            self.scroll.clear(keep_scroll)
            {"train": self.render_training, "mobs": self.render_monsters, "pq": self.render_pq,
             "items": self.render_items}.get(self.state["tab"], self.render_quests)()
            self.scroll.commit()
        self._fit_height()
        self.render_gps()

    def _fit_height(self):
        """The expanded panel is only as tall as what it shows, up to its most height (the height
        you last dragged its bottom edge to), so a short list never leaves a big empty panel."""
        if self.collapsed or not self.root.winfo_viewable():
            return
        self.root.update_idletasks()
        chrome = self.root.winfo_reqheight() - self.scroll.winfo_reqheight()  # all but the list
        want = chrome + self.scroll.inner.winfo_reqheight() + widgets.px(self.root, 4)
        h = max(widgets.px(self.root, MIN_PANEL_H), min(want, self.state["panel_size"][1]))
        if abs(h - self.root.winfo_height()) > 2:
            self._place(self.state["panel_size"][0], h, at=(self.root.winfo_x(), self.root.winfo_y()))

    def quest_display_order(self):
        tracked = set(self.state["tracked"])
        return sorted(self.state["active"], key=lambda qid: qid not in tracked)

    def render_quests(self):
        active = self.quest_display_order()
        if self.state.get("trainer_on"):
            self.render_trainer_card()
        if not active:
            label(self.scroll.inner, "No quests yet.\n\nClick \"Reset from Quest window\", then press Q in "
                  "the game: every quest you have is read in. Quests you also put in the game's Quest "
                  "Helper get live tracking.", fg="muted", wraplength=self.wrap(70),
                  justify="left", padx=10, pady=12).pack(anchor="w")
        focus = self.focused()
        if focus:  # isolated: just this quest, open, and the way back to all of them
            bar = tk.Frame(self.scroll.inner, bg=C["bg"])
            bar.pack(fill="x", padx=6, pady=(4, 2))
            label(bar, "◉ Focus", fg="accent_hi", size=8, bold=True).pack(side="left")
            link(bar, f"All quests ({len(active)}) ▸", lambda: self.toggle_focus(focus), bg="bg", fg="muted",
                 size=8).pack(side="right")
            self.state["expanded"] = focus
            self.render_card(focus)
            label(self.scroll.inner, "Collapse (▴) to keep just its objectives in view.", fg="muted", size=8,
                  wraplength=self.wrap(40), justify="left", padx=8, pady=4).pack(anchor="w")
            return
        for qid in active:
            self.render_card(qid)
        self.render_suggestions()
        tools = tk.Frame(self.scroll.inner, bg=C["bg"])
        tools.pack(fill="x", padx=6, pady=4)
        button(tools, "⟲ Reset from Quest window", self.start_reset, bg="button", fg="gold", size=8,
               tip="Re-read every quest from the game's Quest window (you press Q)").pack(side="left")
        if active:
            button(tools, "Clear list", self.clear_quests, bg="bg", fg="muted", size=8,
                   tip="Remove every quest from this list").pack(side="right")

    def dist_from(self, map_id):
        """Portals-away from any map (cached: the map graph doesn't change while running)."""
        key = (map_id, self.cabs())
        if key not in self._dist_from:
            self._dist_from[key] = self.db.distances(map_id, self.cabs())
        return self._dist_from[key]

    def quest_value(self, q):
        """quest_rank's estimate for one quest from where you are now (None: can't be reached)."""
        npc_map_of = lambda name: (npc_map(self.db, name) or {}).get("mapId")
        return quest_rank.estimate(self.db, q, self.state["level"], self.distances() or None, self.dist_from,
                                   npc_map_of, self.guides.get(q["id"]), self.reward_prefs())

    def suggested_quests(self, limit=SUGGESTIONS, sort=None):
        """Quests worth picking up now: level and prerequisites met, not on the list or hidden,
        not class-specific or event/daily ones, and not far below your level. Sorted by "value"
        (default: most EXP per minute of estimated effort) or "near" (nearest quest giver).
        Returns (quest, npc map, portals away, estimate or None)."""
        level, dist = self.state["level"], self.distances()
        by_value = (sort or self.state.get("suggest_sort", "value")) == "value"
        hidden = set(self.state.get("hidden_suggestions", []))
        picks = []
        for q in self.db.quests.values():
            jobs = q.get("jobReq") or []
            if (q["id"] in self.state["active"] or q["id"] in hidden or not self.available(q)
                    or (jobs and not (jobs == ["Beginner"] and level < 10))
                    or q.get("endDate") or q.get("isDaily")
                    or (q.get("levelMin") or 0) < level - 20):
                continue
            nm = npc_map(self.db, q.get("npc"))
            away = dist.get(nm["mapId"]) if nm else None
            value = self.quest_value(q) if by_value else None
            if by_value:
                if value is None:
                    continue  # can't get there (yet)
                key = (-value["score"], value["minutes"])
            else:
                key = (away if away is not None else 999, -(q.get("exp") or 0))
            picks.append((key, q, nm, away, value))
        picks.sort(key=lambda p: p[0])
        # tiered quests share a name ("Donating to Henesys" x5): offer each name once, and at
        # most two per quest giver, so the list stays varied
        result, names, per_npc = [], set(), {}
        for _, q, nm, away, value in picks:
            npc = q.get("npc")
            if q["name"] in names or per_npc.get(npc, 0) >= 2:
                continue
            names.add(q["name"])
            per_npc[npc] = per_npc.get(npc, 0) + 1
            result.append((q, nm, away, value))
            if len(result) == limit:
                break
        for q, *_, value in result:  # look up the real droppers, then rank again with them
            if value and value["guessed"]:
                self.fetch_rank_guide(q)
        return result

    def fetch_rank_guide(self, q):
        """Download a suggested quest's guide (which monster drops each item) in the background,
        so its estimate stops being a guess. Each quest is tried once per run."""
        qid = q["id"]
        if qid in self.guides or qid in self.pending or qid in self._rank_tried:
            return
        self._rank_tried.add(qid)
        self.pending.add(qid)

        def done(steps):
            self.pending.discard(qid)
            if isinstance(steps, dict):
                return  # offline or failed: keep the cautious guess
            self.guides[qid] = steps
            try:
                write_atomic(GUIDES_FILE, json.dumps({"v": GUIDES_VERSION, "guides": self.guides}))
            except OSError:
                pass
            if self.state["tab"] == "quests" and self.state.get("suggest_open", True):
                self.render()
        self.run_bg(lambda: self.resolve_guide(q), done)

    def render_suggestions(self):
        open_ = self.state.get("suggest_open", True)
        head = tk.Frame(self.scroll.inner, bg=C["bg"])
        head.pack(fill="x", padx=6, pady=(8, 0))
        link(head, ("▾" if open_ else "▸") + f" {ICON['idea']} Quests you could take now", self.toggle_suggestions,
             bg="bg", fg="gold", size=9).pack(side="left")
        if not open_:
            return
        sort = self.state.get("suggest_sort", "value")
        head = tk.Frame(self.scroll.inner, bg=C["bg"])  # own line: in a narrow window they covered the title
        head.pack(fill="x", padx=6)
        for key, text, tip in (("near", "Nearest", "Closest quest giver first"),
                               ("value", "Best EXP/min", "Most EXP for the time it takes (an estimate: walking, "
                                                         "kills and drops at your level)")):
            button(head, text, lambda k=key: self.set_suggest_sort(k), bg="button" if key == sort else "bg",
                   fg="gold" if key == sort else "muted", size=8, padx=4, tip=tip).pack(side="right", padx=1)
        if not self.state.get("trainer_on"):  # with the trainer on, its card has them
            self.render_reward_prefs(self.scroll.inner)
        picks = self.suggested_quests()
        if not picks:
            label(self.scroll.inner, "Nothing new for your level here. Raise Lv (top right) or "
                  "finish quests to unlock follow-ups.", fg="muted", size=8, wraplength=self.wrap(60),
                  justify="left", padx=10).pack(anchor="w")
            return
        for q, nm, away, value in picks:
            row = tk.Frame(self.scroll.inner, bg=C["card"])
            row.pack(fill="x", padx=5, pady=1)
            text = tk.Frame(row, bg=C["card"])
            text.pack(side="left", fill="x", expand=True, padx=6, pady=2)
            name = label(text, q["name"], fg="text", bg="card", anchor="w", wraplength=self.wrap(150),
                         justify="left")
            name.pack(anchor="w")
            # one short line (level, distance, EXP, time); who gives it and the details on hover
            far = "" if away is None else " · here" if away == 0 else f" · {away} away"
            short = f"Lv {q.get('levelMin') or 0}{far} · {q.get('exp', 0):,} EXP"
            if q.get("mesos"):
                short += f" · {q['mesos']:,} m"
            if quest_rank.reward_items(q):
                short += " · 🎁"
            if value:
                short += f" · ≈{value['minutes']:.0f} min"
            label(text, short, fg="green" if value and not value["tough"] else "muted", bg="card", size=7,
                  anchor="w", wraplength=self.wrap(150), justify="left").pack(anchor="w")
            where = f" at {nm.get('displayMapName') or nm['mapName']}" if nm else ""
            details = f"From {q.get('npc')}{where}\nReward: {quest_rank.reward_text(q, limit=4)}"
            if value:
                details += (f" · ≈{value['minutes']:.0f} min ({quest_rank.effort_words(value['minutes'])})"
                            f" · {value['exp_per_min']:,.0f} EXP/min" + (" · jump quest" if value["jump"] else "")
                            + (" · rough estimate" if value["guessed"] else "")
                            + (" · tough monsters" if value["tough"] else ""))
            Tooltip(name, details)
            button(row, "✕", lambda q=q: self.hide_suggestion(q["id"]), bg="card", fg="muted", padx=4,
                   tip="Don't suggest this one again").pack(side="right")
            button(row, "＋", lambda q=q: self.add_quest(q["id"]), bg="button", fg="green", padx=6,
                   tip="Add to my list").pack(side="right", padx=2)

    def render_reward_prefs(self, parent, bg="bg"):
        """ "Also count: Mesos · Items · Citizenship": what the ranking (and the trainer) values
        besides EXP. Shared by the suggestions and the trainer card."""
        prefs = set(self.state.get("reward_prefs") or ())
        row = tk.Frame(parent, bg=C[bg])
        row.pack(fill="x", padx=6, pady=(2, 2))
        label(row, "Also count:", fg="muted", bg=bg, size=8).pack(side="left", padx=(0, 4))
        for key, text, tip in (("mesos", "Mesos", "Mesos count as much EXP as they usually come with at your level"),
                               ("items", "Items", f"Quests that give items count {round(quest_rank.ITEM_BONUS * 100)}% "
                                                  f"more ({round(quest_rank.SCROLL_BONUS * 100)}% for scrolls)"),
                               ("citizen", "Citizenship", "Contribution to your town counts too (citizenship grades): "
                                                          "pick Henesys or Kerning City")):
            on = key in prefs
            if key == "citizen" and on:
                text = self.state.get("citizen_town") or text
            chip = button(row, ("✓ " if on else "") + text, lambda: None, bg="press" if on else "button",
                          fg="text" if on else "muted", size=8, padx=4, tip=tip)
            chip.bind("<Button-1>", lambda e, k=key, c=chip: (self.pick_citizen_town(c) if k == "citizen" and
                                                               k not in prefs else self.toggle_reward_pref(k)) or "break")
            chip.pack(side="left", padx=(0, 2))

    def reward_prefs(self):
        """The "Also count" switches for quest_rank: Citizenship carries your town."""
        town = self.state.get("citizen_town")
        return tuple(f"citizen:{town}" if p == "citizen" and town else p for p in self.state.get("reward_prefs") or ())

    def pick_citizen_town(self, anchor):
        """Citizenship needs a town (you're a citizen of one): a small choice under the switch."""
        pop = widgets.Popover(anchor)
        label(pop.body, "Your town", fg="muted", bg="header", size=8, anchor="w", padx=10).pack(fill="x", pady=(6, 2))

        def choose(town):
            pop.close()
            self.state["citizen_town"] = town
            if "citizen" not in (self.state.get("reward_prefs") or []):
                self.toggle_reward_pref("citizen")
            else:
                self.render()
        for town in quest_rank.CITIZEN_TOWNS:
            widgets.menu_item(pop.body, town, lambda t=town: choose(t)).pack(fill="x")
        tk.Frame(pop.body, bg=C["header"], height=4).pack()
        pop.show()

    def toggle_reward_pref(self, key):
        prefs = list(self.state.get("reward_prefs") or ())
        prefs.remove(key) if key in prefs else prefs.append(key)
        self.state["reward_prefs"] = prefs
        if self.state.get("trainer_on"):
            self.trainer_tick(force=True)  # the best quest may be another one now
        self.render()

    def set_suggest_sort(self, how):
        self.state["suggest_sort"] = how
        self.render()

    def toggle_suggestions(self):
        self.state["suggest_open"] = not self.state.get("suggest_open", True)
        self.render()

    def hide_suggestion(self, qid):
        self.state.setdefault("hidden_suggestions", []).append(qid)
        self.render()

    def done_steps(self, qid):
        return set(self.state["done"].get(qid, []))

    def quest_share(self, qid):
        """How far along a quest is, 0..1: each objective counts equally, partly done ones by
        their count ("12 / 20" is 0.6 of that objective)."""
        needs = self.db.quests[qid].get("need") or []
        if not needs:
            return 1.0
        done, progress = self.done_steps(qid), self.state["progress"].get(qid, {})
        share = 0.0
        for i, need in enumerate(needs):
            count = need.get("count", 1) or 1
            share += 1.0 if i in done else min(1.0, (progress.get(str(i)) or 0) / count)
        return share / len(needs)

    def render_card(self, qid):
        """One quest. Closed: its name, a progress bar, how many objectives are done and a dot
        when the game tracks it live. Open: the objectives, the best map to go to, where to turn
        it in, and the GPS one click away (the map itself is in the GPS, not in the card)."""
        q = self.db.quests[qid]
        steps = self.guides.get(qid)
        expanded = self.state["expanded"] == qid
        done = self.done_steps(qid)
        progress = self.state["progress"].get(qid, {})
        n_needs = len(q.get("need") or [])
        ready = n_needs == 0 or len([i for i in done if i < n_needs]) >= n_needs
        bg = "card_hi" if expanded else "card"
        p = lambda n: widgets.px(self.root, n)

        card = tk.Frame(self.scroll.inner, bg=C[bg], highlightthickness=1,
                        highlightbackground=C["gold"] if ready and n_needs else C["border"] if expanded else C[bg])
        card.pack(fill="x", padx=5, pady=2)

        head = tk.Frame(card, bg=C[bg])
        head.pack(fill="x", pady=(p(2), 0))
        arrow = label(head, "▾" if expanded else "▸", fg="muted", bg=bg, padx=4)
        arrow.pack(side="left")
        npc=self.db.npc(q.get("npc") or "")
        if npc:portrait(self,head,"npc",npc["id"],npc.get("name") or q["npc"],C[bg],28)
        title = label(head, q["name"], fg="gold", bg=bg, bold=True, anchor="w", justify="left",
                      wraplength=self.panel_width() - p(130), cursor="hand2")
        title.pack(side="left", fill="x", expand=True)
        for w in (head, arrow, title):
            w.bind("<Button-1>", lambda e: self.toggle_card(qid))
        button(head, "✕", lambda: self.remove_quest(qid), bg=bg, fg="muted", padx=4,
               tip="Remove from list").pack(side="right")
        on = self.focused() == qid
        button(head, "◉", lambda: self.toggle_focus(qid), bg=bg, fg="accent_hi" if on else "muted", padx=3,
               tip="Show all quests again" if on else "Focus: work on just this quest").pack(side="right")
        if expanded and not on and self.state["active"].index(qid) > 0:
            button(head, "▲", lambda: self.move_to_top(qid), bg=bg, fg="muted", padx=3,
                   tip="Move to the top").pack(side="right")
        live = qid in self.state["tracked"]
        if n_needs:
            count = label(head, f"{len([i for i in done if i < n_needs])}/{n_needs}",
                          fg="green" if ready else "muted", bg=bg, size=8)
            count.pack(side="right", padx=(0, 2))
            Tooltip(count, "Objectives done" + ("" if live else ". Counts follow the game as you kill or loot "
                                                                 "(from its gold progress lines)"))
        if live:
            dot = label(head, "●", fg="green", bg=bg, size=7)
            dot.pack(side="right", padx=(0, p(3)))
            Tooltip(dot, "Live: in the game's Quest Helper, its counts update by themselves")
        bar = self.quest_bars[qid] = widgets.Bar(card, self.quest_share(qid), bg=bg, done=ready)
        bar.pack(fill="x", padx=(p(22), p(10)), pady=(p(2), p(5) if not expanded else p(3)))
        self.render_quest_rewards(card,bg,qid)
        if not expanded:
            return

        body = tk.Frame(card, bg=C[bg])
        body.pack(fill="x", padx=(p(22), 6), pady=(0, 4))
        self.render_quest_guide(body, bg, qid)
        turn_in = q.get("completeNpc") or q.get("npc")
        nm = npc_map(self.db, turn_in)

        # where to go: the map covering the most unfinished objectives (more in "Maps per objective")
        best = self.best_maps(qid, q, steps) if steps and not ready else []
        if best:
            b = best[0]
            row = tk.Frame(body, bg=C[bg])
            row.pack(fill="x", pady=(0, 3))
            name = self.db.maps.get(b["map"], {}).get("displayName", b["map"])
            button(row, f"{ICON['gps']} Go", lambda: self.start_route(qid, b["map"], b["mobs"]), bg="button",
                   fg="green", size=8, padx=p(5), tip=f"GPS to {name}").pack(side="right")
            label(row, f"{ICON['best']} ", fg="gold", bg=bg, size=8).pack(side="left")
            where = tk.Frame(row, bg=C[bg])
            where.pack(side="left", fill="x", expand=True)
            link(where, name, lambda: self.start_route(qid, b["map"], b["mobs"]), bg=bg,
                 fg="green" if b["dist"] == 0 else "link", size=8, anchor="w").pack(anchor="w")
            d = b["dist"]
            away = "here" if d == 0 else f"{d} portal{'s' if d != 1 else ''}" if d is not None else ""
            n, total = len(b["covers"]), b["open"]
            covers = ("covers all" if total > 1 else "") if n == total else f"{n} of {total} objectives"
            label(where, " · ".join(t for t in (f"{b['count']} mobs", covers, away) if t), fg="muted", bg=bg,
                  size=7, anchor="w").pack(anchor="w")
        elif steps is None:
            label(body, "Finding where to go...", fg="muted", bg=bg, size=8).pack(anchor="w", pady=2)

        if any(need.get('mobId') is not None for need in q.get('need') or []) or any(step.get('lines') for step in steps or []):
            self.render_objective_map_sort(body,bg)
        # objectives, written like the game: "have / need Name"
        for i, need in enumerate(q.get("need") or []):
            step = steps[i] if steps and i < len(steps) else {}
            name = step.get("name") or need["name"].replace("Defeat ", "")
            count = need.get("count", 1)
            have = progress.get(str(i))
            is_done = i in done
            if is_done and have is None:
                have = count
            text = f"{'–' if have is None else have} / {count}  {name}"
            row = tk.Frame(body, bg=C[bg])
            row.pack(fill="x")
            check = label(row, "✔" if is_done else "☐", fg="green" if is_done else "muted", bg=bg, cursor="hand2")
            check.pack(side="left")
            check.bind("<Button-1>", lambda e, i=i: self.toggle_step(qid, i))
            text_label = label(row, text, fg="muted" if is_done else "text", bg=bg, anchor="w")
            text_label.pack(side="left")
            text_label.objective_name = name  # for update_numbers()
            self.objective_labels[(qid, i)] = text_label
            if step.get("level"):
                Tooltip(text_label, f"{'Kill' if 'mobId' in need else 'Loot'} · monster Lv {step['level']}")
            if not is_done and step.get('sources'):
                self.render_acquisition_sources(body,bg,qid,step)
            self.render_objective_monster_maps(body,bg,qid,i,need,step,is_done)
            if not is_done and steps and self.all_maps.get(qid):
                if step.get("note"):
                    label(body, step["note"], fg="muted", bg=bg, size=8, wraplength=self.wrap(80),
                          justify="left").pack(anchor="w", padx=16)
        for text in q.get("textObjectives") or []:
            label(body, f"• {text}", fg="text", bg=bg, anchor="w", wraplength=self.wrap(80),
                  justify="left").pack(anchor="w")

        # turn-in
        row = tk.Frame(body, bg=C[bg])
        row.pack(fill="x", pady=(3, 0))
        label(row, "★ Turn in: " if ready else "➜ Turn in: ", fg="gold" if ready else "muted",
              bg=bg, size=8, bold=ready).pack(side="left")
        label(row, turn_in or "?", fg="text", bg=bg, size=8, bold=ready).pack(side="left")
        if nm:
            label(row, " · ", fg="muted", bg=bg, size=8).pack(side="left")
            link(row, nm.get("displayMapName") or nm["mapName"],
                 lambda: self.start_route(qid, nm["mapId"], None, turn_in), bg=bg, size=8).pack(side="left")
        if qid in self.routes:
            self.render_route_slot(body, qid)
        actions = tk.Frame(body, bg=C[bg])
        actions.pack(fill="x", pady=(4, 2))
        if steps and not ready:
            showing = self.all_maps.get(qid)
            link(actions, "▾ Hide notes" if showing else "▸ Notes",
                 lambda: self.toggle_all_maps(qid), bg=bg, fg="muted", size=8).pack(side="left")
        button(actions, "✓ Complete", lambda: self.complete_quest(qid), bg="button", fg="green", size=8,
               tip="Turned in: remove it and suggest the next quest").pack(side="right")

    def order_maps(self, maps, mob_id, sort="mobs"):
        """[[map_id, name], ...] for one monster, best first. "mobs": most of that monster,
        then the shortest trip; "near": shortest trip, then most monsters. Once we know where
        you are, maps you can't get to (e.g. Maple Island's "Mushroom Garden" from Victoria
        Island) are left out, unless that would leave nothing."""
        dist = self.distances()
        count = lambda mid: self.mob_count(mid, mob_id)
        reachable = [m for m in maps if m[0] in dist]
        options = reachable if dist and reachable else list(maps)
        if sort == "near":
            return sorted(options, key=lambda m: (dist.get(m[0], 999), -count(m[0])))
        return sorted(options, key=lambda m: (-count(m[0]), dist.get(m[0], 999)))

    def render_acquisition_sources(self,parent,bg,qid,step,all_sources=False):
        sources=item_sources.ranked_sources(step.get('sources') or [],self.distances())
        for source in sources if all_sources else sources[:1]:
            target=item_sources.nearest_target(source,self.distances())
            if not target:continue
            row=tk.Frame(parent,bg=C[bg]);row.pack(fill='x',padx=14,pady=(2,4))
            route=lambda source=source,target=target:self.start_route(qid,target[0],None,source.get('npc'))
            button(row,'GPS',route,bg='button',fg='green',size=8,padx=4,
                   tip='Route to '+target[1]).pack(side='right',padx=(4,0))
            verb='Buy' if source['kind']=='shop' else 'Break / collect'
            title=f"{verb}: {source['name']}"
            if source.get('price') is not None:title+=f" · {source['price']:,.0f} mesos each"
            title+='\n'+target[1]
            if source.get('citizen'):title+=' · '+str(source['citizen'])+' required'
            info=link(row,title,route,bg=bg,size=8,anchor='w',justify='left',wraplength=max(140,self.wrap(110)))
            info.pack(side='left',fill='x',expand=True)
            Tooltip(info,('Break the named object and collect its drops. Drop reports are community sourced; drops are not guaranteed.\n' if source['kind']=='breakable' else 'Buy from the named NPC. Any citizenship requirement is shown.\n')+source.get('source',''))
        if sources and not all_sources and (len(sources)>1 or len(sources[0].get('maps',[]))>1):
            button(parent,'Other sources…',lambda:self.open_acquisition_sources(qid,step),bg=bg,size=8,padx=6).pack(anchor='w',padx=14,pady=(0,3))

    def open_acquisition_sources(self,qid,step):
        window=self.ui_dialog('Sources · '+step['name'])
        area=ScrollArea(window);area.pack(fill='both',expand=True)
        for source in item_sources.ranked_sources(step.get('sources') or [],self.distances()):
            for target in sorted(source.get('maps') or [],key=lambda row:self.distances().get(row[0],10**9)):
                self.render_acquisition_sources(area.inner,'bg',qid,{'sources':[{**source,'maps':[target]}]},True)
        area.commit()

    def render_map_line(self, parent, bg, qid, line, sort="mobs", limit=MAX_MAPS):
        row = tk.Frame(parent, bg=C[bg])
        row.pack(fill="x", padx=16)
        if line.get("prefix"):
            label(row, line["prefix"], fg="muted", bg=bg, size=8).pack(anchor="w")
        # simple flow layout: start a new row when the next map name would not fit
        room = self.panel_width() - 80
        maps, used = None, room
        dist = self.distances()
        count = lambda mid: self.mob_count(mid, line.get("mob"))
        for mid, name in self.order_maps(line["maps"], line.get("mob"), sort)[:limit]:
            here = mid == self.state.get("map")
            away = dist.get(mid)
            # in "nearest" order the distance is what matters, so show it too
            far = f" · {away} away" if sort == "near" and away else ""
            text = name + (" (here)" if here else "") + (f" ×{count(mid)}" if count(mid) else "") + far
            width = tkfont.Font(family=FONT, size=widgets.font_size(8)).measure(text) + 14
            if maps is None or used + width > room:  # measured, so "×N" can't push it off
                maps, used = tk.Frame(row, bg=C[bg]), 0
                maps.pack(anchor="w")
            elif used:
                label(maps, "·", fg="muted", bg=bg, size=8).pack(side="left", padx=2)
            l = link(maps, text, lambda mid=mid: self.start_route(qid, mid, line.get("mob")),
                     bg=bg, fg="green" if here else "link", size=8)
            l.pack(side="left")
            used += l.winfo_reqwidth() + 12

    def cabs(self):
        """Whether routes may use the Regular Cab (off unless ticked in the GPS window)."""
        return bool(self.state.get("allow_cabs"))

    def mob_count(self, map_id, mob_id):
        """How many of a monster spawn on a map (0 if unknown)."""
        for mob in (self.db.map_data.get(map_id) or {}).get("monsters") or []:
            if str(mob.get("id")) == str(mob_id):
                return mob.get("count") or 0
        return 0

    def distances(self):
        """Portals-away from the current map to every map (cached per current map)."""
        cur = self.state.get("map")
        if self._dist[0] != (cur, self.cabs()):
            self._dist = ((cur, self.cabs()), self.db.distances(cur, self.cabs()) if cur else {})
        return self._dist[1]

    def best_maps(self, qid, q, steps):
        """Maps for the quest's unfinished objectives (a monster to kill, or one that drops a
        needed item, spawns there), ranked by how many of those monsters the map has, then by
        objectives covered, then by distance."""
        done = self.done_steps(qid)
        n_needs = len(q.get("need") or [])
        wanted = {i: {str(line["mob"]) for line in steps[i].get("lines", [])}
                  for i in range(min(n_needs, len(steps))) if i not in done}
        wanted = {i: mobs for i, mobs in wanted.items() if mobs}
        if not wanted:
            return []
        dist = self.distances()
        ranked = []
        for m in self.db.map_data.values():
            here = {str(mob["id"]): mob.get("count", 0) for mob in m.get("monsters") or []}
            covers = [i for i, mobs in wanted.items() if mobs & here.keys()]
            if not covers or (dist and m["id"] not in dist):
                continue  # once we know where you are, skip maps you can't get to from there
            mobs = tuple(sorted({mob for i in covers for mob in wanted[i] & here.keys()}))
            ranked.append({"map": m["id"], "covers": covers, "open": len(wanted), "mobs": mobs,
                           "dist": dist.get(m["id"]), "count": sum(here[mob] for mob in mobs)})
        # the user's priority: most of the needed monsters first (faster kills and drops), then
        # how many objectives the map covers, then the shortest trip
        ranked.sort(key=lambda b: (-b["count"], -len(b["covers"]),
                                   b["dist"] if b["dist"] is not None else 999))
        return ranked

    def route_preview(self, key):
        """While navigating: the current map with the portal to take highlighted."""
        goal, mob, npc = self.routes[key]
        cur = self.state.get("map")
        if cur == goal:
            return goal, mob, npc, None
        steps = self.db.route(cur, goal, self.cabs()) if cur else None
        if steps:
            first = steps[0][1]
            if first.get("transport"):  # a ship or taxi: star the NPC to talk to
                return cur, None, first.get("npc") or None, None
            return cur, None, None, first["name"]
        return None

    def render_minimap(self, parent, key, target):
        map_id, mob, npc, exit_portal = target
        m = self.db.maps.get(map_id, {})
        box = tk.Frame(parent, bg=C["bg"], highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="x", pady=(6, 0))
        top = tk.Frame(box, bg=C["bg"])
        top.pack(fill="x")
        names = tk.Frame(top, bg=C["bg"])
        names.pack(side="left", padx=4)
        label(names, m.get("displayName", map_id), fg="text", bg="bg", size=8, anchor="w",
              wraplength=150, justify="left").pack(anchor="w")
        legend = (("◉ go to the yellow ENTER", "#ffe14d") if exit_portal else (f"★ {npc}", C["gold"]) if npc
                  else ("● where they spawn", "#ff6b6b") if mob else None)
        if legend:
            label(names, legend[0], fg=legend[1], bg="bg", size=7, anchor="w").pack(anchor="w")
        button(top, "↗", lambda: self.open_meowdb_route(map_id), bg="button", size=8,
               tip="Open this route on meowdb.com").pack(side="right")
        if map_id != self.state.get("map") or (key in self.routes and self.routes[key][0] != map_id):
            button(top, f"{ICON['gps']} Go", lambda: self.start_route(key, map_id, mob, npc),
                   bg="button", fg="green", size=8, tip="Show the way here, portal by portal").pack(side="right", padx=2)
        img_label = label(box, "loading map...", fg="muted", bg="bg", size=8)
        img_label.pack(pady=3)
        cache_key = (map_id, mob, npc, exit_portal)
        if cache_key not in self.images and self.db.has_minimap_file(map_id):
            # already on disk: draw it now (a few ms) instead of flashing "loading map..."
            img = render_minimap(self.db, map_id, mob, npc, exit_portal)
            if img is not None:
                self.images[cache_key] = ImageTk.PhotoImage(img)
        if cache_key in self.images:
            img_label.config(image=self.images[cache_key], text="")
            return

        def show(img):
            if img is None:
                if img_label.winfo_exists():
                    img_label.config(text="No minimap for this map")
                return
            self.images[cache_key] = ImageTk.PhotoImage(img)
            if img_label.winfo_exists():
                img_label.config(image=self.images[cache_key], text="")

        self.run_bg(lambda: render_minimap(self.db, map_id, mob, npc, exit_portal), show)

    def toggle_full_route(self, key):
        self.full_routes.symmetric_difference_update({key})
        self.render()

    def start_route(self, key, goal, mob=None, npc=None):
        self.routes[key] = (goal, mob, npc)
        self.previews.pop(key, None)  # follow the route on the minimap
        self.gps_key = key
        self.open_gps()
        self.render()

    def stop_route(self, key):
        if key == "trainer" and self.state.get("trainer_on"):
            self.toggle_trainer()  # ✕ on the GPS: you don't want to be led now
            return
        self._end_route(key)
        self.render()

    def _end_route(self, key):
        self.routes.pop(key, None)
        self.previews.pop(key, None)
        if key == self.gps_key:
            self.gps_key = None
            self.close_gps()

    def _drop_gone_quest_routes(self):
        """A quest that left the list (done, removed, turned in, or gone after a Reset) takes its
        route with it. Before, the GPS kept following the old quest and nothing in the list could
        stop it."""
        for key in [k for k in self.routes if k in self.db.quests and k not in self.state["active"]]:
            self._end_route(key)

    # ---------- map search ----------

    MAP_RESULTS = 8

    # words that mean a kind of shop in the map search ("potion" finds the nearest grocer)
    SHOP_WORDS = {"potion": "Grocer", "potions": "Grocer", "grocer": "Grocer", "grocery": "Grocer",
                  "weapon": "Weapon Seller", "weapons": "Weapon Seller", "armor": "Armor Seller",
                  "armour": "Armor Seller", "scroll": "Scroll", "scrolls": "Scroll", "pet": "Pet Food"}

    def find_npcs(self, text):
        """NPCs with a name word starting with each typed word ("stan" → Chief Stan, not
        Assistant), names that start with the
        text first, then the nearest; an NPC on several maps gets its two nearest. [{mapId, npc, label}]"""
        words = text.lower().split()
        if not words or len(text.strip()) < 3:
            return []
        dist = self.distances()
        npcs = {n["id"]: n for n in self.db.npcs.values() if n.get("maps")}
        found = []
        for n in npcs.values():
            name = n.get("displayName") or n["name"]
            parts = re.findall(r"[a-z0-9']+", name.lower())
            if not all(any(part.startswith(w) for part in parts) for w in words):
                continue
            starts = not name.lower().startswith(text.lower().strip())
            maps = sorted(n["maps"], key=lambda m: dist.get(m["mapId"], 999))[:2]
            role = " · " + n["roles"][0].lower() if n.get("roles") else ""
            for m in maps:
                where = m.get("displayMapName") or m.get("mapName") or m["mapId"]
                found.append(((starts, dist.get(m["mapId"], 999), name),
                              {"mapId": m["mapId"], "npc": name, "label": f"{ICON['npc']} {name} · {where}{role}"}))
        return [f[1] for f in sorted(found, key=lambda f: f[0])[:4]]

    def find_shops(self, text):
        """Shops for the map search: by kind ("potion", "weapon shop") or by an item they sell
        ("red potion"), nearest first. [{mapId, npc, label}]"""
        text = text.lower().strip()
        if len(text) < 3:
            return []
        dist = self.distances()
        kinds = {self.SHOP_WORDS[w] for w in text.split() if w in self.SHOP_WORDS}
        # a kind word ("weapon") lists shops of that kind, not every item with the word in it; and a
        # map name ("perion") is a place, not "Return Scroll to Perion"
        by_item = not (kinds and set(text.split()) <= set(self.SHOP_WORDS) | {"shop", "store"}) and             not any(text in m.get("displayName", "").lower() for m in self.db.maps.values())
        found = []
        for shop in self.db.shops:
            where = self.db.maps.get(shop["mapId"], {}).get("displayName", shop["mapId"]).replace(
                "Department Store", "Dept. Store")
            sells = by_item and next(((name, price) for name, price in sorted(shop["stock"].items(),
                                                                             key=lambda x: len(x[0]))
                                      if text in name.lower()), None)
            if sells:  # a named item: show its price
                label_text = f"{ICON['shop']} {shop['npc']} · {where} · {sells[0]} {sells[1]:,} m"
            elif any(k in shop["kind"] for k in kinds) or text in shop["kind"].lower():
                label_text = f"{ICON['shop']} {shop['npc']} ({shop['kind']}) · {where}"
            else:
                continue
            found.append((dist.get(shop["mapId"], 999), {"mapId": shop["mapId"], "npc": shop["npc"],
                                                         "label": label_text}))
        return [f[1] for f in sorted(found, key=lambda f: f[0])[:4]]

    def find_maps(self, text):
        """Maps whose name (or street, or an NPC on it) matches every typed word: names that start
        with the text first, then by how close they are."""
        words = text.lower().split()
        if not words:
            return []
        dist = self.distances()
        found = []
        for m in self.db.maps.values():
            name = m.get("displayName", "").lower()
            haystack = name + " " + (m.get("searchText") or "")
            if all(w in haystack for w in words):
                rank = 0 if name.startswith(text.lower().strip()) else 1 if all(w in name for w in words) else 2
                away = dist.get(m["id"])
                found.append((rank, away is None, away or 0, name, m))
        return [f[-1] for f in sorted(found, key=lambda f: f[:4])[:self.MAP_RESULTS]]

    def open_map_search(self, anchor, correct=False):
        """A small search box under `anchor`: type part of a map's name (or an NPC on it), click a
        result (or press Enter for the first) and the GPS shows the way there. With `correct`
        ("I'm on:", from the location line) the pick is where you are instead."""
        if getattr(self, "map_search", None) and self.map_search.winfo_exists():
            self.map_search.destroy()
        pop = self.map_search = tk.Toplevel(self.root, bg=C["border"])
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.withdraw()  # placed once its size is known, so it never shows up somewhere else first
        inner = tk.Frame(pop, bg=C["bg"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        top = tk.Frame(inner, bg=C["bg"])
        top.pack(fill="x", padx=4, pady=4)
        title = label(top, f"{ICON['here']} I'm on:" if correct else f"{ICON['gps']} GPS to:", fg="accent_hi",
                      size=9, bold=True, cursor="fleur")
        title.pack(side="left")
        button(top, "✕", pop.destroy, bg="bg", fg="muted", padx=4, tip="Close").pack(side="right")
        grip = label(top, "⠿ drag", fg="muted", size=7, cursor="fleur")
        grip.pack(side="right", padx=4)
        for w in (top, title, grip):  # drag by the top row; the spot is remembered for next time
            w.bind("<ButtonPress-1>", lambda e: setattr(self, "_search_drag", (e.x_root - pop.winfo_x(),
                                                                                e.y_root - pop.winfo_y())))
            w.bind("<B1-Motion>", self._move_map_search)
        query = tk.StringVar()
        entry = widgets.entry(inner, query, width=30)
        entry.pack(fill="x", padx=6, pady=(0, 4), ipady=2)
        hint = label(inner, "Type a map, street or NPC, or a shop: potion, weapon, red potion...", fg="muted",
                     size=8, anchor="w")
        hint.pack(fill="x", padx=6, pady=(0, 4))
        rows, results = [], []
        for i in range(self.MAP_RESULTS):  # fixed rows whose text changes: typing doesn't rebuild them
            row = label(inner, "", fg="link", bg="bg", size=9, anchor="w", justify="left", cursor="hand2", padx=6)
            row.bind("<Button-1>", lambda e, i=i: pick(i))
            row.bind("<Enter>", lambda e, r=row: r.config(bg=C["card_hi"]))
            row.bind("<Leave>", lambda e, r=row: r.config(bg=C["bg"]))
            rows.append(row)

        def pick(i):
            if i < len(results):
                r = results[i]
                pop.destroy()
                if correct:
                    self.correct_location(r["mapId"])
                else:
                    self.start_route("map", r["mapId"], None, r["npc"])

        def update(*_):
            # NPCs by name, then shops (by kind or by something they sell), then maps by name
            results[:] = self.find_npcs(query.get())
            seen = {(r["mapId"], r["npc"]) for r in results}
            results.extend(r for r in self.find_shops(query.get()) if (r["mapId"], r["npc"]) not in seen)
            del results[self.MAP_RESULTS:]
            results.extend({"mapId": m["id"], "npc": None, "label": f"{m['displayName']}   ·  {m.get('displayStreet', '')}"}
                           for m in self.find_maps(query.get())[:self.MAP_RESULTS - len(results)])
            dist = self.distances()
            for i, row in enumerate(rows):
                if i < len(results):
                    r = results[i]
                    away = dist.get(r["mapId"])
                    far = "you're here" if away == 0 else f"{away} away" if away is not None else "no known way"
                    row.config(text=f"{r['label']} · {far}", fg=C["gold"] if r["npc"] else C["link"])
                    row.pack(fill="x", pady=(0, 2 if i == len(results) - 1 else 0))
                else:
                    row.pack_forget()
            text = ("Type a map, street or NPC, or a shop: potion, weapon, red potion..."
                    if not query.get().strip() else "" if results else "No map or shop with that name")
            hint.config(text=text)
            if text:
                hint.pack(fill="x", padx=6, pady=(0, 4), before=rows[0] if rows[0].winfo_ismapped() else None)
            else:
                hint.pack_forget()
        query.trace_add("write", update)
        entry.bind("<Return>", lambda e: pick(0))
        entry.bind("<Escape>", lambda e: pop.destroy())
        pop.update_idletasks()
        w, h = pop.winfo_reqwidth(), pop.winfo_reqheight() + 8 * 22  # room for the results as they come
        saved = self.state.get("search_pos")
        user32 = ctypes.windll.user32
        if saved and all(user32.MonitorFromPoint(ctypes.wintypes.POINT(px, saved[1] + 10), 0)
                         for px in (saved[0] + 20, saved[0] + w - 20)):  # still on a screen
            x, y = saved
        else:  # right edge under the button, on the same monitor as the button
            x, y = widgets.on_monitor_of(anchor, anchor.winfo_rootx() + anchor.winfo_width() - w,
                                         anchor.winfo_rooty() + anchor.winfo_height() + 2, w, h)
        pop.geometry(f"+{x}+{y}")
        pop.deiconify()
        pop.after(50, lambda: (pop.focus_force(), entry.focus_set()))

    def _move_map_search(self, e):
        x, y = e.x_root - self._search_drag[0], e.y_root - self._search_drag[1]
        self.map_search.geometry(f"+{x}+{y}")
        self.state["search_pos"] = [x, y]

    # ---------- GPS window ----------

    def render_route_slot(self, parent, key):
        """Inside a card: a one-line pointer to the GPS, which shows every route (from any tab);
        "Show" brings it back if it was closed or showed another route."""
        if key not in self.routes:
            return
        goal = self.routes[key][0]
        shown = key == self.gps_key and self.gps and self.gps.winfo_exists()
        row = tk.Frame(parent, bg=C["bg"], highlightthickness=1, highlightbackground=C["border_hi"])
        row.pack(fill="x", pady=(6, 0))
        label(row, f"{ICON['gps']} GPS to {self.db.maps.get(goal, {}).get('displayName', goal)}"
              + (" is open" if shown else ""), fg="green", bg="bg", size=8, anchor="w").pack(side="left", padx=4, pady=2)
        button(row, "✕", lambda: self.stop_route(key), bg="bg", fg="muted", padx=4,
               tip="Stop navigating").pack(side="right")
        if not shown:
            button(row, "Show", lambda: self.show_gps(key), bg="button", size=8, padx=4,
                   tip="Bring the GPS back").pack(side="right", padx=2)

    def show_gps(self, key):
        self.gps_key = key
        self.open_gps()
        self.render()

    def _gps_position(self):
        """Saved spot, or just right of the game's minimap (top-left of the game window): next to
        the map you compare it with, without covering the map name the sync reads."""
        mm = getattr(self, "_minimap", None)
        if mm and self.state.get("gps_docked", True):
            return [mm[2] + 1, mm[1]]
        saved = self.state.get("gps_pos")
        if saved and self._on_screen(saved[0], saved[1], widgets.px(self.root, GPS_STRIP[0])):
            return saved
        box = find_game_window()
        if box:
            return [box[0] + int((box[2] - box[0]) * MINIMAP_CORNER[0]) + widgets.px(self.root, 8),
                    box[1] + widgets.px(self.root, 8)]
        left, top, _, _ = widgets.work_area(self.root.winfo_x(), self.root.winfo_y())
        return [left + widgets.px(self.root, 320), top + widgets.px(self.root, 8)]

    def open_gps(self):
        """The GPS: a slim strip with the next move (big arrow, where to go, which map it leads
        to). The map with the portal marked and every step open below it with ▾."""
        if not (self.gps and self.gps.winfo_exists()):
            g = self.gps = tk.Toplevel(self.root, bg=C["border_hi"])
            g.overrideredirect(True)
            g.attributes("-topmost", True)
            self._alpha(g, self.state.get("gps_alpha", GPS_ALPHA))  # also click-through, if on
            self._gps_hovered = None
            p = lambda n: widgets.px(self.root, n)
            outer = tk.Frame(g, bg=C["header"])
            outer.pack(fill="both", expand=True, padx=1, pady=1)
            strip = tk.Frame(outer, bg=C["header"])
            strip.pack(fill="x")
            side = tk.Frame(strip, bg=C["header"])
            side.pack(side="right", fill="y")
            self._gps = {"side": side}
            button(side, "✕", lambda: self.stop_route(self.gps_key) if self.gps_key else self.close_gps(),
                   bg="header", fg="bar_muted", size=8, padx=p(5), tip="Stop navigating").pack(side="top")
            more = button(side, "▾", self.toggle_gps_details, bg="header", fg="bar_muted", size=10, padx=p(5),
                          tip="The map and every step")
            more.pack(side="top")
            picture = tk.Label(strip, bg=C["header"], bd=0, padx=0, pady=0, cursor="fleur")
            picture.pack(side="left")
            for w in (strip, picture):  # drag the strip anywhere; the spot is remembered
                w.bind("<ButtonPress-1>", self._start_move_gps)
                w.bind("<B1-Motion>", self._move_gps)
                w.bind("<ButtonRelease-1>", self._end_move_gps)
                w.bind("<MouseWheel>", lambda e: self.set_gps_opacity(
                    self.state.get("gps_alpha", GPS_ALPHA) + (0.05 if e.delta > 0 else -0.05)) or "break")
            Tooltip(picture, "Drag to move (it stops following the minimap) · mouse wheel: opacity · ▴ hide the map")
            self._gps.update(strip=picture, more=more)
            self._build_gps_details(outer)
            x, y = self._gps_position()
            g.geometry(f"+{x}+{y}")
        else:
            self.gps.deiconify()
            self.gps.lift()
        self.render_gps()

    def _start_move_gps(self, e):
        self._gps_drag = (e.x_root - self.gps.winfo_x(), e.y_root - self.gps.winfo_y())
        self._gps_drag_from = (self.gps.winfo_x(), self.gps.winfo_y())

    def _move_gps(self, e):
        if self.state.get("pinned") or not getattr(self, "_gps_drag", None):
            return
        self.gps.geometry(f"+{e.x_root - self._gps_drag[0]}+{e.y_root - self._gps_drag[1]}")

    def _end_move_gps(self, _):
        """A real drag puts the GPS where you dropped it and undocks it; a click (it moved a few
        pixels at most) changes nothing, so clicking the GPS never undocks it."""
        if not (getattr(self, "_gps_drag", None) and self.gps and self.gps.winfo_exists()):
            return
        self._gps_drag = None
        g = self.gps
        x, y = g.winfo_x(), g.winfo_y()
        x0, y0 = getattr(self, "_gps_drag_from", (x, y))
        if abs(x - x0) + abs(y - y0) <= 3:
            g.geometry(f"+{x0}+{y0}")
            return
        if not self._on_screen(x, y, g.winfo_width()):  # dropped off every screen
            left, top, right, bottom = widgets.work_area(x, y)
            x, y = max(left, min(x, right - g.winfo_width())), max(top, min(y, bottom - g.winfo_height()))
            g.geometry(f"+{x}+{y}")
        self.state["gps_pos"] = [x, y]
        if self.state.get("gps_docked", True):
            self.state["gps_docked"] = False
            self._gps_shown = None
            self.render_gps()  # back to its own size
            self.set_status("GPS undocked: it stays where you put it (⇱ docks it to the minimap again)")

    def dock_gps(self):
        """Put the GPS back against the game's minimap, and keep it there when maps change."""
        self.state["gps_docked"] = True
        self._gps_shown = None
        self._dock_gps_now()
        self.render_gps()

    def _dock_gps_now(self):
        """Docked (the default), the GPS sits against the right edge of the game's minimap and is
        exactly as tall, so their top and bottom lines are level. Minimaps differ in size from
        map to map, so it moves and resizes along whenever you change maps; not after you drag
        it somewhere else yourself (until you dock it again)."""
        g, mm = self.gps, getattr(self, "_minimap", None)
        if not (g and g.winfo_exists() and mm) or not self.state.get("gps_docked", True) \
                or getattr(self, "_gps_drag", None):
            return
        x, y = mm[2] + 1, mm[1]
        if (g.winfo_x(), g.winfo_y()) != (x, y):
            g.geometry(f"+{x}+{y}")
            self.state["gps_pos"] = [x, y]
        self.render_gps()  # redraws only if the minimap's size changed

    def _gps_step_aside(self):
        """The minimap of the map you just entered is wider than the last one and runs under the
        docked GPS, so its right edge (and part of its name) can't be seen. Move the GPS its own
        width to the right; the next sync sees the whole minimap and docks it exactly again."""
        g = self.gps
        if not (g and g.winfo_exists()) or not self.state.get("gps_docked", True) or getattr(self, "_gps_drag", None):
            return
        x = g.winfo_x() + g.winfo_width() + widgets.px(self.root, 8)
        g.geometry(f"+{x}+{g.winfo_y()}")

    def _build_gps_details(self, outer):
        """What ▾ opens under the strip: the map with the portal (or NPC, or spawns) marked, and
        a row of controls. A fixed size: a window that grew and shrank with its text showed the
        new size a moment before the content (a flicker)."""
        g = self._gps
        w, h = self._gps_layout()["details"]
        details = g["details"] = tk.Frame(outer, bg=C["bg"], width=w, height=h)
        details.pack_propagate(False)
        controls = g["controls"] = tk.Frame(details, bg=C["bg"])
        g["picture"] = tk.Label(details, bg=C["bg"], bd=0, padx=0, pady=0, anchor="n")
        g["picture"].pack(fill="both", expand=True)
        g["steps"] = link(controls, "▸ Every step", lambda: self.toggle_full_route(self.gps_key), bg="bg",
                          fg="muted", size=8)
        g["steps"].pack(side="left")
        button(controls, "↗", lambda: self.open_meowdb_route(self.routes[self.gps_key][0]), bg="button",
               size=8, tip="Open this route on meowdb.com").pack(side="right")
        find = button(controls, ICON["search"], lambda: self.open_map_search(find), bg="button", size=8,
                      padx=4, tip="Go somewhere else: a map, NPC or shop")
        find.pack(side="right", padx=2)
        g["size"] = button(controls, "⤢", self.cycle_gps_size, bg="button", size=8, padx=4,
                           tip="GPS size: small / medium / large (when not docked)")
        g["size"].pack(side="right", padx=2)
        g["dock"] = button(controls, "⇱", self.dock_gps, bg="button", size=8, padx=4,
                           tip="Dock to the game's minimap: same height, follows it when you change maps")
        g["dock"].pack(side="right", padx=2)
        g["cabs"] = tk.BooleanVar(value=self.cabs())
        tk.Checkbutton(controls, text="Taxis", variable=g["cabs"], bg=C["bg"], fg=C["muted"],
                       selectcolor=C["card_hi"], activebackground=C["bg"], activeforeground=C["text"],
                       font=(FONT, widgets.font_size(8)), command=lambda: self.set_cabs(g["cabs"].get())
                       ).pack(side="right", padx=4)
        if self.state.get("gps_details", True):
            details.pack(fill="x")

    def _gps_scale(self):
        return GPS_SIZES[self.state.get("gps_size", 0) % len(GPS_SIZES)]

    def cycle_gps_size(self):
        self.state["gps_size"] = (self.state.get("gps_size", 0) + 1) % len(GPS_SIZES)
        self.set_status(f"GPS size: {('small', 'medium', 'large')[self.state['gps_size']]}"
                        + (" (docked, it matches the minimap; drag it away to use this)"
                           if self._gps_layout()["docked"] else ""))
        self._gps_shown = None
        self.render_gps()

    def _gps_layout(self):
        """Sizes of the GPS parts. Docked next to a minimap we've seen: exactly the minimap's
        height (at least as wide as a small GPS), with the strip on top and the map filling the
        rest. Otherwise the size setting decides, with room for the steps when they're open."""
        p = lambda n: widgets.px(self.root, n)
        side = self._gps["side"].winfo_reqwidth() if getattr(self, "_gps", None) else p(26)
        side_h = self._gps["side"].winfo_reqheight() if getattr(self, "_gps", None) else p(40)
        mm = getattr(self, "_minimap", None)
        if mm and self.state.get("gps_docked", True):
            inner_w = max(mm[2] - mm[0] + 1, p(215)) - 2  # the window has a 1 px rim
            inner_h = mm[3] - mm[1] + 1 - 2
            strip_h = max(side_h, min(p(44), round(inner_h * 0.27)))
            return {"docked": True, "strip": (inner_w - side, strip_h), "details": (inner_w, inner_h - strip_h),
                    "scale": strip_h / p(GPS_STRIP[1])}
        s = self._gps_scale()
        strip = (p(GPS_STRIP[0] * s), max(side_h, p(GPS_STRIP[1] * s)))
        lines = 0
        if self.gps_key in self.full_routes and self.gps_key in self.routes and self.state.get("map"):
            lines = len(self.db.route(self.state["map"], self.routes[self.gps_key][0], self.cabs()) or [])
        # the map and its text scale with the GPS size; the row of buttons doesn't
        h = round((GPS_DETAILS_HEIGHT + p(95) + min(lines, 12) * p(17)) * s) + p(30)
        return {"docked": False, "strip": strip, "details": (strip[0] + side, h), "scale": s}

    def toggle_gps_details(self):
        self.state["gps_details"] = not self.state.get("gps_details", True)
        if self.gps and self.gps.winfo_exists():
            details = self._gps["details"]
            if self.state["gps_details"]:
                details.pack(fill="x")
            else:
                details.pack_forget()
            self._gps_shown = None
            self.render_gps()

    def _show_gps_controls(self, show):
        """Docked, the GPS is all map: its buttons appear over the bottom of the map only while
        the mouse is on it (laid over the map, so the map itself doesn't move)."""
        g = getattr(self, "_gps", None)
        if not g or not g["details"].winfo_exists():
            return
        if show or not g.get("docked"):
            g["controls"].place(relx=0, rely=1, anchor="sw", relwidth=1)
            g["controls"].lift()
        else:
            g["controls"].place_forget()

    def set_gps_opacity(self, alpha):
        """The GPS window's own opacity (while the mouse is away from it): mouse wheel over it."""
        alpha = round(min(1.0, max(0.3, alpha)), 2)
        self.state["gps_alpha"] = alpha
        self.set_status(f"GPS opacity {round(alpha * 100)}% (when the mouse is away)")
        if self.gps and self.gps.winfo_exists():
            self._alpha(self.gps, alpha)  # show the new level now
            self._gps_hovered = None
            self._gps_preview_until = time.monotonic() + 1.2

    def close_gps(self):
        if self.gps and self.gps.winfo_exists():
            self.gps.destroy()
        self.gps, self._gps_shown = None, None

    def render_gps(self):
        """The strip (and, opened, the map), each drawn as one picture and redrawn only when what
        it shows changes, so updates can't flicker."""
        if not (self.gps and self.gps.winfo_exists()):
            return
        key = self.gps_key
        if key not in self.routes:
            self.close_gps()
            return
        opened = bool(self.state.get("gps_details", True))
        layout = self._gps_layout()
        shown = (key, self.routes[key], self.state.get("map"), self.previews.get(key), self.cabs(),
                 key in self.full_routes, widgets.text_scale, opened, layout["strip"], layout["details"])
        if shown == getattr(self, "_gps_shown", None):
            return  # same route, same place, same size: nothing to change
        view = self.gps_view(key, with_map=opened)
        self._gps_shown = shown
        g = self._gps
        g["docked"] = layout["docked"]
        # same text size as the rest of the overlay: Tk's pixels per point, times the text size
        points = self.root.winfo_fpixels("1p") * widgets.text_scale * layout["scale"]
        self._gps_strip_photo = ImageTk.PhotoImage(gps_image.compose_strip(view, *layout["strip"], points))
        g["strip"].config(image=self._gps_strip_photo)  # keep a reference or Tk drops it
        g["more"].config(text="▴" if opened else "▾")
        if not opened:
            return
        w, h = layout["details"]
        details = g["details"]
        if (int(details.cget("width")), int(details.cget("height"))) != (w, h):
            details.config(width=w, height=h)
        for part, needed in ((g["steps"], not layout["docked"]), (g["size"], not layout["docked"]),
                             (g["dock"], not layout["docked"])):
            if part.winfo_ismapped() != needed:
                part.pack(side="left" if part is g["steps"] else "right", padx=0 if part is g["steps"] else 2) \
                    if needed else part.pack_forget()
        if layout["docked"]:  # all map, the buttons only on hover
            picture = gps_image.compose_map(view, w, h, points)
        else:
            room = h - widgets.px(self.root, 30)
            picture = gps_image.compose(view, w, points, header=False)
            full = Image.new("RGB", (w, max(room, picture.height)), C["bg"])  # always the same size
            full.paste(picture, (0, 0))
            picture = full
        self._gps_photo = ImageTk.PhotoImage(picture)
        g["picture"].config(image=self._gps_photo)
        self._show_gps_controls(bool(self._gps_hovered))
        g["cabs"].set(self.cabs())
        steps = "▴ Hide steps" if key in self.full_routes else "▸ Every step"
        if g["steps"].cget("text") != steps:
            g["steps"].config(text=steps)

    def gps_view(self, key, with_map=True):
        """What the GPS shows, as plain values for gps_image: a `headline` and `sub` line and an
        arrow (or a `state`) for the strip; the NEXT card, the maps after it and the minimap for
        the opened part. A minimap that isn't downloaded yet is fetched, then the GPS redraws."""
        goal, mob, npc = self.routes[key]
        cur = self.state.get("map")
        goal_name = self.db.maps.get(goal, {}).get("displayName", goal)
        view = {"title": f"Route to {goal_name}"}
        steps = self.db.route(cur, goal, self.cabs()) if cur and cur != goal else None
        if not cur:
            view.update(state="wait", headline="Finding where you are…", sub="Keep the minimap visible, AUTO on",
                        message="Finding where you are... keep the game's minimap (with the map name) "
                                "visible and AUTO on.")
        elif cur == goal:
            look = f"★ {npc}" if npc else "the red spawn dots" if mob else "your target"
            view.update(state="there", headline=f"You're at {goal_name}", sub=f"Look for {look}",
                        message=f"You're there! Look for {look}.")
        elif steps is None:
            view.update(state="lost", headline="No known way there", sub=f"to {goal_name}",
                        message=f"No known way from {self.db.maps.get(cur, {}).get('displayName', cur)} to there.")
        else:
            mid, portal = steps[0]
            detail = self.db.map_detail(mid) or {}
            if portal.get("transport"):
                who = portal.get("npc") or "the NPC"
                view.update(arrow="talk", where=f"Talk to {who} (★ on the map)",
                            then_do=portal["transport"][0].upper() + portal["transport"][1:], headline=f"Talk to {who}")
            else:
                symbol, where = portal_direction(detail, portal)
                view.update(arrow={"▶": "right", "◀": "left", "▲": "up", "▼": "down"}.get(symbol, "right"),
                            where=where, then_do="Enter the portal there (the yellow ENTER on the map)",
                            headline=where)
            view.update(step=f"NEXT  ·  step 1 of {len(steps)}", dest=f"→ {portal['toMapName']}",
                        sub=f"→ {portal['toMapName']}   ·   {1}/{len(steps)}")
            rest = [p["toMapName"] for _, p in steps[1:]]
            if len(rest) > 3:  # the next two maps and the destination; the full list is one click away
                rest = rest[:2] + [f"… {len(rest) - 3} more"] + rest[-1:]
            if rest:
                view["chain"] = "Then: " + " → ".join(rest)
            if key in self.full_routes:
                view["steps"] = []
                for i, (m_id, p) in enumerate(steps):
                    d = self.db.map_detail(m_id) or {}
                    how = p["transport"] if p.get("transport") else f"take the portal on the {portal_side(d, p)}"
                    view["steps"].append(f"{i + 1}. In {d.get('name', m_id)}: {how} → {p['toMapName']}")
        if not with_map:
            return view
        map_id, mob_, npc_, exit_portal = (self.previews.get(key) or self.route_preview(key)
                                           or (goal, mob, npc, None))
        view["map_name"] = self.db.maps.get(map_id, {}).get("displayName", map_id)
        view["legend"], view["legend_colour"] = (
            ("◉ go to the yellow ENTER", "#ffe14d") if exit_portal else (f"★ {npc_}", C["gold"]) if npc_
            else ("● where they spawn", "#ff6b6b") if mob_ else ("", C["muted"]))
        if not self.db.has_minimap_file(map_id) and (map_id, "gps") not in self.pending:
            self.pending.add((map_id, "gps"))

            def arrived(_, map_id=map_id):
                self.pending.discard((map_id, "gps"))
                self._gps_shown = None
                self.render_gps()
            self.run_bg(lambda: self.db.minimap_png(map_id), arrived,
                        on_error=lambda _: self.pending.discard((map_id, "gps")))
        mm = render_minimap(self.db, map_id, mob_, npc_, exit_portal) if self.db.has_minimap_file(map_id) else None
        s = 1 if self._gps_layout()["docked"] else self._gps_scale()  # docked, the map is fitted to the minimap's size
        if mm is not None and s != 1:  # the GPS size setting: the map with it
            mm = mm.resize((round(mm.width * s), round(mm.height * s)), Image.LANCZOS if s < 1 else Image.NEAREST)
        view["minimap"] = mm
        return view

    def set_cabs(self, allow):
        self.state["allow_cabs"] = allow
        for key in self.routes:
            self.previews.pop(key, None)
        self.render()

    def preview(self, key, map_id, mob=None, npc=None, exit_portal=None):
        self.previews[key] = (map_id, mob, npc, exit_portal)
        if self.state["tab"] == "quests":
            self.state["expanded"] = key
        self.render()

    def render_training(self):
        inner = self.scroll.inner
        mobs = lambda m: m.get("totalMobCount") or 0
        exp = lambda m: m.get("expPerHour") or 0
        away_of = lambda m: self.distances().get(m["id"], 999)
        level = self.state["level"]
        dist = self.distances()
        sort = self.state.get("train_sort") or "mobs"
        if sort == "near" and not dist:
            sort = "mobs"  # no location yet: fall back to the most monsters
        top = tk.Frame(inner, bg=C["bg"])
        top.pack(fill="x", padx=6, pady=4)
        label(top, f"Lv {level} (mobs Lv {max(1, level - 3)}-{level + 5})", fg="muted",
              size=8).pack(side="left")
        for key, text, tip in (("exp", "EXP", "Most EXP per hour first"),
                               ("near", "Nearest", "Closest to where you are first"),
                               ("mobs", "Most mobs", "Maps with the most monsters first")):
            active = key == sort
            button(top, text, lambda k=key: self.set_train_sort(k), bg="button" if active else "bg",
                   fg="gold" if active else "muted", size=8, padx=4, tip=tip).pack(side="right", padx=1)
        if self.state.get("train_sort") == "near" and not dist:
            label(inner, "Waiting to see where you are: keep the game's minimap visible and AUTO on.",
                  fg="muted", size=8, wraplength=self.wrap(60), justify="left", padx=6).pack(anchor="w")
        # every sort breaks ties by the number of monsters: more mobs = faster kills
        order = {"mobs": lambda m: (-mobs(m), away_of(m), -exp(m)),
                 "exp": lambda m: (-exp(m), -mobs(m)),
                 "near": lambda m: (away_of(m), -mobs(m), -exp(m))}[sort]
        maps = sorted(self.db.training_maps(level, limit=None), key=order)[:TRAINING_MAPS]
        opened = self.state.get("train_open")
        for m in maps:
            card = tk.Frame(inner, bg=C["card"])
            card.pack(fill="x", padx=5, pady=2)
            row = tk.Frame(card, bg=C["card"], cursor="hand2")
            row.pack(fill="x")
            left = tk.Frame(row, bg=C["card"])
            left.pack(side="left", fill="x", expand=True, padx=6, pady=2)
            name = label(left, m["displayName"], fg="gold", bg="card", bold=True, anchor="w")
            name.pack(anchor="w")
            away = dist.get(m["id"])
            away = (" · you're here" if away == 0 else f" · {away} portal{'s' if away != 1 else ''} away"
                    if away else "")
            sub = label(left, f"{m.get('displayStreet', '')} · avg Lv {m['avgMobLevel']:.0f}{away}",
                        fg="muted", bg="card", size=8, anchor="w", justify="left", wraplength=self.wrap(170))
            sub.pack(anchor="w")
            # packed before the name column so the numbers always get their room
            label(row, f"{mobs(m)} mobs\n{exp(m):,} EXP/h", fg="green", bg="card", size=8,
                  justify="right").pack(side="right", padx=6, before=left)
            for w in (row, left, name, sub):
                w.bind("<Button-1>", lambda e, mid=m["id"]: self.toggle_training(mid))
            if m["id"] == opened:
                body = tk.Frame(card, bg=C["card"])
                body.pack(fill="x", padx=6, pady=(0, 4))
                here = self.render_map_monsters(body, m["id"])
                self.render_route_slot(body, "train")
                self.render_minimap(body, "train", self.previews.get("train")
                                    or ("train" in self.routes and self.route_preview("train"))
                                    or (m["id"], here or None, None, None))

    def render_map_monsters(self, parent, map_id):
        """What lives on a map: "Zombie Mushroom ×61 (Lv 24)", most first. Clicking one shows
        where it spawns on the minimap. Returns all their ids (to mark every spawn by default)."""
        mobs = sorted((self.db.map_data.get(map_id) or {}).get("monsters") or [],
                      key=lambda x: -(x.get("count") or 0))
        if not mobs:
            return ()
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill="x", pady=(2, 2))
        label(row, "Mobs here:", fg="muted", bg="card", size=8).pack(anchor="w")
        for mob in mobs:
            mid = int(mob["id"])
            info = self.db.monsters.get(mid) or {}
            line = tk.Frame(row, bg=C["card"])
            line.pack(anchor="w", padx=10)
            link(line, info.get("display") or mob["name"],
                 lambda mid=mid: self.preview("train", map_id, mob=mid), bg="card", size=8).pack(side="left")
            label(line, f" ×{mob.get('count', 0)}  Lv {info.get('level', '?')}"
                        f"  · {info.get('exp', 0)} EXP", fg="muted", bg="card", size=8).pack(side="left")
        return tuple(int(m["id"]) for m in mobs)

    def _build_level_filter(self, frame):
        """Two small boxes, "Lv from - to", that narrow the monster list by level."""
        self.mob_lv_min, self.mob_lv_max = tk.StringVar(), tk.StringVar()
        box = tk.Frame(frame, bg=C["bg"])
        box.pack(side="right", padx=(0, 6))
        label(box, "Lv", fg="muted", size=8).pack(side="left", padx=(0, 2))
        for i, var in enumerate((self.mob_lv_min, self.mob_lv_max)):
            if i:
                label(box, "-", fg="muted", size=8).pack(side="left", padx=1)
            e = entry(box, var, width=4, justify="center")
            e.pack(side="left", ipady=2)
            Tooltip(e, "Lowest level" if i == 0 else "Highest level")
            var.trace_add("write", lambda *_: self.render(keep_scroll=False))

    def mob_level_range(self):
        """(low, high) from the level boxes; an empty or non-number box means no limit."""
        def num(var):
            text = var.get().strip()
            return int(text) if text.isdigit() else None
        low, high = num(self.mob_lv_min), num(self.mob_lv_max)
        if low is not None and high is not None and low > high:
            low, high = high, low  # typed the other way round
        return low, high

    def _debounce_mob_search(self):
        job = getattr(self, '_mob_search_job', None)
        if job:
            self.root.after_cancel(job)
        def finish():
            self._mob_search_job = None
            if self.state['tab'] == 'mobs':
                self.render(keep_scroll=False)
        self._mob_search_job = self.root.after(150, finish)

    def render_monsters(self):
        inner = self.scroll.inner
        words = self.mob_query.get().lower().split()
        level = self.state["level"]
        low, high = self.mob_level_range()
        if words or low is not None or high is not None:
            mobs = [m for m in self.db.monsters.values()
                    if all(w in (m.get("display") or m["name"]).lower() for w in words)
                    and (low is None or m.get("level", 0) >= low)
                    and (high is None or m.get("level", 0) <= high)]
            mobs.sort(key=lambda m: (m.get("level", 0), m.get("display") or m["name"]))
            levels = ("" if low is None and high is None else
                      f" at Lv {low if low is not None else 1}-{high if high is not None else '∞'}")
            hint = f"{len(mobs)} mob{'s' if len(mobs) != 1 else ''}{levels}" + (" (showing 40)" if len(mobs) > 40 else "")
        else:  # nothing typed yet: monsters around your level
            mobs = sorted((m for m in self.db.monsters.values() if abs(m.get("level", 0) - level) <= 4),
                          key=lambda m: m.get("level", 0))
            hint = f"Near Lv {level} · Search by name or level"
        label(inner, hint, fg="muted", size=8, padx=6, pady=2, anchor="w", justify="left",
              wraplength=self.wrap(30)).pack(fill="x")
        opened = self.state.get("mob_open")
        dist = self.distances()
        for m in mobs[:40]:
            mid = m["id"]
            card = tk.Frame(inner, bg=C["card_hi" if mid == opened else "card"])
            card.pack(fill="x", padx=5, pady=2)
            bg = "card_hi" if mid == opened else "card"
            row = tk.Frame(card, bg=C[bg], cursor="hand2")
            row.pack(fill="x",padx=10,pady=5)
            picture=portrait(self,row,"mob",mid,m.get("display") or m["name"],C[bg],32)
            details=tk.Frame(row,bg=C[bg]);details.pack(side="left",fill="x",expand=True,padx=(4,0))
            name = label(details, m.get("display") or m["name"], fg="gold", bg=bg, bold=True, anchor="w",
                         justify="left",wraplength=self.wrap(105))
            name.pack(fill="x",anchor="w")
            stats = label(details, f"Lv {m.get('level', '?')} · {m.get('hp', 0):,} HP · {m.get('exp', 0)} EXP",
                          fg="muted", bg=bg, size=8,anchor="w",justify="left",wraplength=self.wrap(105))
            stats.pack(fill="x",anchor="w")
            for w in (row,details,name,stats,*([picture] if picture is not None else [])):
                w.bind("<Button-1>", lambda e, mid=mid: self.toggle_monster(mid))
            if mid != opened:
                continue
            body = tk.Frame(card, bg=C[bg])
            body.pack(fill="x", padx=8, pady=(0, 4))
            locs = [[l["mapId"], l["mapName"]] for l in self.db.mob_locations(mid)]
            sort = self.state.get("mob_sort") or "mobs"
            if sort == "near" and not dist:
                sort = "mobs"  # no location yet
            head = tk.Frame(body, bg=C[bg])
            head.pack(fill="x")
            label(head, "Found in:", fg="muted", bg=bg, size=8).pack(side="left")
            for key, text, tip in (("near", "Nearest", "Closest to where you are first"),
                                   ("mobs", "Most mobs", f"Most {m.get('display') or m['name']} first")):
                button(head, text, lambda k=key: self.set_mob_sort(k), bg="button" if key == sort else bg,
                       fg="gold" if key == sort else "muted", size=8, padx=4, tip=tip).pack(side="right", padx=1)
            if locs:
                self.render_map_rows(body, bg, mid, locs, sort)
            else:
                label(body, "No known spawn", fg="muted", bg=bg, size=8).pack(anchor="w", padx=16)
            drops = self.mob_drops.get(mid)
            if drops is None:
                label(body, "Drops: loading...", fg="muted", bg=bg, size=8).pack(anchor="w")
                self.run_bg(lambda mid=mid: self.db.mob_drops(mid), lambda d, mid=mid: self._on_drops(mid, d))
            elif drops:
                label(body, "Drops: " + ", ".join(drops[:12]), fg="text", bg=bg, size=8, wraplength=self.wrap(70),
                      justify="left").pack(anchor="w", pady=(2, 0))
            if "mob" in self.routes:
                self.render_route_slot(body, "mob")
            first = self.order_maps(locs, mid, sort)[:1]  # the minimap shows the top map in that order
            target = self.previews.get("mob") or ("mob" in self.routes and self.route_preview("mob")) \
                or ((first[0][0], mid, None, None) if first else None)
            if target:
                self.render_minimap(body, "mob", target)

    def render_map_rows(self, parent, bg, mob_id, maps, sort, limit=6):
        """Where a mob lives, one map per row: the name on the left, then a clear
        "15 mobs · 3 away" column on the right. The number the list is sorted by is bold."""
        dist = self.distances()
        table = tk.Frame(parent, bg=C[bg])
        table.pack(fill="x", padx=(10, 0), pady=(2, 0))
        for mid, name in self.order_maps(maps, mob_id, sort)[:limit]:
            here = mid == self.state.get("map")
            count, away = self.mob_count(mid, mob_id), dist.get(mid)
            row = tk.Frame(table, bg=C[bg])
            row.pack(fill="x", pady=1)
            # packed right-to-left so the numbers always keep their room
            far = "here" if away == 0 else f"{away} away" if away is not None else ""
            if far:
                label(row, far, fg="green" if here else ("text" if sort == "near" else "muted"), bg=bg,
                      size=8, bold=sort == "near", width=7, anchor="e").pack(side="right")
            label(row, f"{count} mob{'s' if count != 1 else ''}", fg="green" if sort == "mobs" else "muted",
                  bg=bg, size=8, bold=sort == "mobs", width=8, anchor="e").pack(side="right")
            # anchored left and filling the rest, so a long name is cut at its end, not its start
            if not here:
                button(row, ICON["gps"], lambda mid=mid: self.start_route("mob", mid, mob_id), bg="button", fg="green",
                       size=9, padx=5, tip="GPS to this map").pack(side="right", padx=(4, 0))
            link(row, name, lambda mid=mid: self.preview("mob", mid, mob=mob_id), bg=bg,
                 fg="green" if here else "link", size=8, anchor="w", justify="left",
                 wraplength=self.wrap(230)).pack(side="left", fill="x", expand=True)

    def set_mob_sort(self, how):
        self.state["mob_sort"] = how
        self.previews.pop("mob", None)  # let the minimap follow the new top map
        self.render()

    def _on_drops(self, mob_id, drops):
        self.mob_drops[mob_id] = drops or []
        if self.state["tab"] == "mobs" and self.state.get("mob_open") == mob_id:
            self.render()

    # ---------- party quests ----------

    def render_pq(self):
        """Every party quest: requirements, how to get there, each stage (quiz answers, puzzle
        combinations you can cross off as your party tries them), EXP and rewards."""
        inner = self.scroll.inner
        wrap = max(220, self.panel_width() - 70)
        folded_keys = set(self.state.get("pq_folded", []))
        for pq in party_quests.PARTY_QUESTS:
            folded = pq["key"] in folded_keys
            card = tk.Frame(inner, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
            card.pack(fill="x", padx=5, pady=3)
            head = tk.Frame(card, bg=C["card"], cursor="hand2")
            head.pack(fill="x", padx=6, pady=(4, 0))
            arrow = label(head, "▸" if folded else "▾", fg="muted", bg="card")
            arrow.pack(side="left")
            title = label(head, pq["name"], fg="gold", bg="card", bold=True, anchor="w")
            title.pack(side="left", fill="x", expand=True)
            for w in (head, arrow, title):
                w.bind("<Button-1>", lambda e, k=pq["key"]: self.toggle_pq(k))
            body = tk.Frame(card, bg=C["card"])
            body.pack(fill="x", padx=(16, 8), pady=(0, 6))
            label(body, f"{pq['quest']} · Lv {pq['level']} · {pq['party']} · {pq['time']} · channels {pq['channels']}",
                  fg="muted", bg="card", size=8, anchor="w", justify="left", wraplength=wrap).pack(fill="x")
            go = tk.Frame(body, bg=C["card"])
            go.pack(fill="x", pady=(2, 0))
            away = self.distances().get(pq["map"])
            where = self.db.maps.get(pq["map"], {}).get("displayName", pq["map"])
            far = "" if away is None else " · here" if away == 0 else f" · {away} portals"
            button(go, f"{ICON['gps']} Go", lambda pq=pq: self.start_route("pq", pq["map"], None, pq["npc"]), bg="button",
                   fg="green", size=8, tip=f"GPS to {pq['npc']}").pack(side="right")
            label(go, f"Start: {pq['npc']} · {where}{far}", bg="card", size=9, anchor="w", justify="left",
                  wraplength=self.wrap(130)).pack(side="left", fill="x", expand=True)
            if folded:
                continue
            for si, stage in enumerate(pq["stages"]):
                label(body, stage["name"], fg="text", bg="card", bold=True, anchor="w").pack(fill="x", pady=(8, 0))
                label(body, stage["do"], fg="muted", bg="card", size=8, anchor="w", justify="left",
                      wraplength=wrap).pack(fill="x")
                if stage.get("answers"):
                    table = tk.Frame(body, bg=C["card"])
                    table.pack(fill="x", pady=(2, 0))
                    for r, (question, coupons) in enumerate(stage["answers"]):
                        label(table, question, bg="card", size=8, anchor="w", justify="left",
                              wraplength=wrap - 60).grid(row=r, column=0, sticky="w")
                        label(table, str(coupons), fg="green", bg="card", bold=True, anchor="e").grid(
                            row=r, column=1, sticky="e", padx=(8, 0))
                    table.columnconfigure(0, weight=1)
                if stage.get("combos"):
                    label(body, "Tap one your party tried to cross it off:", fg="muted", bg="card", size=8,
                          anchor="w").pack(fill="x", pady=(2, 0))
                    grid = tk.Frame(body, bg=C["card"])
                    grid.pack(fill="x")
                    for ci, combo in enumerate(stage["combos"]):
                        self._pq_chip(grid, (pq["key"], si, combo)).grid(row=ci // 5, column=ci % 5,
                                                                          padx=2, pady=2, sticky="ew")
                if stage.get("tip"):
                    label(body, "Tip: " + stage["tip"], fg="muted", bg="card", size=8, anchor="w", justify="left",
                          wraplength=wrap).pack(fill="x")
            label(body, "EXP", fg="text", bg="card", bold=True, anchor="w").pack(fill="x", pady=(8, 0))
            total = 0
            for mob, lv, exp, count in pq["exp"]:
                total += exp * count
                row = tk.Frame(body, bg=C["card"])
                row.pack(fill="x")
                label(row, f"{mob} (Lv {lv})", bg="card", size=8, anchor="w").pack(side="left")
                label(row, f"{exp:,} × {count} = {exp * count:,}", fg="green", bg="card", size=8).pack(side="right")
            row = tk.Frame(body, bg=C["card"])
            row.pack(fill="x")
            label(row, "Monsters in one run", bg="card", size=8, bold=True, anchor="w").pack(side="left")
            label(row, f"{total:,} EXP", fg="green", bg="card", size=8, bold=True).pack(side="right")
            label(body, pq["exp_note"], fg="muted", bg="card", size=8, anchor="w", justify="left",
                  wraplength=wrap).pack(fill="x")
            label(body, pq["once"], bg="card", size=8, anchor="w", justify="left",
                  wraplength=wrap).pack(fill="x", pady=(2, 0))
            label(body, "Rewards", fg="text", bg="card", bold=True, anchor="w").pack(fill="x", pady=(8, 0))
            for heading, items in pq["rewards"]:
                label(body, heading, fg="muted", bg="card", size=8, anchor="w", justify="left",
                      wraplength=wrap).pack(fill="x")
                label(body, " · ".join(items), bg="card", size=8, anchor="w", justify="left",
                      wraplength=wrap).pack(fill="x", padx=(8, 0), pady=(0, 2))
            for note in pq["notes"]:
                label(body, "• " + note, fg="muted", bg="card", size=8, anchor="w", justify="left",
                      wraplength=wrap).pack(fill="x")
            label(body, "Sources: " + ", ".join(pq["sources"]), fg="muted", bg="card", size=8, anchor="w",
                  justify="left", wraplength=wrap).pack(fill="x", pady=(4, 0))

    def _pq_chip(self, parent, key):
        """A combination to try; clicking crosses it off (only this chip repaints)."""
        chip = label(parent, key[2], bg="button", size=9, padx=4, pady=1, cursor="hand2")

        def paint():
            tried = key in self.pq_tried
            chip.config(fg=C["muted"] if tried else C["text"], bg=C["card"] if tried else C["button"],
                        font=(FONT, widgets.font_size(9), "overstrike" if tried else "normal"))

        def toggle(_):
            self.pq_tried.symmetric_difference_update({key})
            paint()
        chip.bind("<Button-1>", toggle)
        chip.toggle = toggle  # for tests: clicks don't reach a hidden window
        paint()
        return chip

    def toggle_pq(self, key):
        folded = self.state.setdefault("pq_folded", [])
        if key in folded:
            folded.remove(key)
        else:
            folded.append(key)
        self.render()

    # ---------- item drops ----------

    def _debounce_item_search(self):
        if self._item_search_job:
            self.root.after_cancel(self._item_search_job)
        self._item_search_job = self.root.after(400, self._search_items)

    def _search_items(self):
        self._item_search_job = None
        text = self.item_query.get().strip().lower()
        if len(text) >= 2 and text not in self.item_results:
            self.item_results[text] = None

            def done(items, text=text):
                self.item_results[text] = items or []
                if self.state["tab"] == "items":
                    self.render(keep_scroll=False)

            self.run_bg(lambda: self.db.search_items(text), done,
                        on_error=lambda _, text=text: self.item_results.pop(text, None))
        if self.state["tab"] == "items":
            self.render(keep_scroll=False)

    def render_items(self):
        inner = self.scroll.inner
        text = self.item_query.get().strip().lower()
        note = lambda t: label(inner, t, fg="muted", size=8, wraplength=self.wrap(60), justify="left",
                               padx=6, pady=4).pack(anchor="w")
        if len(text) < 2:
            note("Type an item name (e.g. Snail Shell) to see which monsters drop it, "
                 "how often, and how to get to them.")
            return
        results = self.item_results.get(text)
        if results is None:
            note("Searching...")
            return
        if not results:
            note("No items found.")
            return
        opened = self.state.get("item_open")
        for item in results:
            iid = item["id"]
            bg = "card_hi" if iid == opened else "card"
            card = tk.Frame(inner, bg=C[bg])
            card.pack(fill="x", padx=5, pady=2)
            row = tk.Frame(card, bg=C[bg], cursor="hand2")
            row.pack(fill="x")
            name = label(row, item["name"], fg="gold", bg=bg, bold=True, anchor="w")
            name.pack(side="left", padx=6, pady=2)
            sub = label(row, item.get("sub", ""), fg="muted", bg=bg, size=8)
            sub.pack(side="right", padx=6)
            for w in (row, name, sub):
                w.bind("<Button-1>", lambda e, iid=iid: self.toggle_item(iid))
            if iid == opened:
                self.render_item_drops(card, bg, iid, item)

    def item_quests(self, item_id):
        """(quests you bring this item to, quests that give it): game item id -> quest ids."""
        if getattr(self, "_item_index", None) is None:
            index = {}
            for q in self.db.quests.values():
                for need in q.get("need") or []:
                    if need.get("itemId"):
                        index.setdefault(str(need["itemId"]), ([], []))[0].append(q["id"])
                given = list(q.get("get") or []) + [i for c in (q.get("rewardChoices") or []) +
                                                    (q.get("rewardRandom") or []) for i in c.get("items") or []]
                for got in given:
                    if got.get("itemId") and got.get("count", 1) > 0 and q["id"] not in index.get(str(got["itemId"]), ([], []))[1]:
                        index.setdefault(str(got["itemId"]), ([], []))[1].append(q["id"])
            self._item_index = index
        return self._item_index.get(str(item_id), ([], []))

    def render_item_quests(self, body, bg, item):
        """How to get an item no monster drops: the quest that sends you for it, with its guide's
        steps (Pink Anthurium: Sabitrama's Forest of Patience, Shane lets you in), and the quests
        that give it as a reward. True if anything was shown."""
        needed, rewarded = self.item_quests(item.get("iconKey"))
        if not quest_rank.is_quest_item(int(item.get("iconKey") or 0)):
            needed = []  # an ordinary item: the quests that ask for it use it up, they don't give it
        p = lambda n: widgets.px(self.root, n)
        # quests that explain where it is (a guide, or the NPC's words) first, then the rest
        needed = sorted(needed, key=lambda q: (q not in self.db.quest_guides, self.db.quests[q].get("levelMin") or 0))
        for qid in needed[:3]:
            q = self.db.quests[qid]
            row = tk.Frame(body, bg=C[bg])
            row.pack(fill="x", pady=(p(4), p(2)))
            label(row, "🎯 Get it in: ", fg="muted", bg=bg, size=8).pack(side="left", anchor="n")
            label(row, f"{q['name']} · Lv {q.get('levelMin') or 0}+", fg="text", bg=bg, size=8, bold=True,
                  anchor="w", justify="left", wraplength=self.wrap(140)).pack(side="left", fill="x")
            self._quest_start_line(body, bg, q)
            self.render_quest_guide(body, bg, qid, key="item")
        if rewarded:
            label(body, "🎁 A reward of:", fg="muted", bg=bg, size=8).pack(anchor="w", pady=(p(4), 0))
            for qid in sorted(rewarded, key=lambda q: self.db.quests[q].get("levelMin") or 0)[:4]:
                q = self.db.quests[qid]
                label(body, f"{q['name']} · Lv {q.get('levelMin') or 0}+", fg="text", bg=bg, size=8, anchor="w",
                      justify="left", wraplength=self.wrap(70)).pack(fill="x", padx=(p(10), 0))
                self._quest_start_line(body, bg, q, indent=p(10))
        return bool(needed or rewarded)

    def _quest_start_line(self, body, bg, q, indent=0):
        """ "From Sabitrama · Sleepywood · 3 away 🧭": who starts a quest, with the GPS to them."""
        nm = npc_map(self.db, q.get("npc"))
        if not nm:
            return
        row = tk.Frame(body, bg=C[bg])
        row.pack(fill="x", padx=(indent, 0))
        away = self.distances().get(nm["mapId"])
        label(row, f"From {q.get('npc')} · ", fg="muted", bg=bg, size=8).pack(side="left")
        link(row, nm.get("displayMapName") or nm["mapName"], lambda: self.start_route("item", nm["mapId"], None, q.get("npc")),
             bg=bg, size=8).pack(side="left")
        if away is not None:
            label(row, f" · {'here' if away == 0 else f'{away} away'}", fg="muted", bg=bg, size=8).pack(side="left")

    def render_item_shops(self, body, bg, item):
        """Who sells this item (from meowdb's NPC shop list), nearest first, with the price and a
        ➤ to the shopkeeper. Returns True when some shop sells it."""
        sellers = self.db.sold_by.get(str(item.get("iconKey"))) or []
        if not sellers:
            return False
        dist = self.distances()
        sellers = sorted(sellers, key=lambda s: (dist.get(s["mapId"], 999), s["price"]))
        label(body, "Sold by:", fg="muted", bg=bg, size=8).pack(anchor="w", pady=(2, 0))
        for s in sellers[:4]:
            row = tk.Frame(body, bg=C[bg])
            row.pack(fill="x", padx=(10, 0), pady=1)
            where = self.db.maps.get(s["mapId"], {}).get("displayName", s["mapId"]).replace(
                "Department Store", "Dept. Store")
            away = dist.get(s["mapId"])
            here = away == 0
            # the button first, then two lines: who and where (wrapping), price and distance
            if not here:
                button(row, ICON["gps"], lambda s=s: self.start_route("item", s["mapId"], None, s["npc"]), bg="button",
                       fg="green", size=9, padx=5, tip=f"GPS to {s['npc']}").pack(side="right", padx=(4, 0))
            left = tk.Frame(row, bg=C[bg])
            left.pack(side="left", fill="x", expand=True)
            text = f"{s['npc']} · {where}" + (" · citizens only" if s["citizen"] else "")
            link(left, text, lambda s=s: self.preview("item", s["mapId"], npc=s["npc"]), bg=bg,
                 fg="green" if here else "link", size=8, anchor="w", justify="left",
                 wraplength=self.wrap(90)).pack(fill="x")
            far = "here" if here else f"{away} away" if away is not None else ""
            label(left, f"{s['price']:,} mesos" + (f" · {far}" if far else ""), fg="gold", bg=bg, size=8,
                  anchor="w").pack(fill="x")
        if len(sellers) > 4:
            label(body, f"   +{len(sellers) - 4} more shops", fg="muted", bg=bg, size=7).pack(anchor="w")
        return True

    def render_item_drops(self, card, bg, iid, item=None):
        body = tk.Frame(card, bg=C[bg])
        body.pack(fill="x", padx=8, pady=(0, 4))
        sold = self.render_item_shops(body, bg, item or {})
        sold = self.render_item_quests(body, bg, item or {}) or sold
        drops = self.item_drops.get(iid)
        if drops is None:
            label(body, "Loading drops...", fg="muted", bg=bg, size=8).pack(anchor="w")
            if iid not in self.pending:
                self.pending.add(iid)
                self.run_bg(lambda: self.db.item_drop_info(iid), lambda d: self._on_item_drops(iid, d),
                            on_error=lambda _: self.pending.discard(iid))
            return
        if not drops:
            if not sold:
                label(body, "No monster drops this, no shop sells it and no quest gives it (crafting?).", fg="muted",
                      bg=bg, size=8, wraplength=self.wrap(70), justify="left").pack(anchor="w")
            if "item" in self.routes:
                self.render_route_slot(body, "item")
            target = self.previews.get("item") or ("item" in self.routes and self.route_preview("item"))
            if target:
                self.render_minimap(body, "item", target)
            return
        if sold:
            label(body, "Dropped by:", fg="muted", bg=bg, size=8).pack(anchor="w", pady=(4, 0))
        dist = self.distances()
        first = None
        for d in drops[:8]:
            mob = self.db.monsters.get(d["mob"], {})
            locs = sorted(self.db.mob_locations(d["mob"]), key=lambda l: (dist.get(l["mapId"], 999), -l["count"]))
            row = tk.Frame(body, bg=C[bg])
            row.pack(fill="x", pady=(4, 0))
            label(row, f"{d['name']}  Lv {mob.get('level', '?')}", fg="text", bg=bg, bold=True).pack(side="left")
            rate = f"{d['rate']:g}% · {d['odds']}" if d["rate"] is not None else "rate unknown"
            label(row, rate, fg="green" if d["rate"] else "muted", bg=bg, size=8).pack(side="right")
            if not locs:
                label(body, "no known spawn", fg="muted", bg=bg, size=8).pack(anchor="w", padx=10)
                continue
            near = locs[0]
            first = first or (near["mapId"], d["mob"])
            where = tk.Frame(body, bg=C[bg])
            where.pack(fill="x", padx=10)
            # packed first so a long map name can't squeeze the button to "G"
            button(where, f"{ICON['gps']} Go", lambda n=near, d=d: self.start_route("item", n["mapId"], d["mob"]),
                   bg="button", fg="green", size=8).pack(side="right")
            left = tk.Frame(where, bg=C[bg])
            left.pack(side="left", fill="x", expand=True)
            link(left, near["mapName"], lambda n=near, d=d: self.preview("item", n["mapId"], mob=d["mob"]),
                 bg=bg, size=8, anchor="w", justify="left", wraplength=self.wrap(110)).pack(fill="x")
            away = dist.get(near["mapId"])
            details = [] if away is None else ["here" if away == 0 else f"{away} portal{'s' if away != 1 else ''}"]
            if len(locs) > 1:
                details.append(f"+{len(locs) - 1} more maps")
            if details:
                label(left, " · ".join(details), fg="muted", bg=bg, size=7, anchor="w").pack(fill="x")
        if any(d["rate"] is not None for d in drops):
            label(body, "Rates are OSMLib reference values and may differ in Classic.", fg="muted",
                  bg=bg, size=7).pack(anchor="w", pady=(4, 0))
        if "item" in self.routes:
            self.render_route_slot(body, "item")
        target = self.previews.get("item") or ("item" in self.routes and self.route_preview("item")) \
            or ((first[0], first[1], None, None) if first else None)
        if target:
            self.render_minimap(body, "item", target)

    def _on_item_drops(self, iid, drops):
        self.pending.discard(iid)
        self.item_drops[iid] = drops
        if self.state["tab"] == "items" and self.state.get("item_open") == iid:
            self.render()

    def toggle_item(self, iid):
        self.state["item_open"] = None if self.state.get("item_open") == iid else iid
        self._drop_route_unless_gps("item")
        self.previews.pop("item", None)
        self.render()

    def toggle_monster(self, mob_id):
        self.state["mob_open"] = None if self.state.get("mob_open") == mob_id else mob_id
        self._drop_route_unless_gps("mob")
        self.previews.pop("mob", None)
        self.render()

    def _drop_route_unless_gps(self, key):
        """A card closed or switched: forget its route, unless the GPS window is following it."""
        if not (key == self.gps_key and self.gps and self.gps.winfo_exists()):
            self.routes.pop(key, None)

    def set_train_sort(self, how):
        self.state["train_sort"] = how
        self.render(keep_scroll=False)

    def toggle_training(self, map_id):
        opening = self.state.get("train_open") != map_id
        self.state["train_open"] = map_id if opening else None
        self.previews.pop("train", None)
        self.render()

    # ---------- game sync ----------

    def sync_from_game(self, auto=False, map_only=False):
        if self.syncing or not self.db.quests or (auto and self.resetting):
            return
        self.syncing = True
        if not auto and not self.resetting:
            self.set_status("Reading the game screen...")
        # our own windows are blacked out of the screenshot (closed ones don't cover anything)
        windows = [self.root] + [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        ours = [window_rect(w) for w in windows if w.winfo_viewable()]
        # auto syncs re-read only the areas found by the last full scan (quest helper + map name)
        # Existing titles can keep an old crop alive after the helper grows or moves.
        # Rediscover its bounds regularly even when another old quest is still readable.
        if auto and not map_only:
            self._quest_scan_tick = (getattr(self, "_quest_scan_tick", 0) + 1) % 5
        regions = self.focus if auto and (map_only or self._quest_scan_tick != 0) else None
        # the EXP bar takes ~0.5 s to read: on manual syncs and every EXP_BAR_EVERY-th auto sync
        self._exp_tick = (getattr(self, "_exp_tick", 0) + 1) % EXP_BAR_EVERY
        exp_bar = not auto or self._exp_tick == 0
        character_revision = getattr(self, "_character_read_revision", 0)
        def loaded(result):
            # Another reader or manual calibration may have accepted newer character evidence.
            # Keep this scan's map/quest evidence, but never overwrite that newer EXP reading.
            if result and character_revision != getattr(self, "_character_read_revision", 0):
                result = dict(result)
                result.pop("exp_bar", None)
            self._on_synced(result)
        self.run_bg(lambda: capture_and_read(self.db, auto, ours, regions, map_only, exp_bar), loaded,
                    on_error=lambda _: setattr(self, "syncing", False))

    def _snapshot(self):
        return json.dumps([self.state[k] for k in ("active", "done", "progress", "map", "tracked")],
                          sort_keys=True)

    def _on_synced(self, result):
        self.syncing = False
        if result is None:
            self.set_status("Auto sync waiting: MapleStory window not found")
            return
        if result.get("minimap"):
            self._minimap, self._blocked_reads = result["minimap"], 0
            self._dock_gps_now()
        elif result.get("minimap_blocked"):
            # one read like that is often just the minimap's right edge missed for a moment (the
            # GPS jumped aside and straight back for no reason): step aside only on the second
            self._blocked_reads = getattr(self, "_blocked_reads", 0) + 1
            if self._blocked_reads >= 2:
                self._blocked_reads = 0
                self._gps_step_aside()
        else:
            self._blocked_reads = 0
        if self.resetting:
            self._on_reset_read(result)
            return
        if result.get("map_only"):  # AUTO off, GPS open: only where you are, quests untouched
            if self._apply_location(result, self._confirmed):
                self.render()
            return
        if result["full"]:
            self.focus = result["regions"] or None
        elif not result["quests"]:
            self.focus = None  # the quest helper moved or closed: next auto sync looks everywhere
        # Auto syncs only trust a reading once it comes out the same twice in a row: the
        # see-through in-game window OCRs a little differently each time, and acting on every
        # wobble would redraw the window every 2 seconds.
        confirm = self._confirmed if result["auto"] else (lambda key, value, needed=2: True)
        if result.get("exp_bar"):
            self.on_exp_bar(result["exp_bar"], confirm)
        before = self._snapshot()
        new, changed_numbers = 0, []
        tracked = self.state["tracked"]
        for qid in result["quests"]:
            live = qid in result["tracked"]
            if live and qid not in tracked and confirm(("tracked", qid), True):
                tracked.append(qid)  # it's in the game's Quest Helper: track it live from now on
            # auto syncs add only Quest Helper quests; a manual sync adds whatever is on screen
            if qid not in self.state["active"]:
                if (result["auto"] and qid not in tracked) or not confirm(("quest", qid), True):
                    continue
                self.state["active"].append(qid)
                new += 1
            if qid in self.state["completed"]:
                self.state["completed"].remove(qid)
            if qid not in tracked:
                continue  # live counts only for quests in the game's Quest Helper
            q = self.db.quests[qid]
            saved = self.state["progress"].setdefault(qid, {})
            done = self.done_steps(qid)
            for i, value in result["progress"].get(qid, {}).items():
                finished = value >= (q.get("need") or [])[i].get("count", 1)
                # finishing an objective takes one more matching read: on the see-through game
                # window "0 / 1 Garnet Ore" was misread as "1 / 1" twice in a row
                needed = 3 if finished and i not in done else 2
                if not confirm(("progress", qid, i), value, needed):
                    continue
                if saved.get(str(i)) != value:
                    saved[str(i)] = value
                    changed_numbers.append((qid, i))
                # the check mark follows the game both ways (it used to only ever be added,
                # so one bad read left "0 / 1" ticked for good)
                if finished:
                    done.add(i)
                else:
                    done.discard(i)
            if sorted(done) != self.state["done"].get(qid, []):
                self.state["done"][qid] = sorted(done)
        # the gold lines the game shows on a kill or a pickup ("Jr. Necki 12 / 20"): counts for
        # any quest on the list, also ones not in the game's Quest Helper
        noticed = self.notice_progress(result.get("notices") or [])
        for qid, i, have in noticed + self._finished_between(noticed):
            saved = self.state["progress"].setdefault(qid, {})
            old = saved.get(str(i))
            if old is not None and have < old:
                # fewer than before (an item used or dropped, or the earlier reading was wrong):
                # only once a second reading agrees (the same number, or a few more after it)
                low = self._notice_low.get((qid, i))
                self._notice_low[(qid, i)] = have
                if low is None or not 0 <= have - low <= 3:
                    continue
            self._notice_low.pop((qid, i), None)
            if old != have:
                saved[str(i)] = have
                changed_numbers.append((qid, i))
            done = self.done_steps(qid)
            if have >= (self.db.quests[qid].get("need") or [])[i].get("count", 1):
                done.add(i)
            else:
                done.discard(i)
            if sorted(done) != self.state["done"].get(qid, []):
                self.state["done"][qid] = sorted(done)
        turned_in = self._check_gone(result)
        moved = self._apply_location(result, confirm)
        # auto syncs stay silent unless something new shows up, so the window doesn't "tick"
        where = "game window" if result["window"] else "whole screen"
        if turned_in:
            self.set_status("✓ Turned in: " + ", ".join(turned_in))
        elif new:
            self.set_status(f"Added {new} new quest{'s' if new != 1 else ''} from the game")
        elif not result["auto"]:
            if result["quests"]:
                self.set_status(f"Synced from {where}: {len(result['quests'])} quests seen")
            else:
                self.set_status("No quests on screen: open the in-game Quest Helper, not under this window")
        if self.state["tab"] == "quests" and self._snapshot() != before:
            if self._structure() != self._structure(json.loads(before)):
                self.render()  # quests, finished objectives or the map changed: rebuild
            else:
                self.update_numbers(changed_numbers)  # only counts moved: change just those labels
        elif moved:
            # Training / Monsters / Items show distances, nearest-first order and routes from
            # where you are, so they need a redraw when you change maps too
            self.render()
        self.prefetch()
        self.trainer_tick()
        self.snap_to_corner()  # the game window may have moved

    def _finished_between(self, noticed):
        """A gold line shows for a few seconds; one can come and go between two syncs, such as
        the "20 / 20" that finished an objective (the game shows no line for it after that). So
        when the same monster or item keeps counting for another quest while ours stands one
        short, ours was finished: [(quest id, objective index, count)]."""
        names = {self.objectives(qid)[i][2].lower() for qid, i, _ in noticed}
        seen = {(qid, i) for qid, i, _ in noticed}
        finished = []
        for qid in self.state["active"]:
            for i, (have, count, name, done) in enumerate(self.objectives(qid)):
                if not done and (qid, i) not in seen and name.lower() in names and have == count - 1:
                    finished.append((qid, i, count))
        return finished

    def notice_progress(self, lines):
        """Counts from the game's gold progress lines. A line belongs to an objective when it
        starts with that objective's name and ends with its required count ("Jr. Necki 12 / 20"
        is the 20 Jr. Necki of one quest, "Jr. Necki 12 / 40" those of another); what comes
        before the count, minus the slash, is how many you have. The slash is often read as "1"
        or "J", or lost ("19 120", "12 J 20", "5 40"), which knowing the count sorts out.
        [(quest id, objective index, have)]"""
        found = []
        for text in lines:
            m = re.match(r"^\W*(?P<name>[^\d]*?)\s*(?P<rest>\d[\d\s/\\|JIl]*?)\W*$", text)
            if not m or not m["name"].strip():
                continue
            name = m["name"].strip(" .,:;'\"-").lower()
            rest = m["rest"].strip()
            for qid in self.state["active"]:
                for i, (_, count, objective, _) in enumerate(self.objectives(qid)):
                    tail = str(count)
                    if not rest.endswith(tail) or SequenceMatcher(None, name, objective.lower()).ratio() < 0.82:
                        continue
                    have = rest[:-len(tail)].rstrip()
                    if have and have[-1] in "/\\|J":
                        have = have[:-1].rstrip()
                    elif re.search(r"\s[1lI]$", have):  # the slash read as a separate "1"
                        have = have[:-1].rstrip()
                    have = have.replace(" ", "")
                    if not have.isdigit():
                        continue
                    # "2140" is 2 / 40 with the slash read as a glued "1", or 21 with it lost:
                    # counts go up one at a time, so take the one right after what we have
                    options = [int(have)] + ([int(have[:-1])] if len(have) > 1 and have.endswith("1") else [])
                    options = [o for o in options if o <= count]
                    old = self.state["progress"].get(qid, {}).get(str(i))
                    if options and old is not None:
                        options.sort(key=lambda o: (not old <= o <= old + 5, abs(o - old)))
                    else:  # nothing to go by: the lower (one too low is fixed by the next kill,
                        options.sort()  # one too high would block the real counts below it)
                    if options:
                        found.append((qid, i, options[0]))
        return found

    def _apply_location(self, result, confirm):
        """Take a sync's map reading as where you are. True when you moved. A reading you once
        corrected ("I'm on:") means the map you picked from then on. A sure one (read from the
        minimap window's name area) counts at once; a reading from the corner of the game window
        has to come out the same twice in a row first."""
        map_id, text = result.get("map"), result.get("map_text") or ""
        if text:
            self._last_read = (text, result.get("map_image"), map_id)
        fixed = self.state.get("map_fixes", {}).get(text)
        if fixed:
            map_id = fixed
        sure = bool(fixed or result.get("map_sure"))
        if not map_id or map_id == self.state.get("map") or not confirm(("map",), map_id, 1 if sure else 2):
            return False
        self.set_location(map_id)
        return True

    def set_location(self, map_id):
        self.state["map"] = map_id
        self.refresh_map_label()
        for key in self.routes:  # you moved: show the next portal from the new map
            self.previews.pop(key, None)
        self.trainer_tick()
        return True

    def correct_location(self, map_id):
        """"I'm on:" (click the location line): you picked where you really are. If the last
        reading said something else, its text now means this map, so the same misread is right
        from then on; it's also saved in cache/misreads/ (the picture it was read from, what was
        read, the right map) to become a test."""
        last, learned = getattr(self, "_last_read", None), False
        if last and last[2] != map_id:
            text, image, read = last
            self.state.setdefault("map_fixes", {})[text] = map_id
            learned = True
            try:
                folder = os.path.join(CACHE_DIR, "misreads")
                os.makedirs(folder, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                if image is not None:
                    image.save(os.path.join(folder, stamp + ".png"))
                name = lambda mid: self.db.maps.get(mid or "", {}).get("displayName")
                write_atomic(os.path.join(folder, stamp + ".json"), json.dumps(
                    {"text": text, "read": read, "read_name": name(read), "right": map_id,
                     "right_name": name(map_id)}, indent=2))
            except OSError:
                pass
        self._reads.pop(("map",), None)
        self.set_location(map_id)
        self.render()
        where = self.db.maps.get(map_id, {}).get("displayName", map_id)
        self.set_status(f"You're on {where}" + (": remembered, the same reading means this map from now on"
                                                  if learned else ""))

    # ---------- reset from the Quest window ----------

    def start_reset(self):
        """Replace the list with every quest in the game's Quest window. The player opens the
        window (Q) themselves: the helper never presses keys in the game."""
        if self.resetting or not self.db.quests:
            return
        if not messagebox.askokcancel(
                "Reset quests",
                "Open your Quest window in the game now (press Q), on the \"In Progress\" tab, "
                "with every area expanded.\n\nThe helper will read all quest names from it "
                "(scroll the list if it's long), then replace this list.\n\nQuests you also put "
                "in the game's Quest Helper get live tracking.", parent=self.root):
            return
        self.resetting = {"seen": [], "tracked": set(), "window_seen": False, "idle": 0,
                          "started": time.time(), "was_collapsed": self.collapsed}
        # shrink to the title bar so this window doesn't cover (and hide) the Quest window
        if not self.collapsed:
            self.toggle_collapse()
        self._reset_message("Press Q in the game...")
        self._reset_tick()

    def _reset_message(self, text, color="gold"):
        """While resetting the overlay is collapsed to its title row, so progress is shown there."""
        self._pill(text, color)
        self.set_status(text, color)

    def _reset_tick(self):
        if not self.resetting:
            return
        self.sync_from_game()
        self.root.after(RESET_SCAN_MS, self._reset_tick)

    def _on_reset_read(self, result):
        r = self.resetting
        if result["quest_window"]:
            r["window_seen"] = True
        fresh = [q for q in result["quests"] if q not in r["seen"]]
        r["seen"] += fresh
        r["tracked"] |= set(result["tracked"])
        r["idle"] = 0 if fresh else r["idle"] + 1
        if r["window_seen"]:
            self._reset_message(f"Reading quests... {len(r['seen'])} (scroll if long)")
        timed_out = time.time() - r["started"] > RESET_TIMEOUT_S
        finished = r["window_seen"] and (not result["quest_window"] or r["idle"] >= 3)
        if finished or timed_out:
            self._finish_reset()

    def _finish_reset(self):
        r, self.resetting = self.resetting, None
        self.refresh_pill()
        if self.collapsed and not r["was_collapsed"]:
            self.toggle_collapse()
        if not r["window_seen"] or not r["seen"]:
            self.render()
            self.set_status("Couldn't see the Quest window: press Q in the game and try Reset again", "red")
            return
        tracked = [q for q in r["seen"] if q in r["tracked"]]
        self.state["active"] = tracked + [q for q in r["seen"] if q not in r["tracked"]]
        self.state["tracked"] = tracked
        self._drop_gone_quest_routes()
        for key in ("progress", "done"):  # keep counts for quests that are still there
            self.state[key] = {q: v for q, v in self.state[key].items() if q in self.state["active"]}
        self.state["expanded"] = tracked[0] if tracked else None
        self.focus = None
        self._reads.clear()
        self.set_status(f"Read {len(r['seen'])} quests ({len(tracked)} live). You can close the Quest window.")
        self.render(keep_scroll=False)
        self.prefetch()

    def _check_gone(self, result):
        """Notice LIVE quests that left the game's Quest Helper. Only judged while the helper is
        on screen (it showed other quests this sync). After GONE_AFTER syncs in a row: a quest
        whose objectives were all done was turned in, so it moves to completed (its follow-ups
        then show under suggestions); any other one just stops being tracked live.
        Returns the names of quests turned in."""
        if not result["tracked"]:
            return []
        seen, turned_in = set(result["quests"]), []
        for qid in list(self.state["tracked"]):
            if qid in seen:
                self._gone.pop(qid, None)
                continue
            self._gone[qid] = self._gone.get(qid, 0) + 1
            if self._gone[qid] < GONE_AFTER:
                continue
            self._gone.pop(qid, None)
            needs = len(self.db.quests[qid].get("need") or [])
            if needs and qid in self.state["active"] and set(range(needs)) <= self.done_steps(qid):
                self._forget(qid)
                if qid not in self.state["completed"]:
                    self.state["completed"].append(qid)
                turned_in.append(self.db.quests[qid]["name"])
            else:
                self.state["tracked"].remove(qid)
        return turned_in

    def _confirmed(self, key, value, needed=2):
        """True once `value` has been read for `key` in `needed` syncs in a row."""
        last, times = self._reads.get(key, (None, 0))
        times = times + 1 if last == value else 1
        self._reads[key] = (value, times)
        return times >= needed

    def _structure(self, snap=None):
        """Everything except the raw counts: if this is unchanged, no rebuild is needed."""
        active, done, _progress, map_id, tracked = snap or [
            self.state[k] for k in ("active", "done", "progress", "map", "tracked")]
        return json.dumps([active, done, map_id, tracked], sort_keys=True)

    def update_numbers(self, changed):
        for qid, i in changed:
            widget = self.objective_labels.get((qid, i))
            if widget and widget.winfo_exists():
                count = (self.db.quests[qid].get("need") or [])[i].get("count", 1)
                widget.config(text=f"{self.state['progress'][qid][str(i)]} / {count}  {widget.objective_name}")
            bar = self.quest_bars.get(qid)
            if bar and bar.winfo_exists():
                bar.set(self.quest_share(qid), bar.done)
        self.refresh_pill()

    def _schedule_auto_sync(self):
        if self._auto_job:
            self.root.after_cancel(self._auto_job)
            self._auto_job = None
        def tick():
            if self.state["auto_sync"]:
                self.sync_from_game(auto=True)
            elif self.gps and self.gps.winfo_exists():
                # AUTO off still leaves the GPS following you: a GPS that doesn't know where you
                # are just shows an old map. Only the minimap corner is read; quests aren't touched.
                self.sync_from_game(auto=True, map_only=True)
            self._auto_job = self.root.after(AUTO_SYNC_MS, tick)
        self._auto_job = self.root.after(AUTO_SYNC_MS, tick)

    # ---------- routes ----------

    def open_meowdb_route(self, to_map):
        params = [f"to={to_map}"]
        if self.state.get("map"):
            params.insert(0, f"from={self.state['map']}")
        webbrowser.open(f"{BASE}/pathfinder?{'&'.join(params)}")

    # ---------- quest guide data ----------

    def resolve_guide(self, q):
        """Turn a quest's requirements into steps with map suggestions (runs in background)."""
        try:
            return self._resolve_guide(q)
        except Exception as e:  # keep the card usable offline; locations come back next time
            return {"error": str(e)}

    @staticmethod
    def _maps(locations):
        return [[l["mapId"], l["mapName"]] for l in locations[:KEEP_MAPS]]

    def _resolve_guide(self, q):
        steps = []
        for need in q.get("need") or []:
            count = need.get("count", 1)
            if "mobId" in need:
                mob = self.db.monsters.get(need["mobId"], {})
                maps = self._maps(self.db.mob_locations(need["mobId"]))
                steps.append({"name": mob.get("display") or need["name"].replace("Defeat ", ""),
                              "level": mob.get("level"), "count": count,
                              "lines": [{"mob": need["mobId"], "maps": maps}] if maps else [],
                              "note": "" if maps else "Location unknown"})
            else:
                lines = []
                try:droppers=self.rank_droppers(q,need)[:MAX_DROPPERS]
                except Exception:droppers=[]
                for mid in droppers:
                    mob = self.db.monsters.get(mid, {})
                    maps = self._maps(self.db.mob_locations(mid))
                    if maps:
                        lines.append({"prefix": f"Drops from {mob.get('display', 'Monster ' + str(mid))} "
                                                f"(Lv {mob.get('level', '?')}):", "mob": mid, "maps": maps})
                try:sources=self.db.item_acquisition_sources(need['itemId'],need['name'])
                except Exception:sources=item_sources.shop_sources(self.db.sold_by.get(str(need['itemId'])) or [],self.db.maps)
                steps.append({"name": need["name"], "count": count, "lines": lines,'sources':sources,
                              "note": "" if lines or sources else "Source not listed yet"})
        return steps

    def rank_droppers(self, q, need):
        """Monsters to farm an item from: ones this quest already sends you to kill
        (or whose name is in the item's name) first, then those nearest the quest's level."""
        droppers = self.db.item_droppers(need["itemId"], need["name"])
        quest_mobs = [n["mobId"] for n in q.get("need") or [] if "mobId" in n]
        name = lambda m: (self.db.monsters.get(m) or {}).get("display") or "~"
        # e.g. "Tutorial Jr. Sentinel" is a variant of the dropper "Jr. Sentinel"
        related = [m for m in quest_mobs
                   if m in droppers or name(m) in need["name"] or any(name(d) in name(m) for d in droppers)]
        level = q.get("levelMin") or 1
        rest = sorted((m for m in droppers if m not in related),
                      key=lambda m: abs((self.db.monsters.get(m) or {}).get("level", 999) - level))
        return related + rest

    def _on_guide(self, qid, steps):
        self.pending.discard(qid)
        if isinstance(steps, dict):  # failed: retry on the next prefetch
            self.set_status(f"Couldn't load locations: {steps['error']}", "red")
            return
        self.guides[qid] = steps
        try:
            write_atomic(GUIDES_FILE, json.dumps({"v": GUIDES_VERSION, "guides": self.guides}))
        except OSError:
            pass
        if self.state["tab"] == "quests" and qid in self.state["active"]:
            self.render()
        self.trainer_tick()  # its monsters are known now: maybe a better map

    # ---------- quest actions ----------

    def toggle_card(self, qid):
        self.state["expanded"] = None if self.state["expanded"] == qid else qid
        self.render()

    def toggle_step(self, qid, i):
        done = self.done_steps(qid)
        done.symmetric_difference_update({i})
        self.state["done"][qid] = sorted(done)
        self.render()

    def add_quest(self, qid):
        if qid not in self.state["active"]:
            self.state["active"].append(qid)
        self.state["expanded"] = qid
        self.render()
        self.prefetch()
        self.trainer_tick()

    def _forget(self, qid):
        if self.state.get("focus_quest") == qid:
            self.state.pop("focus_quest")
        self.state["active"].remove(qid)
        self.state["done"].pop(qid, None)
        self.state["progress"].pop(qid, None)
        if qid in self.state["tracked"]:
            self.state["tracked"].remove(qid)
        self.previews.pop(qid, None)
        self._drop_gone_quest_routes()
        self.trainer_tick()

    def toggle_all_maps(self, qid):
        self.all_maps[qid] = not self.all_maps.get(qid)
        self.render()

    def move_to_top(self, qid):
        self.state["active"].remove(qid)
        self.state["active"].insert(0, qid)
        self.state["expanded"] = qid
        self.render(keep_scroll=False)

    def clear_quests(self):
        if self.state["active"] and messagebox.askyesno(
                "Clear list", f"Remove all {len(self.state['active'])} quests from the list?\n"
                f"(Sync again with the in-game Quest Helper open to get your real ones back.)",
                parent=self.root):
            for qid in list(self.state["active"]):
                self._forget(qid)
            self.render()

    def remove_quest(self, qid):
        self._forget(qid)
        self.render()

    def complete_quest(self, qid):
        self._forget(qid)
        if qid not in self.state["completed"]:
            self.state["completed"].append(qid)
        self.render()
        for q in self.db.next_quests(qid):
            if q["id"] in self.state["completed"]:
                continue
            m = npc_map(self.db, q.get("npc"))
            if messagebox.askyesno("Next quest unlocked",
                                   f"\"{q['name']}\" from {q.get('npc')}\n"
                                   f"at {m['mapName'] if m else 'unknown location'}\n\nAdd it to your list?",
                                   parent=self.root):
                self.add_quest(q["id"])

    @staticmethod
    def prerequisites(q):
        return q.get("requiresAll") or ([q["requires"]] if q.get("requires") else [])

    def done_quests(self):
        """Quests you've done: the ones completed in this app, plus everything that had to be
        finished before a quest you have or did (Bringing a Mirror to Heena on your list means
        Borrowing Sera's Mirror is done, even if you never marked it here)."""
        key = (tuple(self.state["active"]), tuple(self.state["completed"]))
        if self._done_cache[0] != key:
            done, todo = set(self.state["completed"]), list(self.state["active"]) + list(self.state["completed"])
            while todo:
                q = self.db.quests.get(todo.pop())
                for r in self.prerequisites(q) if q else []:
                    if r not in done:
                        done.add(r)
                        todo.append(r)
            self._done_cache = (key, done)
        return self._done_cache[1]

    def available(self, q):
        done = self.done_quests()
        return ((q.get("levelMin") or 0) <= self.state["level"]
                and all(r in done for r in self.prerequisites(q))
                and q["id"] not in done)

    def _end_startup_preview(self):
        self._preview_job, self._hovered = None, None  # the hover check sets the right alpha

    def on_close(self):
        # position, panel size and collapsed are kept in the state as they change; "geometry" is
        # the expanded panel, for older versions reading this file
        w, h = self.state["panel_size"]
        x, y = self.state.get("pos") or (self.root.winfo_x(), self.root.winfo_y())
        self.set_level()
        self.state["geometry"] = f"{w}x{h}+{x}+{y}"
        self.save_state()
        self.root.destroy()

    def save_state(self):
        try:
            write_atomic(STATE_FILE, json.dumps(self.state, indent=2))
            self._saved = json.dumps(self.state, sort_keys=True)
        except OSError as e:
            self.set_status(f"Couldn't save your list: {e}", "red")

    def _autosave(self):
        """Save quietly every so often when something changed, so a crash or shutdown loses
        at most AUTOSAVE_MS of changes instead of everything since the app was opened."""
        if json.dumps(self.state, sort_keys=True) != self._saved:
            self.save_state()
        self.root.after(AUTOSAVE_MS, self._autosave)


def self_test(out_path):
    """`--selftest out.txt`: check that screen reading works in this build, then exit."""
    try:
        import screen_ocr
        from PIL import ImageGrab
        lines = screen_ocr.read_lines(ImageGrab.grab().convert("RGB"))
        result = f"ok: OCR read {len(lines)} lines"
    except Exception as e:
        result = f"error: {e!r}"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result)


def self_test_image(image_path, out_path):
    """Check packaged Windows OCR on an explicit fixture, without capturing the desktop."""
    try:
        import screen_ocr
        lines = screen_ocr.read_lines(Image.open(image_path).convert("RGB"))
        result = {"ok": True, "line_count": len(lines)}
    except Exception as e:
        result = {"ok": False, "error": repr(e)}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f)


from companion_integration import integrate
App = integrate(App, globals())


if __name__ == "__main__":
    if len(sys.argv)==4 and sys.argv[1]=='--check-context-image':
        try:
            from training_context import context_lines,party_rows,roman_suffix
            image=Image.open(sys.argv[2]).convert('RGB');lines=context_lines(image)
            from game_sync import minimap_title,find_minimap
            frame=find_minimap(image)
            report={'ok':True,'party_visible':party_rows(image,lines),'roman_suffix':roman_suffix(minimap_title(image,frame)) if frame else None,'labels':[l['text'] for l in lines if re.search(r'\bLv[\s.,:]*\d',l['text'],re.I)]}
        except Exception:
            import traceback
            report={'ok':False,'error':traceback.format_exc()}
        with open(sys.argv[3],'w',encoding='utf-8') as f:json.dump(report,f)
        sys.exit()
    if len(sys.argv)==4 and sys.argv[1]=='--check-wallet-image':
        try:
            from session_reader import ocr_rows,wallet_from_rows
            value=wallet_from_rows(ocr_rows(Image.open(sys.argv[2])))
            report={'ok':value is not None,'wallet':value}
        except Exception:
            import traceback
            report={'ok':False,'error':traceback.format_exc()}
        with open(sys.argv[3],'w',encoding='utf-8') as f:json.dump(report,f)
        sys.exit()
    if len(sys.argv)==4 and sys.argv[1]=='--check-character-image':
        from session_reader import read_character_image
        try:
            image=Image.open(sys.argv[2]).convert('RGB');w,h=image.size
            reading=read_character_image(image.crop((int(w*.1),int(h*.91),int(w*.92),h)))
            report={'ok':reading is not None,'character':reading}
        except Exception:
            import traceback
            report={'ok':False,'error':traceback.format_exc()}
        with open(sys.argv[3],'w',encoding='utf-8') as f:json.dump(report,f)
        sys.exit()

    if len(sys.argv)==4 and sys.argv[1]=='--check-rewards-image':
        from session_reader import read_reward_image
        from session_rewards import RewardTracker
        try:
            events=read_reward_image(Image.open(sys.argv[2]));tracker=RewardTracker();tracker.previous=[]
            report={'ok':True,'events':events,'totals':tracker.feed(events)}
        except Exception:
            import traceback
            report={'ok':False,'error':traceback.format_exc()}
        with open(sys.argv[3],'w',encoding='utf-8') as f:json.dump(report,f)
        sys.exit()

    if len(sys.argv)==3 and sys.argv[1]=='--mesowatch-search':
        from mesowatch_browser import run_browser
        try:run_browser(sys.argv[2])
        except Exception:
            import traceback
            with open(os.path.join(APP_DIR,'mesowatch-error.log'),'w',encoding='utf-8') as f:traceback.print_exc(file=f)
        sys.exit()

    try:  # crisp text on high-DPI Windows screens; also makes screen capture use real pixels
        # 2 = per-monitor aware: window positions and screenshots are then both in real pixels on
        # every monitor. With 1 (system-aware) a monitor scaled differently from the main one gets
        # "virtual" window coordinates, so our own windows were blacked out in the wrong place and
        # the sync read the GPS window's text as if it were the game.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        self_test(sys.argv[2])
        sys.exit()
    if len(sys.argv) == 4 and sys.argv[1] == "--selftest-image":
        self_test_image(sys.argv[2], sys.argv[3])
        sys.exit()
    if len(sys.argv) == 3 and sys.argv[1] == '--check-data':
        import traceback,ssl
        try:
            context=ssl.create_default_context()
            if not context.check_hostname or context.verify_mode!=ssl.CERT_REQUIRED:
                raise RuntimeError('HTTPS certificate verification must remain enabled')
            database=MeowDB()
            database.load_indexes()
            report={'ok':True,'tls_verification':True,'quests':len(database.quests),'maps':len(database.maps),'monsters':len(database.monsters),'game_window':find_game_window()}
        except Exception:
            report={'ok':False,'traceback':traceback.format_exc(),'game_window':find_game_window()}
        with open(sys.argv[2],'w',encoding='utf-8') as f:json.dump(report,f)
        sys.exit()
    # one overlay at a time: opening it again brings the one already running forward
    _instance = ctypes.windll.kernel32.CreateMutexW(None, False, r"Local\UmbraleOverlay")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        with open(SHOW_REQUEST, "w") as f:
            f.write("show")
        sys.exit()
    try:  # own taskbar identity, so Windows shows our icon rather than Python's
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Umbrale.Overlay")
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    # always draw at 100%, whatever the Windows display scaling: 1 inch = 96 pixels, so point
    # sizes and widgets.px() come out the same on every screen (the DPI awareness above stays,
    # since screen capture and window positions need real pixels)
    root.tk.call("tk", "scaling", 96 / 72)
    root.title("UMBRΛLE")
    try:
        root.iconbitmap(default=os.path.join(BUNDLE_DIR, "icon.ico"))  # also used by dialogs
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
