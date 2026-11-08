import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training_accounting import NoticeReconciliation,TrainingAccountant
from session_rewards import session_token
class StableHudTests(unittest.TestCase):
 def test_old_difference_is_retired_after_stable_hud(self):
  a=NoticeReconciliation();a.feed(dict(exp=84,kills=3,party_exp=7),65,1)
  self.assertEqual(a.feed({},0,6),19)
  self.assertEqual(a.feed({},0,6.001),0)
  self.assertEqual(a.feed({},None,23),0)
 def test_new_notices_survive_old_difference_retirement(self):
  a=NoticeReconciliation();a.feed(dict(exp=84,kills=3,party_exp=7),65,1)
  self.assertEqual(a.feed(dict(exp=9,kills=1,party_exp=2),0,7),9)
  self.assertEqual(a.feed({},None,24),9)
  self.assertEqual(a.feed({},9,25),0)
 def test_recent_leading_notice_is_not_discarded(self):
  a=NoticeReconciliation();a.feed(dict(exp=9,kills=1,party_exp=2),0,1)
  self.assertEqual(a.feed({},0,4),9)
  self.assertEqual(a.feed({},9,5),0)
 def test_positive_hud_motion_restarts_stable_witness(self):
  a=NoticeReconciliation();a.feed(dict(exp=20,kills=1),0,1)
  self.assertEqual(a.feed({},5,5),15)
  self.assertEqual(a.feed({},0,7),15)
  self.assertEqual(a.feed({},0,10.001),0)
 def test_reset_discards_old_witness(self):
  a=NoticeReconciliation();a.feed(dict(exp=20,kills=1),0,1);a.feed({},None,8,baseline=True)
  self.assertEqual(a.feed(dict(exp=9,kills=1),0,9),9)
 def test_negative_hud_clears_old_witness(self):
  a=NoticeReconciliation();a.feed(dict(exp=20,kills=1),0,1);a.feed({},-10,7)
  self.assertEqual(a.feed(dict(exp=9,kills=1),0,8),9)
 def test_accountant_does_not_restore_retired_loss(self):
  s=dict(id='audit',running_since=1,auto_rewards=True,exp=0,kills=0,mesos=0);a=TrainingAccountant();t=session_token(s)
  a.feed(s,t,[],dict(level=27,exp=1000),0);a.feed(s,t,[],dict(level=27,exp=1000),.1)
  rows=[('exp',77),('bonus',7)];a.feed(s,t,rows,dict(level=27,exp=1065),1)
  a.feed(s,t,rows,dict(level=27,exp=1065),7);a.feed(s,t,rows,None,24)
  self.assertEqual(s['exp'],65)
if __name__=='__main__':unittest.main()
