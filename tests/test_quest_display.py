from pathlib import Path
import sys,unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
class QuestDisplayTests(unittest.TestCase):
 def test_live_quest_is_visible_before_old_saved_cards(self):
  state={'active':['event','old','new'],'tracked':['new']}
  subject=SimpleNamespace(state=state)
  self.assertEqual(app.App.quest_display_order(subject),['new','event','old'])
  self.assertEqual(state['active'],['event','old','new'])
 def test_stable_with_multiple_live_quests_and_missing_tracked_id(self):
  subject=SimpleNamespace(state={'active':['old','a','b','other'],'tracked':['b','missing','a']})
  self.assertEqual(app.App.quest_display_order(subject),['a','b','old','other'])
if __name__=='__main__':unittest.main()
