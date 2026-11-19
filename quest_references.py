"""Exact, local-only references for visible quests absent from the main database.

References never become game IDs or progress objectives. Numbered steps and
ambiguous aliases remain distinct; screen evidence expires rather than going stale.
"""
import re
import unicodedata


def normalized(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def aliases(name):
    values = {normalized(name)}
    # CCPLZ lists chain title (step title); the game helper often displays the step.
    match = re.search(r'\(([^()]*)\)\s*$', name)
    if match and len(normalized(match[1])) >= 6 and not re.fullmatch(r'\d+\s+(?:of|out of)\s+\d+', normalized(match[1])):
        values.add(normalized(match[1]))
    return {value for value in values if len(value) >= 6}


class ReferenceIndex:
    def __init__(self):
        self.signature = None
        self.index = {}
        self._rows_snapshot = ()

    def update(self, catalogs):
        catalog_rows = dict(catalogs.rows)
        signature = tuple((key, id(rows)) for key, rows in sorted(catalog_rows.items()))
        if signature == self.signature:
            return
        index = {}
        snapshot = tuple(catalog_rows.values())
        for rows in snapshot:
            for row in rows:
                for alias in aliases(row['name']):
                    index.setdefault(alias, {})[row['url']] = dict(row)
        safe = {}
        for alias, by_url in index.items():
            rows = list(by_url.values())
            providers = [row['provider'] for row in rows]
            if len(providers) == len(set(providers)):
                safe[alias] = rows
        self.index, self.signature = safe, signature
        self._rows_snapshot = snapshot

    def match(self, lines, known_quests=()):
        known = {value for quest in known_quests for value in aliases(quest.get('name', ''))}
        found = []
        for line in lines:
            text = line.get('text', '')
            if not isinstance(text, str) or len(text) > 500:
                continue
            key = normalized(text)
            if key in known or key not in self.index:
                continue
            rows = self.index[key]
            # Full chain and step aliases can have overlapping provider sets.
            # One shared exact URL establishes the same reference, not a new quest.
            sources = {row['url']: row for row in rows}
            name = text.strip()
            for prior in list(found):
                if sources.keys() & {row['url'] for row in prior['sources']}:
                    sources.update((row['url'], row) for row in prior['sources'])
                    name = min((name, prior['name']), key=lambda value:(len(value), value.casefold()))
                    found.remove(prior)
            found.append(dict(name=name, sources=[sources[url] for url in sorted(sources)]))
        return found[:8]


class VisibleReferences:
    def __init__(self):
        self.pending = {}
        self.visible = []
        self.seen_at = None

    def feed(self, references, now, auto=True):
        keys = lambda rows: tuple(sorted(tuple(sorted(s['url'] for s in row['sources'])) for row in rows))
        display = lambda rows: tuple((row['name'], tuple(sorted((s['url'],s.get('level'),s.get('exp')) for s in row['sources']))) for row in rows)
        previous = display(self.visible)
        if references:
            identity = keys(references)
            prior = self.pending.get('candidate')
            fresh = prior and 0 <= now - prior[1] <= 10
            if not auto or (fresh and prior[0] == identity):
                self.visible = references
                self.seen_at = now
            self.pending['candidate'] = (identity, now)
        else:
            self.pending.clear()
        self.expire(now)
        return previous != display(self.visible)

    def expire(self, now):
        prior = self.pending.get('candidate')
        if prior and not 0 <= now-prior[1] <= 10:
            self.pending.clear()
        if self.seen_at is None or now-self.seen_at <= 15:
            return False
        self.visible, self.seen_at = [], None
        return True

    def clear(self):
        changed = bool(self.visible)
        self.pending.clear()
        self.visible, self.seen_at = [], None
        return changed
