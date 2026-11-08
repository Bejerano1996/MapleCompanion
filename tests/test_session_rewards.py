import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session_rewards import RewardTracker,reward_event,session_token,apply_rewards
class RewardsTests(unittest.TestCase):
 def test_parser(self):
  for text,event in [('You received EXP (+7)',('exp',7)),('Bonus EXP for PARTY (+2)',('bonus',2)),('You have gained mesos (+10)',('mesos',10)),('have qained mesos f+7)',('mesos',7))]:self.assertEqual(reward_event(text),event)
  for text in ('Salad 220 mesos','Quest EXP 500','You lost mesos (-7)','You received EXP (+100000001)'):self.assertIsNone(reward_event(text))
 def test_baseline_and_duplicate(self):
  t=RewardTracker();a=[('mesos',10)];self.assertFalse(any(t.feed(a).values()));self.assertFalse(any(t.feed(a).values()))
  b=a+[('exp',7),('bonus',2),('mesos',7)]
  self.assertEqual(t.feed(b),dict(exp=9,kills=1,mesos=7,party_exp=2));self.assertFalse(any(t.feed(b).values()))
 def test_repeated_equal_rewards(self):
  t=RewardTracker();t.feed([('mesos',10)]);self.assertEqual(t.feed([('mesos',10),('mesos',10)])['mesos'],10)
 def test_scroll(self):
  t=RewardTracker();t.feed([('exp',5),('mesos',10)]);self.assertEqual(t.feed([('mesos',10),('exp',7)])['exp'],7)
 def test_loss_of_continuity(self):
  t=RewardTracker();t.feed([('exp',5)]);self.assertFalse(any(t.feed([('mesos',999)]).values()))
 def test_blank_and_unavailable(self):
  t=RewardTracker();t.feed([('exp',5)]);t.feed([]);t.feed([]);t.feed([]);t.feed([]);self.assertEqual(t.feed([('exp',5)])['exp'],5)
  t.feed(None);self.assertFalse(any(t.feed([('exp',5)]).values()))
 def test_pause_and_archive(self):
  s=dict(id='a',running_since=1,exp=2,mesos=3,kills=0,cost=10);token=session_token(s)
  self.assertTrue(apply_rewards(s,token,dict(exp=7,mesos=10,kills=1)));self.assertEqual(s['cost'],10)
  s['running_since']=None;self.assertFalse(apply_rewards(s,token,dict(exp=7)));s.update(id='b',running_since=1);self.assertFalse(apply_rewards(s,token,dict(exp=7)))
 def test_late_amount_read(self):
  t=RewardTracker();t.feed([]);t.feed([]);t.feed([]);t.feed([])
  t.feed([('mesos',None)])
  self.assertEqual(t.feed([('mesos',10)])['mesos'],10)
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_recovered_old_amount_excluded(self):
  t=RewardTracker();t.feed([('mesos',None)]);self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_party_refinement_no_duplicate_base(self):
  t=RewardTracker();t.feed([('mesos',1)])
  t.feed([('mesos',1),('exp',7),('bonus',None),('exp',7)])
  delta=t.feed([('mesos',1),('exp',7),('bonus',2),('exp',7)])
  self.assertEqual(delta,dict(exp=2,kills=0,mesos=0,party_exp=2))
 def test_brief_ocr_dropout_not_new_money(self):
  t=RewardTracker();t.feed([('mesos',10)]);t.feed([]);t.feed([])
  self.assertEqual(t.feed([('mesos',10)])['mesos'],0)
 def test_party_ocr_formats(self):
  for text in ('BorusEXPforPARTY（+2）','Bonus EXPfor PARTY (+2','Bonus EXP for PARTY (+2)'):
   self.assertEqual(reward_event(text),('bonus',2))
  self.assertIsNone(reward_event('Bonus EXP for PARTY (+?'))
 def test_manual_mode(self):
  s=dict(id='a',running_since=1,auto_rewards=False);self.assertFalse(apply_rewards(s,session_token(s),dict(exp=7)))
if __name__=='__main__':unittest.main()
