from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import index_cache
from index_cache import IndexCache


class IndexCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.cache=IndexCache(self.temp.name,{'/a','/b'})

    def pages(self,version):
        return {'/a':('A '+version,100),'/b':('B '+version,101)}

    def test_complete_snapshot_reopens_with_identical_values(self):
        self.cache.commit(self.pages('one'))
        other=IndexCache(self.temp.name,{'/a','/b'})
        self.assertEqual(other.get('/a'),('A one',100))
        self.assertEqual(other.get('/b'),('B one',101))

    def test_pointer_failure_leaves_previous_generation_active(self):
        self.cache.commit(self.pages('one'))
        old_pointer=self.cache.pointer.read_bytes()
        with patch.object(index_cache.os,'replace',side_effect=OSError('simulated full disk')):
            with self.assertRaises(OSError):self.cache.commit(self.pages('two'))
        self.assertEqual(self.cache.pointer.read_bytes(),old_pointer)
        self.assertEqual(self.cache.get('/a'),('A one',100))
        self.assertEqual(IndexCache(self.temp.name,{'/a','/b'}).get('/a'),('A one',100))

    def test_corrupt_new_generation_falls_back_as_a_whole(self):
        self.cache.commit(self.pages('one'))
        self.cache.commit(self.pages('two'))
        bad=self.cache.root/self.cache.generation/self.cache.filename('/a')
        bad.write_text('broken file',encoding='utf-8')
        other=IndexCache(self.temp.name,{'/a','/b'})
        self.assertEqual(other.get('/a'),('A one',100))
        self.assertEqual(other.get('/b'),('B one',101))

    def test_incomplete_or_invalid_batch_cannot_replace_pointer(self):
        self.cache.commit(self.pages('one'))
        old=self.cache.pointer.read_bytes()
        for pages in ({'/a':('partial',100)}, {'/a':('A',float('nan')),'/b':('B',100)}):
            with self.assertRaises(ValueError):self.cache.commit(pages)
        self.assertEqual(self.cache.pointer.read_bytes(),old)

    def test_manifest_cannot_escape_snapshot_directory(self):
        self.cache.commit(self.pages('one'))
        folder=self.cache.root/self.cache.generation
        manifest=json.loads((folder/'manifest.json').read_text())
        manifest['files']['/a']['file']='../../private.json'
        (folder/'manifest.json').write_text(json.dumps(manifest))
        self.assertIsNone(IndexCache(self.temp.name,{'/a','/b'}).get('/a'))

    def test_cache_key_collision_fails_before_publication(self):
        with patch.object(self.cache,'filename',return_value='same.html'):
            with self.assertRaises(ValueError):self.cache.commit(self.pages('one'))
        self.assertFalse(self.cache.pointer.exists())

    def test_interruption_at_each_write_keeps_previous_restart_snapshot(self):
        self.cache.commit(self.pages('one'))
        original=self.cache._write_new
        for fail_at in range(1,5):  # two pages, manifest, temporary pointer
            with self.subTest(write=fail_at):
                calls=0
                def interrupted(path,raw):
                    nonlocal calls
                    calls+=1
                    if calls==fail_at:raise OSError('simulated interrupted write')
                    return original(path,raw)
                with patch.object(self.cache,'_write_new',side_effect=interrupted):
                    with self.assertRaises(OSError):self.cache.commit(self.pages('two'))
                reopened=IndexCache(self.temp.name,{'/a','/b'})
                self.assertEqual(reopened.get('/a'),('A one',100))
                self.assertEqual(reopened.get('/b'),('B one',101))
