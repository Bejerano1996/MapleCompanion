"""Reading the game from the screen: find its window, screenshot it (hiding our own
window), OCR it, and the global sync hotkey. Read-only: it never touches the game's
memory and never sends the game any input."""
import ctypes
import ctypes.wintypes
import threading

from PIL import ImageChops, ImageDraw

import sync

MINIMAP_CORNER = (0.3, 0.12)  # share of the game window (width, height) holding the map name


def find_game_window():
    """Screen rectangle of the MapleStory window, or None to capture the whole screen."""
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if buf.value.startswith("MapleStory"):
                found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    if not found:
        return None
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(found[0], ctypes.byref(rect))
    if rect.right - rect.left < 200:  # minimized
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def window_rect(widget):
    """Screen rectangle of a Tk toplevel (left, top, right, bottom)."""
    hwnd = ctypes.windll.user32.GetAncestor(widget.winfo_id(), 2)  # GA_ROOT
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


FRAME_BLUE = (85, 119, 153)  # the 1 px steel-blue outline of the game's minimap window, unstretched
TITLE_HEADER = 65            # px from the minimap window's top to the line under the map name, unstretched


def _outline(region):
    """Mask (255 = yes) of the pixels in `region` that have the minimap window's outline colour.
    Not one exact colour: at other resolutions the game stretches its windows, and the 1 px
    steel-blue line blends into the white beside it ((103, 133, 164) seen at 1920x1080). What
    stays is the colour family: darkish red, green ~30 above it, blue ~60 above it."""
    r, g, b = region.split()
    between = lambda band, low, high: band.point(lambda v: 255 if low <= v <= high else 0)
    green_over = between(ImageChops.subtract(g, r), 18, 44)
    blue_over = between(ImageChops.subtract(b, r), 42, 78)
    return ImageChops.multiply(ImageChops.multiply(between(r, 62, 132), green_over), blue_over)


def minimap_title(img, frame):
    """The area and map name of a found minimap window ("Dungeon" / "Ant Tunnel II"): right of
    the map's icon, between the MINI MAP title row and the outline under the name. Cropped to
    just that, nothing else (game scenery, other windows) can get mixed into the reading.
    None if the outline under the name isn't there (the window is minimised or covered)."""
    from PIL import Image
    left, top, right, bottom = frame
    width, height = right - left, bottom - top
    window = img.crop(frame)
    rows = _outline(window).resize((1, height), Image.BOX).tobytes()

    def header_blue_below(y):
        """The light-blue header (153, 187, 204) just below row y: a stretched game blurs the
        edge between the white MINI MAP row and that blue into a line of the outline's colour,
        which isn't the line under the name (below that comes the map, or the window's edge)."""
        band = window.crop((width // 4, min(height - 1, y + 3), width * 3 // 4, min(height, y + 6)))
        mean = [sum(v * n for v, n in enumerate(h)) / max(1, sum(h)) for h in
                (band.getchannel(c).histogram() for c in range(3))]
        return all(abs(m - c) <= 22 for m, c in zip(mean, (153, 187, 204)))

    under = next((y for y in range(max(12, height // 12), height // 2)
                  if rows[y] * width / 255 >= width * 0.6 and not header_blue_below(y)), None)
    if under is None:
        return None
    title = img.crop((left + round(width * 0.2), top + round(under * 0.26), right - 3, top + under - 1))
    title.under = under  # the header's height: how much the game has stretched its windows
    return title


def read_location(img, maps, frame=None):
    """Where you are: (map id or None, the text read, sure). Read from the minimap window's
    name area when the window was found (`frame`), enlarged three times: that's sure. Otherwise
    from the top-left corner of the game window, as before."""
    import screen_ocr
    from PIL import Image
    title = minimap_title(img, frame) if frame else None
    if title is not None:
        # the same text size whatever the game's resolution: three times the unstretched size
        # (the header is 65 px tall unstretched), which Windows OCR reads best
        k = 3 * TITLE_HEADER / title.under
        big = title.resize((round(title.width * k), round(title.height * k)), Image.LANCZOS)
        guess = None
        # the white letters alone first: the letters' dark shadow, read as-is, adds strokes ("III" for II)
        for version in (screen_ocr.title_passes(big)[2], big):
            lines = screen_ocr.read_lines(version)
            found = sync.match_map(lines, maps)
            if found:
                text = " / ".join(line["text"] for line in lines)
                # "Ant Tunnel" (the II not read) is closest to "Ant Tunnel I": a name ending in a
                # number only counts when that number was read too
                tail = sync._number_tail(maps[found]["displayName"])
                if not tail or any(sync._number_tail(line["text"]) == tail for line in lines):
                    return found, text, True
                guess = guess or (found, text, False)
        if guess:
            return guess
    corner = img.crop((0, 0, int(img.width * MINIMAP_CORNER[0]), int(img.height * MINIMAP_CORNER[1])))
    for version in screen_ocr.title_passes(corner):
        lines = screen_ocr.read_lines(version)
        found = sync.match_map(lines, maps)
        if found:
            return found, " / ".join(line["text"] for line in lines), False
    return None, "", False


def find_minimap(img, covers=(), report=None):
    """(left, top, right, bottom) of the game's minimap window in `img` (a screenshot of the game
    window), its white edge included, or None. Found by its outline: the first long horizontal
    run of FRAME_BLUE in the top-left part of the game is its top edge (the corners are rounded,
    so the sides start a few pixels outside that run); the sides are followed down to where the
    outline stops. Mostly Pillow image operations, so it's quick enough for every sync.
    `covers`: rectangles (in `img`'s pixels) of our own windows. When the top edge runs into one
    of them and the right side can't be seen, the window goes on under ours (a wider minimap on
    a new map, under the docked GPS): then `report["blocked"]` is set and None returned."""
    from PIL import Image
    w, h = int(img.width * 0.45), int(img.height * 0.6)
    mask = _outline(img.crop((0, 0, w, h)))
    shortest = max(60, w // 8)  # the top edge of even a small minimap is longer than this

    def column(x, y):
        """Outline pixels down from row y in column x or the one right of it: a stretched line
        falls between two pixel columns and hops from one to the other."""
        pair = mask.crop((x, y, min(w, x + 2), h))
        return pair.resize((1, pair.height), Image.BOX).point(lambda v: 255 if v else 0).tobytes()

    def side(x0, x1, y, allowed):
        """The column in x0..x1 whose outline runs down furthest from row y (gaps up to `allowed`
        px, e.g. where a button sits on the edge): (x, last row) or None."""
        best = None
        for x in range(max(0, x0), min(w, x1 + 1)):
            col, last, gap = column(x, y), None, 0
            for i, v in enumerate(col):
                if v:
                    last, gap = i, 0
                elif last is not None or i > allowed:
                    gap += 1
                    if gap > allowed:
                        break
            if last is not None and (best is None or last > best[1]):
                best = (x, last)
        if not best:
            return None
        x, last = best
        # the line is in column x or x + 1 (the pair was followed): take the one that has it
        single = lambda c: sum(1 for v in mask.crop((c, y, c + 1, y + last + 1)).tobytes() if v)
        return (x + 1 if x + 1 < w and single(x + 1) > single(x) else x), y + last

    rows = mask.resize((1, h), Image.BOX).tobytes()  # each row's share of outline pixels
    for y, share in enumerate(rows):
        if share * w / 255 < shortest * 0.9:
            continue
        line, best, start = mask.crop((0, y, w, y + 1)).tobytes(), (0, -1), None
        for x, v in enumerate(line + b"\0"):
            if v and start is None:
                start = x
            elif not v and start is not None:
                best, start = max(best, (x - start, start)), None
        length, first = best
        if length < shortest:
            continue
        last = first + length - 1
        reach = max(6, length // 25)  # the rounded corners are bigger when the game is stretched
        allowed = max(8, length // 20)  # and so are the gaps in its sides
        right, left = side(last, last + reach, y, allowed), side(first - reach, first, y, allowed)
        if not (right and left) or min(right[1], left[1]) - y < 40:
            if report is not None and left and any(top - 2 <= y <= bottom and abs(cover_left - (last + 1)) <= reach + 3
                                                   for cover_left, top, _, bottom in covers):
                report["blocked"] = True  # its right part is under one of our windows
                return None
            continue  # a line, not a window: keep looking
        # the bottom: the last full-width outline line around where the sides end (the rounded
        # bottom edge is a little below them; stray game pixels can stretch them a little further)
        end = max(right[1], left[1])
        lines = [r for r in range(max(y + 1, end - allowed), min(h, end + 9)) if rows[r] * w / 255 >= length * 0.8]
        bottom = max(lines) if lines else end
        return left[0] - 1, y - 1, right[0] + 1, bottom + 2
    return None


NOTICE_AREA = (0.28, 0.04, 0.72, 0.34)  # share of the game window (left, top, right, bottom) with the gold lines


def read_notices(img):
    """The gold progress lines the game shows near the top of the screen when a quest monster
    dies or a quest item is picked up: "Jr. Necki 5 / 20", one line per quest that needs it (so
    the same monster can show "5 / 40" too). They show without the game's Quest Helper, so the
    counts can follow the game with that window closed. Returns the lines as read (the slash
    often comes out as "1" or "J": the app sorts that out with the counts it knows).
    Cheap when there's nothing to read: OCR runs only if fresh bright gold is in that area."""
    w, h = img.size
    return read_notice_area(img.crop((int(w * NOTICE_AREA[0]), int(h * NOTICE_AREA[1]), int(w * NOTICE_AREA[2]),
                                      int(h * NOTICE_AREA[3]))), h)


def read_notice_area(area, h):
    """read_notices on the area itself (`h`: the game window's height, for the padding)."""
    import screen_ocr
    from PIL import Image, ImageOps
    r, g, b = area.split()
    keep = lambda band, low, high: band.point(lambda v: 255 if low <= v <= high else 0)
    fresh = ImageChops.multiply(ImageChops.multiply(keep(r, 195, 255), keep(g, 145, 225)), keep(b, 0, 75))
    box = fresh.getbbox()
    if not box or fresh.histogram()[255] < 40:  # a few gold specks in the scenery aren't a line
        return []
    pad = max(8, h // 60)
    box = (max(0, box[0] - pad * 4), max(0, box[1] - pad), min(area.width, box[2] + pad * 4), min(area.height, box[3] + pad))
    part = area.crop(box)
    r, g, b = part.split()
    # gold strength: (r + g) / 2 - b, warm pixels only; dark letters on light, soft edges kept
    gold = ImageChops.subtract(ImageChops.add(r.point(lambda v: v // 2), g.point(lambda v: v // 2)), b)
    gold = ImageChops.multiply(gold, ImageChops.subtract(r, b).point(lambda v: 255 if v >= 90 else 0))
    letters = ImageOps.autocontrast(ImageOps.invert(gold), cutoff=1)
    letters = letters.resize((letters.width * 2, letters.height * 2), Image.LANCZOS)
    return [line["text"].strip() for line in screen_ocr.read_lines(letters)]


EXP_BAR_AREA = (0.30, 0.85)  # share of the game window's width with HP / MP / EXP at the bottom
# (white-text cut-off or None for auto-contrast, enlargement): no one version reads every digit
# of this pixel font, so several are read and leveling.read_bar takes what most of them say
EXP_TEXT_VERSIONS = ((90, 5), (90, 8), (110, 5), (130, 5), (130, 8), (150, 8), (160, 4), (None, 4), (None, 6))


def _bright_text(img, cut, scale=1):
    """Only the light pixels (all channels >= `cut`; None: by contrast), black on white,
    enlarged `scale` times."""
    from PIL import Image, ImageOps
    r, g, b = img.split()
    dimmest = ImageChops.darker(ImageChops.darker(r, g), b)
    text = (ImageOps.autocontrast(ImageOps.invert(dimmest)) if cut is None
            else dimmest.point(lambda p: 0 if p >= cut else 255))
    if scale > 1:
        text = ImageOps.expand(text, 10, 255)
        text = text.resize((text.width * scale, text.height * scale), Image.LANCZOS)
    return text


def read_exp_bar(img):
    """The OCR'd texts of the EXP number in the game's status bar ("EXP. 28,474 [51.87%]"),
    several versions of it, or [] when there's no status bar (leveling.read_bar makes sense of
    them). The text is tiny light-grey pixel digits, so it's found first: HP, MP and EXP are
    evenly spaced, so the EXP text is one HP-to-MP step right of "MP". Only that small piece is
    then read, at a few contrasts and sizes, in one go."""
    import screen_ocr
    w, h = img.size
    left, top = int(w * EXP_BAR_AREA[0]), h - max(40, int(h * 0.06))
    area = img.crop((left, top, int(w * EXP_BAR_AREA[1]), h))
    lines = screen_ocr.read_lines(_bright_text(area, 110))
    hp = next((l for l in lines if l["text"].startswith("HP")), None)
    mp = next((l for l in lines if l["text"].startswith("MP")), None)
    if hp and mp and mp["x"] > hp["x"]:
        step = mp["x"] - hp["x"]
        area = area.crop((int(mp["x"] + step * 0.95), int(mp["y"] - mp["h"] * 0.4),
                          int(mp["x"] + step * 2.05), int(mp["y"] + mp["h"] * 1.4)))
    elif not any("%" in l["text"] for l in lines):
        return []  # no status bar here (hidden, or not the game)
    versions = [_bright_text(area, cut, scale) for cut, scale in EXP_TEXT_VERSIONS]
    return [l["text"] for l in screen_ocr.read_lines(*versions)]


def where_am_i(img, maps):
    """The map you're on, read only from the minimap title in the game window's top-left corner.
    Map names elsewhere on screen (the World Map's town labels, chat, quest text) are not where
    you are: reading them made the app think you were in Perion or Kerning City. Each version
    of the corner is tried on its own (see screen_ocr.title_passes); the first that reads wins."""
    return read_title(img.crop((0, 0, int(img.width * MINIMAP_CORNER[0]), int(img.height * MINIMAP_CORNER[1]))),
                      maps)


def read_title(corner, maps):
    """The map named in a minimap-corner image, or None."""
    import screen_ocr
    for version in screen_ocr.title_passes(corner):
        found = sync.match_map(screen_ocr.read_lines(version), maps)
        if found:
            return found
    return None


def capture_and_read(db, auto=False, hide=(), regions=None, map_only=False, exp_bar=True):
    """Screenshot the game, OCR it and match quests / progress / current map (background).
    Auto syncs only look at the game window; they skip the (slow) whole-screen fallback.
    `hide` lists screen rectangles to black out first: our own overlay sits on top of the
    game, and reading it back would just feed our own (stale) numbers into the sync.
    `regions` (from a previous full scan) limits the OCR to those small areas, which keeps
    frequent auto syncs light enough not to slow the game down. `map_only` reads just the
    minimap corner and returns only where you are (for the GPS while AUTO is off). `exp_bar`:
    also read the EXP bar (about half a second, so not on every auto sync)."""
    import screen_ocr  # imported lazily: needs the winrt OCR packages
    from PIL import ImageGrab
    box = find_game_window()
    if auto and box is None:
        return None
    img = ImageGrab.grab(bbox=box, all_screens=True).convert("RGB")
    if box:
        ox, oy = box[0], box[1]
    else:  # whole virtual screen: its origin can be left of / above the main monitor
        ox, oy = ctypes.windll.user32.GetSystemMetrics(76), ctypes.windll.user32.GetSystemMetrics(77)
    # the minimap's frame, found before our own windows are blacked out: the GPS sits right
    # against it, and blacking it out would cut its edge off
    report = {}
    covers = [(left - ox, top - oy, right - ox, bottom - oy) for left, top, right, bottom in hide]
    frame = find_minimap(img, covers, report) if box else None
    minimap = (ox + frame[0], oy + frame[1], ox + frame[2], oy + frame[3]) if frame else None
    draw = ImageDraw.Draw(img)
    for left, top, right, bottom in hide:
        draw.rectangle((left - ox, top - oy, right - ox, bottom - oy), fill="black")
    # where you are comes from the minimap title only (with no game window found, see below)
    # half under our GPS, the map name may be cut off ("Swampy Land in a De"): not read this time
    map_id, map_text, map_sure = read_location(img, db.maps, frame) if box and not report else (None, "", False)
    where = {"map": map_id, "map_text": map_text, "map_sure": map_sure, "minimap": minimap,
             "minimap_blocked": bool(report.get("blocked")),
             "map_image": minimap_title(img, frame) if frame else None}
    if map_only:
        return {"map_only": True, "auto": True, "window": True, **where}
    parts = [(img.crop(r), (r[0], r[1])) for r in regions] if regions else [(img, (0, 0))]
    images, offsets = [], []
    for part, offset in parts:
        versions = screen_ocr.passes(part)  # as-is + high-contrast, for the see-through helper
        images += versions
        offsets += [offset] * len(versions)
    lines = screen_ocr.read_lines(*images, offsets=offsets)
    found = sync.match_quests(lines, db.quests)
    progress = {qid: sync.read_progress(lines, db.quests[qid], db) for qid in found}
    if not box:  # whole screen: only a street + map name pair counts, never a lone name
        where["map"] = map_id = sync.match_map(lines, db.maps, anchored_only=True)
    return {"quests": list(found), "progress": progress, "window": box is not None,
            "auto": auto, "full": not regions, **where,
            "tracked": list(sync.tracked_quests(lines, found, db.quests)),
            "notices": read_notices(img) if box else [],
            "exp_bar": read_exp_bar(img) if box and exp_bar else None,
            "quest_window": sync.quest_window_open(lines),
            "regions": None if regions or not box else
            sync.focus_regions(lines, found, db.quests, map_id, db.maps, img.size)}


class HotkeyThread(threading.Thread):
    """Global Ctrl+Shift+<key> shortcuts via RegisterHotKey (they work while the game has focus).
    `keys` maps a virtual-key code to what to run (on this thread: hand it to the UI thread).
    `registered` holds the keys Windows accepted, once `ready` is set: another program may
    already own a combination, and then that shortcut just doesn't exist."""
    MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT, WM_HOTKEY = 0x2, 0x4, 0x4000, 0x0312

    def __init__(self, keys):
        super().__init__(daemon=True)
        self.keys, self.registered, self.ready = keys, set(), threading.Event()

    def run(self):
        user32 = ctypes.windll.user32
        actions = {}
        for hotkey_id, (vk, on_press) in enumerate(self.keys.items(), start=1):
            if user32.RegisterHotKey(None, hotkey_id, self.MOD_CONTROL | self.MOD_SHIFT | self.MOD_NOREPEAT, vk):
                actions[hotkey_id] = on_press
                self.registered.add(vk)
        self.ready.set()
        if not actions:
            return
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == self.WM_HOTKEY and msg.wParam in actions:
                actions[msg.wParam]()
