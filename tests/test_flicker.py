"""Flicker checks. Run from the project folder:  python tests/test_flicker.py

1. Logic: syncs that read the same thing again must not redraw anything (main window or GPS).
2. On screen: the app's windows are photographed ~20 times a second while it syncs over and
   over with nothing changing; every frame must look the same (a flicker shows up as frames
   that differ). Hover effects are switched off so a passing mouse doesn't count.
"""
import ctypes
import json
import os
import sys
import tkinter as tk

ctypes.windll.shcore.SetProcessDpiAwareness(2)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from PIL import ImageChops, ImageGrab  # noqa: E402

import app  # noqa: E402

app.App.sync_from_game=lambda *args,**kwargs:None
class NoHotkey:
    def __init__(self,*args,**kwargs):pass
    def start(self):pass
app.HotkeyThread=NoHotkey

QUEST, MAP_A = "10123", "010004000"  # Mushroom quest, standing in Perion
FRAMES, FRAME_MS, SYNC_MS = 60, 50, 150  # 3 s of frames while a sync lands every 150 ms
SPECK = 64  # px²: a change smaller than this can't be seen (e.g. a scrollbar end being redrawn)


def differs(a, b):
    """True when two frames look different to a person (any change bigger than a speck)."""
    if a.size != b.size:
        return True
    box = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox()
    return bool(box) and (box[2] - box[0]) * (box[3] - box[1]) > SPECK


def result(map_id, auto=True):
    """A sync result like the game sends: same quest seen, same progress, same map."""
    return {"quests": [QUEST], "progress": {QUEST: {0: 3}}, "map": map_id, "window": True, "auto": auto,
            "full": False, "regions": None, "tracked": [QUEST], "quest_window": False}


def main():
    app.STATE_FILE = os.path.join(HERE, "flicker_state.json")
    with open(app.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"active": [QUEST], "tracked": [QUEST], "expanded": QUEST, "map": MAP_A,
                   "progress": {QUEST: {"0": 3}}, "auto_sync": False, "auto_on_v2": True,
                   "idle_alpha": 1.0, "gps_alpha":1.0, "geometry": "380x600+80+60", "gps_pos": [470, 60]}, f)
    root = tk.Tk()
    a = app.App(root)
    # the test feeds its own syncs; the real screen (a running game) must not move the windows
    a.sync_from_game = lambda *args, **kw: None
    a.db.load_indexes()
    a._on_loaded(None)
    while a.pending:  # quest guide resolved in the background
        root.update()
    a.start_route(QUEST, "010001000", None, "Bruce")
    for _ in range(2):
        a._on_synced(result(MAP_A))  # settle: the map is confirmed
    while a.pending:  # background lookups (e.g. for ranking suggested quests) are not syncs
        root.update()
    root.update()
    # and no hover effect at all: a real mouse passing over the windows during the test (someone
    # using the computer) turns a whole window more solid, which looked like a flicker
    a._watch_hover = lambda: None
    for _ in range(10):
        root.update()
    root.after(300, root.quit)
    root.mainloop()  # let the last scheduled hover check run (it now does nothing)
    a.root.attributes("-alpha", a.state["idle_alpha"])
    a.gps.attributes("-alpha", a.state.get("gps_alpha", app.GPS_ALPHA))
    root.update()

    counts = {"render": 0, "gps": 0, "status": 0}
    real_render, real_gps, real_status = a.render, app.gps_image.compose, a.set_status

    def render(*k, **kw):
        counts["render"] += 1
        real_render(*k, **kw)

    def route(*args, **kw):  # the GPS window draws a new picture whenever what it shows changes
        counts["gps"] += 1
        return real_gps(*args, **kw)

    def status(text, color="muted"):
        if text != a.status.cget("text"):
            counts["status"] += 1
        real_status(text, color)
    a.render, a.set_status = render, status
    app.gps_image.compose = route

    failed = 0

    # 1. logic: identical syncs change nothing
    for _ in range(20):
        a._on_synced(result(MAP_A))
    root.update()
    ok = counts == {"render": 0, "gps": 0, "status": 0}
    failed += not ok
    print(("  ok   " if ok else "  FAIL ") + f"20 identical syncs redraw nothing {counts}")

    # 2. on screen: frames of both windows stay identical while syncs keep arriving
    def frame():
        shots = []
        for w in (a.root, a.gps):
            x, y = w.winfo_rootx(), w.winfo_rooty()
            shots.append(ImageGrab.grab((x, y, x + w.winfo_width(), y + w.winfo_height()), all_screens=True))
        return shots

    first, changed, odd = frame(), [], {}

    def tick(n=0):
        if n % (SYNC_MS // FRAME_MS) == 0:
            a._on_synced(result(MAP_A))
        root.update_idletasks()
        for i, (old, new) in enumerate(zip(first, frame())):
            if differs(old, new):
                changed.append((n, "main" if i == 0 else "GPS"))
                odd.setdefault(i, new)  # the first frame that looked different, to inspect
        if n < FRAMES:
            root.after(FRAME_MS, tick, n + 1)
        else:
            root.quit()

    root.after(FRAME_MS, tick)
    root.mainloop()
    ok = not changed
    failed += not ok
    if not ok and os.environ.get("FLICKER_DUMP"):
        for i, shot in odd.items():
            shot.save(os.path.join(os.environ["FLICKER_DUMP"], f"still_{i}_changed.png"))
            first[i].save(os.path.join(os.environ["FLICKER_DUMP"], f"still_{i}_first.png"))
    print(("  ok   " if ok else "  FAIL ") + f"{FRAMES} screen frames during syncs all identical"
          + ("" if ok else f" (changed frames: {changed[:8]})"))

    # 2b. on screen, through a real change (moving one map along the route): each window may
    #     show its old look and then its new one, never an empty or half-drawn frame in between
    nxt = a.db.route(MAP_A, "010001000")[0][1]["toMapId"]
    films = {"main": [], "GPS": []}

    def film(n=0):
        if n == 4:
            a._on_synced(result(nxt))
            a._on_synced(result(nxt))
        for name, shot in zip(films, frame()):
            films[name].append(shot.convert("RGB"))
        if n < 30:
            root.after(15, film, n + 1)
        else:
            root.quit()

    root.after(50, film)
    root.mainloop()
    for name, shots in films.items():
        looks = []
        for shot in shots:
            if all(differs(l, shot) for l in looks):
                looks.append(shot)
        ok = len(looks) <= 2
        failed += not ok
        if not ok and os.environ.get("FLICKER_DUMP"):  # keep the frames to see what changed
            for i, look in enumerate(looks):
                look.save(os.path.join(os.environ["FLICKER_DUMP"], f"{name}_look{i}.png"))
        print(("  ok   " if ok else "  FAIL ") + f"{name} window through a map change: {len(looks)} looks "
              "(2 = before and after, more = a flicker in between)")

    root.destroy()
    os.remove(app.STATE_FILE)
    print(f"\n{4 - failed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
