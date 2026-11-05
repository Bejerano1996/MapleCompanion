"""Regression checks for screen reading: known screenshots in, expected quests/progress/map out.

Run from the project folder:  python tests/run_regression.py
Every change to OCR matching should keep these passing (and ideally turn misses into hits).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from PIL import Image  # noqa: E402

import screen_ocr  # noqa: E402
import game_sync  # noqa: E402
import sync  # noqa: E402
from meowdb import MeowDB  # noqa: E402

# screenshot -> what reading it must produce. "progress" lists (quest, objective index, have).
CASES = [
    {"file": "quest_screen.webp",  # Quest window (Q) open + see-through Quest Helper
     "quests": {"80014", "10123", "506000", "80011", "80020"},
     "tracked_at_least": {"80014", "10123", "80020"},  # JM needs the darker pass (round 5)
     "progress": [("80014", 0, 26), ("80014", 1, 34), ("10123", 0, 0), ("10123", 1, 1),
                  ("10123", 2, 0), ("10123", 3, 1)],
     "quest_window": True},
    {"file": "live_map.png",  # in game at Perion, the game's Quest Helper open with 4 quests
     "quests": {"80020", "10100", "10125", "10304"},  # 10125 = "...Daughter 2", not "... 1"
     "tracked_at_least": {"80020", "10100", "10125", "10304"},
     "progress": [("80020", 0, 30), ("80020", 1, 12), ("10100", 0, 0), ("10100", 1, 39),
                  ("10125", 0, 1), ("10304", 0, 0), ("10304", 1, 44)],  # checked by eye
     "map": "Perion", "quest_window": False},
    {"file": "live_2.png",  # Damp Tree-Forest (a Dungeon map): Quest Helper over a dark forest
     "quests": {"10100", "10125", "10304"},
     "tracked_at_least": {"10100", "10125", "10304"},
     "progress": [("10100", 0, 0), ("10100", 1, 39), ("10125", 0, 1), ("10304", 0, 0),
                  ("10304", 1, 19)],  # checked by eye
     "map": "Damp Tree-Forest", "quest_window": False},
    {"file": "live_corner.png",  # just the minimap corner
     "map": "Perion", "corner": True},
    {"file": "live_hhg1_corner.png",  # live minimap corner: "Henesys Hunting Ground I" is skipped as-is
     "map": "Henesys Hunting Ground I", "corner": True},
    {"file": "henesys_gps_masked.png",  # Henesys minimap + our GPS blacked out, in a 1366x768 game window
     "map": "Henesys"},             # as the sync does (it used to keep an old map: AUTO was off)
]

# the minimap window found on the screenshot and its name read from inside it (how the app reads
# where you are now): file -> (frame or None, expected map)
FRAME_CASES = [
    ("henesys_gps_masked.png", (2, 2, 309, 223), "Henesys"),
    ("live_frame_ant_tunnel2.png", (10, 39, 199, 235), "Ant Tunnel II"),  # I vs II vs III: the old corner read mixed them up
    ("live_frame_1920.png", (2, 2, 267, 276), "Ant Tunnel II"),  # 1920x1080: the game stretches its windows ~1.4x
]
# the gold lines near the top of a 1920x1080 game (cropped to that area): the name and the count
# must be in what's read (the slash between the numbers is often read as "1" or lost)
NOTICE_CASES = [
    ("notice_necki_5.png", 1080, ["Jr. Necki 5"]),
    ("notice_necki_19.png", 1080, ["Jr. Necki 19", "Jr. Necki 19"]),
    ("notice_skin_10.png", 1080, ["Jr. Necki Skin 10", "Jr. Necki Skin 10"]),
    ("notice_necki_32_skin_13.png", 1080, ["Jr. Necki 32", "Jr. Necki Skin 13"]),
]
# the 1366x768 shot stretched the ways a game or a screen can scale it: (factor, resampling)
STRETCHED = [(1.25, "BILINEAR"), (1.4, "NEAREST"), (1.5, "BICUBIC"), (1.75, "BILINEAR"), (2.0, "NEAREST"),
             (2.5, "BICUBIC")]

# (street line, map line) as the minimap shows them, misreads included -> expected map
MAP_TEXT_CASES = [
    ("Victoria Road", "PeriOli", "Perion"), ("Victoria Road", "Ellinla", "Ellinia"),
    ("Maple Road", "Snail Hunting Ground Il", "Snail Hunting Ground II"),
    ("Maple Road", "Snail Hunting Ground lll", "Snail Hunting Ground III"),
    ("Victoria Road", "L Forest Il", "L Forest II"),
    ("Victoria Road", "Henesys Hunting Ground 1", "Henesys Hunting Ground I"),
]


def read(path):
    img = Image.open(path).convert("RGB")
    return screen_ocr.read_lines(*screen_ocr.passes(img))  # the same passes the app uses


def main():
    db = MeowDB()
    db.load_indexes()
    passed = failed = 0

    def check(ok, what):
        nonlocal passed, failed
        passed, failed = passed + ok, failed + (not ok)
        print(("  ok   " if ok else "  FAIL ") + what)

    for case in CASES:
        path = os.path.join(HERE, case["file"])
        if not os.path.exists(path):
            print(f"{case['file']}: missing, skipped")
            continue
        print(case["file"])
        lines = read(path)
        found = set(sync.match_quests(lines, db.quests))
        if "quests" in case:
            extra, missing = found - case["quests"], case["quests"] - found
            check(not extra and not missing, f"quests (missing {sorted(missing)}, extra {sorted(extra)})")
        if "tracked_at_least" in case:
            tracked = sync.tracked_quests(lines, found, db.quests)
            check(case["tracked_at_least"] <= tracked, f"live quests {sorted(tracked)}")
        for qid, i, have in case.get("progress", []):
            got = sync.read_progress(lines, db.quests[qid], db).get(i)
            check(got == have, f"progress {qid}[{i}] = {got} (want {have})")
        if "map" in case:  # the way the app does: from the minimap title in the top-left corner only
            shot = Image.open(path).convert("RGB")
            got = db.maps.get((game_sync.read_title(shot, db.maps) if case.get("corner")
                               else game_sync.where_am_i(shot, db.maps)) or "",
                              {}).get("displayName")
            check(got == case["map"], f"map = {got} (want {case['map']})")
        if "quest_window" in case:
            check(sync.quest_window_open(lines) == case["quest_window"], "quest window detected")

    print("minimap window: found, and its map name read")
    for name, frame, want in FRAME_CASES:
        shot = Image.open(os.path.join(HERE, name)).convert("RGB")
        found = game_sync.find_minimap(shot)
        check(found == frame, f"{name}: minimap window at {found} (want {frame})")
        map_id, text, sure = game_sync.read_location(shot, db.maps, found)
        got = db.maps.get(map_id or "", {}).get("displayName")
        check(got == want and sure, f"{name}: {got} from {text!r} (want {want}, read inside the window)")
    # a new map's wider minimap running under our docked GPS: seen as covered (the GPS steps aside),
    # while the GPS docked right beside it is not in the way
    from PIL import ImageDraw
    shot = Image.open(os.path.join(HERE, "live_frame_1920.png")).convert("RGB")
    for cover, blocked in (((180, 2, 450, 277), True), ((268, 2, 538, 277), False)):
        covered = shot.copy()
        ImageDraw.Draw(covered).rectangle(cover, fill="#14121E")
        report = {}
        found = game_sync.find_minimap(covered, (cover,), report)
        check(bool(report.get("blocked")) == blocked and (found is None) == blocked,
              f"GPS at x={cover[0]}: {'covers the minimap' if blocked else 'beside it'} -> {found}, {report}")
    base = Image.open(os.path.join(HERE, "live_frame_ant_tunnel2.png")).convert("RGB")
    for factor, how in STRETCHED:
        shot = base.resize((round(base.width * factor), round(base.height * factor)), getattr(Image, how))
        found = game_sync.find_minimap(shot)
        tall = found and (found[3] - found[1]) / (196 * factor)
        check(found and abs(tall - 1) < 0.04, f"stretched {factor}x ({how}): minimap window at {found}")
        map_id, text, sure = game_sync.read_location(shot, db.maps, found)
        got = db.maps.get(map_id or "", {}).get("displayName")
        check(got == "Ant Tunnel II" and sure, f"stretched {factor}x ({how}): {got} from {text!r}")

    print("gold progress lines (the game's own count on a kill or a pickup)")
    for name, height, want in NOTICE_CASES:
        lines = game_sync.read_notice_area(Image.open(os.path.join(HERE, name)).convert("RGB"), height)
        squash = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
        missing = [w for w in want if not any(squash(w) in squash(line) for line in lines)]
        check(not missing, f"{name}: {lines} (missing {missing})")

    print("EXP bar (kills to level up)")
    import leveling
    for name, level, want in (("live_frame_1920.png", 25, 11.31), ("live_frame_ant_tunnel2.png", 25, 11.22),
                              ("live_exp_2560.png", 26, 53.34), ("live_2.png", 20, None)):
        texts = game_sync.read_exp_bar(Image.open(os.path.join(HERE, name)).convert("RGB"))
        got = leveling.read_bar(texts, level)
        check((got and got[2]) == want, f"{name}: {got} (want {want}%) from {texts}")

    print("map names from minimap text")
    for street, text, want in MAP_TEXT_CASES:
        lines = [{"text": street, "x": 100, "y": 50, "h": 18}, {"text": text, "x": 100, "y": 72, "h": 18}]
        got = db.maps.get(sync.match_map(lines, db.maps) or "", {}).get("displayName")
        check(got == want, f"{text!r} -> {got}")

    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
