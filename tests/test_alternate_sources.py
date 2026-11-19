import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error

import alternate_sources as sources

CC = '<li><a href="/quests/first">First &amp; New</a><span>Level 39, from Myen, 12,340 EXP</span></li>'
CL = '<tr><td><a href="/quests/first">First &amp; New</a></td><td>Lv.<!-- -->39</td><td>Myen</td><td>12,340</td></tr>'


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.catalog = sources.AlternateCatalogs(self.temp.name)

    def test_catalogs_keep_distinct_source_ids(self):
        for key, html in [('ccplz', CC), ('classic', CL)]:
            row = sources.parse_catalog(key, html)[0]
            self.assertEqual((row['name'], row['level'], row['exp']), ('First & New', 39, 12340))
            self.catalog.rows[key] = [row]
        self.assertEqual(len(self.catalog.search('new')), 2)

    def test_missing_exp_does_not_become_zero(self):
        row = sources.parse_catalog('classic', CL.replace('12,340', '—'))[0]
        self.assertIsNone(row['exp'])

    def test_negative_or_malformed_exp_is_unknown(self):
        for text in ('-100','−100','1,20','1.5k'):
            row=sources.parse_catalog('classic',CL.replace('12,340',text))[0]
            self.assertIsNone(row['exp'],text)
        row=sources.parse_catalog('ccplz',CC.replace('12,340','-100'))[0]
        self.assertIsNone(row['exp'])

    def test_clock_rewind_keeps_saved_facts_but_does_not_claim_fresh_cache(self):
        self.catalog.folder.mkdir(parents=True)
        payload=dict(rows=sources.parse_catalog('ccplz',CC),fetched_at=2000)
        (self.catalog.folder/'ccplz.json').write_text(json.dumps(payload),encoding='utf-8')
        with patch.object(sources.time,'time',return_value=1000),patch.object(self.catalog,'_download',side_effect=OSError('offline')) as fetch:
            reopened=sources.AlternateCatalogs(self.temp.name)
            self.assertEqual(len(reopened.search()),1)
            self.catalog.refresh()
            self.assertEqual(len(self.catalog.search()),1)
            self.assertEqual(fetch.call_count,2)

    def test_bad_links_or_format_rejected(self):
        for html in ['<html>Maintenance</html>', CC.replace('/quests/first', '//evil.test/quests/first')]:
            with self.assertRaises(ValueError):
                sources.parse_catalog('ccplz', html)

    def test_duplicate_link_is_one_quest(self):
        self.assertEqual(len(sources.parse_catalog('ccplz', CC + CC)), 1)

    def test_cached_read_sends_no_request(self):
        with patch.object(self.catalog, '_download', side_effect=[CC.encode(), CL.encode()]) as fetch:
            self.catalog.refresh()
            self.assertEqual(fetch.call_count, 2)
        other = sources.AlternateCatalogs(self.temp.name)
        with patch.object(other, '_download', side_effect=AssertionError('network')) as fetch:
            other.refresh()
            fetch.assert_not_called()
        self.assertEqual(len(other.search()), 2)

    def test_opening_catalog_loads_saved_data_without_network(self):
        with patch.object(self.catalog, '_download', side_effect=[CC.encode(), CL.encode()]):
            self.catalog.refresh()
        with patch.object(sources.AlternateCatalogs, '_download', side_effect=AssertionError('network')) as fetch:
            reopened = sources.AlternateCatalogs(self.temp.name)
        fetch.assert_not_called()
        self.assertEqual(len(reopened.search()), 2)

    def test_nonfinite_cache_date_is_rejected(self):
        self.catalog.folder.mkdir(parents=True)
        payload = dict(rows=sources.parse_catalog('ccplz', CC), fetched_at=float('nan'))
        (self.catalog.folder/'ccplz.json').write_text(json.dumps(payload), encoding='utf-8')
        with patch.object(self.catalog, '_download', side_effect=OSError('offline')):
            self.catalog.refresh()
        self.assertNotIn('ccplz', self.catalog.rows)

    def test_refresh_failure_preserves_previous_catalog(self):
        with patch.object(self.catalog, '_download', side_effect=[CC.encode(), CL.encode()]):
            self.catalog.refresh()
        before = dict(self.catalog.rows)
        with patch.object(self.catalog, '_download', return_value=b'<html>changed</html>'):
            self.catalog.refresh(force=True)
        self.assertEqual(self.catalog.rows, before)
        self.assertIn('previous data kept', self.catalog.status['ccplz'])

    def test_one_provider_failure_does_not_hide_other(self):
        with patch.object(self.catalog, '_download', side_effect=[OSError('offline'), CL.encode()]):
            self.catalog.refresh()
        self.assertEqual(len(self.catalog.search()), 1)
        self.assertEqual(self.catalog.search()[0]['provider'], 'classic')

    def test_forbidden_stops_next_request(self):
        error = urllib.error.HTTPError(sources.PROVIDERS['ccplz'][1], 403, 'Forbidden', None, None)
        with patch.object(sources, '_BLOCKED', set()), patch.object(sources, '_LAST', None), \
                patch.object(sources, 'open_catalog_request', side_effect=error) as fetch:
            for unused in range(2):
                with self.assertRaises(urllib.error.URLError):
                    sources.AlternateCatalogs._download('ccplz', sources.PROVIDERS['ccplz'][1])
            self.assertEqual(fetch.call_count, 1)

    def test_search_accepts_multiple_keywords_and_level_filter(self):
        self.catalog.rows['ccplz']=[dict(provider='ccplz', name='Arwen and the Glass Shoe', level=25,
                                         exp=100,url='https://ccplz.cc/quests/arwen')]
        self.assertEqual(len(self.catalog.search('shoe arwen')),1)
        self.assertEqual(self.catalog.search('shoe arwen',(26,40)),[])
        self.assertEqual(len(self.catalog.search('shoe arwen',(15,25))),1)

    def test_two_simultaneous_forced_refreshes_share_one_fetch(self):
        entered=threading.Event();release=threading.Event();second_entered=threading.Event()
        def download(key,url):
            if key=='ccplz':
                entered.set()
                self.assertTrue(release.wait(2))
            return CC.encode() if key=='ccplz' else CL.encode()
        def second():
            second_entered.set()
            self.catalog.refresh(force=True)
        with patch.object(self.catalog,'_download',side_effect=download) as fetch:
            first=threading.Thread(target=lambda:self.catalog.refresh(force=True))
            other=threading.Thread(target=second)
            first.start();self.assertTrue(entered.wait(2))
            other.start();self.assertTrue(second_entered.wait(2))
            release.set();first.join(2);other.join(2)
            self.assertFalse(first.is_alive() or other.is_alive())
            self.assertEqual(fetch.call_count,2)

    def test_search_survives_a_provider_arriving_during_iteration(self):
        entered=threading.Event();release=threading.Event();errors=[];results=[]
        class SlowRow(dict):
            def __getitem__(row,key):
                if key=='name' and not entered.is_set():
                    entered.set()
                    if not release.wait(2):raise AssertionError('search not released')
                return super().__getitem__(key)
        self.catalog.rows={'ccplz':[SlowRow(sources.parse_catalog('ccplz',CC)[0])]}
        def search():
            try:results.extend(self.catalog.search('quest'))
            except Exception as error:errors.append(error)
        worker=threading.Thread(target=search);worker.start()
        try:
            self.assertTrue(entered.wait(2))
            self.catalog._accept_saved('classic',dict(rows=sources.parse_catalog('classic',CL),fetched_at=100))
        finally:
            release.set();worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors,[])
        self.assertEqual(len(self.catalog.search()),2)


if __name__ == '__main__':
    unittest.main()
