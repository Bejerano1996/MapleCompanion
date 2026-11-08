"""Checks for the helper's logic (no screen reading): routes, best maps, suggestions, sorting.

Run from the project folder:  python tests/test_logic.py
Uses the downloaded data in cache/, so it needs no network once the app has run once.
"""
import os
import sys
import time
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import app  # noqa: E402
import sync  # noqa: E402

# Install isolation before constructing App: its constructor starts background work.
app.App.sync_from_game=lambda *args,**kwargs:None
class NoHotkey:
    def __init__(self,*args,**kwargs):pass
    def start(self):pass
app.HotkeyThread=NoHotkey

HENESYS, PERION, ELLINIA = "010001000", "010004000", "010002000"
SOUTHPERRY, LITH, ORBIS = "000000060", "010000000", "020000000"
SNAIL_1, SPLIT_ROAD = "000000040", "000000050"

passed = failed = 0


def check(ok, what):
    global passed, failed
    passed, failed = passed + bool(ok), failed + (not ok)
    print(("  ok   " if ok else "  FAIL ") + what)


def make_app(**state):
    """An App with a throw-away state file, data loaded, window hidden."""
    app.STATE_FILE = os.path.join(HERE, "logic_state.json")
    with open(app.STATE_FILE, "w", encoding="utf-8") as f:
        import json
        json.dump({"geometry": "380x600+-3000+-3000", **state}, f)
    root = tk.Tk()
    root.withdraw()
    a = app.App(root)
    a.sync_from_game = lambda *args, **kw: None  # never read the real screen (a running game) in tests
    a.db.load_indexes()  # synchronously, instead of waiting for the background load
    return root, a


def main():
    root, a = make_app(level=20, map=PERION)
    db = a.db
    name = lambda mid: db.map_data[mid]["name"]

    print("routes")
    r = db.route(SNAIL_1, SPLIT_ROAD)
    check(r and [p["name"] for _, p in r] == ["east00"] * 3, "walking route: 3 portals east")
    r = db.route(SPLIT_ROAD, HENESYS)
    check(r and any(p.get("npc") == "Shanks" for _, p in r), "Maple Island -> Henesys takes Shanks' ship")
    check(db.route(LITH, SOUTHPERRY) is None, "no way back to Maple Island (one-way ship)")
    r = db.route(HENESYS, PERION)
    check(r and not any(p.get("cab") for _, p in r), f"Henesys -> Perion walks by default ({len(r)} steps)")
    r = db.route(HENESYS, PERION, cabs=True)
    check(r and len(r) == 1 and "Cab" in r[0][1].get("transport", ""), "with taxis allowed: one cab ride")
    check(db.route(HENESYS, ORBIS) is not None and db.route(ORBIS, HENESYS) is not None,
          "Henesys <-> Orbis both ways (ship)")
    check(db.route(HENESYS, HENESYS) == [], "route to where you are is empty")
    d = db.distances(HENESYS)
    check(d[HENESYS] == 0 and d[PERION] == len(db.route(HENESYS, PERION)),
          f"distances: here 0, Perion = the walking route's {d.get(PERION)} steps")
    check(db.distances(HENESYS, cabs=True)[PERION] == 1, "with taxis: Perion is 1 step")

    same = all(d[mid] == len(db.route(HENESYS, mid)) for mid in list(d)[::15])
    check(same, "distance shown = number of steps in the route (round 12)")

    print("portal side")
    detail = db.map_detail(SNAIL_1)
    east = next(p for p in detail["portals"] if p["name"] == "east00")
    check("right" in app.portal_side(detail, east), f"east00 is on the right ({app.portal_side(detail, east)})")
    check(app.portal_side({"minimapWidth": 0}, {"name": "x"}) == '"x" portal', "no map size: no crash")

    print("best maps for a quest")
    q = db.quests["10123"]  # Shroom, Orange Mushroom, Mushroom Spore, Orange Mushroom Cap
    steps = a._resolve_guide(q)
    a.state["map"] = HENESYS
    a._dist = (None, {})
    best = a.best_maps("10123", q, steps)
    check(best and len(best[0]["covers"]) >= 1, f"best map: {name(best[0]['map'])} "
          f"({best[0]['count']} mobs, covers {len(best[0]['covers'])} of 4)")
    check(best[0]["count"] == max(b["count"] for b in best),
          f"first map has the most of the needed monsters ({best[0]['count']})")
    check(all(b["dist"] is not None for b in best), "no unreachable maps once your location is known")
    a.state["done"]["10123"] = [0, 1, 2, 3]
    check(a.best_maps("10123", q, steps) == [], "nothing to farm once every objective is done")
    a.state["done"]["10123"] = []

    print("suggestions")
    a.state.update(level=15, active=["80014"], completed=[], hidden_suggestions=[])
    picks = a.suggested_quests()
    names = [p[0]["name"] for p in picks]
    check(len(picks) == app.SUGGESTIONS, f"{app.SUGGESTIONS} suggestions")
    check(len(names) == len(set(names)), "no duplicate names (tiered quests)")
    check(all((p[0].get("levelMin") or 0) <= 15 for p in picks), "none above your level")
    check("80014" not in [p[0]["id"] for p in picks], "nothing already on your list")
    a.hide_suggestion(picks[0][0]["id"])
    check(picks[0][0]["id"] not in [p[0]["id"] for p in a.suggested_quests()], "hidden stays hidden")

    print("quest ranking (EXP for the effort)")
    import quest_rank
    sam = db.quests["1021"] if "1021" in db.quests else next(q for q in db.quests.values()
                                                             if q["name"] == "Sam's Suggestion")
    a.state["map"] = SOUTHPERRY  # Sam is on Maple Island
    v = a.quest_value(sam)
    check(v and 0.5 <= v["minutes"] < 30 and v["exp_per_min"] > 0, f"Sam's Suggestion: about {v and round(v['minutes'], 1)} min")
    a.state["map"] = PERION
    check(a.quest_value(sam) is None, "from Victoria Island, Maple Island quests can't be reached (one-way ship)")
    jq = next(q for q in db.quests.values() if q["name"].startswith("[Forest of Patience]"))
    check(quest_rank.is_jump_quest(jq), f"jump quest spotted: {jq['name']}")
    check(quest_rank.kill_seconds(40, 15) > 10 * quest_rank.kill_seconds(15, 15), "monsters far above you take far longer")
    a.state.update(level=30, map=HENESYS, suggest_sort="value")
    ranked = a.suggested_quests()
    scores = [p[3]["score"] for p in ranked]
    check(scores == sorted(scores, reverse=True), "Best EXP/min: highest score first")
    check(all(p[3] for p in ranked), "every ranked quest has an estimate (unreachable ones are left out)")
    a.state["suggest_sort"] = "near"
    near = [p[2] if p[2] is not None else 999 for p in a.suggested_quests()]
    check(near == sorted(near), "Nearest: closest quest giver first")
    a.state.update(level=15, map=PERION, suggest_sort="value")

    print("done quests from prerequisites")
    chain = next(q for q in db.quests.values() if q["name"] == "Bringing a Mirror to Heena")
    first = a.prerequisites(chain)[0]
    a.state.update(active=[chain["id"]], completed=[])
    check(first in a.done_quests(), f"{db.quests[first]['name']} counts as done when its follow-up is on the list")
    check(not a.available(db.quests[first]), "so it isn't suggested again")
    a.state.update(active=["80014"], completed=[])

    print("GPS route ends with its quest")
    a.state.update(active=["10301", "80014"], completed=[])
    a.start_route("10301", HENESYS, None, "Chief Stan")
    check(a.gps_key == "10301" and a.gps is not None, "GPS following Talking to Stan")
    app.messagebox.askyesno = lambda *k, **kw: False  # don't stop on the "next quest" question
    a.complete_quest("10301")
    check("10301" not in a.routes and a.gps_key is None and a.gps is None,
          "completing the quest ends its route and closes the GPS (it used to stay stuck on it)")
    a.start_route("80014", HENESYS)
    a.state["active"] = []
    a._drop_gone_quest_routes()
    check("80014" not in a.routes, "a quest gone after a Reset drops its route too")
    a.start_route("map", PERION)
    a._drop_gone_quest_routes()
    check("map" in a.routes, "routes that aren't quests (map search, Mobs, Items) are kept")
    a.stop_route("map")
    a.state.update(active=["80014"], completed=[])

    print("AUTO off: the GPS still follows you")
    a.state.update(auto_sync=False, map=PERION, active=["80014"])
    a.start_route("map", HENESYS)
    calls = []
    real_sync = a.sync_from_game
    a.sync_from_game = lambda auto=False, map_only=False: calls.append((auto, map_only))
    a._schedule_auto_sync()
    end = time.time() + app.AUTO_SYNC_MS / 1000 + 1
    while time.time() < end:
        root.update()
    check(calls and all(c == (True, True) for c in calls), f"with the GPS open, the timer reads only the map ({calls[:2]})")
    a.sync_from_game = real_sync
    before = list(a.state["active"]), dict(a.state["progress"])
    for _ in range(2):  # a reading counts once it comes out the same twice
        a._on_synced({"map_only": True, "map": HENESYS, "auto": True, "window": True})
    check(a.state["map"] == HENESYS, "the map reading moves you (and the GPS)")
    check((list(a.state["active"]), dict(a.state["progress"])) == before, "quests and counts untouched")
    a.stop_route("map")
    calls.clear()
    a.sync_from_game = lambda auto=False, map_only=False: calls.append((auto, map_only))
    a._schedule_auto_sync()
    end = time.time() + app.AUTO_SYNC_MS / 1000 + 1
    while time.time() < end:
        root.update()
    check(not calls, "AUTO off and no GPS: nothing is read")
    a.sync_from_game = real_sync
    if a._auto_job:
        root.after_cancel(a._auto_job)
    a.state.update(map=PERION)

    print("training sorts")
    a.state.update(level=20, map=PERION, tab="train")
    a._dist = (None, {})
    for how in ("mobs", "exp", "near"):
        a.state["train_sort"] = how
        a.render()
        cards = a.scroll.inner.winfo_children()[1:]
        check(len(cards) == app.TRAINING_MAPS, f"{how}: {app.TRAINING_MAPS} maps listed")
    maps = db.training_maps(20, limit=None)
    top = max(maps, key=lambda m: m.get("totalMobCount") or 0)
    a.state["train_sort"] = "mobs"
    a.render()
    first = a.scroll.inner.winfo_children()[1]
    texts = []

    def collect(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Label):
                texts.append(child.cget("text"))
            collect(child)
    collect(first)
    check(top["displayName"] in texts, f"Most mobs puts {top['displayName']} first")

    print("turned-in detection")
    a.state.update(active=["80020", "10100", "10304"], tracked=["80020", "10100", "10304"],
                   done={"80020": [0, 1]}, completed=[])
    a._gone.clear()
    res = lambda seen: {"quests": seen, "progress": {}, "map": None, "window": True, "auto": True,
                        "full": False, "regions": None, "tracked": seen, "quest_window": False}
    for _ in range(app.GONE_AFTER + 2):
        a._on_synced(res([]))  # Quest Helper not on screen: can't tell, so nothing changes
    check(a.state["tracked"] == ["80020", "10100", "10304"], "helper hidden: nothing changes")
    for _ in range(app.GONE_AFTER):
        a._on_synced(res(["10304"]))
    check("80020" in a.state["completed"] and "80020" not in a.state["active"],
          "finished quest gone from the helper = turned in")
    check("10100" in a.state["active"] and "10100" not in a.state["tracked"],
          "unfinished quest gone = just not live any more")

    print("check marks follow the game (Garnet Ore)")
    q = "80023"  # Chrishrama: Dark Stump x30, Garnet Ore x1
    a.state.update(active=[q], tracked=[q], done={q: [0, 1]}, progress={q: {"0": 30, "1": 0}})
    a._reads.clear()
    read = lambda have: a._on_synced({"quests": [q], "progress": {q: have}, "map": None, "window": True,
                                      "auto": True, "full": False, "regions": None, "tracked": [q],
                                      "quest_window": False})
    read({0: 30, 1: 0})
    read({0: 30, 1: 0})
    check(a.state["done"][q] == [0], f"0 / 1 read twice removes the wrong ✔ (done {a.state['done'][q]})")
    read({0: 30, 1: 1})
    read({0: 30, 1: 1})
    check(1 not in a.state["done"][q], "a misread 1 / 1 twice doesn't tick it any more")
    read({0: 30, 1: 1})
    check(1 in a.state["done"][q], "three matching reads of 1 / 1 do tick it")

    print("map detection, every map")
    wrong = []
    for m in db.maps.values():
        lines = [{"text": m.get("displayStreet") or "", "x": 100, "y": 50, "h": 18},
                 {"text": m["displayName"], "x": 100, "y": 72, "h": 18}]
        got = sync.match_map(lines, db.maps)
        if got is None or db.maps[got]["displayName"] != m["displayName"]:
            wrong.append(m["displayName"])
    check(not wrong, f"all {len(db.maps)} maps read from their minimap title (wrong: {wrong[:5]})")

    print("location only from the minimap title")
    labels = [{"text": t, "x": 100 + 90 * i, "y": 300, "h": 16} for i, t in enumerate(["Perion", "Ellinia", "Henesys"])]
    check(sync.match_map(labels, db.maps, anchored_only=True) is None,
          "World Map town labels alone are not where you are")
    title = [{"text": "Victoria Road", "x": 72, "y": 42, "h": 14}, {"text": "Henesys Hunting Ground I", "x": 72, "y": 65, "h": 14}]
    check(db.maps.get(sync.match_map(title, db.maps, anchored_only=True), {}).get("displayName") == "Henesys Hunting Ground I",
          "street + map name (the minimap title) still reads")

    print("NPCs in the map search")
    a.state["map"] = HENESYS
    stan = a.find_npcs("stan")
    check(stan and stan[0]["npc"] == "Chief Stan" and stan[0]["mapId"] == HENESYS, f"'stan' → Chief Stan in Henesys ({stan[:1]})")
    check(all("Assistant" not in r["npc"] for r in stan), "word starts only: 'stan' doesn't match Assistant")
    check(a.find_npcs("shanks") and a.find_npcs("shanks")[0]["mapId"] == SOUTHPERRY, "Shanks → Southperry")
    check(a.find_npcs("st") == [], "under 3 letters: no NPC results")

    print("party quests")
    import party_quests
    kpq = party_quests.PARTY_QUESTS[0]
    combos = [len(st.get("combos") or []) for st in kpq["stages"] if st.get("combos")]
    check(combos == [4, 10, 20], f"KPQ combinations: ropes 4, kittens 10, barrels 20 ({combos})")
    check(all(len(set(st["combos"])) == len(st["combos"]) for st in kpq["stages"] if st.get("combos")),
          "no combination listed twice")
    check(kpq["map"] in db.maps and db.npc(kpq["npc"]) and db.npc(kpq["npc"])["maps"][0]["mapId"] == kpq["map"],
          "Lakelis stands on the PQ's start map")
    a.state["tab"] = "pq"
    a.render()
    renders = []
    real_render = a.render
    a.render = lambda *k, **kw: renders.append(1)
    chips = []

    def walk(w):
        for c in w.winfo_children():
            if getattr(c, "cget", None) and isinstance(c, tk.Label) and c.cget("text") == "3 4 5":
                chips.append(c)
            walk(c)
    walk(a.scroll.inner)
    chips[0].toggle(None)  # the test window is hidden, so a real click wouldn't arrive
    root.update()
    check(("kpq", 2, "3 4 5") in a.pq_tried and not renders, "crossing off a combination repaints only that chip")
    a.render = real_render
    a.pq_tried.clear()
    a.start_route("pq", kpq["map"], None, kpq["npc"])
    check(a.routes.get("pq") == (kpq["map"], None, "Lakelis"), "🧭 Go routes the GPS to Lakelis")
    a.stop_route("pq")
    a.state["tab"] = "quests"

    print("narrow window")
    renders = []
    real_refit = a._refit
    def counted_refit():
        renders.append(1)
        real_refit()
    a._refit = counted_refit
    a._render_width = 380
    a._on_window_resize(type("E", (), {"widget": a.root, "width": 382})())
    check(a._refit_job is None, "a 2 px change doesn't redraw")
    a._on_window_resize(type("E", (), {"widget": a.root, "width": 340})())
    a._on_window_resize(type("E", (), {"widget": a.root, "width": 330})())
    end = time.time() + 0.6
    while time.time() < end:
        root.update()
    check(len(renders) == 1, f"resizing redraws once, after the width settles ({len(renders)})")
    a._refit = real_refit

    print("number tails / short words")
    check(sync._number_tail("I Need to Find My Daughter 2") == "2", "trailing 2")
    check(sync._number_tail("Snail Hunting Ground III") == "3", "trailing III")
    check(sync.title_score("Mr. Thunder in Need of an...", "Mr. Thunder in Need of Help") <
          sync.title_score("Mr. Thunder in Need of an...", "Mr. Thunder in Need of an Apprentice"),
          '"an" tells Apprentice from Help')

    print("NPC shops")
    red = db.sold_by.get("2000000") or []
    check(any(s["npc"] == "Lucy" and s["price"] == 50 for s in red), "Red Potion: Lucy sells it for 50")
    check([s["price"] for s in red] == sorted(s["price"] for s in red), "sellers listed cheapest first")
    check(all(s["mapId"] in db.maps for v in db.sold_by.values() for s in v), "every shop is on a known map")
    check(any(s["citizen"] for v in db.sold_by.values() for s in v), "citizen-only stock is marked")
    a.state["map"] = PERION
    shops = a.find_shops("potion")
    check(shops and shops[0]["npc"] == "Arturo", f"'potion' from Perion: nearest grocer first ({shops[:1]})")
    check(all("(Weapon Seller)" in r["label"] for r in a.find_shops("weapon")), "'weapon' lists weapon shops only")
    check("50 m" in (a.find_shops("red potion") or [{"label": ""}])[0]["label"], "'red potion' shows the price")
    check(a.find_shops("perion") == [], "a town name finds maps, not 'Return Scroll to Perion'")

    print("patch notes: new maps")
    exc = [m["id"] for m in db.maps.values() if m["displayName"].startswith("Excavation Site")]
    check(len(exc) >= 4 and all(db.route(PERION, m) for m in exc),
          f"Excavation Site (Oct 21 launch, Perion) is in the data and routable ({len(exc)} maps)")

    print("gold progress lines")
    luke = next(q for q in db.quests.values() if q["name"] == "Luke the Security Guy")["id"]
    a.state["active"], a.state["progress"], a.state["done"] = [luke], {}, {}
    necki = next(i for i, o in enumerate(a.objectives(luke)) if o[2] == "Jr. Necki")
    for text, want in (("Jr. Necki 19 120", 19), ("Jr. Necki 12 J 20", 12), ("Jr. Necki 5 20", 5),
                       ("Jr. Necki 32 / 20", None), ("'Jr. Neöki 7 1 20", 7), ("Jr. Necki 4 40", None),
                       ("Jr. Necki2120", 2)):
        got = [h for q, i, h in a.notice_progress([text]) if (q, i) == (luke, necki)]
        check(got == ([want] if want is not None else []), f"{text!r} -> {got} (want {want})")
    a.state["progress"] = {luke: {str(necki): 7}}
    got = [h for q, i, h in a.notice_progress(["Jr. Necki 8120"]) if (q, i) == (luke, necki)]
    check(got == [8], f"'Jr. Necki 8120' after 7 -> {got}: the count right after what we have")
    a.state["active"], a.state["progress"], a.state["done"] = [], {}, {}

    print("kills to level up")
    import leveling
    table = {1: 15, 5: 135, 6: 372, 25: 47216, 50: 709716, 51: 748608, 89: 5684790, 90: 11938059}
    check(all(leveling.exp_to_next(lv) == v for lv, v in table.items()), "EXP table matches meowdb's (Lv 1-90)")
    # texts as Windows OCR really read them, from tests/live_frame_1920.png and the user's 2560 screen
    check(leveling.read_bar(["EXP.s 340 11.31%", "s ,340 11.31%"], 25) == (25, None, 11.31),
          "bar with a garbled number: the % is kept")
    check(leveling.read_bar(["28,474", "dP28,474 Sl .87%", "28,474 Sl .B7%"], 26) == (26, 28474, 51.87),
          "'Sl .B7%' (51.87%): the number is trusted when the % ending agrees")
    check(leveling.read_bar([". 29,2es 9.34%", "S3.34%", "s3.34%", "d229,as 53.34%"], 26) == (26, None, 53.34),
          "look-alike letters: 'S3.34%' is 53.34%, and most versions win over '9.34%'")
    check(leveling.read_bar(["9.34%", "53.34%"], 26, previous=52.9)[2] == 53.34, "a tie goes to the nearest %")
    check(leveling.read_bar(["HP 721", "MP ss2/63S"], 26) is None, "HP / MP alone are not the EXP bar")
    check(leveling.read_bar(["5,340 11.31%"], 24) == (25, 5340, 11.31), "'5,340 [11.31%]' is Lv 25, not 24")
    check(leveling.exp_from_bar(340, 11.31, 25) == 5340, "a number that disagrees with the % is replaced")
    check(leveling.party_exp(50, 25) == 50, "solo: the monster's EXP")
    check(leveling.party_exp(50, 25, 4, "all") == 19, "party of 4, all hit: 13 + 45% bonus = 19")
    check(leveling.party_exp(50, 25, 6, "me") == 22, "party of 6, you kill: 17 + 30% = 22")
    check(leveling.party_exp(50, 25, 2, "leech") == 22, "party of 2, you leech: 20 + 10% = 22")
    evil_eye_3 = "010005073"
    a.state.update(level=25, map=evil_eye_3, party=1, exp_bar=[5340, 11.31])
    rows = a.levelup_rows()
    check(rows and rows[0][:2] == ("Evil Eye", 50) and rows[0][3] == 838,
          f"Evil Eye at Lv 25, 11.31%: 50 EXP, 838 kills ({rows[:1]})")
    check(rows and abs(rows[0][2] - 0.1059) < 0.001, "one Evil Eye is 0.11% of the bar")
    a.state["level"], a.state["exp_bar"] = 24, None
    a.on_exp_bar(["5,340 11.31%"], lambda *k: True)
    check(a.state["level"] == 25, "the level box follows the bar's numbers (24 -> 25)")
    a.on_exp_bar(["0.42%"], lambda *k: True)
    check(a.state["level"] == 25, "a bar with only a % doesn't change the level")
    a.state["exp_bar"] = [None, 99.1]
    a.on_exp_bar(["0.20%"], lambda *k: True)
    check(a.state["level"] == 25, "a percentage-only drop cannot prove a level-up")
    a._reads.clear()
    a.state["exp_bar"] = [None, 40.0]
    a.on_exp_bar(["40.12%"], a._confirmed)
    check(a.state["exp_bar"][1] == 40.0, "percentage-only reads cannot overwrite validated numeric EXP")
    a.on_exp_bar(["30.00%"], a._confirmed)
    check(a.state["exp_bar"][1] == 40.0, "an unvalidated percentage drop is rejected")
    a.on_exp_bar(["30.00%"], a._confirmed)
    check(a.state["exp_bar"][1] == 40.0, "repetition alone cannot validate a percentage-only drop")
    a.state["party"] = 3
    a.render_levelup()
    a.companion_exp_details()
    from companion_widgets import ui_walk_widgets
    texts=[w.cget('text') for w in ui_walk_widgets(a._companion_exp_window) if isinstance(w,(tk.Label,tk.Button))]
    check('Party on map' in texts and 'Apply' in texts, 'Party and calibration controls remain available')
    a._companion_exp_window.destroy()
    a.state.update(party=1,level=26)
    a.training_accept_character({'level':26,'exp':29285})
    a.refresh_exp_pill()
    pill=a.exp_pill.cget('text')
    check(pill.startswith('53') and 'EXP left' in a.exp_pill.tip.text,'Title percentage and forecast tooltip use validated EXP')

    print("trainer")
    import trainer
    quests = {"q1": {"id": "q1", "name": "One", "need": [{"count": 10}]},
              "q2": {"id": "q2", "name": "Two", "need": [{"count": 10}]},
              "q3": {"id": "q3", "name": "Three", "need": [{"count": 1}], "npc": "Far NPC"},
              "q4": {"id": "q4", "name": "Four", "need": [{"count": 1}], "npc": "Near NPC"}}
    guides = {"q1": [{"lines": [{"mob": 1}]}], "q2": [{"lines": [{"mob": 2}]}], "new": [{"lines": [{"mob": 2}]}]}
    map_data = {"M1": {"id": "M1", "name": "Busy A", "monsters": [{"id": "1", "count": 40}]},
                "M2": {"id": "M2", "name": "A and B", "monsters": [{"id": "1", "count": 10}, {"id": "2", "count": 10}]},
                "M3": {"id": "M3", "name": "Busiest A", "monsters": [{"id": "1", "count": 60}]},
                "M4": {"id": "M4", "name": "Lonely B", "monsters": [{"id": "1", "count": 1}, {"id": "2", "count": 1}]}}

    def ctx(active, done=None, suggestions=(), dist=None, training=()):
        return {"level": 20, "map": "H", "active": list(active), "quests": quests, "done": done or {},
                "guides": guides, "map_data": map_data, "suggestions": list(suggestions), "active_score": 10,
                "dist": dist or {"H": 0, "M1": 2, "M2": 5, "M3": 1, "M4": 3, "N1": 3, "N2": 1, "G": 2, "F": 9},
                "npc_map": {"Far NPC": "N1", "Near NPC": "N2", "Giver": "G", "Far giver": "F"}.get,
                "mob_name": lambda mid: f"Mob {mid}", "training": list(training)}
    c = ctx(["q1", "q2", "q3", "q4"], {"q3": {0}, "q4": {0}})
    first = trainer.next_step(c)
    check(first["kind"] == "turn_in" and first["quest"] == "q4", f"turn in first, nearest NPC first ({first['text']})")
    farm = trainer.farm_steps(c)
    check(farm[0]["map"] == "M2", f"the map covering both quests wins ({[s['map'] for s in farm]})")
    check("M4" not in [s["map"] for s in farm], "a map with almost no monsters doesn't win by covering two quests")
    near = ({"id": "new2", "name": "Close one", "npc": "Giver"}, {"mapId": "G"}, 2, {"score": 9, "exp_per_min": 900})
    far = ({"id": "new3", "name": "Far one", "npc": "Far giver"}, {"mapId": "F"}, 9, {"score": 9, "exp_per_min": 900})
    along = ({"id": "new", "name": "Same mobs", "npc": "Far giver"}, {"mapId": "F"}, 9, {"score": 9, "exp_per_min": 900})
    picks = [s["quest"] for s in trainer.pickup_steps(ctx(["q1", "q2"], suggestions=[near, far, along]))]
    check(picks == ["new2", "new"], f"new quests: close, or with the monsters you hunt; not far ones ({picks})")
    t = trainer.train_steps(ctx([], training=[{"id": "M1", "displayName": "Busy A", "totalMobCount": 40},
                                             {"id": "M3", "displayName": "Busiest A", "totalMobCount": 60}]))
    check(t and t[0]["kind"] == "train" and t[0]["map"] == "M3",
          f"no quests: train on the busiest nearby map ({[s['map'] for s in t]})")
    tr = trainer.Trainer()
    c = ctx(["q1", "q2"])
    tr.update(c, event=True)
    check(tr.step["map"] == "M2", "trainer starts on the shared map")
    check(not tr.update(ctx(["q1", "q2"]), event=False), "a sync with nothing new keeps the step")
    quests["q2"]["npc"] = "Near NPC"
    c = ctx(["q1", "q2"], {"q2": {0}})
    check(tr.update(c, event=True) and tr.step["kind"] == "turn_in" and tr.step["quest"] == "q2",
          f"q2's objective done: off to turn it in ({tr.step and tr.step['text']})")
    tr.skip(c)
    check(tr.step["kind"] == "farm" and tr.step["map"] in ("M3", "M1"), f"Skip: hunting for q1 instead ({tr.step['text']})")
    tr.update(c, event=True)
    check(tr.step["kind"] == "farm", "a skipped step doesn't come back this run")
    a.state.update(level=26, map=evil_eye_3, trainer_on=False)
    a.toggle_trainer()
    check(a.state["trainer_on"] and "trainer" in a.routes and a.gps_key == "trainer",
          f"▶ starts leading: the GPS follows the trainer ({a.trainer.step and a.trainer.step['text']})")
    check(a.pill_status.cget("text").startswith("▶"), f"title row shows the step ({a.pill_status.cget('text')!r})")
    a.stop_route("trainer")
    check(not a.state["trainer_on"] and "trainer" not in a.routes, "✕ on the GPS pauses the trainer")

    print("quest rewards")
    home = next(q for q in db.quests.values() if q["name"] == "The Right to Own a Home")
    todd = next(q for q in db.quests.values() if q["name"] == "Todd's How-to-Hunt")
    hollow = next(q for q in db.quests.values() if q["name"] == "Welcome to the Hollow")
    check(quest_rank.reward_text(home) == "772 EXP · 388 mesos · +100 Henesys",
          f"reward line: {quest_rank.reward_text(home)}")
    check(quest_rank.reward_text(todd) == "10 EXP · 3 Egg", f"items in the reward: {quest_rank.reward_text(todd)}")
    check("of your choice" in quest_rank.reward_text(hollow), "a choice of items is said")
    check(quest_rank.reward_points(db, home, 26) == 772, "EXP only by default")
    with_mesos = quest_rank.reward_points(db, home, 26, ("mesos",))
    check(with_mesos > 772 and quest_rank.reward_points(db, home, 26, ("mesos", "citizen")) > with_mesos,
          f"+Mesos and +Citizenship raise its worth ({round(with_mesos)})")
    plain = quest_rank.reward_points(db, hollow, 26)
    check(abs(quest_rank.reward_points(db, hollow, 26, ("items",)) - plain * (1 + quest_rank.SCROLL_BONUS)) < 1,
          "+Items: a scroll reward counts 30% more")
    a.state.update(level=17, map=HENESYS, reward_prefs=[])
    base = a.quest_value(home)
    a.state["reward_prefs"] = ["citizen"]
    check(base and a.quest_value(home)["score"] > base["score"], "the ranking follows the switches")
    check(quest_rank.reward_points(db, home, 26, ("citizen:Kerning City",)) == 772,
          "Citizenship for Kerning City doesn't count Henesys contribution")
    a.state.update(reward_prefs=["citizen"], citizen_town="Henesys")
    check(a.reward_prefs() == ("citizen:Henesys",), "the town picked goes with the switch")
    a.state.update(reward_prefs=[], citizen_town=None)

    print("quest guides from meowdb")
    sabi, first_mark, jay = "10509", "600005", "600004"
    entry = (db.quest_guides.get(sabi) or [{}])[0]
    check(("Bring back", "Pink Anthurium x1") in entry.get("facts", []), f"Sabitrama: what to bring ({entry.get('facts')})")
    check(("Shane", ELLINIA) in entry.get("npcs", []) and any("Get in" in n for n in entry.get("notes", [])),
          "Sabitrama: Shane in Ellinia lets you in")
    check([s for s, _ in entry.get("stages", [])] == ["Step 1", "Step 2"], f"its own steps only ({entry.get('stages')})")
    mark = (db.quest_guides.get(first_mark) or [{}])[0]
    check(("Where", "The Pig Beach") in mark.get("facts", []) and any("3-Way Road-Split" in n for n in mark.get("notes", [])),
          "event page 1: The Pig Beach, and how to find the spot there")
    check(len(db.quest_guides) >= 40, f"{len(db.quest_guides)} quests have a guide")
    goal = a.quest_goal(sabi)
    check(goal and goal[:2] == (ELLINIA, "Shane"), f"trainer goal for the jump quest: Shane ({goal})")
    check((a.quest_goal(jay) or (0, 0))[1] == "Jay", f"'Talk to Jay in Henesys' becomes a GPS target ({a.quest_goal(jay)})")
    hint = db.quest_hint(sabi)
    check(hint and ("Ellinia", ELLINIA) in hint["maps"] and "entrance fee" in hint["text"],
          "the NPC's own words: Ellinia, and the entrance fee")
    c = ctx([sabi])
    c["quests"] = db.quests
    c["goals"] = {sabi: goal}
    go = trainer.go_steps(c, {})
    check(go and go[0]["npc"] == "Shane", f"trainer step for a quest with nothing to hunt: go to Shane ({go[:1]})")

    print("items: how to get them")
    needed, rewarded = a.item_quests("4031025")  # Pink Anthurium, a quest item
    check(needed == [sabi] and not rewarded, f"Pink Anthurium comes from Sabitrama's quest ({needed}, {rewarded})")
    needed, rewarded = a.item_quests("4020109")  # Star Rock
    check("10510" in rewarded, "Star Rock is a reward of Sabitrama's Anti-Aging Medicine")
    frame = tk.Frame(a.scroll.inner)
    shown = a.render_item_quests(frame, "card", {"iconKey": "4003000", "name": "Screw"})
    texts = []

    def gather(w):
        for c in w.winfo_children():
            if isinstance(c, tk.Label):
                texts.append(c.cget("text"))
            gather(c)
    gather(frame)
    check(shown and not any("Get it in" in t for t in texts) and any("reward of" in t for t in texts),
          "an ordinary item (Screw): quests that use it aren't a way to get it; rewards are")
    frame.destroy()

    print("dock in the game's top-right corner")
    real_find = app.find_game_window
    app.find_game_window = lambda: (-3000, -2400, -2000, -1700)  # a fake game window, off every screen
    real_place = a._place
    a._place = lambda w, h, at=None: (a.root.geometry(f"{w}x{h}+{at[0]}+{at[1]}"), a.root.update_idletasks())
    a.state["corner_docked"] = False
    placed = []
    a._place = lambda w, h, at=None: placed.append((w, at))
    a.toggle_corner_dock()
    check(placed and placed[-1][1][0] + placed[-1][0] == -2000 and placed[-1][1][1] == -2400,
          f"◥ puts it flush in the corner ({placed[-1:]})")
    a.root.geometry(f"+{-2600}+{-2300}")
    a.root.update()
    a._drag = (0, 0)
    a._end_move(None)
    check(not a.state["corner_docked"], "dragging it away undocks it")
    a.state["corner_docked"] = False
    app.find_game_window, a._place = real_find, real_place

    root.destroy()
    os.remove(app.STATE_FILE)
    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
