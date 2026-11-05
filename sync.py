"""Match noisy OCR text from the game's quest windows against the meowdb quest list.

The game's font over busy backgrounds OCRs badly, so instead of trusting the text we
compare it with what we already know: every quest name, its objectives and their counts.
"""
import difflib
import functools
import re

TITLE_MIN_SCORE = 0.78
OBJECTIVE_MIN_SCORE = 0.7


# Short words kept when comparing names; other 1-2 letter bits are usually OCR noise. "an"
# matters: without it "Mr. Thunder in Need of an..." also matched "... in Need of Help".
SHORT_WORDS = {"a", "an", "at", "by", "do", "go", "in", "is", "it", "jm", "me", "my", "no", "of",
               "on", "or", "so", "to", "up", "we"}


@functools.lru_cache(maxsize=4096)
def _letters(text):
    """Lowercase words only; drops digits, punctuation and 1-2 letter OCR junk."""
    words = re.findall(r"[A-Za-z']+", text)
    return " ".join(w for w in words if len(w) > 2 or w.lower() in SHORT_WORDS).lower()


def _ratio(a, b, minimum=0.0):
    """Similarity of two strings; cheap upper bounds skip hopeless pairs early."""
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if m.real_quick_ratio() < minimum or m.quick_ratio() < minimum:
        return 0.0
    return m.ratio()


def title_score(line_text, quest_name, minimum=0.0):
    """How well an OCR line matches a quest name; handles names cut off with '...'."""
    text = line_text.strip()
    truncated = bool(re.search(r"(\.\.|…)\s*\W*$", text))
    a = _letters(re.sub(r"(\.\.+|…).*$", "", text))
    b = _letters(quest_name)
    if len(a) < 6:
        return 0
    # Only compare against the start of the name when the game cut it off ("...") or the
    # OCR plausibly lost the dots on a long fragment. Otherwise a short line such as the
    # map name "L Forest I" would match "[Forest of Patience] ..." by its first word.
    if truncated or (len(a) >= 12 and len(a) >= 0.6 * len(b)):
        b = b[:len(a)]
    score = _ratio(a, b, minimum)
    # Numbered quests ("I Need to Find My Daughter 1" / "... 2") differ only in the number
    # that _letters() drops: when both show one and they differ, it's not the same quest.
    if not truncated and _number_tail(text) and _number_tail(quest_name) \
            and _number_tail(text) != _number_tail(quest_name):
        return 0.0
    return score


def _number_tail(text):
    """Trailing number or roman numeral of a name ("2", "II"), normalised, or None."""
    m = re.search(r"\b([0-9]+|[ivxlIVXL|]+)\W*$", text.strip())
    if not m:
        return None
    tail = m.group(1).lower().replace("|", "i").replace("l", "i")
    return {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5"}.get(tail, tail)


def match_quests(lines, quests):
    """Return {quest_id: score} for quests whose title appears in the OCR lines."""
    found = {}
    for line in lines:
        best_id, best, runner_up = None, 0, 0
        if len(line["text"]) < 6:
            continue
        for q in quests.values():
            s = title_score(line["text"], q["name"], TITLE_MIN_SCORE)
            if s > best:
                best_id, best, runner_up = q["id"], s, best
            elif s > runner_up:
                runner_up = s
        # a tie means the line can't tell two quests apart (e.g. "Daughter ?" when the number
        # didn't read): skip it rather than guess; another line or pass will usually settle it
        if best >= TITLE_MIN_SCORE and best - runner_up > 0.01:
            found[best_id] = max(best, found.get(best_id, 0))
    return found


def _digit_runs(text):
    # common OCR confusions inside numbers: o/O -> 0, b -> 6
    fixed = re.sub(r"(?<![A-Za-z])[oO](?![A-Za-z])", "0", text)
    fixed = re.sub(r"(?<=\d)b|b(?=\d)", "6", fixed)
    return re.findall(r"\d+", fixed)


def parse_count(text, need):
    """Find 'have' in text like '34 / 20 Leaf' or 'Orange Mushroom 1 120' (slash read as 1)."""
    runs = _digit_runs(text)
    need_s = str(need)
    for i in range(len(runs) - 1, -1, -1):
        tail = "".join(runs[i:])
        if tail in (need_s, "1" + need_s, "7" + need_s) and i > 0:
            return int(runs[i - 1])
        if runs[i].endswith(need_s) and len(runs[i]) > len(need_s):
            head = runs[i][:-len(need_s)]
            if head in ("1", "7") and i > 0:      # the slash itself was read as a digit
                return int(runs[i - 1])
            return int(head[:-1] or 0) if head[-1] in "17" and len(head) > 1 else int(head)
    return None


def objective_names(q, db):
    names = []
    for need in q.get("need") or []:
        if "mobId" in need:
            names.append((db.monsters.get(need["mobId"]) or {}).get("display")
                         or need["name"].replace("Defeat ", ""))
        else:
            names.append(need["name"])
    return names


def read_progress(lines, q, db):
    """{objective index: have} for one quest, using lines that mention its objectives."""
    names = objective_names(q, db)
    counts = [n.get("count", 1) for n in q.get("need") or []]
    progress = {}
    candidates = []
    for li, line in enumerate(lines):
        words = _letters(line["text"])
        if not words:
            continue
        for oi, name in enumerate(names):
            target = name.lower()
            # compare against the same number of trailing words as the objective name
            tail = " ".join(words.split()[-len(target.split()):])
            score = max(_ratio(tail, target), _ratio(words, target))
            if score >= OBJECTIVE_MIN_SCORE:
                candidates.append((score, li, oi))
    used_lines, used_obj = set(), set()
    for score, li, oi in sorted(candidates, reverse=True):
        if li in used_lines or oi in used_obj:
            continue
        have = parse_count(lines[li]["text"], counts[oi])
        if have is None:
            continue
        used_lines.add(li)
        used_obj.add(oi)
        progress[oi] = have
    return progress


PROGRESS_LINE = re.compile(r"\d\s*[/l|I1!]\s*\d")


def focus_regions(lines, found, quests, map_id, maps, size, margin=(70, 45)):
    """Screen areas worth re-reading on the next quick sync: one around the quest titles and
    "have / need" lines that were recognised, one around the map name. Boxes are
    (left, top, right, bottom) in screenshot pixels, padded and clipped to `size`."""
    def box(group):
        if not group:
            return None
        mx, my = margin
        return (max(0, int(min(l["x"] for l in group) - mx)),
                max(0, int(min(l["y"] for l in group) - my)),
                min(size[0], int(max(l["x"] + l.get("w", 200) for l in group) + mx)),
                min(size[1], int(max(l["y"] + l["h"] for l in group) + my * 4)))  # room to grow down

    boxes = [box(group) for group, _ in _helper_panels(lines, found, quests)]
    if map_id:
        name = maps[map_id]["displayName"].lower()
        boxes.append(box([l for l in lines if _ratio(l["text"].strip().lower(), name, 0.9) >= 0.9]))
    return [b for b in boxes if b]


def _helper_panels(lines, found, quests):
    """On-screen panels that show quest titles *with* "have / need" lines under them: the
    in-game Quest Helper (and the Quest window's summary of the selected quest). The plain
    quest list in the Quest window has titles only, so it is not one of these.
    Returns [(lines in the panel, quest ids titled in it)]."""
    titled = {}
    for line in lines:
        best = max(found, key=lambda q: title_score(line["text"], quests[q]["name"]), default=None)
        if best and title_score(line["text"], quests[best]["name"], TITLE_MIN_SCORE) >= TITLE_MIN_SCORE:
            titled[id(line)] = best
    quest_lines = [l for l in lines if PROGRESS_LINE.search(l["text"]) or id(l) in titled]
    panels = []
    for group in _clusters(quest_lines, gap_x=40):
        ids = {titled[id(l)] for l in group if id(l) in titled}
        if ids and any(PROGRESS_LINE.search(l["text"]) for l in group):
            panels.append((group, ids))
    return panels


def tracked_quests(lines, found, quests):
    """Quests shown in the in-game Quest Helper (title with progress lines): the live ones."""
    return {q for _, ids in _helper_panels(lines, found, quests) for q in ids}


def quest_window_open(lines):
    """True when the game's Quest window (Q) is on screen: one of its tab or button labels is
    visible (the active tab sits on red and doesn't always OCR, hence several to look for)."""
    labels = ("in progress", "available", "completed", "quest summary", "forfeit")
    return any(_ratio(_letters(l["text"]), name, 0.8) >= 0.8 for l in lines for name in labels)


def _clusters(lines, gap_x=90, gap_y=140):
    """Group lines that sit close together (one group per on-screen window or panel)."""
    groups = []
    for line in sorted(lines, key=lambda l: (l["y"], l["x"])):
        right = line["x"] + line.get("w", 200)
        for g in groups:
            gx0 = min(l["x"] for l in g) - gap_x
            gx1 = max(l["x"] + l.get("w", 200) for l in g) + gap_x
            gy1 = max(l["y"] + l["h"] for l in g) + gap_y
            if line["x"] <= gx1 and right >= gx0 and line["y"] <= gy1:
                g.append(line)
                break
        else:
            groups.append([line])
    return groups


def _map_name(text):
    """Map name for comparison: keeps short words and the trailing roman numeral (I/II/III
    tell maps apart), reading OCR's usual l, 1 and | for I."""
    words = re.findall(r"[A-Za-z0-9|']+", text.lower())
    if words and re.fullmatch(r"[il1|]+", words[-1]) and len(words) > 1:
        words[-1] = "i" * len(words[-1])
    return " ".join(words)


STREET_MIN_SCORE = 0.8
MAP_UNDER_STREET_MIN_SCORE = 0.6


def match_map(lines, maps, anchored_only=False):
    """Id of the map the player is on, read from the minimap title, or None.

    The minimap shows the area ("Victoria Road") with the map name right under it
    ("Perion"). The area name OCRs reliably, so once it is found the line below is only
    compared with that area's maps, which tolerates misreads like "PeriOli". Without an
    area line, a map name has to match almost exactly."""
    streets = {}
    for m in maps.values():
        streets.setdefault((m.get("displayStreet") or "").lower(), []).append(m)
    best_id, best = None, 0
    for street_line in lines:
        text = _map_name(street_line["text"])  # keeps short words: "El Nath" must not become "Nath"
        street = max(streets, key=lambda s: _ratio(text, s, STREET_MIN_SCORE) if s else 0)
        if not street or _ratio(text, street) < STREET_MIN_SCORE:
            continue
        for line in lines:  # the map name: just below the area name, starting about where it does
            dy = line["y"] - street_line["y"]
            if not (0 < dy <= street_line["h"] * 3 and abs(line["x"] - street_line["x"]) <= street_line["h"] * 3):
                continue
            name = _map_name(line["text"])
            for m in streets[street]:
                s = _ratio(name, _map_name(m["displayName"]), MAP_UNDER_STREET_MIN_SCORE)
                if s > best:
                    best_id, best = m["id"], s
    if best >= MAP_UNDER_STREET_MIN_SCORE:
        return best_id
    if anchored_only:  # a bare map name anywhere (world map labels, chat) isn't where you are
        return None

    names = {m["displayName"].lower(): m["id"] for m in maps.values()}
    best_id, best = None, 0
    for line in lines:
        text = line["text"].strip().lower()
        if len(text) < 5:
            continue
        for name, mid in names.items():
            s = _ratio(text, name, 0.9)
            if s > best:
                best_id, best = mid, s
    return best_id if best >= 0.9 else None
