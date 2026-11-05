from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion_feature_model import utility_compare_maps
class HistoryAnchorTests(unittest.TestCase):
 def test_corrupt_row_does_not_crash_or_poison_other_sessions(self):
  good=dict(finished_at=1,running_since=None,map_id='a',elapsed=100,mesos=10,cost=0,exp=20,kills=1)
  for mode,key in [('wallet','wallet_elapsed_anchor'),('notices','money_elapsed_anchor')]:
   for bad in ('bad',{},[],True,False,-1,101,float('nan'),float('inf')):
    with self.subTest(mode=mode,bad=bad):
     r=utility_compare_maps([good,dict(good,money_mode=mode,**{key:bad})],minimum_seconds=0)
     self.assertEqual(r['excluded']['invalid'],1);self.assertEqual(r['maps'][0]['sessions'],1)
     self.assertEqual(r['maps'][0]['net_hour'],360)
 def test_legacy_none_and_numeric_string_anchors(self):
  good=dict(finished_at=1,running_since=None,map_id='a',elapsed=100,mesos=10,cost=0,exp=20,kills=1)
  for anchor,rate in [(None,360),('50',720),(100,0)]:
   r=utility_compare_maps([dict(good,money_elapsed_anchor=anchor)],minimum_seconds=0)
   self.assertEqual(r['excluded']['invalid'],0);self.assertEqual(r['maps'][0]['net_hour'],rate)
if __name__=='__main__':unittest.main()
