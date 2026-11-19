import json
from pathlib import Path
import tempfile
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
                patch.object(sources.urllib.request, 'urlopen', side_effect=error) as fetch:
            for unused in range(2):
                with self.assertRaises(urllib.error.URLError):
                    sources.AlternateCatalogs._download('ccplz', sources.PROVIDERS['ccplz'][1])
            self.assertEqual(fetch.call_count, 1)


if __name__ == '__main__':
    unittest.main()
