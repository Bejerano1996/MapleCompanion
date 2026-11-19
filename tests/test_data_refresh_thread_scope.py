from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from meowdb import MeowDB


class RefreshThreadScopeTests(unittest.TestCase):
    def test_forced_index_refresh_does_not_invalidate_other_thread_cache(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            db=MeowDB(folder)
            path='/fixture-detail'
            Path(db._cache_path(path)).write_text('saved detail',encoding='utf-8')
            entered=threading.Event();release=threading.Event()
            def indexes():
                entered.set()
                self.assertTrue(release.wait(2))
            with patch.object(db,'_load_indexes',side_effect=indexes),patch.object(db,'_fetch',return_value=b'network detail') as fetch:
                worker=threading.Thread(target=lambda:db.load_indexes(force=True))
                worker.start();self.assertTrue(entered.wait(2))
                try:
                    result=db._get(path,86400)
                finally:
                    release.set();worker.join(2)
                self.assertEqual(result,'saved detail')
                fetch.assert_not_called()
                self.assertFalse(db._force_refresh)


if __name__=='__main__': unittest.main()
