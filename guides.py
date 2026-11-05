"""What to do in a quest, from meowdb.com's guides and quest pages (NiaMeowDB, used with permission).

Some quests are hard to follow from their objectives alone: jump quests ("bring back a Pink
Anthurium" says nothing about Shane's forest in Ellinia), event trails, the Forgotten Hollow chain.
meowdb's guides explain them, and their tables link each quest by id, so every piece can be
filed under the exact quests it explains. Every other quest gets its NPC's own words ("If you
accept": usually where to go). Pages are React Server Component payloads: a tree split over
numbered lines that refer to each other ("$1a"), read here in page order.
"""
import json
import re

# meowdb.com/msclassic/guides/<slug> pages that explain quests (others are about classes or games)
QUEST_GUIDES = ("jump-quests", "mark-of-the-beta-event-guide", "forgotten-hollow-the-new-endgame-area",
                "beginners-guide-first-steps-in-maple-world", "kerning-city-party-quest-kpq-guide")
KEEP_FACTS = ("Where", "Journal hint", "What you do", "Start and turn-in", "Bring back")  # table columns shown
SMALL_SECTION = 20  # a section this short (in blocks) that names at most
FEW_QUESTS = 3      # this many quests is about them: its general notes go to each
MAX_NOTES = 8
_SKIP = re.compile(r"^(Stages|Quests, in order|Map rules on every stage|\d[\d,]* EXP\b.*)$")


def _lines(rsc):
    """{line id: parsed JSON} of an RSC payload (lines like `1a:[...]`)."""
    lines = {}
    for line in rsc.split("\n"):
        m = re.match(r"^([0-9a-f]+):(.*)$", line)
        if m and m[2][:1] in "[{\"":
            try:
                lines[m[1]] = json.loads(m[2])
            except ValueError:
                pass
    return lines


def _ref(node, lines):
    m = re.fullmatch(r"\$L?([0-9a-f]+)", node) if isinstance(node, str) else None
    return lines.get(m[1]) if m else None


def _resolve(node, lines, depth=0):
    """`node` with "$1a" references replaced by what they point to."""
    if depth > 60:
        return None
    target = _ref(node, lines)
    if target is not None:
        return _resolve(target, lines, depth + 1)
    if isinstance(node, list):
        return [_resolve(n, lines, depth + 1) for n in node]
    if isinstance(node, dict):
        return {k: _resolve(v, lines, depth + 1) for k, v in node.items()}
    return node


def _element(node):
    """(tag, props) of a React element ["$", tag, key, props], else None."""
    if isinstance(node, list) and len(node) == 4 and node[0] == "$" and isinstance(node[3], dict):
        return node[1], node[3]
    return None


def text(node):
    """All the text in an element tree."""
    if isinstance(node, str):
        return "" if node.startswith("$") else node
    el = _element(node)
    if el:
        return text(el[1].get("children"))
    if isinstance(node, list):
        return "".join(text(n) for n in node)
    return ""


def links(node, found=None):
    """[(href, text)] of every link in an element tree, in order."""
    found = [] if found is None else found
    el = _element(node)
    if el:
        if el[1].get("href"):
            found.append((el[1]["href"], text(el[1].get("children"))))
        links(el[1].get("children"), found)
    elif isinstance(node, list):
        for n in node:
            links(n, found)
    return found


def _cells(row):
    el = _element(row)
    return [text(c).strip() for c in (el[1].get("children") or []) if _element(c)] if el else []


def page_events(rsc):
    """The page in reading order: ("h2" / "h3", id, title), ("block", tag, element) for p, li
    and table rows, ("link", href, text) for links outside those."""
    lines = _lines(rsc)
    referenced = {m for v in lines.values() for m in re.findall(r'"\$L?([0-9a-f]+)"', json.dumps(v))}
    out = []

    def walk(node, seen):
        target = _ref(node, lines)
        if target is not None:
            key = re.fullmatch(r"\$L?([0-9a-f]+)", node)[1]
            if key not in seen:
                walk(target, seen | {key})
            return
        el = _element(node)
        if el:
            tag, props = el
            if tag in ("h2", "h3"):
                out.append((tag, props.get("id"), text(_resolve(props.get("children"), lines)).strip()))
            elif tag in ("p", "li", "tr"):
                out.append(("block", tag, _resolve(node, lines)))
            elif props.get("href"):
                out.append(("link", props["href"], text(_resolve(props.get("children"), lines)).strip()))
            else:
                walk(props.get("children"), seen)
        elif isinstance(node, list):
            for n in node:
                walk(n, seen)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v, seen)

    for key in sorted(lines, key=lambda k: int(k, 16)):
        if key not in referenced:
            walk(lines[key], {key})
    return out


def _quests_in(node):
    return list(dict.fromkeys(re.findall(r"quest-tracker/(\d+)", " ".join(h for h, _ in links(node)))))


def _npc_spots(blocks):
    """[(npc name, map id)] where a note names an NPC followed by its map ("Shane in Ellinia")."""
    spots = []
    for b in blocks:
        found = links(b)
        for (h1, t1), (h2, _) in zip(found, found[1:]):
            npc, place = re.search(r"/npcs/\d+", h1), re.search(r"/maps/(\d+)", h2)
            if npc and place and (t1, place[1]) not in spots:
                spots.append((t1, place[1]))
    return spots


def sections(rsc):
    """The page cut at its headings: [{id, title, blocks, links}] (an h3 is a section of its own)."""
    out, cur = [], {"id": None, "title": "", "blocks": [], "links": []}
    for kind, a, b in page_events(rsc):
        if kind in ("h2", "h3"):
            out.append(cur)
            cur = {"id": a, "title": b, "blocks": [], "links": []}
        elif kind == "block":
            cur["blocks"].append((a, b))
        else:
            cur["links"].append((a, b))
    out.append(cur)
    return out


def guide_entries(slug, title, rsc):
    """{quest id: [entry]} from one guide page. An entry: {guide, section, url, facts [(column,
    text)], notes [text], npcs [(name, map id)], stages [(label, map id)]}."""
    secs = sections(rsc)
    found = {}
    for sec in secs:
        blocks = sec["blocks"]
        header = next((_cells(b) for tag, b in blocks if tag == "tr" and not _quests_in(b)), [])
        general = [b for tag, b in blocks if tag != "tr" and not _quests_in(b)]
        notes = [t for t in (text(b).strip() for b in general) if t and not _SKIP.match(t)]
        named = list(dict.fromkeys(q for _, b in blocks for q in _quests_in(b)))
        for qid in named:
            mine = [b for tag, b in blocks if tag != "tr" and qid in _quests_in(b)]
            facts = []
            for tag, b in blocks:
                if tag == "tr" and _quests_in(b) == [qid]:
                    facts += [(h, c) for h, c in zip(header, _cells(b)) if h in KEEP_FACTS and c]
            entry = {"guide": title, "section": sec["title"] or title, "facts": facts,
                     "url": f"/guides/{slug}" + (f"#{sec['id']}" if sec["id"] else ""),
                     "notes": [text(b).strip() for b in mine] +
                              (notes if len(blocks) <= SMALL_SECTION and len(named) <= FEW_QUESTS else []),
                     "npcs": _npc_spots(general + mine),
                     "stages": [(re.sub(r"\s*·\s*Quest \d+.*", "", t).replace("Minimap of ", "").strip("<> "),
                                 re.search(r"/maps/(\d+)", h)[1])
                                for h, t in sec["links"] if f"Quest {qid}" in t and "/maps/" in h]}
            found.setdefault(qid, []).append(entry)
    # sections that name no quest but describe a place a quest sends you ("Page 2: The Pig Beach")
    for entries in found.values():
        for entry in entries:
            for column, cell in entry["facts"]:
                if column != "Where":
                    continue
                place = cell.split(",")[0].strip()
                for sec in secs:
                    if len(place) >= 6 and place.lower() in sec["title"].lower() and not any(
                            _quests_in(b) for _, b in sec["blocks"]):
                        entry["notes"] += [text(b).strip() for _, b in sec["blocks"] if text(b).strip()]
                        entry["npcs"] += [s for s in _npc_spots([b for _, b in sec["blocks"]]) if s not in entry["npcs"]]
    for entries in found.values():
        for entry in entries:
            entry["notes"] = list(dict.fromkeys(entry["notes"]))[:MAX_NOTES]
    return found


def quest_guides(fetch):
    """{quest id: [entry]} from every guide in QUEST_GUIDES. `fetch(slug)` returns its RSC text."""
    found = {}
    for slug in QUEST_GUIDES:
        rsc = fetch(slug)
        title = next((t for kind, _, t in page_events(rsc) if kind == "h1"), "") or slug.replace("-", " ").title()
        for qid, entries in guide_entries(slug, title, rsc).items():
            found.setdefault(qid, []).extend(entries)
    return found


def _paragraphs(node, out=None):
    """The text of each p element in a tree, in order."""
    out = [] if out is None else out
    el = _element(node)
    if el and el[0] == "p":
        out.append(text(node).strip())
    elif el:
        _paragraphs(el[1].get("children"), out)
    elif isinstance(node, list):
        for n in node:
            _paragraphs(n, out)
    return out


def accept_hint(rsc):
    """What a quest's NPC says when you accept it (where to go, what to bring), with the maps and
    NPCs it links: {text, maps [(name, map id)], npcs [name]}, or None."""
    m = re.search(r'\["\$","div","yes",\{', rsc)
    if not m:
        return None
    try:
        node, _ = json.JSONDecoder().raw_decode(rsc, m.start())
    except ValueError:
        return None
    node = _resolve(node, _lines(rsc))
    body = [c for c in (_element(node)[1].get("children") or []) if text(c).strip() != "If you accept"]
    said = re.sub(r"\s+", " ", " ".join(_paragraphs(body))).strip()
    found = links(body)
    return {"text": said,
            "maps": [(t, re.search(r"/maps/(\d+)", h)[1]) for h, t in found if re.search(r"/maps/\d+", h)],
            "npcs": [t for h, t in found if "/npcs/" in h]} if said else None
