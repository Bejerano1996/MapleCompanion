import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
import session_reader as reader
from session_rewards import RewardTracker
class ConfidenceTests(unittest.TestCase):
 def read(self,amount_score,prefix='You have gained mesos'):
  rows=[([[0,10],[220,10],[220,22],[0,22]],prefix,.999),([[225,10],[260,10],[260,22],[225,22]],'(+7)',amount_score)]
  with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',return_value=None):
   return reader.read_reward_image(Image.new('RGB',(300,100)),True)
 def test_clear_prefix_does_not_make_weak_amount_trusted(self):
  events=self.read(.8);self.assertEqual(list(events),[('mesos',7)]);self.assertFalse(events.trusted_money)
  tracker=RewardTracker(confirm_money=2);tracker.feed([])
  self.assertEqual(tracker.feed(events)['mesos'],0);self.assertEqual(tracker.feed(events)['mesos'],7)
 def test_low_amount_confidence_stays_pending(self):
  self.assertEqual(list(self.read(.6)),[('mesos',None)])
 def test_low_party_bonus_amount_stays_pending(self):
  self.assertEqual(list(self.read(.6,'Bonus EXP for PARTY')),[('bonus',None)])
 def test_malformed_grouping_is_pending_not_trusted(self):
  rows=[([[0,10],[250,10],[250,22],[0,22]],'You have gained mesos (+1,2)',.99)]
  with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',return_value=None):
   events=reader.read_reward_image(Image.new('RGB',(300,100)),True)
   self.assertEqual(list(events),[('mesos',None)]);self.assertFalse(events.trusted_money)
 def test_merged_rewards_do_not_credit_one_wrong_amount(self):
  rows=[([[0,10],[290,10],[290,22],[0,22]],'You received EXP (+7) Bonus EXP for PARTY (+2)',.99)]
  with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',return_value=None):
   events=reader.read_reward_image(Image.new('RGB',(300,100)),True)
   self.assertEqual(list(events),[('bonus',None)])
   tracker=RewardTracker(confirm_money=2);tracker.feed([])
   self.assertEqual(tracker.feed(events)['exp'],0)
 def test_clear_amount_retains_fast_credit(self):
  events=self.read(.99);self.assertEqual(events.trusted_money,{0})
  tracker=RewardTracker(confirm_money=2);tracker.feed([])
  self.assertEqual(tracker.feed(events)['mesos'],7);self.assertEqual(tracker.feed(events)['mesos'],0)
if __name__=='__main__':unittest.main()
