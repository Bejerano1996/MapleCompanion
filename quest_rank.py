"""Which quest to do next: an estimate of how long each quest takes (walking, kills, drops) and
how much EXP it gives for that time.

The numbers are estimates from the quest data (objectives, NPCs, monster levels and where they
live), not measurements: they're for ranking quests against each other, not a stopwatch.
"""

PORTAL_MIN = 0.4    # minutes to cross one map to the next portal
TALK_MIN = 0.3      # minutes to talk to an NPC / hand something in
DROP_RATE = 0.4     # assumed chance a quest monster drops the item (most rates aren't known)
SPARSE = 8          # a map with fewer of the monster than this: slower to farm
GUESS_KILLS = 5     # item with an unknown source: counted as this many kills each, a bit above your level
LONG_MIN = 30       # ease: a quest this long counts half as attractive as a quick one
JUMP_MIN = 10       # a jump quest ("[Forest of Patience] ...", "[Construction Site B1] ..."): climbing takes a while
ITEM_BONUS = 0.15   # "+Items": a quest that hands out gear or other items counts this much more
SCROLL_BONUS = 0.3  # ... and this much when one of them is a scroll
NEAR_LEVELS = 10    # quests this many levels around yours set what mesos and contribution are worth
REWARD_PREFS = ("mesos", "items", "citizen")  # what can count besides EXP (App state "reward_prefs")
CITIZEN_TOWNS = ("Henesys", "Kerning City")    # the towns with citizenship (contribution goes to one)


def kill_seconds(mob_level, level):
    """Seconds per kill: a few seconds at your level, much longer for monsters above it."""
    gap = (mob_level if mob_level is not None else level) - level
    return max(2.0, min(60.0, 5.0 * 1.15 ** gap))


def dropper_for(db, need, guide_step=None):
    """The monster to farm an item from: the one the quest's guide found (when downloaded), or
    one whose name is in the item's name ("Snail Shell" -> Snail). None if not known."""
    for line in (guide_step or {}).get("lines") or []:
        if line.get("mob"):
            return line["mob"]
    item = need.get("name", "").lower()
    named = [m for m in db.monsters.values() if (m.get("display") or m["name"]).lower() in item]
    if named:  # the longest name wins: "Red Snail Shell" is from Red Snail, not Snail
        return max(named, key=lambda m: len(m.get("display") or m["name"]))["id"]
    return None


def is_jump_quest(q):
    """Jump quests are named after their place in brackets and ask for an item found at the top."""
    return q["name"].startswith("[") and all("mobId" not in n for n in q.get("need") or [])


def is_quest_item(item_id):
    """Items numbered 403xxxx are quest items an NPC hands over, not monster drops."""
    return item_id // 10000 == 403


def estimate(db, q, level, here, dist_from, npc_map_of, guide=None, prefs=()):
    """{minutes, exp_per_min, score, tough, guessed, jump} for a quest, or None when its NPCs or
    monsters can't be reached. The score ranks by reward per minute: EXP, plus what `prefs` add
    (see reward_points). `here`: distances from where you are (None while that's unknown: the walk to
    the quest giver isn't counted then); `dist_from(map_id)`: distances from a
    map; `npc_map_of(name)`: the map id an NPC stands on (or None)."""
    start = npc_map_of(q.get("npc"))
    away = 0 if here is None else here.get(start) if start else None
    if not start or away is None:
        return None
    from_start = dist_from(start)
    minutes = away * PORTAL_MIN + TALK_MIN
    tough = guessed = False
    jump = is_jump_quest(q)
    if jump:  # the item waits at the top of the climb: the climb is the effort
        minutes += JUMP_MIN
    kills_by_mob = {}  # kill objectives, so a drop from the same monster isn't counted twice
    for need in q.get("need") or []:
        if "mobId" in need:
            kills_by_mob[need["mobId"]] = kills_by_mob.get(need["mobId"], 0) + need.get("count", 1)
    farm = {}  # monster -> kills needed in total
    for i, need in enumerate(q.get("need") or []):
        count = need.get("count", 1)
        if "mobId" in need:
            farm[need["mobId"]] = max(farm.get(need["mobId"], 0), kills_by_mob[need["mobId"]])
            continue
        step = guide[i] if guide and i < len(guide) else None
        mob = dropper_for(db, need, step)
        if mob is None:
            if jump or is_quest_item(need.get("itemId", 0)):
                minutes += TALK_MIN  # handed over by an NPC on the way
            else:
                guessed = True  # unknown source (until its guide is downloaded): count it cautiously
                minutes += count * GUESS_KILLS * kill_seconds(max(q.get("levelMin") or 0, level) + 3, level) / 60
            continue
        farm[mob] = max(farm.get(mob, 0), kills_by_mob.get(mob, 0) + count / DROP_RATE)
    for mob, kills in farm.items():
        info = db.monsters.get(mob) or {}
        locs = [l for l in db.mob_locations(mob) if from_start.get(l["mapId"]) is not None]
        if not locs:
            return None
        best = min(locs, key=lambda l: (from_start[l["mapId"]], -(l.get("count") or 0)))
        slow = 1.5 if (best.get("count") or 0) < SPARSE else 1.0
        minutes += 2 * from_start[best["mapId"]] * PORTAL_MIN  # there and back to the quest giver
        minutes += kills * kill_seconds(info.get("level"), level) * slow / 60
        tough = tough or (info.get("level") or 0) > level + 3
    finish = npc_map_of(q.get("completeNpc")) if q.get("completeNpc") else start
    if finish and finish != start and from_start.get(finish) is not None:
        minutes += from_start[finish] * PORTAL_MIN + TALK_MIN
    minutes = max(minutes, 0.5)
    exp = q.get("exp") or 0
    # ranking: reward per minute, weighed by how easy it is to actually finish (short, and no
    # monsters well above your level)
    ease = 1 / (1 + minutes / LONG_MIN) * (0.5 if tough else 1)
    points = reward_points(db, q, level, prefs) if prefs else exp
    return {"minutes": minutes, "exp_per_min": exp / minutes, "score": points / minutes * ease,
            "tough": tough, "guessed": guessed, "jump": jump}


_exchange = {}


def exchange(db, level):
    """(EXP per meso, EXP per contribution point) in quests near your level: the medians of
    their EXP-to-mesos and EXP-to-contribution. With "+Mesos" on, a quest's mesos then count
    as much EXP as mesos usually come with at your level (and the same for contribution)."""
    key = (id(db.quests), level)
    if key not in _exchange:
        near = [q for q in db.quests.values() if abs((q.get("levelMin") or 0) - level) <= NEAR_LEVELS and q.get("exp")]

        def median(values):
            values = sorted(values)
            return values[len(values) // 2] if values else 0
        per_meso = median(q["exp"] / q["mesos"] for q in near if q.get("mesos"))
        per_point = median(q["exp"] / q["contribution"]["amount"] for q in near
                           if (q.get("contribution") or {}).get("amount"))
        _exchange[key] = (per_meso, per_point)
    return _exchange[key]


def reward_items(q):
    """Item names a quest gives (fixed ones, plus "choice" / "random" when you pick or get one)."""
    items = [f"{i.get('count', 1)} {i['name']}" if i.get("count", 1) > 1 else i["name"]
             for i in q.get("get") or [] if i.get("count", 1) > 0]
    if q.get("rewardChoices"):
        items.append("an item of your choice")
    if q.get("rewardRandom"):
        items.append("a random item")
    return items


def reward_points(db, q, level, prefs=()):
    """A quest's reward in EXP: its EXP, plus (with those `prefs` on) its mesos and citizenship
    contribution at their usual worth near your level, and a bonus for items. "citizen:Henesys"
    counts only contribution to that town (you're a citizen of one)."""
    points = q.get("exp") or 0
    per_meso, per_point = exchange(db, level)
    if "mesos" in prefs:
        points += (q.get("mesos") or 0) * per_meso
    citizen = next((p for p in prefs if p.split(":")[0] == "citizen"), None)
    town = (q.get("contribution") or {}).get("town")
    if citizen and (":" not in citizen or citizen.split(":", 1)[1] == town):
        points += ((q.get("contribution") or {}).get("amount") or 0) * per_point
    if "items" in prefs and reward_items(q):
        names = " ".join(i["name"] for i in q.get("get") or []) + " ".join(
            i["name"] for c in (q.get("rewardChoices") or []) + (q.get("rewardRandom") or []) for i in c["items"])
        points *= 1 + (SCROLL_BONUS if "Scroll" in names else ITEM_BONUS)
    return points


def reward_text(q, limit=2):
    """ "772 EXP · 388 mesos · 3 Egg · +100 Henesys" (the first `limit` items, then "+N more")."""
    parts = []
    if q.get("exp"):
        parts.append(f"{q['exp']:,} EXP")
    if q.get("mesos"):
        parts.append(f"{q['mesos']:,} mesos")
    items = reward_items(q)
    parts += items[:limit] + ([f"+{len(items) - limit} more"] if len(items) > limit else [])
    if q.get("fame"):
        parts.append(f"+{q['fame']} fame")
    town = q.get("contribution") or {}
    if town.get("amount"):
        parts.append(f"+{town['amount']} {town.get('town', 'town')}")
    return " · ".join(parts) or "no reward listed"


def effort_words(minutes):
    return "quick" if minutes < 3 else "short" if minutes < 10 else "long"
