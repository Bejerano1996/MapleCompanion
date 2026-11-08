from pathlib import Path
import sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
class QuestRediscoveryTests(unittest.TestCase):
 def subject(self):
  class Root:
   def winfo_children(self):return []
   def winfo_viewable(self):return False
  class Subject:
   syncing=False;resetting=False;root=Root();db=type('DB',(),{'quests':{'old':{},'new':{}}})();focus=[(1500,500,1900,600)]
   def set_status(self,*args):pass
   def run_bg(self,work,callback,on_error):callback(work())
   def _on_synced(self,result):
    self.syncing=False
    if result['full']:self.focus=result['regions']
    self.seen=getattr(self,'seen',[])+result['quests']
  return Subject()
 def test_new_quest_below_old_crop_is_rediscovered(self):
  a=self.subject();scans=[]
  def capture(db,auto,ours,regions,map_only,exp_bar):
   scans.append(regions)
   return {'full':regions is None,'regions':[(1500,500,1900,750)],'quests':['old','new'] if regions is None or regions[0][3]==750 else ['old']}
  with patch.object(app,'capture_and_read',side_effect=capture):
   for _ in range(6):app.App.sync_from_game(a,auto=True)
  self.assertIn('new',a.seen)
  self.assertIsNone(scans[4]);self.assertEqual(scans[5][0][3],750)
  self.assertEqual(sum(x is None for x in scans),1)
 def test_map_only_scan_does_not_consume_rediscovery_schedule(self):
  a=self.subject()
  with patch.object(app,'capture_and_read',return_value={'full':False,'quests':[]}) as capture:
   for _ in range(8):app.App.sync_from_game(a,auto=True,map_only=True)
  self.assertFalse(hasattr(a,'_quest_scan_tick'))
  self.assertTrue(all(c.args[3]==a.focus for c in capture.call_args_list))
 def test_manual_sync_always_reads_full_screen(self):
  a=self.subject()
  with patch.object(app,'capture_and_read',return_value={'full':False,'quests':[]}) as capture:app.App.sync_from_game(a)
  self.assertIsNone(capture.call_args.args[3])
if __name__=='__main__':unittest.main()
