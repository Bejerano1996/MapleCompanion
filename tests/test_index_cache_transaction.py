from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import meowdb
import test_data_refresh as fixtures


class IndexTransactionTests(unittest.TestCase):
    def test_interrupted_optional_guide_batch_keeps_previous_pages_after_restart(self):
        rsc='1:["$","p",null,{"children":"GUIDE_READY"}]'
        good='<script>self.__next_f.push('+json.dumps([1,rsc])+')</script>'
        def parser(fetch):
            for slug in meowdb.guides.QUEST_GUIDES:
                if 'GUIDE_READY' not in fetch(slug):raise ValueError('guide format changed')
            return {'q':[{'notes':['Saved guide']}]}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            db,pages=self.setup_database(folder)
            pages.update(('/guides/'+slug,good) for slug in meowdb.guides.QUEST_GUIDES)
            with patch.object(db,'_fetch',side_effect=lambda key:pages[key].encode()),patch.object(meowdb.guides,'quest_guides',side_effect=parser):
                db.refresh_indexes()
            self.assertIn('q',db.quest_guides)
            broken=dict(pages);broken['/guides/'+meowdb.guides.QUEST_GUIDES[1]]='<html>temporary error</html>'
            with patch.object(db,'_fetch',side_effect=lambda key:broken[key].encode()),patch.object(meowdb.guides,'quest_guides',side_effect=parser):
                db.refresh_indexes()
            self.assertIn('q',db.quest_guides)
            restarted=meowdb.MeowDB(folder)
            with patch.object(restarted,'_fetch',side_effect=AssertionError('network')),patch.object(meowdb.guides,'quest_guides',side_effect=parser):
                restarted.load_indexes()
            self.assertIn('q',restarted.quest_guides)

    def test_bad_optional_shop_refresh_keeps_saved_shops_after_restart(self):
        def page(rows):return '<script>self.__next_f.push('+json.dumps([1,json.dumps(rows,separators=(',',':'))])+')</script>'
        shop=page([{'slug':'fixture-shop','npcName':'Seller','mapId':'m','items':[{'name':'Potion','iconKey':2000000,'classicPrice':50}]}])
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            db,pages=self.setup_database(folder)
            pages['/npc-shops']=shop
            with patch.object(db,'_fetch',side_effect=lambda key:pages[key].encode()),patch.object(meowdb.guides,'quest_guides',return_value={}):
                db.refresh_indexes()
            self.assertEqual(db.sold_by['2000000'][0]['price'],50)
            invalid_pages=['<html>temporary error, HTTP 200</html>']
            for invalid_price in (-10,'50',True):
                invalid_pages.append(page([{'slug':'fixture-shop','npcName':'Seller','mapId':'m','items':[{'name':'Potion','iconKey':2000000,'classicPrice':invalid_price}]}]))
            for bad_page in invalid_pages:
                with self.subTest(page=bad_page):
                    broken=dict(pages);broken['/npc-shops']=bad_page
                    with patch.object(db,'_fetch',side_effect=lambda key:broken[key].encode()),patch.object(meowdb.guides,'quest_guides',return_value={}):
                        db.refresh_indexes()
                    self.assertEqual(db.sold_by['2000000'][0]['price'],50)
                    restarted=meowdb.MeowDB(folder)
                    with patch.object(restarted,'_fetch',side_effect=AssertionError('network')),patch.object(meowdb.guides,'quest_guides',return_value={}):
                        restarted.load_indexes()
                    self.assertEqual(restarted.sold_by['2000000'][0]['price'],50)

    def setup_database(self, folder):
        pages=fixtures.DataRefreshTests().pages()
        db=meowdb.MeowDB(folder)
        for key,text in pages.items():
            Path(db._cache_path(key)).write_text(text,encoding='utf-8')
        with patch.object(meowdb.guides,'quest_guides',return_value={}):db.load_indexes()
        return db,pages

    def test_bad_refresh_does_not_poison_next_startup_cache(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            db,pages=self.setup_database(folder)
            original={key:Path(db._cache_path(key)).read_bytes() for key in pages}
            broken=dict(pages);broken['/quest-tracker/all']='<html>changed upstream format</html>'
            with patch.object(db,'_fetch',side_effect=lambda key:broken[key].encode()),patch.object(meowdb.guides,'quest_guides',return_value={}):
                with self.assertRaises(ValueError):db.refresh_indexes()
            for key,raw in original.items():
                self.assertEqual(Path(db._cache_path(key)).read_bytes(),raw,key)
            restarted=meowdb.MeowDB(folder)
            with patch.object(restarted,'_fetch',side_effect=AssertionError('network')),patch.object(meowdb.guides,'quest_guides',return_value={}):
                restarted.load_indexes()
            self.assertEqual(restarted.quests['q']['name'],'Quest')

    def test_successful_refresh_survives_restart_without_overwriting_legacy(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            db,pages=self.setup_database(folder)
            legacy=Path(db._cache_path('/quest-tracker/all')).read_bytes()
            changed={key:text.replace('Quest','New Quest') if key=='/quest-tracker/all' else text for key,text in pages.items()}
            with patch.object(db,'_fetch',side_effect=lambda key:changed[key].encode()),patch.object(meowdb.guides,'quest_guides',return_value={}):
                db.refresh_indexes()
            self.assertEqual(db.quests['q']['name'],'New Quest')
            self.assertEqual(Path(db._cache_path('/quest-tracker/all')).read_bytes(),legacy)
            restarted=meowdb.MeowDB(folder)
            with patch.object(restarted,'_fetch',side_effect=AssertionError('network')),patch.object(meowdb.guides,'quest_guides',return_value={}):
                restarted.load_indexes()
            self.assertEqual(restarted.quests['q']['name'],'New Quest')

    def test_cache_commit_failure_keeps_memory_indexes_and_metadata(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            db,pages=self.setup_database(folder)
            old_quests,old_shops=db.quests,db.shops
            sources=dict(db.data_sources)
            changed={key:text.replace('Quest','New Quest') if key=='/quest-tracker/all' else text for key,text in pages.items()}
            with patch.object(db,'_fetch',side_effect=lambda key:changed[key].encode()), \
                 patch.object(meowdb.guides,'quest_guides',return_value={}), \
                 patch.object(db._index_cache,'commit',side_effect=OSError('simulated disk failure')):
                with self.assertRaises(OSError):db.refresh_indexes()
            self.assertIs(db.quests,old_quests);self.assertIs(db.shops,old_shops)
            self.assertEqual(db.data_sources,sources)


if __name__=='__main__':unittest.main()
