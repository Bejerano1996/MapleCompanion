"""Validated index snapshots published by one atomic pointer replacement.

Legacy cache files are never overwritten by an index refresh. Interrupted or
invalid updates leave the old snapshot usable, including after app restart.
All files live in the local cache and are excluded from source/program releases.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import uuid

MAX_PAGE = 16 * 1024 * 1024
MAX_SNAPSHOT = 64 * 1024 * 1024


class IndexCache:
    def __init__(self, folder, required_keys):
        self.folder = Path(folder)
        self.root = self.folder / 'index-snapshots'
        self.pointer = self.folder / 'active-indexes.json'
        self.required_keys = set(required_keys)
        self._entries = {}
        self.generation = None
        self._load()

    @staticmethod
    def filename(key):
        return hashlib.sha1(key.encode('utf-8')).hexdigest()[:20] + '.html'

    @staticmethod
    def valid_stamp(value):
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 32503680000

    def _load(self):
        try:
            if self.pointer.stat().st_size > 8192:
                return
            pointer = json.loads(self.pointer.read_text(encoding='utf-8'))
            for generation in (pointer.get('generation'), pointer.get('previous')):
                entries = self._read_generation(generation)
                if entries is not None:
                    self._entries, self.generation = entries, generation
                    return
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def _read_generation(self, generation):
        if not isinstance(generation, str) or not re.fullmatch(r'[a-f0-9]{32}', generation):
            return None
        try:
            folder = self.root / generation
            manifest_path = folder / 'manifest.json'
            if manifest_path.stat().st_size > 512 * 1024:
                return None
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            files = manifest['files']
            if manifest.get('format') != 1 or not isinstance(files, dict) or not 1 <= len(files) <= 128:
                return None
            if not self.required_keys <= files.keys():
                return None
            total, entries = 0, {}
            for key, record in files.items():
                if not isinstance(key, str) or not 1 <= len(key) <= 2048 or record['file'] != self.filename(key):
                    return None
                if not self.valid_stamp(record['fetched_at']) or type(record['size']) is not int or not 0 <= record['size'] <= MAX_PAGE:
                    return None
                total += record['size']
                if total > MAX_SNAPSHOT:
                    return None
                path = folder / record['file']
                if path.is_symlink() or path.stat().st_size != record['size']:
                    return None
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != record['sha256']:
                    return None
                entries[key] = (raw.decode('utf-8'), record['fetched_at'])
            return entries
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def get(self, key):
        return self._entries.get(key)

    @staticmethod
    def _write_new(path, raw):
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    def commit(self, pages):
        if not self.required_keys <= pages.keys() or not 1 <= len(pages) <= 128:
            raise ValueError('Incomplete validated index cache snapshot')
        files, encoded, total = {}, {}, 0
        for key, (text, stamp) in pages.items():
            if not isinstance(key, str) or not 1 <= len(key) <= 2048 or not isinstance(text, str) or not self.valid_stamp(stamp):
                raise ValueError('Invalid index cache record')
            raw = text.encode('utf-8')
            total += len(raw)
            if len(raw) > MAX_PAGE or total > MAX_SNAPSHOT:
                raise ValueError('Index cache snapshot too large')
            filename = self.filename(key)
            if filename in encoded:
                raise ValueError('Colliding index cache keys')
            files[key] = dict(file=filename, sha256=hashlib.sha256(raw).hexdigest(), size=len(raw), fetched_at=stamp)
            encoded[filename] = raw
        generation = uuid.uuid4().hex
        folder = self.root / generation
        folder.mkdir(parents=True, exist_ok=False)
        for filename, raw in encoded.items():
            self._write_new(folder / filename, raw)
        self._write_new(folder / 'manifest.json', json.dumps(dict(format=1, files=files), allow_nan=False).encode('utf-8'))
        pointer = json.dumps(dict(generation=generation, previous=self.generation)).encode('utf-8')
        temporary = self.folder / ('.active-indexes-' + generation + '.tmp')
        self._write_new(temporary, pointer)
        os.replace(temporary, self.pointer)
        # Readers switch only after every file and the pointer have been committed.
        self._entries = {key:(text, stamp) for key,(text,stamp) in pages.items()}
        self.generation = generation
