"""Trainer: what to do next, so the GPS can lead the way without being asked.

Only decides; it never touches the game. The app gives it a context (plain values) and follows
the step it picks: turn a finished quest in, take a worthwhile quest that's close or goes with
what you're hunting, hunt for your open quests on the map that covers most of them, or, with
nothing worth doing, train on the best map for your level.
"""

PICKUP_NEAR = 4        # portals: a new quest this close is "on the way"
PICKUP_ALONE = 10      # with no open quests, a quest giver up to this far is still worth the trip
PICKUP_SHARE = 0.5     # a new quest must be worth at least this share of your best open quest
MAX_OPEN = 6           # with this many quests open, finish some before taking more
FARM_MIN_SHARE = 0.3   # a map covering more objectives must still have this share of the busiest's monsters
BETTER_BY = 3          # portals: on a plain map change, switch only to a step this much closer
KINDS = ("turn_in", "pickup", "farm", "go", "train")  # most urgent first


def _step(kind, key, map_id, text, reason, quest=None, npc=None, mobs=None):
    return {"kind": kind, "key": (kind, key), "map": map_id, "quest": quest, "npc": npc,
            "mobs": tuple(mobs or ()), "text": text, "reason": reason}


def _portals(away):
    return "here" if away == 0 else "1 portal" if away == 1 else f"{away} portals" if away is not None else "far"


def wanted_mobs(ctx):
    """{monster id (str): {(quest id, objective index)}} still needed by the open quests."""
    wanted = {}
    for qid in ctx["active"]:
        steps, done = ctx["guides"].get(qid), ctx["done"].get(qid, set())
        if not steps:
            continue  # its guide (who drops what) isn't known yet
        for i, _ in enumerate(ctx["quests"][qid].get("need") or []):
            if i in done or i >= len(steps):
                continue
            for line in steps[i].get("lines") or []:
                wanted.setdefault(str(line["mob"]), set()).add((qid, i))
    return wanted


def turn_ins(ctx):
    """Open quests with every objective done, nearest turn-in NPC first."""
    out = []
    for qid in ctx["active"]:
        q = ctx["quests"][qid]
        needs = len(q.get("need") or [])
        if not needs or not set(range(needs)) <= ctx["done"].get(qid, set()):
            continue
        npc = q.get("completeNpc") or q.get("npc")
        map_id = ctx["npc_map"](npc)
        away = ctx["dist"].get(map_id) if map_id else None
        out.append((away if away is not None else 999,
                    _step("turn_in", qid, map_id, f"Turn in: {npc or q['name']}",
                          f"{q['name']} is done · {npc} · {_portals(away)}", quest=qid, npc=npc)))
    return [s for _, s in sorted(out, key=lambda x: x[0])]


def farm_maps(ctx, wanted=None):
    """Maps for the open quests together: the most objectives covered (of any quest), then the
    most of those monsters, then the shortest trip. Maps far poorer than the busiest are left
    out, so one lonely monster doesn't win just by covering a second quest."""
    wanted = wanted_mobs(ctx) if wanted is None else wanted
    if not wanted:
        return []
    dist, rows = ctx["dist"], []
    for m in ctx["map_data"].values():
        here = {str(mob["id"]): mob.get("count", 0) for mob in m.get("monsters") or []}
        mobs = wanted.keys() & here.keys()
        if not mobs or (dist and m["id"] not in dist):
            continue
        covers = set().union(*(wanted[mob] for mob in mobs))
        rows.append({"map": m["id"], "name": m.get("name", m["id"]), "mobs": sorted(mobs, key=lambda x: -here[x]),
                     "covers": covers, "count": sum(here[mob] for mob in mobs), "dist": dist.get(m["id"])})
    if not rows:
        return []
    busiest = max(r["count"] for r in rows)
    rows = [r for r in rows if r["count"] >= busiest * FARM_MIN_SHARE]
    rows.sort(key=lambda r: (-len(r["covers"]), -r["count"], r["dist"] if r["dist"] is not None else 999))
    return rows


def farm_steps(ctx, wanted=None):
    out = []
    for r in farm_maps(ctx, wanted):
        quests = {qid for qid, _ in r["covers"]}
        names = [ctx["mob_name"](mob) for mob in r["mobs"][:2]]
        text = f"Hunt: {' + '.join(names)}" + (f" ({len(quests)} quests)" if len(quests) > 1 else "")
        reason = (f"{r['name']} · {len(r['covers'])} objective{'s' * (len(r['covers']) > 1)} of "
                  f"{len(quests)} quest{'s' * (len(quests) > 1)} · {r['count']} monsters · {_portals(r['dist'])}")
        out.append(_step("farm", r["map"], r["map"], text, reason,
                         quest=next(iter(sorted(quests))), mobs=[int(mob) for mob in r["mobs"]]))
    return out


def go_steps(ctx, wanted=None):
    """Open quests that aren't about hunting (a jump quest, a page to find, someone to see): go
    where their guide or NPC says ("Shane" lets you into the Forest of Patience)."""
    wanted = wanted_mobs(ctx) if wanted is None else wanted
    hunted = {qid for objectives in wanted.values() for qid, _ in objectives}
    out = []
    for qid in ctx["active"]:
        q, goal = ctx["quests"][qid], ctx.get("goals", {}).get(qid)
        needs = len(q.get("need") or [])
        if qid in hunted or not goal or (needs and set(range(needs)) <= ctx["done"].get(qid, set())):
            continue
        map_id, npc, what = goal
        out.append(_step("go", qid, map_id, f"Go: {npc or what}"[:60],
                         f"{q['name']} · {what} · {_portals(ctx['dist'].get(map_id))}", quest=qid, npc=npc))
    return sorted(out, key=lambda s: ctx["dist"].get(s["map"], 999))


def pickup_steps(ctx, wanted=None):
    """Suggested quests worth taking now: close (or going with what you hunt) while you have
    open quests and worth at least half your best one; the best within reach when you have none."""
    wanted = wanted_mobs(ctx) if wanted is None else wanted
    out = []
    if len(ctx["active"]) >= MAX_OPEN:
        return out
    for q, nm, away, value in ctx["suggestions"]:
        if not nm or away is None or not value:
            continue
        if ctx["active"]:
            mobs = {str(line["mob"]) for step in ctx["guides"].get(q["id"]) or [] for line in step.get("lines") or []}
            along = bool(mobs & wanted.keys())
            if not (away <= PICKUP_NEAR or along) or value["score"] < ctx["active_score"] * PICKUP_SHARE:
                continue
            why = "goes with what you're hunting" if along else "on your way"
        elif away > PICKUP_ALONE:
            continue
        else:
            why = "the best quest for you now"
        out.append(_step("pickup", q["id"], nm["mapId"], f"Take: {q['name']}",
                         f"{q.get('npc')} · {_portals(away)} · {round(value['exp_per_min']):,} EXP/min, {why}",
                         quest=q["id"], npc=q.get("npc")))
    return out


def train_steps(ctx):
    """With nothing worth doing: the busiest training maps for your level, nearest of the top 5."""
    dist = ctx["dist"]
    maps = [m for m in ctx["training"] if not dist or m["id"] in dist]
    top = sorted(maps, key=lambda m: -(m.get("totalMobCount") or 0))[:5]
    top.sort(key=lambda m: (dist.get(m["id"], 999) if dist else 0, -(m.get("totalMobCount") or 0)))
    return [_step("train", m["id"], m["id"], f"Train: {m['displayName']}",
                  f"{m.get('totalMobCount', 0)} monsters, Lv ~{round(m.get('avgMobLevel') or 0)} · "
                  f"{_portals(dist.get(m['id']) if dist else None)}") for m in top]


def candidates(ctx):
    """Every step worth doing, most urgent first (see KINDS)."""
    wanted = wanted_mobs(ctx)
    steps = turn_ins(ctx) + pickup_steps(ctx, wanted) + farm_steps(ctx, wanted) + go_steps(ctx, wanted)
    if not ctx["active"] or not steps:
        steps += train_steps(ctx)
    return steps


def next_step(ctx, skipped=()):
    return next((s for s in candidates(ctx) if s["key"] not in skipped), None)


class Trainer:
    """Keeps one step until something happens (an objective done, a quest taken or turned in, a
    level-up, Skip), so the GPS doesn't hop between maps on every sync."""

    def __init__(self):
        self.step, self.skipped = None, set()

    def update(self, ctx, event=False):
        """Plan again if needed. True when the step changed."""
        new = next_step(ctx, self.skipped)
        old = self.step
        if event or old is None or not self._still_valid(old, ctx):
            self.step = new
        elif new and new["key"] != old["key"]:
            if KINDS.index(new["kind"]) < KINDS.index(old["kind"]):
                self.step = new  # something more urgent turned up (a quest got done)
            else:
                d_new, d_old = ctx["dist"].get(new["map"]), ctx["dist"].get(old["map"])
                if d_new is not None and (d_old is None or d_new + BETTER_BY <= d_old):
                    self.step = new  # clearly closer from where you are now
        return (self.step or {}).get("key") != (old or {}).get("key")

    def skip(self, ctx):
        """Leave the current step for this run and take the next one."""
        if self.step:
            self.skipped.add(self.step["key"])
        self.step = next_step(ctx, self.skipped)
        return self.step

    @staticmethod
    def _still_valid(step, ctx):
        if step["kind"] == "turn_in":
            return any(s["key"] == step["key"] for s in turn_ins(ctx))
        if step["kind"] == "pickup":
            return step["quest"] not in ctx["active"]
        if step["kind"] == "farm":
            return any(s["key"] == step["key"] for s in farm_steps(ctx))
        if step["kind"] == "go":
            return any(s["key"] == step["key"] for s in go_steps(ctx))
        return not ctx["active"]  # train: until you have quests
