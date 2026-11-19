"""Cached NiaDB data access. Live access requires renewed operator permission.

Fetches pages one at a time, rate-limited, and caches every response on disk so each
page is only downloaded once (index pages refresh weekly).
"""
import hashlib
import json
import os
import re
import sys
import threading
import time
import heapq
import urllib.error
import urllib.parse
import urllib.request

import guides
import item_sources

BASE = "https://meowdb.com/msclassic"
MAP_DATA_URL = "https://meowdb.com/_data/maps.json"  # every map with portals, NPCs and spawns
CORE_INDEX_PATHS = frozenset(('/quest-tracker/all', '/npcs', '/maps', '/monsters', MAP_DATA_URL))
USER_AGENT = "UmbraleCompanion/3.38 (https://github.com/Bejerano1996/MapleCompanion/issues)"
MIN_INTERVAL = 10.0        # https://meowdb.com/reuse#tool-rules
ACCESS_RENEWAL_REQUIRED = True  # Operator explicitly revoked this tool's old permission.
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST = None
_ACCESS_DENIED = None
INDEX_MAX_AGE = 7 * 86400   # quests / npcs / maps / monsters lists
DETAIL_MAX_AGE = 30 * 86400 # monster and item pages
RETRY_DELAYS = (1, 3)       # seconds to wait before the 2nd and 3rd try of a failed download


class DataAccessPaused(urllib.error.URLError):
    """No automatic retry after provider refusal or withdrawn permission."""


def data_access_message():
    return 'NiaDB access paused: renewed permission required (https://meowdb.com/reuse)'

# Where the cache and saved state live: next to the .exe when packaged, else next to the code
APP_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
           else os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(APP_DIR, "cache")

def write_atomic(path, data):
    """Write a file so a crash or power cut mid-write can never leave it half-written:
    write a temporary file next to it, flush it to disk, then swap it into place."""
    tmp = path + ".tmp"
    with open(tmp, "wb" if isinstance(data, bytes) else "w", **({} if isinstance(data, bytes)
                                                               else {"encoding": "utf-8"})) as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def validate_index(name, rows):
    """Reject unusable provider data before replacing any existing index."""
    def invalid(field):
        raise ValueError('NiaDB data format changed: ' + name + ' ' + field + '; previous data kept')
    if not isinstance(rows, list) or not rows:
        invalid('catalog')
    identities = set()
    for row in rows:
        if not isinstance(row, dict):
            invalid('record')
        identity = row.get('id')
        if type(identity) not in (str, int) or (isinstance(identity, str) and (not identity or identity != identity.strip())):
            invalid('identity')
        if identity in identities:
            invalid('duplicate identity')
        identities.add(identity)
        label_field = 'displayName' if name == 'maps' else 'name'
        if not isinstance(row.get(label_field), str) or not row[label_field].strip():
            invalid(label_field)
        if name == 'quests':
            needs = row.get('need')
            if needs is not None and not isinstance(needs, list):
                invalid('objectives')
            for need in needs or []:
                if not isinstance(need, dict) or not isinstance(need.get('name'), str) or not need['name'].strip():
                    invalid('objective name')
                count = need.get('count', 1)
                if type(count) is not int or count <= 0:
                    invalid('objective count')
            for field in ('exp', 'mesos', 'levelMin'):
                if field in row and (type(row[field]) is not int or row[field] < 0):
                    invalid(field)
        elif name == 'monsters':
            if type(identity) is not int:
                invalid('numeric identity')
            for field in ('level', 'hp', 'exp'):
                if type(row.get(field)) is not int or row[field] < (1 if field == 'hp' else 0):
                    invalid(field)
        elif name == 'NPCs' and row.get('maps') is not None and not isinstance(row['maps'], list):
            invalid('locations')


_PUSH_RE = re.compile(r"self\.__next_f\.push\((\[.*?\])\)</script>", re.S)
_decoder = json.JSONDecoder()


class MeowDB:
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._last_request = 0.0
        self.quests = {}
        self.npcs = {}
        self.maps = {}
        self.monsters = {}
        self.areas = {}
        self.map_data = {}
        self.sold_by = {}  # game item id (iconKey) -> [{npc, mapId, price, citizen}], cheapest first
        self.shops = []    # [{npc, mapId, kind, stock: {item name: price}}], kind e.g. "Grocer"
        self.quest_guides = {}  # quest id -> [guide entry] (see guides.py)
        self.offline = False  # set when an expired page had to be served from the cache
        self.access_paused = ACCESS_RENEWAL_REQUIRED or _ACCESS_DENIED is not None
        self._force_refresh = False
        self._refresh_thread = None
        self._indexes_lock = threading.Lock()
        self._index_pages = None
        self._index_fresh = False
        from index_cache import IndexCache
        self._index_cache = IndexCache(cache_dir, CORE_INDEX_PATHS)
        self.data_sources = {}
        from alternate_sources import AlternateCatalogs
        from quest_references import ReferenceIndex
        self.reference_catalogs = AlternateCatalogs(cache_dir)
        self.reference_index = ReferenceIndex()

    # ---------- network + cache ----------

    def _cache_path(self, key):
        # Hashed names keep paths short (Windows' 260-char limit) and filesystem-safe
        return os.path.join(self.cache_dir, hashlib.sha1(key.encode()).hexdigest()[:20] + ".html")

    def _get(self, path, max_age, binary=False):
        if binary:  # images are cached by the caller under their own name
            return self._fetch(path)
        cache = self._cache_path(path)
        snapshot = self._index_cache.get(path)
        legacy_exists = os.path.exists(cache)
        if snapshot is not None and path not in CORE_INDEX_PATHS and legacy_exists and os.path.getmtime(cache) > snapshot[1]:
            snapshot = None  # An independently refreshed optional detail can be newer.
        have_cache = snapshot is not None or legacy_exists
        stamp = snapshot[1] if snapshot is not None else os.path.getmtime(cache) if legacy_exists else None
        owner = self._refresh_thread == threading.get_ident() and self._index_pages is not None
        if owner and path in self._index_pages:
            return self._index_pages[path][0]
        def remember(text, fetched_at, fresh=False):
            if owner:
                self._index_pages[path] = (text, fetched_at)
                self._index_fresh = self._index_fresh or fresh
            self.data_sources[path] = {'source': 'network' if fresh else 'cache', 'fetched_at': fetched_at}
            return text
        def saved():
            if snapshot is not None:
                return remember(snapshot[0], snapshot[1])
            with open(cache, encoding='utf-8') as stream:
                return remember(stream.read(), stamp)
        force_refresh = self._force_refresh and self._refresh_thread == threading.get_ident()
        if have_cache and not force_refresh and 0 <= time.time() - stamp < max_age:
            return saved()
        try:
            text = self._fetch(path).decode("utf-8")
        except (urllib.error.URLError, OSError):
            if not have_cache:
                raise
            self.offline = True  # site unreachable: keep working from the older copy
            return saved()
        if owner:
            # Publish no raw response until the complete index batch validates.
            return remember(text, time.time(), fresh=True)
        write_atomic(cache, text)
        return remember(text, os.path.getmtime(cache), fresh=True)

    def _fetch(self, path):
        """Retry transient failures only. Provider 403/429 responses stop requests."""
        for delay in RETRY_DELAYS + (None,):
            try:
                return self._fetch_once(path)
            except urllib.error.HTTPError as e:
                if e.code < 500 or delay is None:
                    raise
            except DataAccessPaused:
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if delay is None:
                    raise
            time.sleep(delay)

    def _fetch_once(self, path):
        global _LAST_REQUEST, _ACCESS_DENIED
        if ACCESS_RENEWAL_REQUIRED or _ACCESS_DENIED is not None:
            self.access_paused = True
            raise DataAccessPaused(data_access_message())
        with _REQUEST_LOCK:
            # Shared across all MeowDB instances, including portrait and guide jobs.
            if ACCESS_RENEWAL_REQUIRED or _ACCESS_DENIED is not None:
                self.access_paused = True
                raise DataAccessPaused(data_access_message())
            if _LAST_REQUEST is not None:
                wait = MIN_INTERVAL - (time.monotonic() - _LAST_REQUEST)
                if wait > 0:
                    time.sleep(wait)
            try:
                return self._request_url(path)
            except urllib.error.HTTPError as error:
                if error.code in (403, 429):
                    _ACCESS_DENIED = error.code
                    self.access_paused = True
                    raise DataAccessPaused(data_access_message()) from None
                raise
            finally:
                _LAST_REQUEST = time.monotonic()

    def _request_url(self, path):
        with self._lock:
            url = path if path.startswith("https://") else BASE + path
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read()
            finally:
                self._last_request = time.time()

    @staticmethod
    def _rsc(html):
        """Concatenate the Next.js flight payload embedded in a page."""
        out = []
        for chunk in _PUSH_RE.findall(html):
            try:
                arr = json.loads(chunk)
            except ValueError:
                continue
            if len(arr) > 1 and isinstance(arr[1], str):
                out.append(arr[1])
        return "".join(out)

    @staticmethod
    def _largest_list(text, start_pattern, required_key):
        best = []
        for m in re.finditer(start_pattern, text):
            try:
                value, _ = _decoder.raw_decode(text, m.start())
            except ValueError:
                continue
            if (isinstance(value, list) and len(value) > len(best)
                    and all(isinstance(v, dict) and required_key in v for v in value)):
                best = value
        return best

    # ---------- indexes ----------

    def load_indexes(self, force=False):
        with self._indexes_lock:
            previous_sources, previous_offline = dict(self.data_sources), self.offline
            self._force_refresh = force
            self._refresh_thread = threading.get_ident()
            self._index_pages = {}
            self._index_fresh = False
            self.offline = False
            try:
                indexes = self._load_indexes()
                if indexes is not None:
                    if self._index_fresh:
                        self._index_cache.commit(self._index_pages)
                    self.__dict__.update(indexes)
                return None
            except Exception:
                self.data_sources, self.offline = previous_sources, previous_offline
                raise
            finally:
                self._force_refresh = False
                self._refresh_thread = None
                self._index_pages = None
                self._index_fresh = False

    def refresh_indexes(self):
        return self.load_indexes(force=True)

    def _load_indexes(self):
        html = self._get("/quest-tracker/all", INDEX_MAX_AGE)
        areas = {int(v): name for v, name in
                      re.findall(r'<option value="(\d+)">([^<]+)</option>', html)}
        quests = self._largest_list(self._rsc(html), r'\[\{"id":', "need")

        npcs = self._largest_list(self._rsc(self._get("/npcs", INDEX_MAX_AGE)), r'\[\{"id":', "maps")

        maps = self._largest_list(self._rsc(self._get("/maps", INDEX_MAX_AGE)), r'\[\{"id":', "avgMobLevel")

        mobs = self._largest_list(self._rsc(self._get("/monsters", INDEX_MAX_AGE)), r'\[\{"id":', "level")
        map_rows = json.loads(self._get(MAP_DATA_URL, INDEX_MAX_AGE))
        for name, rows in (('quests', quests), ('NPCs', npcs), ('maps', maps),
                           ('monsters', mobs), ('map routes', map_rows)):
            validate_index(name, rows)
        npc_index = {}
        for npc in npcs:
            for key in {npc.get('name'), npc.get('displayName')}:
                if isinstance(key, str) and key:
                    npc_index.setdefault(key.lower(), npc)

        try:  # shops are extra: the app works without them (e.g. offline with no copy cached yet)
            sold_by, shops = self._index_shops(self._get("/npc-shops", INDEX_MAX_AGE))
        except Exception:
            sold_by, shops = self.sold_by, self.shops
            self._retain_index_page('/npc-shops')

        try:  # guides are extra too: quests that need explaining (jump quests, events, the Hollow)
            quest_guides = guides.quest_guides(self._guide_index_payload)
        except Exception:
            quest_guides = self.quest_guides
            for slug in guides.QUEST_GUIDES:
                self._retain_index_page('/guides/'+slug)
        # A failed refresh must never leave half-new indexes or empty the quest list.
        return dict(areas=areas, quests={q['id']: q for q in quests},
                             npcs=npc_index, maps={m['id']: m for m in maps},
                             monsters={m['id']: m for m in mobs if not is_job_test_monster(m)},
                             map_data={m['id']: m for m in map_rows},
                    sold_by=sold_by, shops=shops, quest_guides=quest_guides)

    def _guide_index_payload(self, slug):
        rsc = self._rsc(self._get('/guides/'+slug, DETAIL_MAX_AGE))
        if not rsc or not guides.page_events(rsc):
            raise ValueError('NiaDB guide format changed; previous data kept')
        return rsc

    def _retain_index_page(self, path):
        """An invalid optional response must not replace its last saved page."""
        if self._index_pages is None:
            return
        saved = self._index_cache.get(path)
        if saved is None:
            try:
                cache = self._cache_path(path)
                with open(cache, encoding='utf-8') as stream:
                    saved = (stream.read(), os.path.getmtime(cache))
            except (OSError, ValueError):
                pass
        self._index_pages.pop(path, None)
        self.data_sources.pop(path, None)
        if saved is not None:
            self._index_pages[path] = saved
            self.data_sources[path] = {'source':'cache', 'fetched_at':saved[1]}

    def _index_shops(self, html):
        """Every NPC shop's stock, by game item id: who sells it, where, and the Classic price."""
        shops = self._largest_list(self._rsc(html), r'\[\{"slug":', "npcName")
        if not shops:
            raise ValueError('NiaDB shop catalog format changed; previous data kept')
        sold = {}
        shop_index = []
        for shop in shops:
            if not isinstance(shop.get('npcName'), str) or not shop['npcName'].strip():
                raise ValueError('Invalid shop NPC name; previous data kept')
            if shop.get("opensNoShop") or not shop.get("mapId"):
                continue
            if not isinstance(shop.get('items') or [], list):
                raise ValueError('Invalid shop inventory; previous data kept')
            for item in shop.get('items') or []:
                if not isinstance(item, dict):
                    raise ValueError('Invalid shop item; previous data kept')
                price = item.get('classicPrice')
                if price is not None and (type(price) is not int or price < 0):
                    raise ValueError('Invalid shop price; previous data kept')
            shop_index.append({"npc": shop["npcName"], "mapId": shop["mapId"], "kind": shop.get("npcFunction") or "Shop",
                               "stock": {i["name"]: i["classicPrice"] for i in shop.get("items") or []
                                         if i.get("name") and i.get("classicPrice") is not None}})
            for item in shop.get("items") or []:
                if item.get("classicPrice") is None or not item.get("iconKey"):
                    continue
                sold.setdefault(str(item["iconKey"]), []).append(
                    {"npc": shop["npcName"], "mapId": shop["mapId"], "price": item["classicPrice"],
                     "citizen": item.get("citizenReq")})
        for sellers in sold.values():
            sellers.sort(key=lambda s: s["price"])
        return sold, shop_index

    # ---------- lookups ----------

    def npc(self, name):
        return self.npcs.get((name or "").lower())

    def next_quests(self, quest_id):
        return [q for q in self.quests.values()
                if quest_id in (q.get("requiresAll") or []) or q.get("requires") == quest_id]

    def mob_locations(self, mob_id):
        """List of {mapId, mapName, streetName, count, ...} for a monster, most mobs first."""
        if self.map_data:  # answered from the all-maps file, no download needed
            locs = [{"mapId": m["id"], "mapName": m["name"], "streetName": m.get("streetName", ""),
                     "count": mob.get("count", 0)}
                    for m in self.map_data.values() for mob in m.get("monsters") or []
                    if str(mob.get("id")) == str(mob_id)]
            if locs:
                return sorted(locs, key=lambda l: -(l.get("count") or 0))
        rsc = self._rsc(self._get(f"/monsters/{mob_id}", DETAIL_MAX_AGE))
        locs = self._largest_list(rsc, r'\[\{"mapId":', "mapId")
        return sorted(locs, key=lambda l: -(l.get("count") or 0))

    def quest_hint(self, quest_id):
        """What the quest's NPC says when you accept it (often where to go), from its meowdb
        page: {text, maps, npcs} or None. Downloads the page once (kept for 30 days)."""
        return guides.accept_hint(self._rsc(self._get(f"/quest-tracker/{quest_id}", DETAIL_MAX_AGE)))

    def mob_drops(self, mob_id):
        """Names of the items a monster drops, from its meowdb page."""
        rsc = self._rsc(self._get(f"/monsters/{mob_id}", DETAIL_MAX_AGE))
        names = []
        for name in re.findall(r'"href":"/msclassic/item-db/\d+"[^{}]*?"children":\[\["\$","img",null,'
                               r'\{"src":"/msclassic/api/assets/icons/\d+","alt":"([^"]+)"', rsc):
            if name not in names:
                names.append(name)
        return names

    def search_items(self, text):
        """Items whose name matches, via the site's own search: [{id, name, sub, iconKey}]."""
        q = urllib.parse.urlencode({"q": text, "locale": "en"})
        return json.loads(self._get(f"/api/search?{q}", DETAIL_MAX_AGE)).get("items", [])

    def item_drop_info(self, page_id):
        """Monsters that drop an item: [{mob, name, rate, odds}] with OSMLib reference rates
        (highest first), followed by droppers that have no rate listed (rate None)."""
        rsc = self._rsc(self._get(f"/item-db/{page_id}", DETAIL_MAX_AGE))
        rows = []
        for mob, name, rate, odds in re.findall(
                r'"href":"/msclassic/monsters/(\d+)","className":"text-maple-accent hover:underline",'
                r'"children":"([^"]+)"\}\]\}\]\]\}\]\}\],\["\$","td",null,\{[^{}]*"children":\[\["\$","a",null,'
                r'\{[^{}]*"children":"([\d.]+)%"\}\],\["\$","span",null,\{[^{}]*"children":"([^"]+)"', rsc):
            if not any(r["mob"] == int(mob) for r in rows):
                rows.append({"mob": int(mob), "name": name, "rate": float(rate), "odds": odds})
        rows.sort(key=lambda r: -r["rate"])
        for mob in re.findall(r'"href":"/msclassic/monsters/(\d+)"', rsc):
            if not any(r["mob"] == int(mob) for r in rows):
                m = self.monsters.get(int(mob)) or {}
                rows.append({"mob": int(mob), "name": m.get("display") or f"Monster {mob}",
                             "rate": None, "odds": ""})
        return rows

    def item_droppers(self, item_id, item_name):
        """Monster ids that drop a given game item id, lowest level first."""
        q = urllib.parse.urlencode({"q": item_name, "locale": "en"})
        results = json.loads(self._get(f"/api/search?{q}", DETAIL_MAX_AGE))
        page_id = next((i["id"] for i in results.get("items", [])
                        if str(i.get("iconKey")) == str(item_id)), None)
        if page_id is None:
            return []
        rsc = self._rsc(self._get(f"/item-db/{page_id}", DETAIL_MAX_AGE))
        ids = []
        for mid in re.findall(r'"href":"/msclassic/monsters/(\d+)"', rsc):
            mid = int(mid)
            if mid not in ids:
                ids.append(mid)
        return sorted(ids, key=lambda m: (self.monsters.get(m) or {}).get("level", 999))

    def item_acquisition_sources(self,item_id,item_name):
        """Verified shops and linked breakable spawn maps for a game item id."""
        sources=item_sources.shop_sources(self.sold_by.get(str(item_id)) or [],self.maps)
        results=self.search_items(item_name)
        page_id=next((row['id'] for row in results if str(row.get('iconKey'))==str(item_id)),None)
        if page_id is None:return sources
        rsc=self._rsc(self._get(f'/item-db/{page_id}',DETAIL_MAX_AGE))
        for breakable in item_sources.breakable_links(rsc):
            detail=self._rsc(self._get('/breakables/'+breakable['id'],DETAIL_MAX_AGE))
            maps=item_sources.breakable_maps(detail,self.maps)
            if maps:
                sources.append({'kind':'breakable','id':breakable['id'],'name':breakable['name'],
                                'maps':maps,'community':True,'source':BASE+'/breakables/'+breakable['id']})
        return sources

    def map_detail(self, map_id):
        """Minimap size/centre plus NPC, monster-spawn and portal coordinates for one map."""
        if map_id in self.map_data:
            return self.map_data[map_id]
        rsc = self._rsc(self._get(f"/maps/{map_id}", DETAIL_MAX_AGE))
        for m in re.finditer(r'\{"id":"%s"' % re.escape(map_id), rsc):
            try:
                value, _ = _decoder.raw_decode(rsc, m.start())
            except ValueError:
                continue
            if isinstance(value, dict) and "minimapWidth" in value:
                return value
        return None

    def has_minimap_file(self, map_id):
        """True when the map's minimap picture is already on disk (drawing it needs no download)."""
        return os.path.exists(self._cache_path(f"/maps/minimaps/{map_id}.png")[:-5] + ".png")

    def minimap_png(self, map_id):
        """Path of the cached minimap image for a map."""
        path = self._cache_path(f"/maps/minimaps/{map_id}.png")[:-5] + ".png"
        if not os.path.exists(path):
            data = self._get(f"/maps/minimaps/{map_id}.png", DETAIL_MAX_AGE, binary=True)
            write_atomic(path, data)
        return path

    def _transport_links(self):
        """Ships and taxis, which the map data has no portals for: {from map: [link]}. A link
        looks like a portal (toMapId, toMapName) plus how to take it and what it costs in the
        route search (a walk through a portal costs 1)."""
        links = {}

        def add(src, dst, how, npc, cost):
            if src in self.map_data and dst in self.map_data:
                links.setdefault(src, []).append({
                    "name": "", "toMapId": dst, "toMapName": self.map_data[dst]["name"],
                    "transport": how, "npc": npc, "cost": cost, "cab": npc == "Regular Cab"})

        # Maple Island -> Victoria Island is one way: Shanks in Southperry sails to Lith Harbor
        add("000000060", "010000000", "talk to Shanks and sail to Victoria Island", "Shanks", 4)
        # the Ellinia <-> Orbis ship (tickets from Joel in Ellinia Station); the map data has
        # no portal from Ellinia town into its station, so that walk is added here too
        add("010002000", "010002090", "go to Ellinia Station", "", 1)
        add("010002090", "020000012", "buy a ticket from Joel and board the ship to Orbis", "Cherry", 6)
        add("020000012", "010002090", "board the ship to Ellinia", "Rini", 6)
        # Orbis side: from the Ticketing Booth the platform usher lets you into the station tunnel
        add("020000010", "020000011", "buy a ticket from Agatha and go to the platform", "Platform Usher", 1)
        # Regular Cabs connect the Victoria Island towns (they cost mesos, so walking near wins)
        cab_towns = [n["maps"][0]["mapId"] for n in self.npcs.values()
                     if n["name"].startswith("Regular Cab") and n.get("maps")]
        for a in dict.fromkeys(cab_towns):
            for b in dict.fromkeys(cab_towns):
                if a != b:
                    add(a, b, f"take the Regular Cab to {self.map_data.get(b, {}).get('name', b)}",
                        "Regular Cab", 3)
        return links

    def _search(self, start, cabs=True):
        """Cheapest way from start to every map, walking portals (cost 1 each) or taking ships
        (and taxis when `cabs`): {map_id: (cost, previous map, portal or transport link used)}."""
        if not hasattr(self, "_links"):
            self._links = self._transport_links()
        best = {start: (0, None, None)}
        todo = [(0, start)]
        while todo:
            cost, here = heapq.heappop(todo)
            if cost > best[here][0]:
                continue
            exits = [p for p in (self.map_data.get(here) or {}).get("portals") or [] if p.get("toMapId")]
            for p in exits + self._links.get(here, []):
                if p.get("cab") and not cabs:
                    continue
                nxt, c = p["toMapId"], cost + p.get("cost", 1)
                if nxt in self.map_data and (nxt not in best or c < best[nxt][0]):
                    best[nxt] = (c, here, p)
                    heapq.heappush(todo, (c, nxt))
        return best

    def distances(self, start, cabs=False):
        """How many steps (portals, ship or taxi rides) the route to each map takes, the same
        number route() shows: walking unless `cabs`, with a taxi only where walking can't get
        there."""
        result = {}
        for allow in ((True,) if cabs else (False, True)):  # on foot first, then cab fallback
            best = self._search(start, allow)
            steps = {start: 0}

            def count(mid):
                if mid not in steps:
                    steps[mid] = count(best[mid][1]) + 1
                return steps[mid]

            sys.setrecursionlimit(max(sys.getrecursionlimit(), len(best) + 100))
            for mid in best:
                result.setdefault(mid, count(mid))
        return result

    def route(self, start, goal, cabs=False):
        """Route from start to goal as [(map_id, portal or transport link to take)], or None if
        goal can't be reached at all. Walks (and sails where it must) unless `cabs`; a taxi is
        only used when there's no other way."""
        if start == goal:
            return []
        best = self._search(start, cabs)
        if goal not in best and not cabs:
            best = self._search(start, True)  # no way on foot: fall back to a cab
        if goal not in best:
            return None
        steps, cur = [], goal
        while best[cur][1] is not None:
            _, prev, link = best[cur]
            steps.append((prev, link))
            cur = prev
        return steps[::-1]

    def training_maps(self, level, below=3, above=5, limit=15):
        """Mobbing helper: maps whose average mob level is near the player's level."""
        rows = [m for m in self.maps.values()
                if m.get("totalMobCount") and level - below <= m.get("avgMobLevel", 0) <= level + above]
        return sorted(rows, key=lambda m: -(m.get("expPerHour") or 0))[:limit]  # limit=None: all


def is_job_test_monster(monster):
    """Exclude advancement-test variants, preserving normal and PQ monsters."""
    text=" ".join(str(monster.get(k) or "") for k in ("name","display","englishDisplay","tag")).casefold()
    return bool(re.search(r"job\s*(?:test|advancement)|(?:advancement|job).*test",text))
