"""Independent, attributed quest catalogs; never rewrites character quest IDs.

Only two public index pages are read on explicit refresh. No detail-page crawl,
private API, analytics, or game state is sent to either provider.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import json
import math
import re
import threading
import time
import urllib.error
import urllib.request
import unicodedata
from public_http import open_catalog_request

PROVIDERS = {
    'ccplz': ('CCPLZ', 'https://ccplz.cc/quests'),
    'classic': ('MapleStory Classic', 'https://maplestory-classic.com/quests'),
}
_LOCK = threading.Lock()
_LAST = None
_BLOCKED = set()
MAX_BYTES = 8 * 1024 * 1024


def number(text):
    text = unicodedata.normalize('NFKC', text)
    match = re.search(r'[+−–—-]?\d[\d,]*(?:\.\d+)?[A-Za-z]*', text)
    if not match or not re.fullmatch(r'\+?(?:\d+|\d{1,3}(?:,\d{3})+)', match[0]):
        return None
    if re.search(r'\d', text[match.end():]):
        return None
    return int(match[0].replace(',', ''))


class CatalogParser(HTMLParser):
    def __init__(self, provider):
        super().__init__(convert_charrefs=True)
        self.provider = provider
        self.rows = []
        self.active = None
        self.cells = []
        self.cell = None
        self.href = None
        self.title = []
        self.in_link = False
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        boundary = 'li' if self.provider == 'ccplz' else 'tr'
        if tag == boundary:
            self.active = boundary
            self.cells, self.title, self.text = [], [], []
            self.href = None
        if not self.active:
            return
        if tag == 'td':
            self.cell = []
        if tag == 'a' and attrs.get('href', '').startswith('/quests/'):
            self.href = attrs['href']
            self.in_link = True

    def handle_data(self, data):
        if self.active:
            self.text.append(data)
            if self.cell is not None:
                self.cell.append(data)
            if self.in_link:
                self.title.append(data)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_link = False
        if tag == 'td' and self.cell is not None:
            self.cells.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag != self.active:
            return
        if self.href and self.title:
            title = ' '.join(''.join(self.title).split())
            text = ' '.join(' '.join(self.text).split())
            if self.provider == 'ccplz':
                level_match = re.search(r'\bLevel\s+(\d+)', text)
                exp_match = re.search(r'([+−–—-]?\d[\d,]*(?:\.\d+)?[A-Za-z]*)\s+EXP\b', text)
                level = int(level_match[1]) if level_match else None
                exp = number(exp_match[1]) if exp_match else None
            else:
                level = number(self.cells[1]) if len(self.cells) >= 4 else None
                exp = number(self.cells[3]) if len(self.cells) >= 4 else None
            base = PROVIDERS[self.provider][1]
            url = urljoin(base, self.href)
            # Reject malformed and cross-host links rather than opening provider content as commands.
            if level is not None and 1 <= level <= 250 and urlsplit(url).netloc == urlsplit(base).netloc:
                self.rows.append(dict(provider=self.provider, name=title, level=level, exp=exp, url=url))
        self.active = None


def parse_catalog(provider, html):
    parser = CatalogParser(provider)
    parser.feed(html)
    rows = {row['url']: row for row in parser.rows}
    if not rows:
        raise ValueError(PROVIDERS[provider][0] + ': quest catalog format changed; previous data kept')
    return list(rows.values())


class AlternateCatalogs:
    def __init__(self, cache_dir):
        self.folder = Path(cache_dir) / 'alternate-catalogs'
        self.rows = {}
        self.status = {}
        self.fetched_at = {}
        self._refresh_lock = threading.Lock()
        self._revision = 0
        self.load_cached()

    def _saved(self, key):
        """Validate local data with the same trust boundary as downloaded links."""
        try:
            saved = json.loads((self.folder / (key + '.json')).read_text(encoding='utf-8'))
            stamp = saved['fetched_at']
            if not isinstance(stamp, (int, float)) or not math.isfinite(stamp) or stamp <= 0:
                return None
            rows = saved['rows']
            if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
                return None
            for row in rows:
                if row['provider'] != key or not isinstance(row['name'], str) or not 1 <= len(row['name']) <= 500:
                    return None
                if type(row['level']) is not int or not 1 <= row['level'] <= 250:
                    return None
                if row['exp'] is not None and (type(row['exp']) is not int or row['exp'] < 0):
                    return None
                parsed = urlsplit(row['url'])
                if parsed.scheme != 'https' or parsed.netloc != urlsplit(PROVIDERS[key][1]).netloc or not parsed.path.startswith('/quests/'):
                    return None
            return saved
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def load_cached(self):
        """Startup/opening a window must never initiate a provider request."""
        for key in PROVIDERS:
            saved = self._saved(key)
            if saved:
                self._accept_saved(key, saved)
        return self

    def _accept_saved(self, key, saved):
        # Publish a new mapping: readers can finish iterating the old one.
        self.rows = {**self.rows, key:saved['rows']}
        self.fetched_at[key] = saved['fetched_at']
        if saved['fetched_at'] > time.time() + 300:
            self.status[key] = 'Cached · date ahead of system clock'
        else:
            self.status[key] = 'Cached · ' + time.strftime('%Y-%m-%d', time.localtime(saved['fetched_at']))

    def refresh(self, force=False):
        # Multiple source windows share this object; concurrent refreshes coalesce via cache.
        revision = self._revision
        with self._refresh_lock:
            if force and revision != self._revision:
                return self
            result = self._refresh(force)
            self._revision += 1
            return result

    def _refresh(self, force):
        for key, (name, url) in PROVIDERS.items():
            path = self.folder / (key + '.json')
            saved = self._saved(key)
            if saved and not force and 0 <= time.time() - saved['fetched_at'] < 86400:
                self._accept_saved(key, saved)
                continue
            try:
                payload = self._download(key, url)
                rows = parse_catalog(key, payload.decode('utf-8'))
                stamp = time.time()
                self.folder.mkdir(parents=True, exist_ok=True)
                temp = path.with_suffix('.tmp')
                temp.write_text(json.dumps(dict(rows=rows, fetched_at=stamp)), encoding='utf-8')
                temp.replace(path)
                self.rows = {**self.rows, key:rows}
                self.fetched_at[key] = stamp
                self.status[key] = 'Updated · ' + time.strftime('%Y-%m-%d', time.localtime(stamp))
            except Exception as error:
                if saved:
                    self._accept_saved(key, saved)
                self.status[key] = ('Saved catalog · ' if key in self.rows else 'Unavailable · ') + str(error)
        return self

    @staticmethod
    def _download(key, url):
        global _LAST
        with _LOCK:
            if key in _BLOCKED:
                raise urllib.error.URLError('Provider refused access; automatic requests stopped')
            if _LAST is not None:
                time.sleep(max(0, 10 - (time.monotonic() - _LAST)))
            request = urllib.request.Request(url, headers={
                'User-Agent': 'UmbraleCompanion/3.38 (https://github.com/Bejerano1996/MapleCompanion/issues)'})
            try:
                with open_catalog_request(request, timeout=30) as response:
                    if urlsplit(response.url).netloc != urlsplit(url).netloc:
                        raise ValueError('Unexpected provider redirect')
                    payload = response.read(MAX_BYTES + 1)
                    if len(payload) > MAX_BYTES:
                        raise ValueError('Catalog response too large')
                    return payload
            except urllib.error.HTTPError as error:
                if error.code in (403, 429):
                    _BLOCKED.add(key)
                raise
            finally:
                _LAST = time.monotonic()

    def search(self, query='', level_range=None):
        terms = re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKC', query).casefold())
        rows = [row for entries in self.rows.values() for row in entries
                if all(term in unicodedata.normalize('NFKC', row['name']).casefold() for term in terms)
                and (level_range is None or level_range[0] <= row['level'] <= level_range[1])]
        return sorted(rows, key=lambda row: (row['name'].casefold(), row['provider'], row['url']))
