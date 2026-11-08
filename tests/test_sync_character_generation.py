from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import training_ui
from types import SimpleNamespace
class SyncCharacterGenerationTests(unittest.TestCase):
 def run_case(self,changed,result):
  class Root:
   def winfo_children(self): return []
   def winfo_viewable(self): return False
  class Subject:
   syncing=False; resetting=False; root=Root(); db=type("DB",(),{"quests":{"q":{}}})(); focus=None
   _character_read_revision=0
   def set_status(self,*args): pass
   def run_bg(self,work,callback,on_error): self.callback=callback
   def _on_synced(self,result): self.received=result;self.syncing=False
  a=Subject();app.App.sync_from_game(a)
  if changed:a._character_read_revision+=1
  a.callback(result)
  self.assertFalse(a.syncing)
  return a.received
 def test_old_exp_dropped_while_map_kept(self):
  original={"exp_bar":["old HUD"],"map":"map evidence"}
  actual=self.run_case(True,original)
  self.assertFalse(actual.get("exp_bar"));self.assertEqual(actual["map"],"map evidence")
  self.assertEqual(original["exp_bar"],["old HUD"])
 def test_current_exp_kept(self):
  original={"exp_bar":["current HUD"],"map":"map evidence"}
  self.assertEqual(self.run_case(False,original),original)
 def test_missing_game_kept(self):self.assertIsNone(self.run_case(True,None))
 def test_result_without_exp_kept(self):self.assertEqual(self.run_case(True,{"map":"x"}),{"map":"x"})
 def test_real_character_accept_invalidates_pending_scan(self):
  for exp in (1000,2000,1980):
   a=SimpleNamespace(state={"level":27},render_levelup=lambda:None)
   training_ui.training_accept_character(a,{"level":27,"exp":exp})
   self.assertEqual(a._character_read_revision,1)
   training_ui.training_accept_character(a,{"level":27,"exp":exp})
   self.assertEqual(a._character_read_revision,2)
   self.assertEqual(a.state["character_exp"]["exp"],exp)
 def test_contradictory_checkpoint_clears_only_character_confirmation(self):
  key=('validated-character-level',)
  for previous in (28,29):
   a=SimpleNamespace(state={"level":27},render_levelup=lambda:None,_reads={key:(previous,1),("map",):("x",2)})
   training_ui.training_accept_character(a,{"level":27,"exp":2000})
   self.assertNotIn(key,a._reads);self.assertEqual(a._reads[("map",)],("x",2))
 def test_matching_checkpoint_keeps_character_confirmation(self):
  key=('validated-character-level',)
  a=SimpleNamespace(state={"level":27},render_levelup=lambda:None,_reads={key:(27,2)})
  training_ui.training_accept_character(a,{"level":27,"exp":2000})
  self.assertEqual(a._reads[key],(27,2))
if __name__=="__main__":unittest.main()
