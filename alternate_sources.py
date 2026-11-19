"""Independent, attributed quest catalogs; never rewrites character quest IDs.

Only two public index pages are read on explicit refresh. No detail-page crawl,
private API, analytics, or game state is sent to either provider.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import json
import re
import threading
import time
import urllib.error
import urllib.request

PROVIDERS = {
    'ccplz': ('CCPLZ', 'https://ccplz.cc/quests'),
    'classic': ('MapleStory Classic', 'https://maplestory-classic.com/quests'),
}
_LOCK = threading.Lock()
_LAST = None
_BLOCKED = set()
MAX_BYTES = 8 * 1024 * 1024


def number(text):
    match = re.search(r'\d[\d,]*', text)
    return int(match[0].replace(',', '')) if match else None


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
                exp_match = re.search(r'([\d,]+)\s+EXP\b', text)
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

    def refresh(self, force=False):
        for key, (name, url) in PROVIDERS.items():
            path = self.folder / (key + '.json')
            saved = None
            try:
                saved = json.loads(path.read_text(encoding='utf-8'))
                assert isinstance(saved['fetched_at'], (int, float))
                # Cache is data, not executable code. Revalidate source URLs and record types.
                assert isinstance(saved['rows'], list) and saved['rows']
                for row in saved['rows']:
                    assert row['provider'] == key and isinstance(row['name'], str)
                    assert isinstance(row['level'], int) and 1 <= row['level'] <= 250
                    assert row['exp'] is None or (isinstance(row['exp'], int) and row['exp'] >= 0)
                    parsed = urlsplit(row['url'])
                    assert parsed.scheme == 'https' and parsed.netloc == urlsplit(url).netloc
                    assert parsed.path.startswith('/quests/')
            except (OSError, ValueError, KeyError, TypeError, AssertionError):
                saved = None
            if saved and not force and time.time() - saved['fetched_at'] < 86400:
                self.rows[key] = saved['rows']
                self.status[key] = 'Cached · ' + time.strftime('%Y-%m-%d', time.localtime(saved['fetched_at']))
                continue
            try:
                payload = self._download(key, url)
                rows = parse_catalog(key, payload.decode('utf-8'))
                stamp = time.time()
                self.folder.mkdir(parents=True, exist_ok=True)
                temp = path.with_suffix('.tmp')
                temp.write_text(json.dumps(dict(rows=rows, fetched_at=stamp)), encoding='utf-8')
                temp.replace(path)
                self.rows[key] = rows
                self.status[key] = 'Updated · ' + time.strftime('%Y-%m-%d', time.localtime(stamp))
            except Exception as error:
                if saved:
                    self.rows[key] = saved['rows']
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
                with urllib.request.urlopen(request, timeout=30) as response:
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

    def search(self, query=''):
        query = query.casefold().strip()
        return [row for rows in self.rows.values() for row in rows
                if query in row['name'].casefold()]
