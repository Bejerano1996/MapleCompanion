import io,json,tempfile,unittest,urllib.error
from pathlib import Path
import sys
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import meowdb
class DataRefreshTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
  self.addCleanup(self.temp.cleanup)
  self.folder=self.temp.name
 def db(self):return meowdb.MeowDB(self.folder)
 def test_revoked_access_never_sends_request_or_retries(self):
  with patch.object(meowdb,'ACCESS_RENEWAL_REQUIRED',True),patch.object(meowdb.urllib.request,'urlopen') as request,patch.object(meowdb.time,'sleep') as sleep:
   with self.assertRaises(meowdb.DataAccessPaused):self.db()._fetch('/maps')
   request.assert_not_called();sleep.assert_not_called()
 def test_403_and_429_stop_other_database_instances(self):
  for code in (403,429):
   with self.subTest(code=code),patch.object(meowdb,'ACCESS_RENEWAL_REQUIRED',False),patch.object(meowdb,'_ACCESS_DENIED',None),patch.object(meowdb,'_LAST_REQUEST',None),patch.object(meowdb.MeowDB,'_request_url',side_effect=urllib.error.HTTPError('https://meowdb.com',code,'Refused',{},None)) as request,patch.object(meowdb.time,'sleep') as sleep:
    with self.assertRaises(meowdb.DataAccessPaused):self.db()._fetch('/maps')
    with self.assertRaises(meowdb.DataAccessPaused):self.db()._fetch('/monsters')
    self.assertEqual(request.call_count,1);sleep.assert_not_called()
 def test_ten_second_limit_is_shared_across_instances(self):
  clock=[0.0];calls=[]
  def sleep(seconds):clock[0]+=seconds
  def request(path):calls.append(clock[0]);return b'payload'
  with patch.object(meowdb,'ACCESS_RENEWAL_REQUIRED',False),patch.object(meowdb,'_ACCESS_DENIED',None),patch.object(meowdb,'_LAST_REQUEST',None),patch.object(meowdb.time,'monotonic',side_effect=lambda:clock[0]),patch.object(meowdb.time,'sleep',side_effect=sleep),patch.object(meowdb.MeowDB,'_request_url',side_effect=request):
   self.db()._fetch('/maps');self.db()._fetch('/npcs');self.db()._fetch('/monsters')
  self.assertEqual(calls,[0,10,20])
 def test_expired_cache_remains_usable_while_paused(self):
  db=self.db();path=Path(db._cache_path('/maps'));path.write_text('saved data',encoding='utf-8')
  with patch.object(meowdb,'ACCESS_RENEWAL_REQUIRED',True),patch.object(meowdb.urllib.request,'urlopen') as request:
   self.assertEqual(db._get('/maps',-1),'saved data');request.assert_not_called()
  self.assertTrue(db.offline);self.assertEqual(db.data_sources['/maps']['source'],'cache')
 def test_missing_cache_does_not_produce_empty_success(self):
  with self.assertRaises(meowdb.DataAccessPaused):self.db()._get('/unknown',1)
 def test_force_refresh_and_failure_restore_flags_and_metadata(self):
  db=self.db();db.data_sources={'old':{'source':'cache'}}
  def fail():
   self.assertTrue(db._force_refresh);db.data_sources={'partial':{}};raise ValueError('changed schema')
  with patch.object(db,'_load_indexes',side_effect=fail):
   with self.assertRaises(ValueError):db.refresh_indexes()
  self.assertFalse(db._force_refresh);self.assertEqual(db.data_sources,{'old':{'source':'cache'}})
 def pages(self):
  def page(rows):return '<script>self.__next_f.push('+json.dumps([1,json.dumps(rows,separators=(',',':'))])+')</script>'
  return {'/quest-tracker/all':page([{'id':'q','need':[]}]),'/npcs':page([{'id':'n','name':'NPC','maps':[]}]),'/maps':page([{'id':'m','avgMobLevel':1}]),'/monsters':page([{'id':1,'level':1,'name':'Slime'}]),meowdb.MAP_DATA_URL:json.dumps([{'id':'m','monsters':[]}]),'/npc-shops':''}
 def test_invalid_new_catalog_leaves_all_existing_indexes_intact(self):
  db=self.db();old={'old':{'id':'old'}};db.quests=old;db.maps=old;db.monsters=old;db.npcs=old
  pages=self.pages();pages['/maps']='<html>changed upstream format</html>'
  with patch.object(db,'_get',side_effect=lambda path,age:pages[path]):
   with self.assertRaisesRegex(ValueError,'previous data kept'):db.load_indexes()
  for field in ('quests','maps','monsters','npcs'):self.assertIs(getattr(db,field),old)
 def test_complete_catalog_commits_after_validation(self):
  db=self.db();pages=self.pages()
  with patch.object(db,'_get',side_effect=lambda path,age:pages[path]),patch.object(meowdb.guides,'quest_guides',return_value={}):db.load_indexes()
  self.assertEqual(set(db.quests),{'q'});self.assertEqual(set(db.maps),{'m'});self.assertEqual(set(db.monsters),{1});self.assertIn('npc',db.npcs)
 def test_refresh_dialog_keeps_guides_until_success(self):
  import app
  from types import SimpleNamespace
  callbacks=[];guides={'old':'saved guide'}
  db=SimpleNamespace(access_paused=False,data_sources={},quests={'old':{}},maps={'m':{}},monsters={1:{}},refresh_indexes=Mock())
  subject=SimpleNamespace(db=db,root=None,guides=guides,_on_loaded=Mock(),run_bg=lambda work,callback:callbacks.append(callback))
  with patch('app.messagebox.askyesno',return_value=True):app.App.open_data_status(subject)
  self.assertEqual(guides,{'old':'saved guide'})
  callbacks[0](None);self.assertEqual(guides,{})
  subject._on_loaded.assert_called_once_with(None)
 def test_paused_refresh_dialog_sends_no_download_job(self):
  import app
  from types import SimpleNamespace
  db=SimpleNamespace(access_paused=True,data_sources={},quests={'old':{}},maps={'m':{}},monsters={1:{}})
  subject=SimpleNamespace(db=db,root=None,run_bg=Mock())
  with patch('app.messagebox.showinfo') as info:app.App.open_data_status(subject)
  subject.run_bg.assert_not_called();self.assertIn('renewed permission',info.call_args.args[1])
if __name__=='__main__':unittest.main()
