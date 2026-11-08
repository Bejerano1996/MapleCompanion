import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageEnhance
import session_reader as reader
from session_rewards import RewardTracker
class RetryTests(unittest.TestCase):
 def test_recorded_bright_money_recovered_without_trust_or_duplicates(self):
  image=ImageEnhance.Brightness(Image.open(Path(__file__).parent/'session-rewards-fixture.png').convert('RGB')).enhance(1.2)
  events=reader.read_reward_image(image,True)
  self.assertIn(('mesos',7),events)
  index=events.index(('mesos',7));self.assertNotIn(index,events.trusted_money)
  tracker=RewardTracker(confirm_money=2);tracker.feed([])
  first=tracker.feed(events);second=tracker.feed(events);third=tracker.feed(events)
  self.assertEqual(first['mesos']+second['mesos'],sum(v for k,v in events if k=='mesos' and v is not None));self.assertEqual(third['mesos'],0)
  old=RewardTracker(confirm_money=2);baseline=list(events);baseline[index]=('mesos',None);old.feed(baseline)
  self.assertEqual(old.feed(events)['mesos'],0)
 def test_disagreement_low_confidence_wrong_kind_and_multiple_rows_rejected(self):
  image=Image.new('RGB',(300,100));pos=(90,30)
  for answers in [([['You have gained mesos (+7)',.99]],[['You have gained mesos (+8)',.99]]),([['You have gained mesos (+7)',.89]],),([['You received EXP (+7)',.99]],),([],),([['You have gained mesos (+7)',.99],['You have gained mesos (+7)',.99]],)]:
   with self.subTest(answers=answers),patch.object(reader,'_engine',side_effect=[(rows,None) for rows in answers]) as engine:
    self.assertIsNone(reader.retry_money_row(image,pos));self.assertLessEqual(engine.call_count,2)
 def test_agreement_uses_recognition_only(self):
  rows=[['You have gained mesos (+7)',.99]]
  with patch.object(reader,'_engine',return_value=(rows,None)) as engine:
   self.assertEqual(reader.retry_money_row(Image.new('RGB',(300,100)),(90,30)),7)
   self.assertEqual(engine.call_count,2)
   for call in engine.call_args_list:self.assertEqual(call.kwargs,dict(use_det=False,use_cls=False))
 def test_retry_failure_preserves_detector_rows(self):
  with patch.object(reader,'_engine',side_effect=RuntimeError('probe')):
   self.assertIsNone(reader.retry_money_row(Image.new('RGB',(300,100)),(90,30)))
 def test_at_most_one_pending_money_row_and_positions_unchanged(self):
  rows=[([[0,y],[100,y],[100,y+12],[0,y+12]],'You have gained mesos (+?)',.9) for y in (10,30)]
  with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row',return_value=7) as retry:
   events=reader.read_reward_image(Image.new('RGB',(300,100)),True)
   self.assertEqual(list(events),[('mesos',7),('mesos',None)])
   self.assertEqual(len(events.positions),2);self.assertEqual(retry.call_count,1);self.assertFalse(events.trusted_money)
 def test_no_retry_for_normal_or_nonpending_reads(self):
  rows=[([[0,10],[100,10],[100,22],[0,22]],'You have gained mesos (+7)',.99)]
  with patch.object(reader,'ocr_rows',return_value=rows),patch.object(reader,'retry_money_row') as retry:
   self.assertEqual(reader.read_reward_image(Image.new('RGB',(300,100)),True),[('mesos',7)])
   retry.assert_not_called()
if __name__=='__main__' :unittest.main()
